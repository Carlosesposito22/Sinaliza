"""Contrato web ↔ API (versão 2). Esta é a fonte de verdade dos formatos; ver docs/contrato-api-web.md.

O mock e a API real devem devolver exatamente estes formatos. Mudou algo aqui? Mude o contrato
(docs/contrato-api-web.md), `CONTRACT_VERSION` e `web/src/contract.ts` juntos.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

CONTRACT_VERSION = "2"

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
#
# Versão 2 (2026-11-17): a trilha é feita de TEMAS (escola, família, saúde...). Cada tema tem aulas
# (sinais e frases) e termina numa PROVA: o avatar sinaliza sem legenda e a pessoa escreve o que
# entendeu. Nota >= `pass_score` libera o próximo tema; abaixo disso, a pessoa refaz as aulas do tema
# antes de tentar de novo. Tudo isto é regra, não ML.


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


class LearnPhrase(BaseModel):
    """Cartão de apresentação de uma frase: o avatar toca `glosses` em sequência e mostra `text`.

    A sequência segue a ordem do português; não é a gramática da Libras (mostre isso na tela).
    """

    id: str
    type: Literal["learn_phrase"] = "learn_phrase"
    glosses: list[str]
    text: str


class PhraseToText(BaseModel):
    """O avatar toca `glosses`; a pessoa escolhe, entre frases em português, a certa."""

    id: str
    type: Literal["phrase_to_text"] = "phrase_to_text"
    glosses: list[str]
    options: list[TextOption]
    correct_option_id: str


class SignToText(BaseModel):
    """O avatar toca `glosses` (um sinal ou uma frase); a pessoa ESCREVE o que entendeu, como na prova.

    A correção é a mesma da prova, feita pela API em `POST /learn/check`. Diferente da prova, o texto
    esperado vem aqui (`text`), porque a aula é treino; o front só o mostra depois de verificar.
    """

    id: str
    type: Literal["sign_to_text"] = "sign_to_text"
    kind: Literal["sign", "phrase"]
    glosses: list[str]
    text: str


Exercise = Annotated[
    Union[LearnSign, SignToWord, WordToSign, MatchPairs, LearnPhrase, PhraseToText, SignToText],
    Field(discriminator="type"),
]


class LessonSummary(BaseModel):
    id: str
    title: str
    kind: Literal["signs", "phrases"]
    xp_reward: int
    n_exercises: int
    glosses: list[str] = Field(description="sinais que a aula ensina (nas de frases, os que as frases usam)")


class ExamSummary(BaseModel):
    n_questions: int
    pass_score: float = Field(ge=0, le=1, description="nota mínima para passar (0 a 1)")
    xp_reward: int


class Theme(BaseModel):
    id: str
    title: str
    description: str
    color: str
    lessons: list[LessonSummary]
    exam: ExamSummary


class PathResponse(BaseModel):
    title: str
    disclaimer: str
    themes: list[Theme]


class Lesson(BaseModel):
    id: str
    theme_id: str
    title: str
    kind: Literal["signs", "phrases"]
    xp_reward: int
    exercises: list[Exercise]


class LessonProgress(BaseModel):
    status: Literal["locked", "available", "completed"]
    stars: int = Field(ge=0, le=3)
    best_accuracy: float = Field(ge=0, le=1)
    completions: int
    needs_redo: bool = Field(description="a pessoa reprovou na prova do tema e precisa refazer esta aula")


class ThemeProgress(BaseModel):
    """`status`: `locked` (tema anterior sem prova aprovada), `learning` (faltam aulas),
    `exam_ready` (aulas feitas, prova liberada) ou `passed` (prova aprovada; o próximo tema abre)."""

    status: Literal["locked", "learning", "exam_ready", "passed"]
    lessons_completed: int
    lessons_total: int
    exam_attempts: int
    best_exam_score: float = Field(ge=0, le=1)
    last_exam_score: float | None = Field(ge=0, le=1)
    must_redo: bool = Field(description="reprovou na última prova e ainda não refez todas as aulas")


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
    themes: dict[str, ThemeProgress]
    lessons: dict[str, LessonProgress]
    review_signs: int = Field(default=0, description="sinais errados esperando revisão")
    challenge_available: bool = Field(default=False, description="já há sinais vistos para o desafio do dia")
    challenge_done_today: bool = Field(default=False)


# ---------------------------------------------------------------- treino: escrever, revisão, desafio, dicionário
# Tudo regra, não ML. Só usa os 210 sinais do vocabulário curado.


class CheckRequest(BaseModel):
    """Corrige uma resposta escrita de treino (exercício `sign_to_text`) com a regra da prova."""

    glosses: list[str] = Field(min_length=1)
    text: str = Field(description="texto esperado (o do exercício)")
    answer: str = Field(default="", max_length=300)


class CheckResult(BaseModel):
    correct: bool = Field(description="acertou todos os sinais sem palavra sobrando")
    score: float = Field(ge=0, le=1)
    expected_text: str
    signs: list["SignCheck"]
    extra_words: list[str]


class Practice(BaseModel):
    """Sessão de treino fora da trilha: revisão dos erros ou desafio do dia. O front joga como uma aula."""

    id: str = Field(description="id da sessão; use em POST /learn/practice/{id}/complete")
    kind: Literal["review", "challenge"]
    title: str
    xp_reward: int
    glosses: list[str]
    exercises: list[Exercise]
    completed_today: bool = Field(default=False, description="desafio: já foi feito hoje (refazer não dá XP)")


class PracticeResult(BaseModel):
    passed: bool
    accuracy: float
    xp_gained: int
    level_up: bool
    goal_reached_now: bool
    cleared_glosses: list[str] = Field(description="sinais que saíram da revisão (acertados nesta sessão)")
    new_achievements: list["AchievementInfo"] = Field(default_factory=list)
    progress: Progress


class DictionaryEntry(BaseModel):
    gloss: str
    word: str
    forms: list[str]
    theme_ids: list[str] = Field(description="temas da trilha que ensinam este sinal (vazio: só no vocabulário)")
    seen: bool = Field(description="apareceu numa aula que a pessoa já fez")
    mistakes: int = Field(description="erros recentes ainda na revisão")


class DictionaryResponse(BaseModel):
    total: int
    seen_count: int
    signs: list[DictionaryEntry]


class AchievementInfo(BaseModel):
    """Uma conquista (medalha ou troféu) e o estado dela para quem pediu. Regra, não ML."""

    id: str
    title: str
    description: str
    kind: Literal["medal", "trophy"]
    tier: Literal["bronze", "silver", "gold"]
    category: Literal["provas", "temas", "aulas", "habito"]
    icon: str = Field(description="nome curto do desenho: exam, check, star, rocket, comeback, hand, book, flame, level, trophy, crown")
    unlocked: bool
    unlocked_at: str | None = Field(description="AAAA-MM-DD da primeira vez")
    current: int = Field(description="quanto já fez (limitado a `target`)")
    target: int


class AchievementsResponse(BaseModel):
    unlocked_count: int
    total: int
    achievements: list[AchievementInfo]


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
    exam_unlocked: bool = Field(description="esta aula foi a última que faltava: a prova do tema abriu")
    new_achievements: list[AchievementInfo] = Field(default_factory=list, description="conquistas ganhas agora")
    progress: Progress


class ExamQuestion(BaseModel):
    """Uma questão da prova: o avatar toca `glosses`, sem legenda. A resposta certa NÃO vem aqui."""

    id: str
    kind: Literal["sign", "phrase"]
    glosses: list[str]


class Exam(BaseModel):
    theme_id: str
    title: str
    pass_score: float = Field(ge=0, le=1)
    questions: list[ExamQuestion]


class ExamAnswer(BaseModel):
    question_id: str
    text: str = Field(default="", max_length=300)


class ExamSubmit(BaseModel):
    answers: list[ExamAnswer]


class SignCheck(BaseModel):
    gloss: str
    word: str = Field(description="palavra de referência do sinal")
    correct: bool


class QuestionResult(BaseModel):
    question_id: str
    kind: Literal["sign", "phrase"]
    glosses: list[str]
    expected_text: str
    answer: str
    score: float = Field(ge=0, le=1)
    signs: list[SignCheck]
    extra_words: list[str] = Field(description="palavras da resposta que não correspondem a nenhum sinal")


class ExamResult(BaseModel):
    passed: bool
    score: float = Field(ge=0, le=1)
    pass_score: float = Field(ge=0, le=1)
    xp_gained: int
    level_up: bool
    goal_reached_now: bool
    questions: list[QuestionResult]
    unlocked_theme_ids: list[str]
    must_redo_lesson_ids: list[str] = Field(description="reprovou: aulas a refazer antes da próxima tentativa")
    new_achievements: list[AchievementInfo] = Field(default_factory=list, description="conquistas ganhas agora")
    progress: Progress


class Health(BaseModel):
    status: str
    contract_version: str
    mock: bool


# As classes de treino citam SignCheck e AchievementInfo, definidas depois delas.
CheckResult.model_rebuild()
PracticeResult.model_rebuild()
