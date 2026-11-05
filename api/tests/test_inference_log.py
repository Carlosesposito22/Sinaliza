import json

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pandas")
monitor = pytest.importorskip("textgloss.monitor")

from sqlalchemy import create_engine, select  # noqa: E402

from app.inference_log import InferenceLog, clean_origin  # noqa: E402
from app.text_to_gloss import Match  # noqa: E402

MATCHES = [
    Match("a", None, "function", 0.0, "DESCARTAR", 0.02),
    Match("mãe", "MÃE", "exact", 1.0, "MANTER", 0.95),
    Match("banco", None, "ignored", 0.1, "MANTER", 0.5),
    Match("dor de cabeça", "DOR DE CABEÇA", "exact", 1.0, "MANTER", 0.8),
]


def rows(url):
    with create_engine(url).connect() as conn:
        return list(conn.execute(select(monitor.inferencias)).mappings())


def record(log, origin="web"):
    log.record(text="a mãe banco dor de cabeça", matches=MATCHES, model_version="sinaliza-t1/1",
               used_model=True, latency_ms=42.0, origin=origin)


def test_clean_origin():
    assert clean_origin("Simulador") == "simulador"
    assert clean_origin(None) == clean_origin("com espaço") == clean_origin("x" * 40) == "desconhecida"


def test_without_url_nothing_is_recorded():
    log = InferenceLog(None)
    assert not log.enabled
    record(log)  # não levanta


def test_records_counts_probabilities_and_hides_text_by_default(tmp_path):
    url = f"sqlite:///{tmp_path}/t.db"
    record(InferenceLog(url), origin="web")
    (row,) = rows(url)
    assert row["texto"] is None and row["origem"] == "web"
    assert (row["n_palavras"], row["n_mantidas"], row["n_sem_sinal"]) == (6, 5, 1)
    assert row["prob_incerta"] == 1  # só "banco" (0,5) está entre 0,4 e 0,6
    assert row["versao_modelo"] == "sinaliza-t1/1" and row["usou_modelo"] and row["latencia_ms"] == 42.0
    assert row["prob_media"] == pytest.approx((0.02 + 0.95 + 0.5 + 3 * 0.8) / 6)
    detail = json.loads(row["palavras"])
    assert all("palavra" not in d and "glosa" not in d for d in detail)
    assert detail[0] == {"decisao": "DESCARTAR", "probabilidade": 0.02, "tipo": "function"}
    assert not row["processada"]


def test_simulator_and_opt_in_keep_the_text(tmp_path):
    url = f"sqlite:///{tmp_path}/t.db"
    record(InferenceLog(url), origin="simulador")
    record(InferenceLog(url, log_text=True), origin="web")
    for row in rows(url):
        assert row["texto"] == "a mãe banco dor de cabeça"
        assert json.loads(row["palavras"])[1]["palavra"] == "mãe"


def test_database_failure_does_not_raise(tmp_path):
    log = InferenceLog(f"sqlite:///{tmp_path}/nao/existe/t.db")
    record(log)  # o erro só vai para o log
