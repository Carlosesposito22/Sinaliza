"""Ingestão do VLibrasBD: baixa o CSV, confere o hash e carrega no Postgres.

ETAPA: infraestrutura de dados (sem ML). Alimenta a tabela `corpus_bruto`.
Uso: python -m textgloss.ingest
"""
import hashlib
import urllib.request
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from . import config, corpus


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(destination: Path | None = None) -> Path:
    """Baixa o CSV se ainda não existe e falha se o hash divergir do publicado."""
    destination = destination or config.RAW_DIR / config.CSV_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        urllib.request.urlretrieve(config.CSV_URL, destination)
    found = sha256(destination)
    if found != config.CSV_SHA256:
        raise ValueError(f"Hash do corpus diverge: esperado {config.CSV_SHA256}, obtido {found}")
    return destination


def load(path: Path, database_url: str | None = None) -> int:
    """Substitui a tabela `corpus_bruto` pelo conteúdo do CSV. Devolve o número de linhas."""
    df = corpus.read_csv(path)
    df.insert(0, "frase_id", range(len(df)))
    engine = create_engine(database_url or config.DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS corpus_bruto"))
    df.to_sql("corpus_bruto", engine, index=False, chunksize=10_000)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE corpus_bruto ADD PRIMARY KEY (frase_id)"))
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS ingestoes ("
                "id SERIAL PRIMARY KEY, arquivo TEXT, sha256 TEXT, linhas INT, "
                "em TIMESTAMPTZ DEFAULT now())"
            )
        )
        conn.execute(
            text("INSERT INTO ingestoes (arquivo, sha256, linhas) VALUES (:a, :h, :n)"),
            {"a": path.name, "h": config.CSV_SHA256, "n": len(df)},
        )
    return len(df)


def main() -> None:
    path = download()
    print(f"hash ok: {path}")
    print(f"{load(path)} linhas carregadas em corpus_bruto")


if __name__ == "__main__":
    main()
