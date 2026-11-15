"""Receptor MQTT: recebe as frases dos totens, grava no Postgres e pede a inferência ao modelo pela API.

ETAPA: aquisição e integração (sem ML próprio). O ML (classificador T1) roda na API; aqui só se recebe,
persiste e encaminha. Fluxo de cada mensagem:

    totem ──MQTT──► broker ──► receptor ──► Postgres `mensagens_mqtt` (status "recebida")
                                        └─► API /translate (X-Origem: totem) ──► modelo T1 ──► `inferencias`
                                        └─► `mensagens_mqtt` atualizada (glosas, versão do modelo, latências)

Garantias:
- **Persistência antes da inferência:** a mensagem é gravada assim que chega; se a API cair, ela fica com
  status "erro" e o texto não se perde.
- **Sem duplicatas:** QoS 1 entrega "pelo menos uma vez"; `msg_id` é único na tabela e a repetição é ignorada.
- **O callback do MQTT não espera a API:** ele só grava e põe a mensagem numa fila; uma thread separada chama a
  API (com até 3 tentativas). Assim o receptor não perde mensagens enquanto a API responde.
- Mensagem malformada é gravada com status "invalida" (para aparecer no painel), sem derrubar o receptor.

PRIVACIDADE: o totem é simulado e só envia frases públicas de `data/phrases.json`, por isso o texto é gravado.
Num totem real, o texto digitado pode ter dado pessoal: gravar só com consentimento e apagar após a retenção,
como a API já faz para a origem `web` (ver `api/app/inference_log.py`).

Uso: python receptor/receptor.py   (variáveis MQTT_HOST, MQTT_PORT, SINALIZA_DATABASE_URL, SINALIZA_API_URL)
"""
from __future__ import annotations

import json
import logging
import os
import queue
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Float, Integer, MetaData, String, Table, Text, create_engine, func, insert, select, update,
)
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("sinaliza.receptor")

TOPIC_FRASES = "sinaliza/totens/+/frases"
TOPIC_STATUS = "sinaliza/totens/+/status"
ORIGIN = "totem"
MAX_TEXT = 500
RETRIES = 3
READY_FILE = os.environ.get("RECEPTOR_READY_FILE", "/tmp/receptor-pronto")

metadata = MetaData()

