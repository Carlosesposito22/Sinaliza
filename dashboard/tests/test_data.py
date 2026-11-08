import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pandas as pd
import pytest
from sqlalchemy import create_engine, insert

import data
from textgloss import monitor

NOW = datetime.now(timezone.utc).replace(minute=5, second=0, microsecond=0)


def words(*items):
    return json.dumps(
        [{k: v for k, v in item.items() if v is not None} for item in items], ensure_ascii=False
    )


def row(em=NOW, versao="sinaliza-t1/1", origem="simulador", texto="O filho está com dor", detalhe=None, latencia=40.0, **extra):
    detalhe = detalhe if detalhe is not None else words(
        {"palavra": "O", "decisao": "DESCARTAR", "probabilidade": 0.02, "tipo": "function"},
        {"palavra": "filho", "glosa": "FILHO", "decisao": "MANTER", "probabilidade": 0.92, "tipo": "exact"},
        {"palavra": "dor", "glosa": "DOR", "decisao": "MANTER", "probabilidade": 0.55, "tipo": "ignored"},
    )
    base = dict(em=em, origem=origem, texto=texto, n_palavras=3, n_mantidas=2, n_sem_sinal=1, prob_media=0.5,
                prob_incerta=1, latencia_ms=latencia, versao_modelo=versao, usou_modelo=True, palavras=detalhe, processada=False)
    return {**base, **extra}


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    monitor.ensure_schema(engine)
    return engine


def fill(engine, *rows):
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), list(rows))


def test_everything_is_empty_when_the_tables_do_not_exist():
    engine = create_engine("sqlite://")
    assert data.load_recent(engine).empty and data.load_hourly(engine).empty
    assert data.totals(engine) == {"frases": 0, "pendentes": 0, "ultima": None, "primeira": None, "consolidado_ate": None}


def test_totals_recent_and_hourly_after_the_monitoring_ran(engine):
    fill(engine, row(), row(em=NOW + timedelta(minutes=10)), row(em=NOW - timedelta(hours=2), versao="sinaliza-t1/2"))
    before = data.totals(engine)
    assert (before["frases"], before["pendentes"], before["consolidado_ate"]) == (3, 3, None)
    monitor.process(engine)
    after = data.totals(engine)
    assert after["pendentes"] == 0 and after["consolidado_ate"] is not None
    assert after["ultima"] >= after["primeira"]
    recent = data.load_recent(engine)
    assert list(recent["id"]) == [3, 2, 1] and recent["em"].dt.tz is not None and recent["processada"].all()
    hourly = data.load_hourly(engine)
    assert set(hourly["versao_modelo"]) == {"sinaliza-t1/1", "sinaliza-t1/2"}


def test_hourly_overall_merges_versions_by_hour(engine):
    fill(engine, row(), row(versao="sinaliza-t1/2", latencia=90.0))
    monitor.process(engine)
    overall = data.hourly_overall(data.load_hourly(engine))
    assert len(overall) == 1
    line = overall.iloc[0]
    assert line["frases"] == 2 and line["palavras"] == 6
    assert line["taxa_manter"] == pytest.approx(2 / 3)
    assert line["latencia_p95_ms"] == pytest.approx(90.0)  # o maior entre as versões
    since = NOW + timedelta(hours=5)
    assert data.hourly_overall(data.load_hourly(engine), since).empty


def test_fill_hours_adds_the_hours_without_frases():
    overall = pd.DataFrame({"hora": pd.to_datetime(["2026-11-05 09:00", "2026-11-05 12:00"], utc=True), "frases": [3, 5], "palavras": [10, 20]})
    since = datetime(2026, 11, 5, 8, 30, tzinfo=timezone.utc)
    filled = data.fill_hours(overall, since, datetime(2026, 11, 5, 13, 10, tzinfo=timezone.utc))
    assert [h.hour for h in filled["hora"]] == [8, 9, 10, 11, 12, 13]
    assert list(filled["frases"]) == [0, 3, 0, 0, 5, 0]
    empty = data.fill_hours(pd.DataFrame(columns=["hora", "frases", "palavras"]), since, datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc))
    assert list(empty["frases"]) == [0, 0, 0]


