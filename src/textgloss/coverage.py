"""Cobertura do dicionário do VLibras sobre os sinais mais frequentes do corpus.

ETAPA: verificação externa (sem ML). Pergunta ao dicionário público se cada sinal existe
(requisição HEAD, sem baixar o arquivo) e guarda o resultado para a EDA.
Uso: python -m textgloss.coverage [--top 1500]
"""
import argparse
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import config, corpus

DICTIONARY = "https://dicionario2-dth.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/"
_NOT_SIGN = re.compile(r"\[(?:PONTO|INTERROGAÇÃO|EXCLAMAÇÃO)\]|\((?:\+|-)\)")


def sign_names(gloss: str) -> list[str]:
    """Nome de cada sinal como o dicionário o chama (sem marcas, antes do `&`)."""
    return [t.split("&")[0] for t in _NOT_SIGN.sub(" ", gloss).split() if not t.startswith("NÃO_")]


def exists(name: str) -> bool:
    request = urllib.request.Request(DICTIONARY + urllib.parse.quote(name), method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False
    except urllib.error.URLError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=1500)
    args = parser.parse_args()
    frases = pd.read_parquet(config.PROCESSED_DIR / "frases.parquet")
    counts = Counter(n for g in frases["glosa"] for n in sign_names(g))
    top = counts.most_common(args.top)
    with ThreadPoolExecutor(8) as pool:
        found = list(pool.map(lambda item: exists(item[0]), top))
    out = pd.DataFrame({"sinal": [n for n, _ in top], "ocorrencias": [c for _, c in top], "no_dicionario": found})
    out.to_csv(config.PROCESSED_DIR / "cobertura_dicionario.csv", index=False, encoding="utf-8")
    covered = out.loc[out["no_dicionario"], "ocorrencias"].sum() / out["ocorrencias"].sum()
    print(f"{out['no_dicionario'].mean():.1%} dos {len(out)} sinais mais frequentes existem no dicionário "
          f"({covered:.1%} das ocorrências)")


if __name__ == "__main__":
    main()
