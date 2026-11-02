"""Leitura e normalização do VLibrasBD.

ETAPA: regra (sem ML). Aqui só se lê o CSV e se aplica a notação do corpus às glosas.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

from . import config

# Marcas de pontuação e de intensidade que não são sinais.
_MARKS = re.compile(r"\[(?:PONTO|INTERROGAÇÃO|EXCLAMAÇÃO)\]|\((?:\+|-)\)")
_DIRECTIONAL = re.compile(r"^\d[SP]_(.+?)(?:_\d[SP])?$")


def slug(text: str) -> str:
    """Minúsculas, sem acento e sem separadores: chave de comparação entre palavra e sinal."""
    decomposed = unicodedata.normalize("NFD", text)
    plain = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", plain.lower())


def read_csv(path: Path | None = None) -> pd.DataFrame:
    path = path or config.RAW_DIR / config.CSV_NAME
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = df.rename(
        columns={
            "pt-br": "texto",
            "libras-gloss": "glosa",
            "is_government_source": "governo",
            "english_translation": "ingles",
        }
    )
    df["governo"] = df["governo"].str.strip().str.lower() == "true"
    return df


def gloss_marks(gloss: str) -> dict:
    """Conta as marcas da notação, para a EDA."""
    tokens = gloss.split()
    return {
        "n_sinais": len([t for t in tokens if not _MARKS.fullmatch(t)]),
        "tem_homonimo": "&" in gloss,
        "tem_negacao": any(t.startswith("NÃO_") for t in tokens),
        "tem_intensidade": bool(re.search(r"\((?:\+|-)\)", gloss)),
        "tem_direcional": any(_DIRECTIONAL.match(t) for t in tokens),
        "tipo_frase": next(
            (m for m in ("[INTERROGAÇÃO]", "[EXCLAMAÇÃO]", "[PONTO]") if m in gloss), "nenhum"
        ),
    }


def gloss_keys(gloss: str) -> set[str]:
    """Conjunto de chaves `slug()` que representam os sinais da glosa.

    Regras do relatório técnico do VLibrasBD: remove marcas; NÃO_X vira {NÃO, X};
    1S_X_2S vira X; X&Y vira X; compostos com `_` contam inteiros e por partes.
    """
    keys: set[str] = set()
    for token in _MARKS.sub(" ", gloss).split():
        directional = _DIRECTIONAL.match(token)
        if directional:
            token = directional.group(1)
        if token.startswith("NÃO_") and len(token) > 4:
            keys.add(slug("NÃO"))
            token = token[4:]
        token = token.split("&")[0]
        keys.add(slug(token))
        if "_" in token:
            keys.update(slug(part) for part in token.split("_") if part)
    keys.discard("")
    return keys