def test_explode_words_and_privacy_without_text(engine):
    anonymous = row(texto=None, detalhe=words(
        {"decisao": "MANTER", "probabilidade": 0.9, "tipo": "exact"}, {"decisao": "DESCARTAR", "probabilidade": 0.1, "tipo": "function"}))
    fill(engine, row(), anonymous, row(palavras="isto não é json"))
    exploded = data.explode_words(data.load_recent(engine))
    assert len(exploded) == 5  # 3 + 2; a linha com JSON inválido é ignorada
    assert exploded["palavra"].isna().sum() == 2
    table = data.recent_table(data.load_recent(engine))
    assert "(texto não gravado)" in set(table["frase"])
    anonymous_row = table[table["frase"] == "(texto não gravado)"].iloc[0]
    decisions = anonymous_row["decisões (✓ mantém, ✗ descarta, probabilidade)"]
    assert decisions == "✓ 0,90 · ✗ 0,10" and anonymous_row["sequência de sinais"] == "—"


def test_recent_table_shows_decisions_and_the_final_sign_sequence(engine):
    fill(engine, row())
    table = data.recent_table(data.load_recent(engine))
    line = table.iloc[0]
    assert line["frase"] == "O filho está com dor" and line["origem"] == "simulador"
    assert line["decisões (✓ mantém, ✗ descarta, probabilidade)"] == "O ✗ 0,02 · filho ✓ 0,92 · dor ✓ 0,55"
    assert line["sequência de sinais"] == "FILHO DOR" and line["latência (ms)"] == 40


def test_probability_histogram_ignores_the_fixed_list(engine):
    fixed = row(versao="lista-fixa", detalhe=words({"palavra": "a", "decisao": "DESCARTAR", "probabilidade": 0.0, "tipo": "function"}))
    fill(engine, row(), fixed)
    hist = data.probability_histogram(data.explode_words(data.load_recent(engine)))
    assert hist["palavras"].sum() == 3 and len(hist) == 10
    assert hist.loc[hist["inicio"].round(1) == 0.0, "palavras"].iloc[0] == 1  # só o 0,02 do modelo
    assert hist["faixa"].iloc[0] == "0,0–0,1"


def test_unknown_words_and_low_confidence(engine):
    fill(engine, row(), row(), row(texto=None, detalhe=words(
        {"decisao": "MANTER", "probabilidade": 0.5, "tipo": "ignored"})))
    exploded = data.explode_words(data.load_recent(engine))
    unknown = data.unknown_words(exploded)
    assert list(unknown["palavra"]) == ["dor"] and list(unknown["ocorrencias"]) == [2]  # a linha sem texto não conta
    low = data.low_confidence(exploded)
    assert len(low) == 3 and low.iloc[0]["probabilidade"] == 0.5  # a mais perto de 0,5 vem primeiro
    assert data.low_confidence(exploded[exploded["probabilidade"] > 0.9]).empty
    assert data.unknown_words(exploded[exploded["tipo"] == "exact"]).empty


# --- serviços e MLflow, com um servidor HTTP falso ------------------------------------------------------------------

ROUTES: dict = {}


class Handler(BaseHTTPRequestHandler):
    def _reply(self):
        key = self.path.split("?")[0] if self.path.startswith("/api/2.0/mlflow/model-versions") else self.path
        status, body = ROUTES.get(key, (404, {"detail": "não existe"}))
        if self.command == "POST":
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
        payload = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _reply

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    ROUTES.clear()
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_check_api_reports_model_and_readiness(server):
    ROUTES["/health"] = (200, {"status": "ok", "model": "sinaliza-t1/1"})
    ROUTES["/ready"] = (503, {"detail": "carregando o modelo"})
    health, ready = data.check_api(server)
    assert health.ok and "sinaliza-t1/1" in health.detail and health.label == "✔ no ar"
    assert ready.ok is False and ready.detail == "HTTP 503" and ready.label == "✖ fora do ar"
    ROUTES["/ready"] = (200, {"status": "ready"})
    assert data.check_api(server)[1].ok
    assert data.api_model(server) == "sinaliza-t1/1"


def test_check_api_down_does_not_raise():
    down = data.check_api("http://127.0.0.1:9")
    assert down[0].ok is False and down[1].ok is False and "sem resposta" in down[0].detail
    assert data.api_model("http://127.0.0.1:9") is None


