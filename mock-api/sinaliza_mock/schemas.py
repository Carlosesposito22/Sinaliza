"""Contrato web ↔ API (versão 1). Esta é a fonte de verdade dos formatos; ver docs/contrato-api-web.md.

O mock e a API real devem devolver exatamente estes formatos. Mudou algo aqui? Mude o contrato
(docs/contrato-api-web.md), `CONTRACT_VERSION` e `web/src/contract.ts` juntos.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

CONTRACT_VERSION = "1"

# ---------------------------------------------------------------- tradutor (ML)


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

    `kind` (já existe hoje): `exact` está na tabela; `approx` aproximada por embedding;
    `function` artigo/preposição sem sinal próprio; `ignored` sem sinal no vocabulário.
    `decision` e `probability` (novos): o que o modelo de ML decidiu para a palavra.
    """

    word: str
    gloss: str | None
    kind: Literal["exact", "approx", "function", "ignored"]
    score: float
    decision: Literal["MANTER", "DESCARTAR"]
    probability: float = Field(ge=0, le=1, description="probabilidade da classe MANTER")


class PoseSequence(BaseModel):
    fps: int
    layout: dict[str, tuple[int, int]]
    frames: list[list[list[float]]]


class TranslateResponse(BaseModel):
    text: str
    glosses: list[str]
    matches: list[WordMatch]
    generator: str
    pose: PoseSequence | None = Field(default=None, description="legado; o web não deve depender dele")
    model_version: str = Field(description='ex.: "sinaliza-t1/1", "lista-fixa" ou "mock"')
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


# ---------------------------------------------------------------- trilha de aprendizado


class LearnSign(BaseModel):
    """Cartão de apresentação de um sinal: o avatar toca `gloss` e mostra a palavra."""

    id: str
    type: Literal["learn_sign"] = "learn_sign"
    gloss: str
    word_pt: str
    forms: list[str]


class TextOption(BaseModel):
    id: str
    text: str


class SignOption(BaseModel):
    id: str
    gloss: str


class SignToWord(BaseModel):
    """O avatar toca `gloss`; a pessoa escolhe a palavra em português."""

    id: str
    type: Literal["sign_to_word"] = "sign_to_word"
    gloss: str
    options: list[TextOption]
    correct_option_id: str


class WordToSign(BaseModel):
    """Mostra a palavra; a pessoa escolhe, entre sinais que o avatar toca ao toque, o certo."""

    id: str
    type: Literal["word_to_sign"] = "word_to_sign"
    text: str
    options: list[SignOption]
    correct_option_id: str


class Pair(BaseModel):
    id: str
    gloss: str
    text: str


class MatchPairs(BaseModel):
    """Ligar cada sinal à sua palavra."""

    id: str
    type: Literal["match_pairs"] = "match_pairs"
    pairs: list[Pair]


Exercise = Annotated[Union[LearnSign, SignToWord, WordToSign, MatchPairs], Field(discriminator="type")]


class LessonSummary(BaseModel):
    id: str
    title: str
    xp_reward: int
    n_exercises: int
    glosses: list[str]


class Unit(BaseModel):
    id: str
    title: str
    description: str
    color: str
    icon: str
    lessons: list[LessonSummary]


class PathResponse(BaseModel):
    title: str
    disclaimer: str
    units: list[Unit]


class Lesson(BaseModel):
    id: str
    unit_id: str
    title: str
    xp_reward: int
    exercises: list[Exercise]


class LessonProgress(BaseModel):
    status: Literal["locked", "available", "completed"]
    stars: int = Field(ge=0, le=3)
    best_accuracy: float = Field(ge=0, le=1)
    completions: int


class Progress(BaseModel):
    learner_id: str
    xp: int
    level: int
    xp_in_level: int
    xp_to_next_level: int
    streak_days: int
    best_streak: int
    daily_goal_xp: int
    xp_today: int
    goal_reached_today: bool
    last_activity_date: str | None = Field(description="AAAA-MM-DD")
    lessons: dict[str, LessonProgress]


class CompleteRequest(BaseModel):
    correct: int = Field(ge=0)
    total: int = Field(ge=1)
    mistakes: list[str] = Field(default_factory=list, description="ids dos exercícios errados")

    @model_validator(mode="after")
    def correct_not_above_total(self) -> "CompleteRequest":
        if self.correct > self.total:
            raise ValueError("correct não pode ser maior que total")
        return self


class LessonResult(BaseModel):
    passed: bool
    accuracy: float
    stars: int
    xp_gained: int
    bonus_perfect: bool
    level_up: bool
    goal_reached_now: bool
    unlocked_lesson_ids: list[str]
    progress: Progress


class Health(BaseModel):
    status: str
    contract_version: str
    mock: bool
