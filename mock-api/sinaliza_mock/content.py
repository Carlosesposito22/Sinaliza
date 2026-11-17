"""Monta a trilha de aprendizado a partir de data/trilha.json (conteúdo escrito pela equipe; regra, não ML).

A trilha é feita de temas. Cada tema tem aulas de sinais (4 sinais cada), aulas de frases e uma prova.
Regra do projeto: nenhum sinal é inventado e **só usamos o nosso dicionário**: os 210 sinais curados de
data/vocabulary.json (classes do V-LIBRASIL). Glosa da trilha fora dele faz o mock recusar subir.
As formas do vocabulário (`pt`) entram sozinhas nas respostas aceitas; `accept` da trilha só acrescenta
flexões do português. Os rótulos não foram validados por falante de Libras (ver `DISCLAIMER`).
O conteúdo das aulas é determinístico: a mesma trilha sai a cada subida.
"""

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path

from .schemas import (
    ExamQuestion,
    ExamSummary,
    LearnPhrase,
    LearnSign,
    Lesson,
    LessonSummary,
    MatchPairs,
    Pair,
    PathResponse,
    PhraseToText,
    SignOption,
    SignToText,
    SignToWord,
    TextOption,
    Theme,
    WordToSign,
)

ROOT = Path(__file__).resolve().parents[2]
VOCABULARY = Path(os.environ.get("SINALIZA_VOCABULARY", ROOT / "data" / "vocabulary.json"))
TRILHA = Path(os.environ.get("SINALIZA_TRILHA", ROOT / "data" / "trilha.json"))

DISCLAIMER = (
    "Sinais do nosso vocabulário curado (210 sinais do V-LIBRASIL), tocados pelo avatar do VLibras; os rótulos "
    "e as frases não foram validados por falante de Libras. As frases seguem a ordem do português: são "
    "sequências de sinais, não Libras com gramática própria."
)

XP_PER_LESSON = 20
XP_PER_EXAM = 50
PASS_SCORE = 0.7  # nota mínima da prova para liberar o próximo tema


def load_signs(path: Path = VOCABULARY) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["signs"]


def load_trilha(path: Path = TRILHA) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ExamItem:
    """Uma questão da prova com o gabarito (que nunca vai para o front antes da correção)."""

    id: str
    kind: str  # "sign" ou "phrase"
    glosses: list[str]
    expected_text: str

    def question(self) -> ExamQuestion:
        return ExamQuestion(id=self.id, kind=self.kind, glosses=self.glosses)


def _choices(rng: random.Random, correct: str, pool: list[str], n: int = 3) -> list[str]:
    """O item certo mais `n - 1` distratores distintos, em ordem embaralhada."""
    candidates = sorted({p for p in pool if p != correct})
    rng.shuffle(candidates)
    options = [correct, *candidates[: n - 1]]
    rng.shuffle(options)
    return options


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


