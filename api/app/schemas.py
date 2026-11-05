from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PoseSequence(BaseModel):
    fps: int
    layout: dict[str, tuple[int, int]]
    frames: list[list[list[float]]]


class TranslateRequest(BaseModel):
    text: str = Field(max_length=500)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("o texto não pode ser vazio")
        return value


class WordMatch(BaseModel):
    """Como uma palavra do texto virou (ou não) um sinal.

    `exact`: está na tabela. `approx`: aproximada por embedding (proposta, com
    `score`). `function`: artigo/preposição, sem sinal próprio. `ignored`: sem sinal.
    """

    word: str
    gloss: str | None
    kind: Literal["exact", "approx", "function", "ignored"]
    score: float
    # O que o modelo de ML (T1) decidiu para a palavra e a probabilidade de MANTER. `decision` é a
    # decisão do modelo; `kind` é o que aconteceu depois (uma palavra MANTER pode ser `ignored` por
    # não ter sinal no vocabulário). Sem modelo (`model_version: "lista-fixa"`), a probabilidade é 0 ou 1.
    decision: Literal["MANTER", "DESCARTAR"]
    probability: float = Field(ge=0, le=1)


class TranslateResponse(BaseModel):
    text: str
    glosses: list[str]
    matches: list[WordMatch]
    generator: str
    pose: PoseSequence
    model_version: str = Field(description='ex.: "sinaliza-t1/1", ou "lista-fixa" se o modelo não está disponível')
    latency_ms: int


class SignInfo(BaseModel):
    gloss: str
    forms: list[str]
    contexts: list[str]
    note: str | None = None


class VocabularyResponse(BaseModel):
    signs: list[SignInfo]


class Phrase(BaseModel):
    text: str
    glosses: list[str]
    ignored: list[str]


class Category(BaseModel):
    id: str
    label: str
    phrases: list[Phrase]


class CategoriesResponse(BaseModel):
    categories: list[Category]
