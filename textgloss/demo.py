"""Demonstração ponta a ponta do Sinaliza, em um comando, narrando o que cada etapa prova e onde está o ML.

ETAPA: demonstração (sem ML novo). Percorre o mesmo fluxo da apresentação: serviços de pé → modelo registrado no
MLflow → inferência palavra por palavra na API → simulador de uso → consolidação pelo DAG `monitoramento` →
indicadores no banco → painel. Sai com código 0 só se todas as etapas passarem.

Uso: python -m textgloss.demo [--n 20] [--api URL] [--mlflow URL] [--airflow URL] [--painel URL] [--banco URL]
Roteiro falado e o que mostrar em cada passo: references/30-roteiro-da-demonstracao.md
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import config, simulador

FRASES_EXEMPLO = [
    "O filho está com dor de cabeça.",
    "A mãe vai ao hospital hoje.",
    "A criança aprende matemática na escola.",
]


@dataclass(frozen=True)
class Alvos:
    api: str = "http://localhost:8000"
    mlflow: str = "http://localhost:5000"
    airflow: str = "http://localhost:8080"
    painel: str = "http://localhost:8501"
    banco: str = config.DATABASE_URL


@dataclass
class Resultado:
    nome: str
    ok: bool
    detalhe: str
    segundos: float = 0.0


def _get(url: str, timeout: float = 5.0, data: dict | None = None) -> tuple[int, str]:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"} if payload else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read().decode("utf-8")


def _json(url: str, timeout: float = 5.0, data: dict | None = None) -> dict:
    return json.loads(_get(url, timeout, data)[1] or "{}")


def _engine(banco: str):
    from sqlalchemy import create_engine

    return create_engine(banco)


# --- etapas --------------------------------------------------------------------------------------------------------


def servicos(alvos: Alvos, out) -> Resultado:
    """1. Tudo de pé: API (e se o modelo carregou), MLflow, Airflow, painel e banco."""
    estados, falhas = [], []
    try:
        health = _json(f"{alvos.api}/health")
        _get(f"{alvos.api}/ready")
        estados.append(f"API ok (modelo em uso: {health.get('model')})")
        if not str(health.get("model", "")).startswith("sinaliza-t1"):
            falhas.append("a API está sem o modelo (lista fixa)")
    except (urllib.error.URLError, OSError, ValueError) as error:
        falhas.append(f"API sem resposta ({type(error).__name__})")
    for nome, url in (("MLflow", f"{alvos.mlflow}/health"), ("painel", f"{alvos.painel}/_stcore/health"),
                      ("Airflow", f"{alvos.airflow}/api/v2/monitor/health")):
        try:
            _get(url)
            estados.append(f"{nome} ok")
        except (urllib.error.URLError, OSError, ValueError) as error:
            falhas.append(f"{nome} sem resposta ({type(error).__name__})")
    try:
        with _engine(alvos.banco).connect() as conn:
            from sqlalchemy import text

            conn.execute(text("SELECT 1"))
        estados.append("banco ok")
    except Exception as error:
        falhas.append(f"banco sem resposta ({type(error).__name__})")
    out("  " + "; ".join(estados))
    return Resultado("serviços de pé", not falhas, "; ".join(falhas) or "todos respondem")


def modelo(alvos: Alvos, out) -> Resultado:
    """2. O modelo treinado por nós está registrado no MLflow e é o que a API usa."""
    base = f"{alvos.mlflow}/api/2.0/mlflow"
    try:
        registrado = _json(f"{base}/registered-models/get?name=sinaliza-t1")["registered_model"]
        versao = max(int(v["version"]) for v in registrado["latest_versions"])
        info = _json(f"{base}/model-versions/get?name=sinaliza-t1&version={versao}")["model_version"]
        run = _json(f"{base}/runs/get?run_id={info['run_id']}")["run"]
        metricas = {m["key"]: m["value"] for m in run["data"]["metrics"]}
        usando = _json(f"{alvos.api}/health").get("model")
    except (urllib.error.URLError, OSError, KeyError, ValueError) as error:
        return Resultado("modelo registrado", False, f"não consegui ler o MLflow ({type(error).__name__})")
    out(f"  sinaliza-t1 versão {versao}: F1-macro no teste final {metricas.get('teste_f1_macro', float('nan')):.3f}"
        f" (lista fixa, sem ML: {metricas.get('teste_lista_fixa_f1_macro', float('nan')):.3f}); a API usa {usando}")
    coincide = usando == f"sinaliza-t1/{versao}"
    return Resultado("modelo registrado e em uso", coincide, f"registrado v{versao}, a API usa {usando}")


def inferencia(alvos: Alvos, out) -> Resultado:
    """3. A decisão de cada palavra vem do modelo: MANTER ou DESCARTAR, com a probabilidade."""
    problemas = []
    for frase in FRASES_EXEMPLO:
        try:
            resposta = simulador.send(alvos.api, frase)
        except (urllib.error.URLError, OSError, ValueError) as error:
            problemas.append(f"{frase!r}: {type(error).__name__}")
            continue
        out(f"  \"{frase}\"  ->  {' · '.join(resposta['glosses']) or '(nenhum sinal)'}   [{resposta['model_version']}, {resposta['latency_ms']} ms]")
        for m in resposta["matches"]:
            out(f"      {m['word']:<16} {m['decision']:<9} p={m['probability']:.2f}  {m['kind']:<8} {m['gloss'] or '—'}")
        if not resposta["model_version"].startswith("sinaliza-t1"):
            problemas.append(f"{frase!r} atendida sem o modelo ({resposta['model_version']})")
    return Resultado("inferência palavra por palavra", not problemas, "; ".join(problemas) or f"{len(FRASES_EXEMPLO)} frases pelo modelo")


def simular(alvos: Alvos, out, n: int = 20) -> Resultado:
    """4. O simulador faz o papel da fonte de dados novos: a API classifica e grava cada frase."""
    estatisticas = simulador.run(alvos.api, simulador.load_phrases("frases"), n, 0.1, config.SEED, out=lambda _: None)
    out(f"  {estatisticas['enviadas']} frases enviadas, {estatisticas['ok']} atendidas, modelos: {estatisticas['modelos']}")
    return Resultado("simulador de uso", estatisticas["ok"] == n and estatisticas["erros"] == 0, f"{estatisticas['ok']}/{n} atendidas")


def _pendentes(alvos: Alvos) -> int:
    from sqlalchemy import text

    with _engine(alvos.banco).connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM inferencias WHERE NOT processada")).scalar() or 0)


def consolidar(alvos: Alvos, out, esperar: float = 120.0) -> Resultado:
    """5. O DAG `monitoramento` do Airflow consolida as frases novas (se o Airflow não responder, roda o mesmo módulo)."""
    try:
        antes = _pendentes(alvos)
    except Exception as error:
        return Resultado("consolidação", False, f"não consegui ler o banco ({type(error).__name__})")
    via = "DAG monitoramento no Airflow"
    try:
        token = _json(f"{alvos.airflow}/auth/token", data={"username": "admin", "password": "admin"})["access_token"]
        request = urllib.request.Request(
            f"{alvos.airflow}/api/v2/dags/monitoramento/dagRuns", data=json.dumps({"logical_date": None}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
        urllib.request.urlopen(request, timeout=10).read()
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        from . import monitor

        monitor.process(_engine(alvos.banco))
        via = "o mesmo módulo, direto (o Airflow não respondeu)"
    limite = time.monotonic() + esperar
    pendentes = antes
    while time.monotonic() < limite:
        pendentes = _pendentes(alvos)
        if pendentes == 0:
            break
        time.sleep(3)
    out(f"  {antes} frases aguardavam; depois da consolidação via {via}: {pendentes}")
    return Resultado("consolidação dos indicadores", pendentes == 0, f"{antes} -> {pendentes} pendentes ({via})")


def indicadores(alvos: Alvos, out) -> Resultado:
    """6. O resultado da consolidação: indicadores por hora e versão do modelo."""
    from sqlalchemy import text

    try:
        with _engine(alvos.banco).connect() as conn:
            linhas = conn.execute(text(
                "SELECT versao_modelo, SUM(frases) AS frases, SUM(palavras) AS palavras, "
                "SUM(taxa_manter * palavras) / NULLIF(SUM(palavras), 0) AS manter, "
                "SUM(taxa_sem_sinal * palavras) / NULLIF(SUM(palavras), 0) AS sem_sinal, MAX(latencia_p95_ms) AS p95 "
                "FROM indicadores_horarios GROUP BY versao_modelo")).mappings().all()
    except Exception as error:
        return Resultado("indicadores", False, f"não consegui ler `indicadores_horarios` ({type(error).__name__})")
    for l in linhas:
        out(f"  {l['versao_modelo']}: {int(l['frases'])} frases, {int(l['palavras'])} palavras, "
            f"{(l['manter'] or 0):.1%} mantidas, {(l['sem_sinal'] or 0):.1%} sem sinal, latência p95 {(l['p95'] or 0):.0f} ms")
    return Resultado("indicadores no banco", bool(linhas), f"{len(linhas)} versão(ões) com indicadores")


def painel(alvos: Alvos, out) -> Resultado:
    """7. O painel lê tudo isso e mostra em tempo real."""
    try:
        _get(f"{alvos.painel}/_stcore/health")
    except (urllib.error.URLError, OSError) as error:
        return Resultado("painel", False, f"sem resposta ({type(error).__name__})")
    out(f"  abra {alvos.painel} (abas Visão geral, Inferências, Modelo e Serviços)")
    return Resultado("painel", True, alvos.painel)


ETAPAS = [
    ("1. Serviços de pé", "docker compose up: postgres, mlflow, api, airflow, painel", servicos),
    ("2. O modelo (ML nosso)", "Random Forest otimizado, registrado no MLflow, é o que a API usa", modelo),
    ("3. Inferência palavra por palavra", "O MODELO decide MANTER ou DESCARTAR; o resto é tabela e regra", inferencia),
    ("4. Simulador de uso", "faz o papel da fonte de dados novos (no lugar do embarcado)", simular),
    ("5. Consolidação (Airflow)", "DAG monitoramento: das frases gravadas aos indicadores por hora", consolidar),
    ("6. Indicadores", "o que o painel vai mostrar", indicadores),
    ("7. Painel", "monitoramento em tempo de execução", painel),
]


def main() -> int:
    padrao = Alvos()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=20, help="frases do simulador")
    parser.add_argument("--api", default=padrao.api)
    parser.add_argument("--mlflow", default=padrao.mlflow)
    parser.add_argument("--airflow", default=padrao.airflow)
    parser.add_argument("--painel", default=padrao.painel)
    parser.add_argument("--banco", default=padrao.banco)
    args = parser.parse_args()
    alvos = Alvos(args.api, args.mlflow, args.airflow, args.painel, args.banco)

    resultados: list[Resultado] = []
    for titulo, ideia, etapa in ETAPAS:
        print(f"\n{titulo}\n  ({ideia})")
        inicio = time.monotonic()
        try:
            resultado = etapa(alvos, print, args.n) if etapa is simular else etapa(alvos, print)
        except Exception as error:  # a demonstração relata a falha da etapa e segue para a próxima
            resultado = Resultado(titulo, False, f"erro inesperado: {type(error).__name__}: {error}")
        resultado.segundos = time.monotonic() - inicio
        resultados.append(resultado)
        print(f"  {'✔' if resultado.ok else '✖'} {resultado.nome}: {resultado.detalhe} ({resultado.segundos:.1f} s)")

    print("\nResumo")
    for r in resultados:
        print(f"  {'✔' if r.ok else '✖'} {r.nome}")
    ok = all(r.ok for r in resultados)
    print("\nDemonstração completa." if ok else "\nHá etapas que falharam (veja acima).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
