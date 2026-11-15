"""Acesso a dados do painel: Postgres, API e MLflow. Sem Streamlit, para poder ser testado.

ETAPA: visualização (sem ML novo). Só lê. As tabelas `mensagens_mqtt` e `totens` (aquisição pelos totens via
MQTT) vêm de `receptor/receptor.py`. As tabelas `inferencias` (uma linha por frase atendida pela API) e
`indicadores_horarios` (consolidação do DAG `monitoramento`) vêm de `textgloss/monitor.py`; o modelo e as métricas
vêm do MLflow; o estado dos serviços vem de chamadas a cada um.

PRIVACIDADE: o texto e as palavras só existem nas linhas em que a API os gravou (simulador ou opt-in) e somem
depois da retenção. O painel nunca assume que existem: sem texto, mostra só decisão e probabilidade.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import inspect, text

UNCERTAIN = (0.4, 0.6)
MODEL_NAME = "sinaliza-t1"
NO_ML_VERSION = "lista-fixa"

HOURLY_COLUMNS = [
    "hora", "versao_modelo", "frases", "palavras", "taxa_manter", "taxa_sem_sinal", "prob_media", "taxa_incerta",
    "latencia_p50_ms", "latencia_p95_ms", "sem_modelo",
]
RECENT_COLUMNS = [
    "id", "em", "origem", "texto", "n_palavras", "n_mantidas", "n_sem_sinal", "prob_media", "prob_incerta",
    "latencia_ms", "versao_modelo", "usou_modelo", "palavras", "processada",
]
WORD_COLUMNS = ["inferencia_id", "em", "origem", "versao_modelo", "palavra", "glosa", "decisao", "probabilidade", "tipo"]


@dataclass(frozen=True)
class Config:
    database_url: str
    api_url: str
    mlflow_url: str
    mlflow_public_url: str
    airflow_url: str
    experiment: str
    mqtt_host: str = ""
    mqtt_port: int = 1883

    @classmethod
    def from_env(cls) -> "Config":
        mlflow_url = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        return cls(
            database_url=os.environ.get("SINALIZA_DATABASE_URL", "postgresql+psycopg://sinaliza:sinaliza@localhost:5432/sinaliza"),
            api_url=os.environ.get("SINALIZA_API_URL", "http://localhost:8000"),
            mlflow_url=mlflow_url,
            mlflow_public_url=os.environ.get("SINALIZA_MLFLOW_PUBLIC_URL", "http://localhost:5000"),
            airflow_url=os.environ.get("SINALIZA_AIRFLOW_URL", ""),
            # Prefixo dos experimentos do T1 (um por etapa: <prefixo>-01-baseline, -02-comparacao-de-modelos, ...).
            experiment=os.environ.get("SINALIZA_MLFLOW_PREFIXO", "sinaliza-t1"),
            mqtt_host=os.environ.get("MQTT_HOST", ""),
            mqtt_port=int(os.environ.get("MQTT_PORT", "1883")),
        )


# --- Postgres ------------------------------------------------------------------------------------------------------


def _has_table(engine, name: str) -> bool:
    return inspect(engine).has_table(name)


def load_hourly(engine, limit: int = 24 * 14) -> pd.DataFrame:
    """Indicadores por hora e versão do modelo (saída do DAG `monitoramento`), mais antigos primeiro."""
    if not _has_table(engine, "indicadores_horarios"):
        return pd.DataFrame(columns=HOURLY_COLUMNS)
    sql = text(f"SELECT {', '.join(HOURLY_COLUMNS)} FROM indicadores_horarios ORDER BY hora DESC LIMIT :limit")
    frame = pd.read_sql(sql, engine, params={"limit": limit * 4})
    frame["hora"] = pd.to_datetime(frame["hora"], utc=True)
    return frame.sort_values("hora").reset_index(drop=True)


def load_recent(engine, limit: int = 2000) -> pd.DataFrame:
    """As últimas inferências gravadas pela API (mais novas primeiro), com `em` em UTC."""
    if not _has_table(engine, "inferencias"):
        return pd.DataFrame(columns=RECENT_COLUMNS)
    sql = text(f"SELECT {', '.join(RECENT_COLUMNS)} FROM inferencias ORDER BY id DESC LIMIT :limit")
    frame = pd.read_sql(sql, engine, params={"limit": limit})
    frame["em"] = pd.to_datetime(frame["em"], utc=True)
    for column in ("usou_modelo", "processada"):
        frame[column] = frame[column].astype(bool)
    return frame


def totals(engine) -> dict:
    """Contagens gerais: total de frases, pendentes de consolidação, primeira e última inferência."""
    empty = {"frases": 0, "pendentes": 0, "ultima": None, "primeira": None, "consolidado_ate": None}
    if not _has_table(engine, "inferencias"):
        return empty
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT COUNT(*) AS frases, SUM(CASE WHEN processada THEN 0 ELSE 1 END) AS pendentes, "
            "MAX(em) AS ultima, MIN(em) AS primeira FROM inferencias"
        )).mappings().one()
        consolidated = None
        if _has_table(engine, "indicadores_horarios"):
            consolidated = conn.execute(text("SELECT MAX(hora) FROM indicadores_horarios")).scalar()
    return {
        "frases": int(row["frases"] or 0),
        "pendentes": int(row["pendentes"] or 0),
        "ultima": _to_utc(row["ultima"]),
        "primeira": _to_utc(row["primeira"]),
        "consolidado_ate": _to_utc(consolidated),
    }


def _to_utc(value) -> datetime | None:
    if value is None:
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC").to_pydatetime()


def hourly_overall(hourly: pd.DataFrame, since: datetime | None = None) -> pd.DataFrame:
    """Junta as versões do modelo numa linha por hora. Taxas ponderadas pelas palavras; percentis de latência pelo
    maior valor (mesma aproximação conservadora do `monitor.combine`)."""
    columns = ["hora", "frases", "palavras", "taxa_manter", "taxa_sem_sinal", "taxa_incerta", "latencia_p50_ms", "latencia_p95_ms"]
    if hourly.empty:
        return pd.DataFrame(columns=columns)
    frame = hourly if since is None else hourly[hourly["hora"] >= pd.Timestamp(since)]
    out = []
    for hora, group in frame.groupby("hora"):
        palavras = group["palavras"].sum()
        weights = group["palavras"].clip(lower=1)

        def rate(column: str) -> float:
            values = group[column].fillna(0.0)
            return float(np.average(values, weights=weights)) if palavras else 0.0

        out.append({
            "hora": hora,
            "frases": int(group["frases"].sum()),
            "palavras": int(palavras),
            "taxa_manter": rate("taxa_manter"),
            "taxa_sem_sinal": rate("taxa_sem_sinal"),
            "taxa_incerta": rate("taxa_incerta"),
            "latencia_p50_ms": float(group["latencia_p50_ms"].max()),
            "latencia_p95_ms": float(group["latencia_p95_ms"].max()),
        })
    return pd.DataFrame(out, columns=columns)


def fill_hours(overall: pd.DataFrame, since: datetime, until: datetime | None = None) -> pd.DataFrame:
    """Uma linha por hora da janela, com 0 frases onde não houve nenhuma (hora sem frase aparece, não some do eixo)."""
    until = until or datetime.now(timezone.utc)
    index = pd.date_range(pd.Timestamp(since).floor("h"), pd.Timestamp(until).floor("h"), freq="h", tz="UTC", name="hora")
    base = overall.set_index("hora")[["frases", "palavras"]] if not overall.empty else pd.DataFrame(columns=["frases", "palavras"])
    base.index = pd.DatetimeIndex(base.index, name="hora")
    return base.astype(float).reindex(index).fillna(0).astype(int).reset_index()


# --- Palavras (das inferências) ------------------------------------------------------------------------------------


def explode_words(recent: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por palavra decidida. `palavra` e `glosa` são nulas onde a API não gravou o texto."""
    rows = []
    for row in recent.itertuples():
        try:
            detail = json.loads(row.palavras) if row.palavras else []
        except (TypeError, ValueError):
            detail = []
        for item in detail:
            rows.append({
                "inferencia_id": row.id,
                "em": row.em,
                "origem": row.origem,
                "versao_modelo": row.versao_modelo,
                "palavra": item.get("palavra"),
                "glosa": item.get("glosa"),
                "decisao": item.get("decisao"),
                "probabilidade": item.get("probabilidade"),
                "tipo": item.get("tipo"),
            })
    return pd.DataFrame(rows, columns=WORD_COLUMNS)


