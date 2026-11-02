"""Extração de atributos por palavra com o spaCy.

ETAPA: extração de atributos (sem decisão). O spaCy entra como o pandas entraria:
lematiza, marca a classe gramatical e a morfologia. Quem decide é o classificador.
"""
import spacy

from . import config

MORPH_KEYS = ("Gender", "Number", "Tense", "VerbForm", "Mood", "Person", "Polarity", "PronType")


def load_nlp():
    return spacy.load(config.SPACY_MODEL, disable=["ner"])


def sentence_type(text: str) -> str:
    stripped = text.rstrip()
    if stripped.endswith("?"):
        return "interrogativa"
    if stripped.endswith("!"):
        return "exclamativa"
    return "declarativa"


def doc_rows(doc, frase_id: int) -> list[dict]:
    """Uma linha por palavra (pontuação e espaços ficam de fora)."""
    tokens = [t for t in doc if not t.is_punct and not t.is_space]
    size = len(tokens)
    kind = sentence_type(doc.text)
    rows = []
    for i, tok in enumerate(tokens):
        morph = tok.morph.to_dict()
        row = {
            "frase_id": frase_id,
            "pos": i,
            "palavra": tok.text,
            "lema": tok.lemma_.lower(),
            "upos": tok.pos_,
            "dep": tok.dep_,
            "stop": tok.is_stop,
            "pos_relativa": i / max(size - 1, 1),
            "tam_frase": size,
            "tipo_frase": kind,
            "upos_anterior": tokens[i - 1].pos_ if i > 0 else "INICIO",
            "upos_seguinte": tokens[i + 1].pos_ if i < size - 1 else "FIM",
        }
        for key in MORPH_KEYS:
            row[f"m_{key}"] = morph.get(key, "ausente")
        rows.append(row)
    return rows
