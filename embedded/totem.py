"""Totem de atendimento simulado: o "sistema embarcado" do Sinaliza.

ETAPA: aquisição de dados (sem ML). Imita um totem instalado num balcão de atendimento (posto de saúde,
INSS, prefeitura) onde o atendente digita a frase que quer mostrar em sinais para a pessoa surda. O totem
publica cada frase no broker MQTT; quem recebe, grava e pede a inferência ao modelo é o `receptor/`.

Contrato das mensagens (JSON, UTF-8):

- `sinaliza/totens/<dispositivo>/frases` (QoS 1, sem retenção): uma frase digitada.
  `{"v": 1, "msg_id": "<uuid>", "dispositivo": "totem-01", "local": "...", "seq": 7,
    "enviado_em": "2026-11-14T12:00:00+00:00", "texto": "..."}`
  `seq` cresce de 1 em 1 por dispositivo; buracos na sequência indicam mensagem perdida.
- `sinaliza/totens/<dispositivo>/status` (QoS 1, retida): `{"dispositivo", "status": "online"|"offline",
  "local", "em"}`. O "offline" é o testamento (*last will*) do cliente: o broker publica sozinho se o totem
  cair sem se despedir.

As frases vêm de `data/phrases.json` (frases públicas de atendimento, as mesmas do simulador de uso), por
isso o texto pode ser gravado. Um totem real mandaria texto digitado por pessoas: ver a nota de privacidade
em `receptor/receptor.py`.

Uso:
    python embedded/totem.py --host localhost --n 10 --intervalo 2
    (no Docker, o serviço `totem` roda sem parar, com os valores das variáveis TOTEM_*)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import signal
import socket
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TOPIC_ROOT = "sinaliza/totens"
SCHEMA_VERSION = 1


def topic_frases(device: str) -> str:
    return f"{TOPIC_ROOT}/{device}/frases"


def topic_status(device: str) -> str:
    return f"{TOPIC_ROOT}/{device}/status"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def load_phrases(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    phrases = [p["text"] for category in data["categories"] for p in category["phrases"]]
    if not phrases:
        raise ValueError(f"nenhuma frase em {path}")
    return phrases


def build_message(device: str, location: str, seq: int, text: str) -> dict:
    return {
        "v": SCHEMA_VERSION,
        "msg_id": str(uuid.uuid4()),
        "dispositivo": device,
        "local": location,
        "seq": seq,
        "enviado_em": now_iso(),
        "texto": text,
    }


def status_message(device: str, location: str, status: str) -> dict:
    return {"dispositivo": device, "status": status, "local": location, "em": now_iso()}


class Totem:
    """Um dispositivo: conecta no broker, anuncia "online" e publica frases."""

    def __init__(self, host: str, port: int, device: str, location: str, phrases: list[str], seed: int | None = None):
        import paho.mqtt.client as mqtt

        self.device, self.location, self.phrases = device, location, phrases
        self.rng = random.Random(seed)
        self.seq = 0
        self.connected = threading.Event()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{device}-{uuid.uuid4().hex[:6]}")
        self.client.will_set(topic_status(device), json.dumps(status_message(device, location, "offline")), qos=1, retain=True)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = lambda *args: self.connected.clear()
        self.host, self.port = host, port

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            print(f"[{self.device}] broker recusou a conexão: {reason_code}", flush=True)
            return
        client.publish(topic_status(self.device), json.dumps(status_message(self.device, self.location, "online")), qos=1, retain=True)
        self.connected.set()
        print(f"[{self.device}] conectado em {self.host}:{self.port}", flush=True)

    def start(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.client.connect(self.host, self.port, keepalive=30)
                break
            except OSError as error:
                if time.monotonic() > deadline:
                    raise ConnectionError(f"broker {self.host}:{self.port} inacessível: {error}") from error
                time.sleep(2)
        self.client.loop_start()
        if not self.connected.wait(timeout):
            raise ConnectionError(f"sem confirmação de conexão do broker {self.host}:{self.port}")

    def publish(self, text: str | None = None) -> dict:
        self.seq += 1
        message = build_message(self.device, self.location, self.seq, text or self.rng.choice(self.phrases))
        info = self.client.publish(topic_frases(self.device), json.dumps(message, ensure_ascii=False), qos=1)
        info.wait_for_publish(timeout=30)
        return message

    def stop(self) -> None:
        # Despedida limpa: publica "offline" (o testamento só vale para queda sem aviso).
        self.client.publish(topic_status(self.device), json.dumps(status_message(self.device, self.location, "offline")), qos=1, retain=True).wait_for_publish(timeout=5)
        self.client.loop_stop()
        self.client.disconnect()


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Totem de atendimento simulado que publica frases via MQTT.")
    parser.add_argument("--host", default=os.environ.get("MQTT_HOST", "localhost"))
    parser.add_argument("--porta", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    parser.add_argument("--dispositivo", default=os.environ.get("TOTEM_ID") or f"totem-{socket.gethostname()[:12]}")
    parser.add_argument("--local", default=os.environ.get("TOTEM_LOCAL", "balcão de atendimento (simulado)"))
    parser.add_argument("--n", type=int, default=int(os.environ.get("TOTEM_N", "0")), help="quantas frases (0 = sem parar)")
    parser.add_argument("--intervalo", type=float, default=float(os.environ.get("TOTEM_INTERVALO", "20")),
                        help="segundos médios entre frases (varia ±50%%, como um atendimento real)")
    parser.add_argument("--frases", type=Path, default=Path(os.environ.get("TOTEM_FRASES", root / "data" / "phrases.json")))
    parser.add_argument("--semente", type=int, default=None)
    args = parser.parse_args(argv)

    totem = Totem(args.host, args.porta, args.dispositivo, args.local, load_phrases(args.frases), args.semente)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    totem.start()
    try:
        while not stop.is_set() and (args.n == 0 or totem.seq < args.n):
            message = totem.publish()
            print(f"[{totem.device}] #{message['seq']} {message['texto'][:70]}", flush=True)
            if args.n == 0 or totem.seq < args.n:
                stop.wait(args.intervalo * totem.rng.uniform(0.5, 1.5))
    finally:
        totem.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