def _ml_only(words: pd.DataFrame) -> pd.DataFrame:
    """Sem a lista fixa: a probabilidade dela é 0 ou 1 (regra), não ML."""
    return words[words["versao_modelo"] != NO_ML_VERSION]


def probability_histogram(words: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Quantas palavras caíram em cada faixa de probabilidade de MANTER (só decisões do modelo)."""
    ml = _ml_only(words)
    counts, edges = np.histogram(ml["probabilidade"].astype(float), bins=bins, range=(0.0, 1.0))
    return pd.DataFrame({
        "inicio": edges[:-1],
        "fim": edges[1:],
        "faixa": [f"{a:.1f}–{b:.1f}".replace(".", ",") for a, b in zip(edges[:-1], edges[1:])],
        "palavras": counts.astype(int),
    })


def unknown_words(words: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    """Palavras sem sinal no vocabulário (`tipo = ignored`) mais frequentes. Só linhas com o texto gravado."""
    known = words[(words["tipo"] == "ignored") & words["palavra"].notna()]
    if known.empty:
        return pd.DataFrame(columns=["palavra", "ocorrencias"])
    counts = known["palavra"].str.lower().value_counts().head(top)
    return counts.rename_axis("palavra").reset_index(name="ocorrencias")


def low_confidence(words: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    """Decisões do modelo com probabilidade entre 0,4 e 0,6, as mais próximas de 0,5 primeiro."""
    ml = _ml_only(words)
    close = ml[(ml["probabilidade"] >= UNCERTAIN[0]) & (ml["probabilidade"] <= UNCERTAIN[1])].copy()
    close["distancia"] = (close["probabilidade"] - 0.5).abs()
    close = close.sort_values(["distancia", "inferencia_id"], ascending=[True, False]).head(limit)
    return close[["em", "palavra", "decisao", "probabilidade", "tipo"]].reset_index(drop=True)


def _fmt(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def recent_table(recent: pd.DataFrame, limit: int = 40) -> pd.DataFrame:
    """Últimas inferências em formato de leitura: frase, decisão de cada palavra e sequência de sinais final."""
    rows = []
    for row in recent.head(limit).itertuples():
        try:
            detail = json.loads(row.palavras) if row.palavras else []
        except (TypeError, ValueError):
            detail = []
        decisions = " · ".join(
            f"{(item.get('palavra') + ' ') if item.get('palavra') else ''}"
            f"{'✓' if item.get('decisao') == 'MANTER' else '✗'} {_fmt(item.get('probabilidade', 0.0))}"
            for item in detail
        )
        glosses = " ".join(item["glosa"] for item in detail if item.get("glosa"))
        rows.append({
            "quando (UTC)": row.em.strftime("%d/%m %H:%M:%S"),
            "origem": row.origem or "—",
            "frase": row.texto if row.texto else "(texto não gravado)",
            "sequência de sinais": glosses if glosses else "—",
            "decisões (✓ mantém, ✗ descarta, probabilidade)": decisions,
            "modelo": row.versao_modelo,
            "latência (ms)": None if pd.isna(row.latencia_ms) else int(round(row.latencia_ms)),
        })
    return pd.DataFrame(rows)


# --- Aquisição pelos totens (MQTT) ---------------------------------------------------------------------------------
# Tabelas `mensagens_mqtt` e `totens`, gravadas pelo `receptor/` (uma linha por mensagem recebida do broker).

MQTT_COLUMNS = [
    "id", "msg_id", "dispositivo", "local", "seq", "enviada_em", "recebida_em", "texto", "status", "glosas",
    "versao_modelo", "latencia_api_ms", "latencia_total_ms", "tentativas", "erro",
]
DEVICE_COLUMNS = ["dispositivo", "status", "local", "atualizado_em"]


def load_mqtt(engine, limit: int = 5000) -> pd.DataFrame:
    """As últimas mensagens recebidas dos totens (mais novas primeiro), com horários em UTC."""
    if not _has_table(engine, "mensagens_mqtt"):
        return pd.DataFrame(columns=MQTT_COLUMNS)
    sql = text(f"SELECT {', '.join(MQTT_COLUMNS)} FROM mensagens_mqtt ORDER BY id DESC LIMIT :limit")
    frame = pd.read_sql(sql, engine, params={"limit": limit})
    for column in ("enviada_em", "recebida_em"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def load_devices(engine) -> pd.DataFrame:
    if not _has_table(engine, "totens"):
        return pd.DataFrame(columns=DEVICE_COLUMNS)
    frame = pd.read_sql(text(f"SELECT {', '.join(DEVICE_COLUMNS)} FROM totens ORDER BY dispositivo"), engine)
    frame["atualizado_em"] = pd.to_datetime(frame["atualizado_em"], utc=True)
    return frame


def lost_messages(seqs: pd.Series) -> int:
    """Mensagens perdidas pelos buracos em `seq` (em ordem de chegada). Se a sequência volta (o totem reiniciou e
    recomeçou do 1), conta cada trecho separado."""
    values = [int(v) for v in seqs.dropna()]
    lost, segment = 0, []
    for value in values + [None]:
        if segment and (value is None or value <= segment[-1]):
            lost += segment[-1] - segment[0] + 1 - len(set(segment))
            segment = []
        if value is not None:
            segment.append(value)
    return lost


def mqtt_summary(msgs: pd.DataFrame) -> dict:
    """Indicadores da aquisição numa janela: volume, desfecho de cada mensagem, latência ponta a ponta e perdas."""
    if msgs.empty:
        return {"mensagens": 0, "inferidas": 0, "rejeitadas": 0, "erros": 0, "invalidas": 0, "pendentes": 0,
                "latencia_p50_ms": None, "latencia_p95_ms": None, "perdidas": 0}
    status = msgs["status"].value_counts()
    latency = msgs.loc[msgs["status"] == "inferida", "latencia_total_ms"].dropna()
    ordered = msgs.sort_values("id")
    return {
        "mensagens": len(msgs),
        "inferidas": int(status.get("inferida", 0)),
        "rejeitadas": int(status.get("rejeitada", 0)),
        "erros": int(status.get("erro", 0)),
        "invalidas": int(status.get("invalida", 0)),
        "pendentes": int(status.get("recebida", 0)),
        "latencia_p50_ms": float(latency.quantile(0.5)) if len(latency) else None,
        "latencia_p95_ms": float(latency.quantile(0.95)) if len(latency) else None,
        "perdidas": sum(lost_messages(group["seq"]) for _, group in ordered.groupby("dispositivo")),
    }


def devices_table(msgs: pd.DataFrame, devices: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por totem: estado (do tópico de status), mensagens e perdas na janela, última mensagem."""
    names = sorted(set(devices["dispositivo"].dropna()) | set(msgs["dispositivo"].dropna()))
    out = []
    for name in names:
        mine = msgs[msgs["dispositivo"] == name].sort_values("id")
        info = devices[devices["dispositivo"] == name]
        latency = mine.loc[mine["status"] == "inferida", "latencia_total_ms"].dropna()
        out.append({
            "totem": name,
            "estado": info["status"].iloc[0] if len(info) else "desconhecido",
            "local": (info["local"].iloc[0] if len(info) else None) or (mine["local"].dropna().iloc[-1] if mine["local"].notna().any() else ""),
            "mensagens": len(mine),
            "inferidas": int((mine["status"] == "inferida").sum()),
            "perdidas": lost_messages(mine["seq"]),
            "latência p95 (ms)": round(float(latency.quantile(0.95))) if len(latency) else None,
            "última mensagem": mine["recebida_em"].max() if len(mine) else pd.NaT,
        })
    return pd.DataFrame(out, columns=["totem", "estado", "local", "mensagens", "inferidas", "perdidas",
                                      "latência p95 (ms)", "última mensagem"])


def mqtt_per_interval(msgs: pd.DataFrame, since: datetime, freq: str = "10min") -> pd.DataFrame:
    """Mensagens recebidas por intervalo e totem (intervalos vazios com zero), para o gráfico."""
    if msgs.empty:
        return pd.DataFrame(columns=["hora", "dispositivo", "mensagens"])
    start = pd.Timestamp(since).floor(freq)
    end = max(pd.Timestamp(datetime.now(timezone.utc)), msgs["recebida_em"].max()).floor(freq)
    index = pd.date_range(start, end, freq=freq, tz="UTC")
    frames = []
    for name, group in msgs.groupby("dispositivo"):
        counts = group.set_index("recebida_em").resample(freq).size().reindex(index, fill_value=0)
        frames.append(pd.DataFrame({"hora": index, "dispositivo": name, "mensagens": counts.values}))
    return pd.concat(frames, ignore_index=True)


def mqtt_recent_table(msgs: pd.DataFrame, limit: int = 40) -> pd.DataFrame:
    shown = msgs.head(limit)
    return pd.DataFrame({
        "recebida (UTC)": shown["recebida_em"].dt.strftime("%d/%m %H:%M:%S"),
        "totem": shown["dispositivo"],
        "seq": shown["seq"],
        "frase": shown["texto"].fillna("—"),
        "sequência de sinais": shown["glosas"].map(lambda g: " ".join(json.loads(g)) if isinstance(g, str) and g else "—"),
        "status": shown["status"],
        "ponta a ponta (ms)": shown["latencia_total_ms"].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}"),
        "modelo": shown["versao_modelo"].fillna("—"),
    })


