import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from sqlalchemy import create_engine, insert

from textgloss import demo, monitor

ROUTES: dict = {}
POSTED: list = []


class Handler(BaseHTTPRequestHandler):
    def _reply(self):
        if self.command == "POST":
            POSTED.append((self.path, json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")))
        status, body = ROUTES.get((self.command, self.path), ROUTES.get(self.path, (404, {"detail": "não existe"})))
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
    POSTED.clear()
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def stack(server, tmp_path, modelo="sinaliza-t1/1"):
    """Um 'sistema' falso inteiro atrás de um só servidor HTTP e de um SQLite."""
    banco = f"sqlite:///{tmp_path}/demo.db"
    monitor.ensure_schema(create_engine(banco))
    ROUTES["/health"] = (200, {"status": "ok", "model": modelo})
    ROUTES["/ready"] = (200, {"status": "ready"})
    ROUTES["/_stcore/health"] = (200, "ok")
    ROUTES["/api/v2/monitor/health"] = (200, {"scheduler": {"status": "healthy"}})
    ROUTES["/api/2.0/mlflow/registered-models/get?name=sinaliza-t1"] = (200, {"registered_model": {"latest_versions": [{"version": "2"}]}})
    ROUTES["/api/2.0/mlflow/model-versions/get?name=sinaliza-t1&version=2"] = (200, {"model_version": {"run_id": "r"}})
    ROUTES["/api/2.0/mlflow/runs/get?run_id=r"] = (200, {"run": {"data": {"metrics": [
        {"key": "teste_f1_macro", "value": 0.885}, {"key": "teste_lista_fixa_f1_macro", "value": 0.823}]}}})
    ROUTES[("POST", "/translate")] = (200, {
        "glosses": ["FILHO"], "model_version": modelo, "latency_ms": 7,
        "matches": [{"word": "filho", "decision": "MANTER", "probability": 0.92, "kind": "exact", "gloss": "FILHO"},
                    {"word": "o", "decision": "DESCARTAR", "probability": 0.02, "kind": "function", "gloss": None}]})
    return demo.Alvos(api=server, mlflow=server, airflow=server, painel=server, banco=banco)


def lines():
    saida = []
    return saida, saida.append


def test_servicos_ok_when_everything_answers(server, tmp_path):
    saida, out = lines()
    resultado = demo.servicos(stack(server, tmp_path), out)
    assert resultado.ok and "todos respondem" in resultado.detalhe
    assert "modelo em uso: sinaliza-t1/1" in saida[0] and "banco ok" in saida[0]


def test_servicos_fails_when_the_api_runs_without_the_model(server, tmp_path):
    resultado = demo.servicos(stack(server, tmp_path, modelo="lista-fixa"), lines()[1])
    assert not resultado.ok and "sem o modelo" in resultado.detalhe


def test_servicos_reports_what_is_down(server, tmp_path):
    alvos = stack(server, tmp_path)
    resultado = demo.servicos(demo.Alvos(api=alvos.api, mlflow="http://127.0.0.1:9", airflow=alvos.airflow, painel=alvos.painel, banco=alvos.banco), lines()[1])
    assert not resultado.ok and "MLflow sem resposta" in resultado.detalhe


def test_modelo_checks_that_the_registered_version_is_the_one_in_use(server, tmp_path):
    ok = demo.modelo(stack(server, tmp_path, modelo="sinaliza-t1/2"), lines()[1])
    assert ok.ok and "v2" in ok.detalhe
    outra = demo.modelo(stack(server, tmp_path, modelo="sinaliza-t1/1"), lines()[1])
    assert not outra.ok and "registrado v2" in outra.detalhe


def test_inferencia_shows_each_word_decision_and_requires_the_model(server, tmp_path):
    saida, out = lines()
    resultado = demo.inferencia(stack(server, tmp_path), out)
    assert resultado.ok
    texto = "\n".join(saida)
    assert "MANTER" in texto and "DESCARTAR" in texto and "p=0.92" in texto and "sinaliza-t1/1" in texto
    assert not demo.inferencia(stack(server, tmp_path, modelo="lista-fixa"), lines()[1]).ok


def test_consolidar_falls_back_to_the_monitor_module_when_airflow_is_down(server, tmp_path):
    alvos = stack(server, tmp_path)
    engine = create_engine(alvos.banco)
    agora = datetime.now(timezone.utc)
    linha = dict(em=agora, texto=None, n_palavras=4, n_mantidas=2, n_sem_sinal=1, prob_media=0.7, prob_incerta=0,
                 latencia_ms=40.0, versao_modelo="sinaliza-t1/1", usou_modelo=True, palavras="[]", processada=False)
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [linha, linha])
    sem_airflow = demo.Alvos(alvos.api, alvos.mlflow, "http://127.0.0.1:9", alvos.painel, alvos.banco)
    saida, out = lines()
    resultado = demo.consolidar(sem_airflow, out, esperar=5)
    assert resultado.ok and "2 -> 0" in resultado.detalhe and "direto" in resultado.detalhe
    final = demo.indicadores(alvos, out)
    assert final.ok and any("sinaliza-t1/1: 2 frases" in linha for linha in saida)


def test_consolidar_triggers_the_dag_through_the_airflow_api(server, tmp_path):
    alvos = stack(server, tmp_path)
    ROUTES[("POST", "/auth/token")] = (200, {"access_token": "abc"})
    ROUTES[("POST", "/api/v2/dags/monitoramento/dagRuns")] = (200, {"state": "queued"})
    resultado = demo.consolidar(alvos, lines()[1], esperar=3)  # nada pendente: termina na hora
    assert resultado.ok and "DAG monitoramento no Airflow" in resultado.detalhe
    assert ("/api/v2/dags/monitoramento/dagRuns", {"logical_date": None}) in POSTED


def test_indicadores_fails_without_consolidated_rows(server, tmp_path):
    assert not demo.indicadores(stack(server, tmp_path), lines()[1]).ok


def test_painel_checks_the_streamlit_health(server, tmp_path):
    assert demo.painel(stack(server, tmp_path), lines()[1]).ok
    assert not demo.painel(demo.Alvos(painel="http://127.0.0.1:9"), lines()[1]).ok


def test_every_step_has_a_title_a_message_and_a_function():
    assert len(demo.ETAPAS) == 7
    assert all(titulo and ideia and callable(funcao) for titulo, ideia, funcao in demo.ETAPAS)
