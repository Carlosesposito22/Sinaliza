"""Ingestão do VLibrasBD: baixa o CSV, confere o hash e carrega no Postgres.

ETAPA: infraestrutura de dados (sem ML). Alimenta a tabela `corpus_bruto`.
Uso: python -m textgloss.ingest
"""
import hashlib
import shutil
import time
import urllib.error
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


def _fetch(destination: Path) -> str:
    """Baixa para `destination` e devolve o SHA-256 do que chegou."""
    # O Mendeley responde 403 ao User-Agent padrão do urllib.
    request = urllib.request.Request(config.CSV_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; sinaliza-pipeline)"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)
    return sha256(destination)


def download(destination: Path | None = None, attempts: int = 4, wait: float = 15.0) -> Path:
    """Garante o CSV no disco com o hash publicado, baixando se preciso.

    - Arquivo que já existe: confere o hash e, se divergir, **falha sem apagar** (pode ser uma versão que alguém
      colocou de propósito).
    - Download: vai para um arquivo temporário e só entra no lugar se o hash conferir. O Mendeley já respondeu um erro
      em JSON (395 bytes) com status 200; sem esta verificação o erro virava "o CSV" e as tentativas seguintes
      reaproveitavam o arquivo ruim. Em falha, descarta, espera e tenta de novo (até `attempts` vezes).
    """
    destination = destination or config.RAW_DIR / config.CSV_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        found = sha256(destination)
        if found != config.CSV_SHA256:
            raise ValueError(f"Hash do corpus diverge: esperado {config.CSV_SHA256}, obtido {found}")
        return destination

    partial = destination.with_suffix(destination.suffix + ".part")
    problem = "nenhuma tentativa feita"
    for attempt in range(1, attempts + 1):
        try:
            found = _fetch(partial)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            problem = f"erro de rede ({type(error).__name__}: {error})"
        else:
            if found == config.CSV_SHA256:
                partial.replace(destination)
                return destination
            head = partial.read_bytes()[:120].decode("utf-8", errors="replace").replace("\n", " ")
            problem = f"hash {found[:12]}... diverge do esperado ({partial.stat().st_size} bytes; o servidor respondeu: {head!r})"
        partial.unlink(missing_ok=True)
        if attempt < attempts:
            time.sleep(wait * attempt)
    raise ValueError(f"Não consegui baixar o corpus com o hash esperado em {attempts} tentativas: {problem}")


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