class Content:
    def __init__(self, trilha: dict, vocabulary: list[dict]):
        self.vocabulary: dict[str, dict] = {s["gloss"]: s for s in vocabulary}
        outside = sorted(set(trilha["signs"]) - set(self.vocabulary))
        if outside:
            raise ValueError(f"glosas fora do vocabulário curado em data/trilha.json: {', '.join(outside)}")
        self.signs: dict[str, dict] = {
            gloss: {"word": sign["word"], "accept": _dedupe([sign["word"], *self.vocabulary[gloss]["pt"], *sign["accept"]])}
            for gloss, sign in trilha["signs"].items()
        }
        self.themes: list[Theme] = []
        self.lessons: dict[str, Lesson] = {}
        self.theme_lessons: dict[str, list[str]] = {}  # tema → ids das aulas, em ordem
        self.lesson_theme: dict[str, str] = {}
        self.lesson_glosses: dict[str, list[str]] = {}  # aula → sinais que ela ensina ou usa
        self.exercise_targets: dict[str, list[str]] = {}  # exercício → sinais cobrados nele (para a revisão)
        self.exams: dict[str, list[ExamItem]] = {}
        self.theme_order: list[str] = []
        self._build(trilha["themes"])

    # ------------------------------------------------------------ montagem

    def word(self, gloss: str) -> str:
        sign = self.signs.get(gloss)
        return sign["word"] if sign else self.vocabulary[gloss]["pt"][0]

    def accept(self, gloss: str) -> list[str]:
        sign = self.signs.get(gloss)
        return sign["accept"] if sign else list(self.vocabulary[gloss]["pt"])

    @property
    def accept_table(self) -> dict[str, list[str]]:
        return {gloss: self.accept(gloss) for gloss in self.vocabulary}

    def themes_of(self, gloss: str) -> list[str]:
        return [t for t in self.theme_order if any(gloss in self.lesson_glosses[l] for l in self.theme_lessons[t])]

    def _build(self, themes: list[dict]) -> None:
        all_glosses = list(self.signs)
        for theme in themes:
            theme_id = theme["id"]
            theme_signs = [g for lesson in theme["lessons"] for g in lesson.get("signs", [])]
            theme_phrases = [p for lesson in theme["lessons"] for p in lesson.get("phrases", [])]
            sign_pool = theme_signs if len(theme_signs) >= 3 else all_glosses
            summaries: list[LessonSummary] = []
            for raw in theme["lessons"]:
                if "phrases" in raw:
                    lesson = self._phrase_lesson(theme_id, raw, [p["text"] for p in theme_phrases])
                    glosses = _dedupe([g for p in raw["phrases"] for g in p["glosses"]])
                else:
                    lesson = self._sign_lesson(theme_id, raw, sign_pool)
                    glosses = list(raw["signs"])
                self.lessons[lesson.id] = lesson
                self.lesson_theme[lesson.id] = theme_id
                self.lesson_glosses[lesson.id] = glosses
                summaries.append(
                    LessonSummary(
                        id=lesson.id, title=lesson.title, kind=lesson.kind, xp_reward=lesson.xp_reward,
                        n_exercises=len(lesson.exercises), glosses=glosses,
                    )
                )
            self.theme_lessons[theme_id] = [s.id for s in summaries]
            self.exams[theme_id] = [
                *(ExamItem(f"{theme_id}-q{i + 1}", "sign", [g], self.word(g)) for i, g in enumerate(theme_signs)),
                *(
                    ExamItem(f"{theme_id}-q{len(theme_signs) + i + 1}", "phrase", p["glosses"], p["text"])
                    for i, p in enumerate(theme_phrases)
                ),
            ]
            self.theme_order.append(theme_id)
            self.themes.append(
                Theme(
                    id=theme_id, title=theme["title"], description=theme["description"], color=theme["color"],
                    lessons=summaries,
                    exam=ExamSummary(n_questions=len(self.exams[theme_id]), pass_score=PASS_SCORE, xp_reward=XP_PER_EXAM),
                )
            )

    # Exercícios avulsos: usados pelas aulas e pelas sessões de revisão e desafio.

    def learn_sign(self, ex_id: str, gloss: str) -> LearnSign:
        self.exercise_targets[ex_id] = [gloss]
        return LearnSign(id=ex_id, gloss=gloss, word_pt=self.word(gloss), forms=self.accept(gloss))

    def sign_to_word(self, ex_id: str, gloss: str, pool: list[str], rng: random.Random) -> SignToWord:
        options = _choices(rng, gloss, pool)
        ids = {g: chr(ord("a") + i) for i, g in enumerate(options)}
        self.exercise_targets[ex_id] = [gloss]
        return SignToWord(
            id=ex_id, gloss=gloss, options=[TextOption(id=ids[g], text=self.word(g)) for g in options],
            correct_option_id=ids[gloss],
        )

    def word_to_sign(self, ex_id: str, gloss: str, pool: list[str], rng: random.Random) -> WordToSign:
        options = _choices(rng, gloss, pool)
        ids = {g: chr(ord("a") + i) for i, g in enumerate(options)}
        self.exercise_targets[ex_id] = [gloss]
        return WordToSign(
            id=ex_id, text=self.word(gloss), options=[SignOption(id=ids[g], gloss=g) for g in options],
            correct_option_id=ids[gloss],
        )

    def sign_to_text(self, ex_id: str, glosses: list[str], text: str | None = None) -> SignToText:
        self.exercise_targets[ex_id] = list(glosses)
        kind = "phrase" if text is not None else "sign"
        return SignToText(id=ex_id, kind=kind, glosses=list(glosses), text=text if text is not None else self.word(glosses[0]))

    def _sign_lesson(self, theme_id: str, raw: dict, pool: list[str]) -> Lesson:
        lesson_id = raw["id"]
        rng = random.Random(lesson_id)
        chunk: list[str] = raw["signs"]
        exercises: list = []

        def new_id() -> str:
            return f"{lesson_id}-e{len(exercises) + 1}"

        for gloss in chunk:
            exercises.append(self.learn_sign(new_id(), gloss))
        for gloss in chunk:
            exercises.append(self.sign_to_word(new_id(), gloss, pool, rng))
        for gloss in chunk:
            exercises.append(self.word_to_sign(new_id(), gloss, pool, rng))
        # Treino de escrita, no formato da prova: dois sinais por aula.
        for gloss in chunk[1::2]:
            exercises.append(self.sign_to_text(new_id(), [gloss]))
        if len(chunk) >= 2:
            pairs = [Pair(id=f"p{i + 1}", gloss=g, text=self.word(g)) for i, g in enumerate(chunk)]
            rng.shuffle(pairs)
            # Sem alvo para a revisão: o erro num par não diz qual sinal a pessoa confundiu.
            exercises.append(MatchPairs(id=new_id(), pairs=pairs))
        return Lesson(
            id=lesson_id, theme_id=theme_id, title=raw["title"], kind="signs", xp_reward=XP_PER_LESSON, exercises=exercises
        )

    def _phrase_lesson(self, theme_id: str, raw: dict, pool: list[str]) -> Lesson:
        lesson_id = raw["id"]
        rng = random.Random(lesson_id)
        phrases: list[dict] = raw["phrases"]
        exercises: list = []

        def new_id() -> str:
            return f"{lesson_id}-e{len(exercises) + 1}"

        for phrase in phrases:
            ex_id = new_id()
            self.exercise_targets[ex_id] = list(phrase["glosses"])
            exercises.append(LearnPhrase(id=ex_id, glosses=phrase["glosses"], text=phrase["text"]))
        if len(pool) >= 2:
            for phrase in phrases:
                options = _choices(rng, phrase["text"], pool)
                ids = {t: chr(ord("a") + i) for i, t in enumerate(options)}
                ex_id = new_id()
                self.exercise_targets[ex_id] = list(phrase["glosses"])
                exercises.append(
                    PhraseToText(
                        id=ex_id, glosses=phrase["glosses"], options=[TextOption(id=ids[t], text=t) for t in options],
                        correct_option_id=ids[phrase["text"]],
                    )
                )
        # Treino de escrita: duas frases por aula.
        for phrase in phrases[::2]:
            exercises.append(self.sign_to_text(new_id(), phrase["glosses"], phrase["text"]))
        return Lesson(
            id=lesson_id, theme_id=theme_id, title=raw["title"], kind="phrases", xp_reward=XP_PER_LESSON, exercises=exercises
        )

    def practice_exercises(self, prefix: str, glosses: list[str], seed: str, per_sign: int) -> list:
        """Exercícios de treino para `glosses`: escolha, escrita e (no desafio) palavra → sinal, alternando.

        Os distratores vêm dos sinais da trilha, então tudo continua dentro do vocabulário curado.
        """
        rng = random.Random(seed)
        pool = list(self.signs)
        makers = [
            lambda i, g: self.sign_to_word(i, g, pool, rng),
            lambda i, g: self.sign_to_text(i, [g]),
            lambda i, g: self.word_to_sign(i, g, pool, rng),
        ]
        exercises: list = []
        for n, gloss in enumerate(glosses):
            for k in range(per_sign):
                exercises.append(makers[(n + k) % (2 if per_sign > 1 else 3)](f"{prefix}-e{len(exercises) + 1}", gloss))
        return exercises

    # ------------------------------------------------------------ consulta

    def path(self) -> PathResponse:
        return PathResponse(title="Trilha de Libras", disclaimer=DISCLAIMER, themes=self.themes)

    def exam_questions(self, theme_id: str, seed: str) -> list[ExamQuestion]:
        """Questões em ordem embaralhada (a mesma para a mesma `seed`), sem o gabarito."""
        items = list(self.exams[theme_id])
        random.Random(seed).shuffle(items)
        return [item.question() for item in items]

    def exam_item(self, theme_id: str, question_id: str) -> ExamItem | None:
        return next((i for i in self.exams[theme_id] if i.id == question_id), None)
