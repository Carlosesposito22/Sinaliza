"""Preparação do T1: limpeza, spaCy, rotulagem, divisão treino/teste e conjuntos salvos.

ETAPA: preparação de dados. Gera os exemplos supervisionados que o treino consome.
Uso: python -m textgloss.prepare [--limite N]
"""
import argparse
import json

import pandas as pd
from sqlalchemy import create_engine

from . import align, config, corpus, features


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove frases vazias, glosas vazias e duplicatas exatas (texto, glosa)."""
    report = {"linhas_entrada": len(df)}
    df = df.assign(texto=df["texto"].str.strip(), glosa=df["glosa"].str.strip())
    df = df[(df["texto"] != "") & (df["glosa"] != "")]
    report["apos_remover_vazias"] = len(df)
    df = df.drop_duplicates(subset=["texto", "glosa"])
    report["apos_remover_duplicadas"] = len(df)
    df = df[df["glosa"].map(lambda g: bool(corpus.gloss_keys(g)))]
    report["apos_remover_glosa_sem_sinal"] = len(df)
    return df.reset_index(drop=True), report


def split_by_sentence(df: pd.DataFrame) -> pd.Series:
    """10% das FRASES para teste final, estratificado por domínio. Nunca separa palavras da mesma frase."""
    test_ids = df.groupby("governo")["frase_id"].sample(frac=config.TEST_FRACTION, random_state=config.SEED)
    return df["frase_id"].isin(test_ids).map({True: "teste", False: "treino"})


def build(df: pd.DataFrame, n_process: int = 1) -> pd.DataFrame:
    nlp = features.load_nlp()
    keys = {row.frase_id: corpus.gloss_keys(row.glosa) for row in df.itertuples()}
    rows = []
    docs = nlp.pipe(df["texto"].tolist(), batch_size=256, n_process=n_process)
    for frase_id, doc in zip(df["frase_id"], docs):
        for row in features.doc_rows(doc, frase_id):
            row["rotulo"] = align.label_token(row["palavra"], row["lema"], keys[frase_id])
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=None, help="só as N primeiras frases (teste rápido)")
    parser.add_argument("--processos", type=int, default=1)
    args = parser.parse_args()

    engine = create_engine(config.DATABASE_URL)
    df = pd.read_sql("SELECT frase_id, texto, glosa, governo FROM corpus_bruto ORDER BY frase_id", engine)
    if args.limite:
        df = df.head(args.limite)
    df, report = clean(df)
    df["split"] = split_by_sentence(df)

    words = build(df, args.processos).merge(df[["frase_id", "governo", "split"]], on="frase_id")
    report.update(
        palavras=len(words),
        frases_treino=int((df["split"] == "treino").sum()),
        frases_teste=int((df["split"] == "teste").sum()),
        proporcao_manter=float(words["rotulo"].mean()),
    )

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    words.to_parquet(config.PROCESSED_DIR / "palavras.parquet", index=False)
    df.to_parquet(config.PROCESSED_DIR / "frases.parquet", index=False)
    (config.PROCESSED_DIR / "relatorio_preparacao.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    sample = pd.concat(
        [g.sample(100, random_state=config.SEED) for _, g in words.groupby("rotulo")]
    ).merge(df[["frase_id", "texto", "glosa"]], on="frase_id")
    sample = sample[["frase_id", "texto", "glosa", "palavra", "lema", "rotulo"]].assign(rotulo_correto="")
    sample.sample(frac=1, random_state=config.SEED).to_csv(
        config.PROCESSED_DIR / "amostra_conferencia_200.csv", index=False, encoding="utf-8-sig"
    )

    words.to_sql("palavras_t1", engine, if_exists="replace", index=False, chunksize=50_000)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