# Uma linha por mensagem recebida do broker.
mensagens_mqtt = Table(
    "mensagens_mqtt", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("msg_id", String(64), unique=True),
    Column("dispositivo", String(64)),
    Column("local", String(120)),
    Column("topico", String(200), nullable=False),
    Column("seq", Integer),
    Column("enviada_em", DateTime(timezone=True)),
    Column("recebida_em", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("texto", Text),
    # recebida → inferida | rejeitada (a API respondeu 422: nenhuma palavra com sinal) | erro | invalida
    Column("status", String(16), nullable=False),
    Column("glosas", Text),
    Column("versao_modelo", String(64)),
    Column("latencia_api_ms", Float),
    Column("latencia_total_ms", Float),
    Column("processada_em", DateTime(timezone=True)),
    Column("tentativas", Integer, nullable=False, default=0, server_default="0"),
    Column("erro", Text),
)

# Último estado conhecido de cada totem (vem do tópico de status, inclusive do "offline" do testamento).
totens = Table(
    "totens", metadata,
    Column("dispositivo", String(64), primary_key=True),
    Column("status", String(16), nullable=False),
    Column("local", String(120)),
    Column("atualizado_em", DateTime(timezone=True), nullable=False),
)


def ensure_schema(engine) -> None:
    metadata.create_all(engine)


def device_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    return parts[2] if len(parts) == 4 and parts[0] == "sinaliza" and parts[1] == "totens" else None


def parse_time(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def validate(payload: bytes, topic: str) -> tuple[dict | None, str | None]:
    """Devolve (mensagem normalizada, None) ou (o que deu para extrair, motivo da rejeição)."""
    device = device_from_topic(topic)
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"dispositivo": device}, "payload não é JSON UTF-8"
    if not isinstance(data, dict):
        return {"dispositivo": device}, "payload não é um objeto JSON"
    text = data.get("texto")
    message = {
        "msg_id": str(data["msg_id"])[:64] if data.get("msg_id") else None,
        "dispositivo": device or str(data.get("dispositivo", ""))[:64] or None,
        "local": str(data.get("local", ""))[:120] or None,
        "seq": data.get("seq") if isinstance(data.get("seq"), int) else None,
        "enviada_em": parse_time(data.get("enviado_em")),
        "texto": text[:MAX_TEXT] if isinstance(text, str) else None,
    }
    if not message["msg_id"]:
        return message, "sem msg_id"
    if not isinstance(text, str) or not text.strip():
        return message, "sem texto"
    if len(text) > MAX_TEXT:
        return message, f"texto com mais de {MAX_TEXT} caracteres"
    return message, None


def call_api(api_url: str, text: str, timeout: float = 30.0) -> tuple[int, dict]:
    """POST /translate. Devolve (status HTTP, corpo). Erros de rede viram exceção."""
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/translate",
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Origem": ORIGIN},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read())
        except (json.JSONDecodeError, ValueError):
            body = {}
        return error.code, body


class Receptor:
    """Lógica sem MQTT (testável): gravar, enfileirar e processar."""

    def __init__(self, engine, api: Callable[[str], tuple[int, dict]], retry_wait: float = 2.0):
        self.engine = engine
        self.api = api
        self.retry_wait = retry_wait
        self.queue: queue.Queue[int] = queue.Queue()
        ensure_schema(engine)

    # --- chegada (thread do MQTT) -----------------------------------------------------------------------------------

    def on_frase(self, topic: str, payload: bytes) -> int | None:
        """Grava a mensagem e a põe na fila. Devolve o id da linha, ou None se for repetida."""
        message, problem = validate(payload, topic)
        row = {
            "msg_id": message.get("msg_id"), "dispositivo": message.get("dispositivo"), "local": message.get("local"),
            "topico": topic, "seq": message.get("seq"), "enviada_em": message.get("enviada_em"),
            "texto": message.get("texto"), "status": "invalida" if problem else "recebida", "erro": problem,
        }
        try:
            with self.engine.begin() as conn:
                row_id = conn.execute(insert(mensagens_mqtt).values(**row)).inserted_primary_key[0]
        except IntegrityError:
            logger.info("mensagem repetida ignorada (msg_id=%s)", row["msg_id"])
            return None
        if problem:
            logger.warning("mensagem inválida de %s: %s", topic, problem)
        else:
            self.queue.put(row_id)
        return row_id

    def on_status(self, topic: str, payload: bytes) -> None:
        device = device_from_topic(topic)
        try:
            data = json.loads(payload.decode("utf-8"))
            status = str(data["status"])[:16]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
            logger.warning("status inválido em %s", topic)
            return
        if not device:
            return
        values = {"status": status, "local": str(data.get("local", ""))[:120] or None,
                  "atualizado_em": parse_time(data.get("em")) or datetime.now(timezone.utc)}
        with self.engine.begin() as conn:
            changed = conn.execute(update(totens).where(totens.c.dispositivo == device).values(**values)).rowcount
            if not changed:
                conn.execute(insert(totens).values(dispositivo=device, **values))

    # --- processamento (thread de trabalho) -------------------------------------------------------------------------

    def process(self, row_id: int) -> str:
        """Pede a inferência à API e atualiza a linha. Devolve o status final."""
        with self.engine.connect() as conn:
            row = conn.execute(select(mensagens_mqtt).where(mensagens_mqtt.c.id == row_id)).mappings().one()
        values: dict = {}
        for attempt in range(1, RETRIES + 1):
            started = time.perf_counter()
            try:
                code, body = self.api(row["texto"])
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                values = {"status": "erro", "erro": f"API inacessível: {error}", "tentativas": attempt}
                if attempt < RETRIES:
                    time.sleep(self.retry_wait * attempt)
                continue
            elapsed = (time.perf_counter() - started) * 1000
            if code == 200:
                values = {"status": "inferida", "glosas": json.dumps(body.get("glosses", []), ensure_ascii=False),
                          "versao_modelo": body.get("model_version"), "latencia_api_ms": body.get("latency_ms", elapsed),
                          "erro": None, "tentativas": attempt}
            elif code == 422:
                values = {"status": "rejeitada", "erro": str(body.get("detail", "sem palavras com sinal"))[:300], "tentativas": attempt}
            else:
                values = {"status": "erro", "erro": f"API respondeu HTTP {code}", "tentativas": attempt}
                if code >= 500 and attempt < RETRIES:
                    time.sleep(self.retry_wait * attempt)
                    continue
            break
        now = datetime.now(timezone.utc)
        values["processada_em"] = now
        if row["enviada_em"] is not None:
            sent = row["enviada_em"] if row["enviada_em"].tzinfo else row["enviada_em"].replace(tzinfo=timezone.utc)
            values["latencia_total_ms"] = max((now - sent).total_seconds() * 1000, 0.0)
        with self.engine.begin() as conn:
            conn.execute(update(mensagens_mqtt).where(mensagens_mqtt.c.id == row_id).values(**values))
        return values["status"]

    def pending(self) -> list[int]:
        """Mensagens gravadas mas não processadas (o receptor caiu no meio): reprocessadas na partida."""
        with self.engine.connect() as conn:
            return list(conn.execute(select(mensagens_mqtt.c.id).where(mensagens_mqtt.c.status == "recebida").order_by(mensagens_mqtt.c.id)).scalars())

    def worker(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                row_id = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                status = self.process(row_id)
                logger.info("mensagem %s: %s", row_id, status)
            except Exception:
                logger.exception("falha ao processar a mensagem %s", row_id)
            finally:
                self.queue.task_done()


def main() -> int:
    import paho.mqtt.client as mqtt

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    host, port = os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "1883"))
    database_url = os.environ.get("SINALIZA_DATABASE_URL", "postgresql+psycopg://sinaliza:sinaliza@localhost:5432/sinaliza")
    api_url = os.environ.get("SINALIZA_API_URL", "http://localhost:8000")

    try:
        os.remove(READY_FILE)  # um "pronto" de uma execução anterior não vale
    except OSError:
        pass
    receptor = Receptor(create_engine(database_url, pool_pre_ping=True), lambda text: call_api(api_url, text))
    for row_id in receptor.pending():
        receptor.queue.put(row_id)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("broker recusou a conexão: %s", reason_code)
            return
        client.subscribe([(TOPIC_FRASES, 1), (TOPIC_STATUS, 1)])
        # Sinal para o healthcheck do Docker: os totens só começam depois de o receptor assinar.
        try:
            with open(READY_FILE, "w", encoding="utf-8") as ready:
                ready.write(datetime.now(timezone.utc).isoformat())
        except OSError:
            pass
        logger.info("conectado em %s:%s; assinando %s e %s", host, port, TOPIC_FRASES, TOPIC_STATUS)

    def on_message(client, userdata, msg):
        try:
            if msg.topic.endswith("/frases"):
                receptor.on_frase(msg.topic, msg.payload)
            elif msg.topic.endswith("/status"):
                receptor.on_status(msg.topic, msg.payload)
        except Exception:
            logger.exception("falha ao gravar a mensagem de %s", msg.topic)

    # Sessão persistente (clean_session=False + client_id fixo): mensagens QoS 1 publicadas enquanto o receptor
    # está fora ficam guardadas no broker e chegam quando ele volta.
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sinaliza-receptor", clean_session=False)
    client.on_connect, client.on_message = on_connect, on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    threading.Thread(target=receptor.worker, args=(stop,), daemon=True).start()
    while not stop.is_set():
        try:
            client.connect(host, port, keepalive=30)
            break
        except OSError as error:
            logger.warning("broker inacessível (%s); nova tentativa em 2 s", error)
            stop.wait(2)
    client.loop_start()
    stop.wait()
    client.loop_stop()
    client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
