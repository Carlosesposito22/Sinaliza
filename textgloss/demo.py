"""Demonstração ponta a ponta do Sinaliza, em um comando, narrando o que cada etapa prova e onde está o ML.

ETAPA: demonstração (sem ML novo). Percorre o mesmo fluxo da apresentação: serviços de pé → modelo registrado no
MLflow → inferência palavra por palavra na API → totem (sistema embarcado simulado) publicando via MQTT → simulador
de uso → consolidação pelo DAG `monitoramento` → indicadores no banco → painel. Sai com código 0 só se todas as
etapas passarem.

Uso: python -m textgloss.demo [--n 20] [--api URL] [--mlflow URL] [--airflow URL] [--painel URL] [--banco URL]
                              [--mqtt HOST:PORTA]
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
    mqtt: str = "localhost:1883"


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
    """1. Tudo de pé: API (e se o modelo carregou), MLflow, Airflow, painel, broker MQTT e banco."""
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
        import socket

        host, _, port = alvos.mqtt.partition(":")
        socket.create_connection((host, int(port or 1883)), timeout=3).close()
        estados.append("broker MQTT ok")
    except (OSError, ValueError) as error:
        falhas.append(f"broker MQTT sem resposta ({type(error).__name__})")
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


def totem_mqtt(alvos: Alvos, out, esperar: float = 30.0) -> Resultado:
    """4. Um totem (sistema embarcado simulado) publica uma frase no broker MQTT; o receptor grava a mensagem e pede
    a inferência ao modelo pela API. Confere o caminho inteiro no banco: `mensagens_mqtt` e `inferencias`."""
    import sys

    import paho.mqtt.client as mqtt
    from sqlalchemy import text

    sys.path.insert(0, str(config.ROOT / "embedded"))
    import totem

    host, _, port = alvos.mqtt.partition(":")
    frase = FRASES_EXEMPLO[0]
    mensagem = totem.build_message("totem-demo", "demonstração", 1, frase)
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sinaliza-demo-{mensagem['msg_id'][:8]}")
    try:
        cliente.connect(host, int(port or 1883), keepalive=10)
    except OSError as error:
        return Resultado("totem via MQTT", False, f"broker {alvos.mqtt} sem resposta ({type(error).__name__})")
    cliente.loop_start()
    cliente.publish(totem.topic_frases("totem-demo"), json.dumps(mensagem, ensure_ascii=False), qos=1).wait_for_publish(timeout=10)
    cliente.loop_stop()
    cliente.disconnect()
    out(f"  publicado em {totem.topic_frases('totem-demo')} (QoS 1): \"{frase}\"")

    engine = _engine(alvos.banco)
    linha, limite = None, time.monotonic() + esperar
    while time.monotonic() < limite:
        with engine.connect() as conn:
            linha = conn.execute(text(
                "SELECT status, glosas, versao_modelo, latencia_total_ms FROM mensagens_mqtt WHERE msg_id = :m"
            ), {"m": mensagem["msg_id"]}).mappings().first()
        if linha is not None and linha["status"] != "recebida":
            break
        time.sleep(0.5)
    if linha is None:
        return Resultado("totem via MQTT", False, "o receptor não gravou a mensagem (serviço `receptor` de pé?)")
    if linha["status"] != "inferida":
        return Resultado("totem via MQTT", False, f"mensagem gravada, mas com status {linha['status']}")
    with engine.connect() as conn:
        online = conn.execute(text("SELECT COUNT(*) FROM totens WHERE status = 'online'")).scalar()
        inferencias = conn.execute(text("SELECT COUNT(*) FROM inferencias WHERE origem = 'totem'")).scalar()
    out(f"  receptor gravou e a API respondeu: {' · '.join(json.loads(linha['glosas']))}   [{linha['versao_modelo']}, "
        f"{linha['latencia_total_ms']:.0f} ms do totem até a inferência]")
    out(f"  totens online agora: {online}; inferências vindas de totens no banco: {inferencias}")
    ok = str(linha["versao_modelo"]).startswith("sinaliza-t1")
    return Resultado("totem via MQTT", ok, "broker → receptor → banco → API (modelo)" if ok else f"inferida sem o modelo ({linha['versao_modelo']})")


def simular(alvos: Alvos, out, n: int = 20) -> Resultado:
    """5. O simulador de uso gera volume: a API classifica e grava cada frase."""
    estatisticas = simulador.run(alvos.api, simulador.load_phrases("frases"), n, 0.1, config.SEED, out=lambda _: None)
    out(f"  {estatisticas['enviadas']} frases enviadas, {estatisticas['ok']} atendidas, modelos: {estatisticas['modelos']}")
    return Resultado("simulador de uso", estatisticas["ok"] == n and estatisticas["erros"] == 0, f"{estatisticas['ok']}/{n} atendidas")


def _pendentes(alvos: Alvos) -> int:
    from sqlalchemy import text

    with _engine(alvos.banco).connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM inferencias WHERE NOT processada")).scalar() or 0)


def consolidar(alvos: Alvos, out, esperar: float = 120.0) -> Resultado:
    """6. O DAG `monitoramento` do Airflow consolida as frases novas (se o Airflow não responder, roda o mesmo módulo)."""
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
    """7. O resultado da consolidação: indicadores por hora e versão do modelo."""
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
    """8. O painel lê tudo isso e mostra em tempo real."""
    try:
        _get(f"{alvos.painel}/_stcore/health")
    except (urllib.error.URLError, OSError) as error:
        return Resultado("painel", False, f"sem resposta ({type(error).__name__})")
    out(f"  abra {alvos.painel} (abas Visão geral, Inferências, Totens (MQTT), Modelo e Serviços)")
    return Resultado("painel", True, alvos.painel)


ETAPAS = [
    ("1. Serviços de pé", "docker compose up: postgres, mlflow, api, airflow, painel, broker MQTT", servicos),
    ("2. O modelo (ML nosso)", "Random Forest otimizado, registrado no MLflow, é o que a API usa", modelo),
    ("3. Inferência palavra por palavra", "O MODELO decide MANTER ou DESCARTAR; o resto é tabela e regra", inferencia),
    ("4. Totem via MQTT", "sistema embarcado simulado → broker → receptor → banco → API (modelo)", totem_mqtt),
    ("5. Simulador de uso", "gera volume de frases novas pela API", simular),
    ("6. Consolidação (Airflow)", "DAG monitoramento: das frases gravadas aos indicadores por hora", consolidar),
    ("7. Indicadores", "o que o painel vai mostrar", indicadores),
    ("8. Painel", "monitoramento em tempo de execução", painel),
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
    parser.add_argument("--mqtt", default=padrao.mqtt, help="broker MQTT, HOST:PORTA")
    args = parser.parse_args()
    alvos = Alvos(args.api, args.mlflow, args.airflow, args.painel, args.banco, args.mqtt)

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
