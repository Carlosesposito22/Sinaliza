import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from totem import build_message, load_phrases, status_message, topic_frases, topic_status

ROOT = Path(__file__).resolve().parents[2]


def test_topics_follow_the_contract():
    assert topic_frases("totem-ubs") == "sinaliza/totens/totem-ubs/frases"
    assert topic_status("totem-ubs") == "sinaliza/totens/totem-ubs/status"


def test_message_has_every_field_of_the_contract():
    message = build_message("totem-ubs", "UBS Centro", 7, "Bom dia, qual é o seu nome?")
    assert set(message) == {"v", "msg_id", "dispositivo", "local", "seq", "enviado_em", "texto"}
    assert message["v"] == 1 and message["seq"] == 7 and message["dispositivo"] == "totem-ubs"
    uuid.UUID(message["msg_id"])
    assert datetime.fromisoformat(message["enviado_em"]).tzinfo is not None
    json.dumps(message, ensure_ascii=False)


def test_each_message_gets_a_new_id():
    ids = {build_message("t", "l", i, "x")["msg_id"] for i in range(50)}
    assert len(ids) == 50


def test_status_message():
    assert status_message("totem-ubs", "UBS", "offline")["status"] == "offline"


def test_loads_the_public_phrases_of_the_repository():
    phrases = load_phrases(ROOT / "data" / "phrases.json")
    assert len(phrases) > 10 and all(isinstance(p, str) and p for p in phrases)


def test_rejects_an_empty_phrase_file(tmp_path):
    path = tmp_path / "vazio.json"
    path.write_text(json.dumps({"categories": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_phrases(path)
