import json
import urllib.error
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select

from receptor import Receptor, device_from_topic, mensagens_mqtt, totens, validate

TOPIC = "sinaliza/totens/totem-ubs/frases"


def payload(**changes) -> bytes:
    message = {"v": 1, "msg_id": "m-1", "dispositivo": "totem-ubs", "local": "UBS", "seq": 1,
               "enviado_em": (datetime.now(timezone.utc) - timedelta(milliseconds=300)).isoformat(),
               "texto": "Bom dia, qual é o seu nome?"}
    message.update(changes)
    return json.dumps(message).encode("utf-8")


class FakeApi:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, text):
        self.calls.append(text)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def engine(tmp_path):
    return create_engine(f"sqlite:///{tmp_path}/r.db")


def rows(engine):
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(select(mensagens_mqtt).order_by(mensagens_mqtt.c.id)).mappings()]


def test_device_comes_from_the_topic():
    assert device_from_topic(TOPIC) == "totem-ubs"
    assert device_from_topic("outro/topico") is None


def test_validate_accepts_a_good_message_and_rejects_bad_ones():
    assert validate(payload(), TOPIC)[1] is None
    assert validate(b"nao e json", TOPIC)[1] == "payload não é JSON UTF-8"
    assert validate(payload(texto="  "), TOPIC)[1] == "sem texto"
    assert validate(payload(msg_id=None), TOPIC)[1] == "sem msg_id"
    assert "500" in validate(payload(texto="a" * 501), TOPIC)[1]


def test_message_is_saved_then_inferred(engine):
    api = FakeApi((200, {"glosses": ["BOM-DIA", "NOME"], "model_version": "sinaliza-t1/1", "latency_ms": 40}))
    receptor = Receptor(engine, api)
    row_id = receptor.on_frase(TOPIC, payload())
    (row,) = rows(engine)
    assert row["status"] == "recebida" and row["dispositivo"] == "totem-ubs" and receptor.queue.get_nowait() == row_id
    assert receptor.process(row_id) == "inferida"
    (row,) = rows(engine)
    assert json.loads(row["glosas"]) == ["BOM-DIA", "NOME"] and row["versao_modelo"] == "sinaliza-t1/1"
    assert row["latencia_api_ms"] == 40 and row["latencia_total_ms"] >= 300 and row["tentativas"] == 1
    assert api.calls == ["Bom dia, qual é o seu nome?"]


def test_duplicate_delivery_is_ignored(engine):
    receptor = Receptor(engine, FakeApi())
    assert receptor.on_frase(TOPIC, payload()) is not None
    assert receptor.on_frase(TOPIC, payload()) is None  # QoS 1 pode entregar duas vezes
    assert len(rows(engine)) == 1 and receptor.queue.qsize() == 1


def test_invalid_message_is_kept_but_not_sent_to_the_api(engine):
    receptor = Receptor(engine, FakeApi())
    receptor.on_frase(TOPIC, b"{quebrado")
    (row,) = rows(engine)
    assert row["status"] == "invalida" and row["erro"] and receptor.queue.empty()


def test_rejected_phrase(engine):
    receptor = Receptor(engine, FakeApi((422, {"detail": "nenhuma palavra do texto tem sinal"})))
    assert receptor.process(receptor.on_frase(TOPIC, payload())) == "rejeitada"
    assert "nenhuma palavra" in rows(engine)[0]["erro"]


def test_api_down_is_retried_and_then_marked_as_error(engine):
    down = urllib.error.URLError("recusada")
    receptor = Receptor(engine, FakeApi(down, down, down), retry_wait=0)
    assert receptor.process(receptor.on_frase(TOPIC, payload())) == "erro"
    (row,) = rows(engine)
    assert row["tentativas"] == 3 and "inacessível" in row["erro"] and row["texto"]


def test_api_recovers_on_the_second_try(engine):
    ok = (200, {"glosses": ["NOME"], "model_version": "lista-fixa", "latency_ms": 5})
    receptor = Receptor(engine, FakeApi((503, {}), ok), retry_wait=0)
    assert receptor.process(receptor.on_frase(TOPIC, payload())) == "inferida"
    assert rows(engine)[0]["tentativas"] == 2


def test_pending_messages_are_found_after_a_crash(engine):
    receptor = Receptor(engine, FakeApi())
    first = receptor.on_frase(TOPIC, payload(msg_id="a"))
    receptor.on_frase(TOPIC, b"lixo")
    assert receptor.pending() == [first]


def test_status_is_inserted_then_updated(engine):
    receptor = Receptor(engine, FakeApi())
    topic = "sinaliza/totens/totem-ubs/status"
    receptor.on_status(topic, json.dumps({"status": "online", "local": "UBS", "em": "2026-11-14T12:00:00+00:00"}).encode())
    receptor.on_status(topic, json.dumps({"status": "offline", "local": "UBS"}).encode())
    receptor.on_status(topic, b"lixo")  # ignorado
    with engine.connect() as conn:
        (row,) = conn.execute(select(totens)).mappings().all()
    assert row["dispositivo"] == "totem-ubs" and row["status"] == "offline"
