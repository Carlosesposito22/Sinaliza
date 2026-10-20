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


class TranslateResponse(BaseModel):
    text: str
    glosses: list[str]
    matches: list[WordMatch]
    pose: PoseSequence


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
