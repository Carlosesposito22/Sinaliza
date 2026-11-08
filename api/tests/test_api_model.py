"""`POST /translate` com o classificador T1 (falso) e sem ele: campos do contrato, plano B e gravação."""
import re

import pytest
from fastapi.testclient import TestClient

from app import main
from app.generator import StubGenerator
from app.main import app

client = TestClient(app)


class FakeVerdict:
    def __init__(self, start, end, probability):
        self.start, self.end, self.probability = start, end, probability

    @property
    def keep(self):
        return self.probability >= 0.5


class FakeClassifier:
    version = "sinaliza-t1/1"

    def __init__(self, probabilities, fail=False):
        self.probabilities, self.fail = probabilities, fail

    def decide(self, text):
        if self.fail:
            raise RuntimeError("modelo quebrou")
        return [FakeVerdict(m.start(), m.end(), self.probabilities.get(m.group().lower(), 0.9))
                for m in re.finditer(r"\w+", text)]


class FakeProvider:
    enabled = True

    def __init__(self, classifier, settled=False):
        self.classifier = classifier
        self.settled = settled

    def get(self):
        return self.classifier


class RecordingLog:
    def __init__(self):
        self.calls = []

    def record(self, **kwargs):
        self.calls.append(kwargs)


@pytest.fixture(autouse=True)
def stub_generator(monkeypatch):
    monkeypatch.setattr(main, "generator", StubGenerator())


@pytest.fixture
def log(monkeypatch):
    recorder = RecordingLog()
    monkeypatch.setattr(main, "inference_log", recorder)
    return recorder


def use_model(monkeypatch, classifier):
    monkeypatch.setattr(main, "model_provider", FakeProvider(classifier))


def test_with_model_the_response_has_decisions_version_and_latency(monkeypatch, log):
    use_model(monkeypatch, FakeClassifier({"o": 0.02, "está": 0.01, "com": 0.03}))
    body = client.post("/translate", json={"text": "O filho está com dor de cabeça."}).json()
    assert body["model_version"] == "sinaliza-t1/1"
    assert isinstance(body["latency_ms"], int) and body["latency_ms"] >= 0
    assert body["glosses"] == ["FILHO", "DOR DE CABEÇA"]
    by_word = {m["word"]: m for m in body["matches"]}
    assert (by_word["O"]["decision"], by_word["O"]["probability"]) == ("DESCARTAR", 0.02)
    assert (by_word["filho"]["decision"], by_word["filho"]["probability"]) == ("MANTER", 0.9)
    assert by_word["dor de cabeça"]["decision"] == "MANTER"


def test_model_discard_removes_a_known_word_from_the_glosses(monkeypatch, log):
    use_model(monkeypatch, FakeClassifier({"escola": 0.1}))
    body = client.post("/translate", json={"text": "mãe escola hospital"}).json()
    assert body["glosses"] == ["MÃE", "HOSPITAL"]


def test_without_model_falls_back_to_the_fixed_list(monkeypatch, log):
    use_model(monkeypatch, None)
    body = client.post("/translate", json={"text": "O filho está com dor de cabeça."}).json()
    assert body["model_version"] == "lista-fixa"
    assert body["glosses"] == ["FILHO", "DOR DE CABEÇA"]
    assert all(m["probability"] in (0.0, 1.0) for m in body["matches"])
    assert log.calls[0]["used_model"] is False and log.calls[0]["model_version"] == "lista-fixa"


def test_classifier_failure_falls_back_for_that_request(monkeypatch, log):
    use_model(monkeypatch, FakeClassifier({}, fail=True))
    response = client.post("/translate", json={"text": "mãe e pai"})
    assert response.status_code == 200
    assert response.json()["model_version"] == "lista-fixa"


def test_records_the_inference_with_the_cleaned_origin(monkeypatch, log):
    use_model(monkeypatch, FakeClassifier({}))
    client.post("/translate", json={"text": "mãe e pai"}, headers={"X-Origem": "Simulador"})
    client.post("/translate", json={"text": "mãe e pai"}, headers={"X-Origem": "<script>"})
    client.post("/translate", json={"text": "mãe e pai"})
    assert [c["origin"] for c in log.calls] == ["simulador", "desconhecida", "desconhecida"]
    call = log.calls[0]
    assert call["text"] == "mãe e pai" and call["used_model"] is True and call["model_version"] == "sinaliza-t1/1"
    assert [m.word for m in call["matches"]] == ["mãe", "e", "pai"]


def test_errors_are_not_recorded(monkeypatch, log):
    use_model(monkeypatch, None)
    assert client.post("/translate", json={"text": "   "}).status_code == 422
    assert client.post("/translate", json={"text": "xyzzy qwrty"}).status_code == 422
    assert log.calls == []


def test_health_reports_the_model_in_use(monkeypatch):
    use_model(monkeypatch, FakeClassifier({}))
    assert client.get("/health").json()["model"] == "sinaliza-t1/1"
    use_model(monkeypatch, None)
    assert client.get("/health").json()["model"] == "lista-fixa (carregando o modelo)"
    monkeypatch.setattr(main, "model_provider", FakeProvider(None, settled=True))
    assert client.get("/health").json()["model"] == "lista-fixa (modelo indisponível)"


def test_ready_waits_for_the_first_load_attempt(monkeypatch):
    monkeypatch.setattr(main, "model_provider", FakeProvider(None, settled=False))
    response = client.get("/ready")
    assert response.status_code == 503 and "carregando" in response.json()["detail"]
    monkeypatch.setattr(main, "model_provider", FakeProvider(None, settled=True))
    assert client.get("/ready").status_code == 200
    monkeypatch.setattr(main, "model_provider", FakeProvider(FakeClassifier({}), settled=True))
    assert client.get("/ready").json() == {"status": "ready"}
