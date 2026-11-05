"""Monitoramento: transforma as inferências gravadas pela API em indicadores por hora.

ETAPA: regra/estatística (sem ML novo). Lê as frases que a API classificou com o modelo T1
(tabela `inferencias`), agrega por hora e versão do modelo e grava em `indicadores_horarios`,
que o painel lê. Roda no DAG `monitoramento` (a cada hora).

CONTRATO COM A API (fase 8): a API grava uma linha em `inferencias` por frase recebida.
`processada` começa em falso; só este módulo a marca como verdadeira.

PRIVACIDADE: o texto digitado pode ter dado pessoal. A API só grava `texto` e as palavras de quem
envia `X-Origem: simulador` (frases públicas) ou se `SINALIZA_LOG_TEXT=true`. Passada a retenção
(`SINALIZA_RETENCAO_DIAS`, padrão 30, proposta ainda não confirmada pela equipe), `purge` apaga `texto` e
`palavras` das linhas já processadas; os indicadores agregados ficam.
Uso: python -m textgloss.monitor
"""
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, MetaData, String, Table, Text, create_engine, func, select, text,
    update,
)

from . import config

metadata = MetaData()

# Uma linha por frase recebida pela API. `palavras` é um JSON com palavra, decisão e probabilidade.
inferencias = Table(
    "inferencias", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("em", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("origem", String(32)),
    Column("texto", Text),
    Column("n_palavras", Integer, nullable=False),
    Column("n_mantidas", Integer, nullable=False),
    Column("n_sem_sinal", Integer, nullable=False, default=0),
    Column("prob_media", Float),
    Column("prob_incerta", Integer, nullable=False, default=0),
    Column("latencia_ms", Float),
    Column("versao_modelo", String(64), nullable=False),
    Column("usou_modelo", Boolean, nullable=False, default=True),
    Column("palavras", Text),
    Column("processada", Boolean, nullable=False, default=False, server_default="false"),
)

# Um registro por (hora, versão do modelo), reescrito se novas frases da mesma hora chegarem depois.
indicadores_horarios = Table(
    "indicadores_horarios", metadata,
    Column("hora", DateTime(timezone=True), primary_key=True),
    Column("versao_modelo", String(64), primary_key=True),
    Column("frases", Integer, nullable=False),
    Column("palavras", Integer, nullable=False),
    Column("taxa_manter", Float),
    Column("taxa_sem_sinal", Float),
    Column("prob_media", Float),
    Column("taxa_incerta", Float),
    Column("latencia_p50_ms", Float),
    Column("latencia_p95_ms", Float),
    Column("sem_modelo", Integer, nullable=False, default=0),
)


def ensure_schema(engine) -> None:
    metadata.create_all(engine)


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    """Agrega frases por hora e versão do modelo. Entrada: linhas de `inferencias`."""
    if rows.empty:
        return pd.DataFrame(columns=[c.name for c in indicadores_horarios.columns])
    rows = rows.assign(hora=pd.to_datetime(rows["em"], utc=True).dt.floor("h"))
    out = []
    for (hora, versao), group in rows.groupby(["hora", "versao_modelo"]):
        palavras = int(group["n_palavras"].sum())
        out.append({
            "hora": hora.to_pydatetime(),
            "versao_modelo": versao,
            "frases": len(group),
            "palavras": palavras,
            "taxa_manter": float(group["n_mantidas"].sum() / palavras) if palavras else None,
            "taxa_sem_sinal": float(group["n_sem_sinal"].sum() / palavras) if palavras else None,
            "prob_media": float(np.average(group["prob_media"].fillna(0.5), weights=group["n_palavras"].clip(lower=1))),
            "taxa_incerta": float(group["prob_incerta"].sum() / palavras) if palavras else None,
            "latencia_p50_ms": float(group["latencia_ms"].quantile(0.5)) if group["latencia_ms"].notna().any() else None,
            "latencia_p95_ms": float(group["latencia_ms"].quantile(0.95)) if group["latencia_ms"].notna().any() else None,
            "sem_modelo": int((~group["usou_modelo"].astype(bool)).sum()),
        })
    return pd.DataFrame(out)


def purge(engine, days: int) -> int:
    """Apaga o texto e as palavras das inferências já processadas com mais de `days` dias. Devolve quantas."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with engine.begin() as conn:
        result = conn.execute(
            update(inferencias)
            .where(inferencias.c.processada.is_(True), inferencias.c.em < cutoff)
            .where((inferencias.c.texto.is_not(None)) | (inferencias.c.palavras.is_not(None)))
            .values(texto=None, palavras=None)
        )
    return result.rowcount


def process(engine) -> dict:
    """Agrega as inferências ainda não processadas e as marca como processadas. Devolve um resumo."""
    ensure_schema(engine)
    with engine.begin() as conn:
        pending = pd.read_sql(select(inferencias).where(inferencias.c.processada.is_(False)), conn)
        if pending.empty:
            return {"frases_novas": 0, "horas_atualizadas": 0}
        new = summarize(pending)
        for record in new.to_dict("records"):
            record["hora"] = record["hora"].to_pydatetime()
            existing = conn.execute(
                text("SELECT * FROM indicadores_horarios WHERE hora = :hora AND versao_modelo = :versao_modelo"),
                record,
            ).mappings().first()
            if existing:
                record = combine(dict(existing), record)
            conn.execute(text(_UPSERT), record)
        conn.execute(update(inferencias).where(inferencias.c.id.in_(pending["id"].tolist())).values(processada=True))
    return {"frases_novas": int(len(pending)), "horas_atualizadas": int(len(new))}


def combine(old: dict, new: dict) -> dict:
    """Soma uma hora já gravada com as frases novas dela. Taxas viram médias ponderadas pelas palavras;
    os percentis de latência ficam com o maior valor visto (aproximação conservadora, declarada)."""
    total = old["palavras"] + new["palavras"]

    def weighted(key: str):
        if not total:
            return None
        a, b = old[key] or 0.0, new[key] or 0.0
        return (a * old["palavras"] + b * new["palavras"]) / total

    return {
        "hora": new["hora"],
        "versao_modelo": new["versao_modelo"],
        "frases": old["frases"] + new["frases"],
        "palavras": total,
        "taxa_manter": weighted("taxa_manter"),
        "taxa_sem_sinal": weighted("taxa_sem_sinal"),
        "prob_media": weighted("prob_media"),
        "taxa_incerta": weighted("taxa_incerta"),
        "latencia_p50_ms": max(filter(None, [old["latencia_p50_ms"], new["latencia_p50_ms"]]), default=None),
        "latencia_p95_ms": max(filter(None, [old["latencia_p95_ms"], new["latencia_p95_ms"]]), default=None),
        "sem_modelo": old["sem_modelo"] + new["sem_modelo"],
    }


_UPSERT = (
    "INSERT INTO indicadores_horarios (hora, versao_modelo, frases, palavras, taxa_manter, taxa_sem_sinal, "
    "prob_media, taxa_incerta, latencia_p50_ms, latencia_p95_ms, sem_modelo) VALUES "
    "(:hora, :versao_modelo, :frases, :palavras, :taxa_manter, :taxa_sem_sinal, :prob_media, :taxa_incerta, "
    ":latencia_p50_ms, :latencia_p95_ms, :sem_modelo) "
    "ON CONFLICT (hora, versao_modelo) DO UPDATE SET frases = excluded.frases, palavras = excluded.palavras, "
    "taxa_manter = excluded.taxa_manter, taxa_sem_sinal = excluded.taxa_sem_sinal, prob_media = excluded.prob_media, "
    "taxa_incerta = excluded.taxa_incerta, latencia_p50_ms = excluded.latencia_p50_ms, "
    "latencia_p95_ms = excluded.latencia_p95_ms, sem_modelo = excluded.sem_modelo"
)


def main() -> None:
    engine = create_engine(config.DATABASE_URL)
    result = process(engine)
    result["texto_expurgado"] = purge(engine, int(os.environ.get("SINALIZA_RETENCAO_DIAS", "30")))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