# --- Serviços ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    ok: bool | None  # None = não monitorado
    detail: str
    ms: int | None = None

    @property
    def label(self) -> str:
        if self.ok is None:
            return "– não monitorado"
        return "✔ no ar" if self.ok else "✖ fora do ar"


def _get_json(url: str, timeout: float = 3.0, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"} if payload else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body) if body else {}


def _ping(url: str, timeout: float = 3.0) -> int:
    """Status HTTP da resposta, sem ler o corpo como JSON (o /health do MLflow responde texto puro)."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status


def _timed(name: str, call) -> ServiceStatus:
    started = time.perf_counter()
    try:
        ok, detail = call()
    except urllib.error.HTTPError as error:
        ok, detail = False, f"HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        ok, detail = False, f"sem resposta ({type(error).__name__})"
    return ServiceStatus(name, ok, detail, round((time.perf_counter() - started) * 1000))


def check_api(api_url: str) -> list[ServiceStatus]:
    def health():
        body = _get_json(f"{api_url.rstrip('/')}/health")
        return body.get("status") == "ok", f"modelo em uso: {body.get('model', '?')}"

    def ready():
        _get_json(f"{api_url.rstrip('/')}/ready")
        return True, "primeira carga do modelo concluída"

    status = _timed("API (/health)", health)
    readiness = _timed("API (/ready)", ready) if status.ok else ServiceStatus("API (/ready)", False, "API fora do ar")
    return [status, readiness]


def check_mlflow(mlflow_url: str) -> ServiceStatus:
    def health():
        return _ping(f"{mlflow_url.rstrip('/')}/health") == 200, "servidor de experimentos e registro de modelos"

    return _timed("MLflow", health)


def check_database(engine) -> ServiceStatus:
    started = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return ServiceStatus("Banco de dados (Postgres)", True, "consulta simples respondeu", round((time.perf_counter() - started) * 1000))
    except Exception as error:  # qualquer falha de conexão vira "fora do ar"
        return ServiceStatus("Banco de dados (Postgres)", False, f"sem resposta ({type(error).__name__})")


def check_airflow(airflow_url: str) -> ServiceStatus:
    if not airflow_url:
        return ServiceStatus("Airflow", None, "defina SINALIZA_AIRFLOW_URL para monitorar")

    def health():
        body = _get_json(f"{airflow_url.rstrip('/')}/api/v2/monitor/health")
        parts = {key: (value or {}).get("status") for key, value in body.items() if isinstance(value, dict)}
        ok = bool(parts) and all(status == "healthy" for status in parts.values())
        return ok, ", ".join(f"{k}: {v}" for k, v in parts.items()) or "sem detalhes"

    return _timed("Airflow", health)


def check_broker(host: str, port: int) -> ServiceStatus:
    """Abre uma conexão TCP com o broker MQTT (não publica nada)."""
    if not host:
        return ServiceStatus("Broker MQTT (Mosquitto)", None, "defina MQTT_HOST para monitorar")
    import socket

    def connect():
        with socket.create_connection((host, port), timeout=3):
            return True, f"{host}:{port} aceitando conexões"

    return _timed("Broker MQTT (Mosquitto)", connect)


def check_services(config: Config, engine) -> list[ServiceStatus]:
    """Checa todos ao mesmo tempo: um serviço parado (que demora para dar timeout) não atrasa os demais."""
    with ThreadPoolExecutor(max_workers=5) as pool:
        api = pool.submit(check_api, config.api_url)
        database = pool.submit(check_database, engine)
        mlflow = pool.submit(check_mlflow, config.mlflow_url)
        airflow = pool.submit(check_airflow, config.airflow_url)
        broker = pool.submit(check_broker, config.mqtt_host, config.mqtt_port)
        return [*api.result(), database.result(), mlflow.result(), airflow.result(), broker.result()]


def api_model(api_url: str) -> str | None:
    """O que a API diz estar usando agora (`sinaliza-t1/1`, `lista-fixa (...)`), ou None se não responde."""
    try:
        return _get_json(f"{api_url.rstrip('/')}/health").get("model")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


# --- MLflow --------------------------------------------------------------------------------------------------------


def _mlflow(base: str, path: str, data: dict | None = None, timeout: float = 5.0) -> dict:
    return _get_json(f"{base.rstrip('/')}/api/2.0/mlflow/{path}", timeout=timeout, data=data)


def registered_model(mlflow_url: str, name: str = MODEL_NAME) -> dict | None:
    """Última versão registrada e as métricas da run que a gerou. None se não há modelo ou o MLflow não responde."""
    try:
        model = _mlflow(mlflow_url, f"registered-models/get?{urllib.parse.urlencode({'name': name})}")["registered_model"]
        versions = [int(v["version"]) for v in model.get("latest_versions", [])]
        if not versions:
            return None
        version = max(versions)
        info = _mlflow(mlflow_url, f"model-versions/get?{urllib.parse.urlencode({'name': name, 'version': version})}")["model_version"]
        run = _mlflow(mlflow_url, f"runs/get?{urllib.parse.urlencode({'run_id': info['run_id']})}")["run"]
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
        return None
    metrics = {m["key"]: float(m["value"]) for m in run["data"].get("metrics", [])}
    params = {p["key"]: p["value"] for p in run["data"].get("params", [])}
    return {
        "nome": name,
        "versao": str(version),
        "registrado_em": datetime.fromtimestamp(int(info["creation_timestamp"]) / 1000, tz=timezone.utc),
        "run_id": info["run_id"],
        "run_name": run["info"].get("run_name"),
        "metricas": metrics,
        "parametros": params,
    }


# Experimentos do MLflow que têm modelos comparáveis na validação (o de validação e teste final fica de fora).
COMPARISON_EXPERIMENTS = ("01-baseline", "02-comparacao-de-modelos", "03-otimizacao-de-hiperparametros")


def training_comparison(mlflow_url: str, prefix: str) -> pd.DataFrame:
    """F1-macro de validação de cada modelo treinado (baseline, comparação e Random Forest otimizado), lido dos
    experimentos `<prefixo>-01-baseline`, `-02-comparacao-de-modelos` e `-03-otimizacao-de-hiperparametros`.

    Linhas: modelo, etapa, f1_macro, ml (False para a lista fixa, que é a referência sem ML).
    """
    columns = ["modelo", "etapa", "f1_macro", "ml"]
    ids = []
    for suffix in COMPARISON_EXPERIMENTS:
        name = urllib.parse.urlencode({"experiment_name": f"{prefix}-{suffix}"})
        try:
            ids.append(_mlflow(mlflow_url, f"experiments/get-by-name?{name}")["experiment"]["experiment_id"])
        except urllib.error.HTTPError:
            continue  # experimento ainda não criado (etapa não rodou)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
            return pd.DataFrame(columns=columns)
    if not ids:
        return pd.DataFrame(columns=columns)
    try:
        runs = _mlflow(mlflow_url, "runs/search", {
            "experiment_ids": ids, "max_results": 500,
            "filter": "attributes.status = 'FINISHED'", "order_by": ["attributes.start_time DESC"],
        }).get("runs", [])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
        return pd.DataFrame(columns=columns)
    latest: dict[str, dict] = {}
    for run in runs:
        tags = {t["key"]: t["value"] for t in run["data"].get("tags", [])}
        metrics = {m["key"]: float(m["value"]) for m in run["data"].get("metrics", [])}
        name, stage = tags.get("modelo"), tags.get("etapa")
        keep = stage in ("baseline", "comparacao") or (stage == "otimizacao" and name == "random-forest-otimizado")
        value = metrics.get("f1_macro_val", metrics.get("val_f1_macro"))
        if keep and name and value is not None and name not in latest:  # a run mais recente de cada modelo
            latest[name] = {"modelo": name, "etapa": stage, "f1_macro": value, "ml": name != "lista-fixa"}
    return pd.DataFrame(list(latest.values()), columns=columns).sort_values("f1_macro", ascending=False).reset_index(drop=True)