def test_check_mlflow_database_and_airflow(server, engine):
    ROUTES["/health"] = (200, "OK")  # o /health do MLflow responde texto puro, não JSON
    assert data.check_mlflow(server).ok
    ROUTES["/health"] = (503, "indisponível")
    assert data.check_mlflow(server).ok is False
    assert data.check_database(engine).ok
    broken = create_engine("sqlite:///nao/existe/x.db")
    assert data.check_database(broken).ok is False
    assert data.check_airflow("").ok is None and data.check_airflow("").label == "– não monitorado"
    ROUTES["/api/v2/monitor/health"] = (200, {"metadatabase": {"status": "healthy"}, "scheduler": {"status": "healthy"}})
    assert data.check_airflow(server).ok
    ROUTES["/api/v2/monitor/health"] = (200, {"metadatabase": {"status": "healthy"}, "scheduler": {"status": "unhealthy"}})
    assert data.check_airflow(server).ok is False


def mlflow_run(name, stage, metrics, start=1):
    return {"info": {"run_name": name, "start_time": start},
            "data": {"tags": [{"key": "modelo", "value": name}, {"key": "etapa", "value": stage}],
                     "metrics": [{"key": k, "value": v} for k, v in metrics.items()]}}


def test_registered_model_reads_the_latest_version_and_its_run(server):
    ROUTES["/api/2.0/mlflow/registered-models/get?name=sinaliza-t1"] = (
        200, {"registered_model": {"latest_versions": [{"version": "1"}, {"version": "3"}]}})
    ROUTES["/api/2.0/mlflow/model-versions/get"] = (200, {"model_version": {"run_id": "abc", "creation_timestamp": 1793669518573}})
    ROUTES["/api/2.0/mlflow/runs/get?run_id=abc"] = (200, {"run": {
        "info": {"run_name": "teste-final"}, "data": {"metrics": [{"key": "teste_f1_macro", "value": 0.885}], "params": []}}})
    model = data.registered_model(server)
    assert model["versao"] == "3" and model["run_name"] == "teste-final"
    assert model["metricas"]["teste_f1_macro"] == pytest.approx(0.885)
    assert model["registrado_em"].tzinfo is not None
    ROUTES["/api/2.0/mlflow/registered-models/get?name=sinaliza-t1"] = (404, {})
    assert data.registered_model(server) is None


def test_training_comparison_keeps_the_latest_run_of_each_model_and_marks_the_fixed_list(server):
    ROUTES["/api/2.0/mlflow/experiments/get-by-name?experiment_name=t1"] = (200, {"experiment": {"experiment_id": "7"}})
    ROUTES["/api/2.0/mlflow/runs/search"] = (200, {"runs": [
        mlflow_run("random-forest-otimizado", "otimizacao", {"f1_macro_val": 0.884}),
        mlflow_run("random-forest-otimizado", "otimizacao", {"f1_macro_val": 0.1}),  # mais antiga: ignorada
        mlflow_run("regressao-logistica", "baseline", {"f1_macro_val": 0.876}),
        mlflow_run("lista-fixa", "baseline", {"val_f1_macro": 0.822}),
        mlflow_run("random-forest-trial", "otimizacao", {"f1_macro_val": 0.99}),  # trial do Optuna: fora
        mlflow_run("cv-regressao-logistica", "validacao", {"f1_macro_val": 0.5}),  # outra etapa: fora
    ]})
    frame = data.training_comparison(server, "t1")
    assert list(frame["modelo"]) == ["random-forest-otimizado", "regressao-logistica", "lista-fixa"]
    assert frame["f1_macro"].iloc[0] == pytest.approx(0.884)
    assert list(frame["ml"]) == [True, True, False]
    assert data.training_comparison(server, "nao-existe").empty
    assert data.training_comparison("http://127.0.0.1:9", "t1").empty


def test_check_services_runs_in_parallel_and_keeps_the_order(server, engine):
    ROUTES["/health"] = (200, {"status": "ok", "model": "sinaliza-t1/1"})
    ROUTES["/ready"] = (200, {"status": "ready"})
    config = data.Config("sqlite://", server, server, server, "", "t1")
    names = [s.name for s in data.check_services(config, engine)]
    assert names == ["API (/health)", "API (/ready)", "Banco de dados (Postgres)", "MLflow", "Airflow"]


def test_config_reads_the_environment(monkeypatch):
    monkeypatch.setenv("SINALIZA_API_URL", "http://api:8000")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    config = data.Config.from_env()
    assert config.api_url == "http://api:8000" and config.mlflow_url == "http://mlflow:5000"
    assert config.airflow_url == "" and config.experiment == "t1-manter-descartar"
