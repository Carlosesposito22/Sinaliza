"""Monta a trilha de aprendizado a partir do vocabulário curado (data/vocabulary.json).

Regra do projeto: nenhum sinal é inventado. Toda lição usa só glosas do vocabulário, que existem no
dicionário do VLibras; os rótulos não foram validados por falante de Libras (ver `DISCLAIMER`).
O conteúdo é determinístico: a mesma trilha sai a cada subida do mock.
"""

import json
import os
import random
from pathlib import Path

from .schemas import (
    Lesson,
    LessonSummary,
    LearnSign,
    MatchPairs,
    Pair,
    PathResponse,
    SignOption,
    SignToWord,
    TextOption,
    Unit,
    WordToSign,
)

ROOT = Path(__file__).resolve().parents[2]
VOCABULARY = Path(os.environ.get("SINALIZA_VOCABULARY", ROOT / "data" / "vocabulary.json"))

DISCLAIMER = (
    "Sinais do vocabulário curado pela equipe a partir do dicionário do VLibras; os rótulos não foram "
    "validados por falante de Libras. Isto é uma sequência de sinais, não uma aula de Libras."
)

# (id do contexto no vocabulário, id da unidade, título, ícone, cor)
UNITS = [
    ("família", "familia", "Família", "👪", "#58cc02"),
    ("geral", "dia-a-dia", "Dia a dia", "☀️", "#ffb020"),
    ("escola", "escola", "Escola", "📚", "#1cb0f6"),
    ("saúde", "saude", "Saúde", "🩺", "#ff4b4b"),
    ("serviços", "servicos", "Serviços", "🏛️", "#a560e8"),
    ("trabalho", "trabalho", "Trabalho", "💼", "#2b70c9"),
]
SIGNS_PER_LESSON = 4
LESSONS_PER_UNIT = 4
XP_PER_LESSON = 20


def load_signs(path: Path = VOCABULARY) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["signs"]


def _word(sign: dict) -> str:
    return sign["pt"][0]


def _choices(rng: random.Random, correct: dict, pool: list[dict], n: int = 3) -> list[dict]:
    """O sinal certo mais `n - 1` distratores com palavra diferente, em ordem embaralhada."""
    seen = {_word(correct)}
    distractors: list[dict] = []
    candidates = [s for s in pool if s["gloss"] != correct["gloss"]]
    rng.shuffle(candidates)
    for sign in candidates:
        if _word(sign) not in seen:
            seen.add(_word(sign))
            distractors.append(sign)
        if len(distractors) == n - 1:
            break
    options = [correct, *distractors]
    rng.shuffle(options)
    return options


class Content:
    def __init__(self, signs: list[dict]):
        self.signs = signs
        self.units: list[Unit] = []
        self.lessons: dict[str, Lesson] = {}
        self.order: list[str] = []
        self._build()

    def _build(self) -> None:
        for context, unit_id, title, icon, color in UNITS:
            members = [s for s in self.signs if s["contexts"][0] == context]
            summaries: list[LessonSummary] = []
            for n in range(LESSONS_PER_UNIT):
                chunk = members[n * SIGNS_PER_LESSON : (n + 1) * SIGNS_PER_LESSON]
                if len(chunk) < SIGNS_PER_LESSON:
                    break
                lesson = self._lesson(unit_id, title, n + 1, chunk, members or self.signs)
                self.lessons[lesson.id] = lesson
                self.order.append(lesson.id)
                summaries.append(
                    LessonSummary(
                        id=lesson.id,
                        title=lesson.title,
                        xp_reward=lesson.xp_reward,
                        n_exercises=len(lesson.exercises),
                        glosses=[s["gloss"] for s in chunk],
                    )
                )
            if summaries:
                self.units.append(
                    Unit(
                        id=unit_id,
                        title=title,
                        description=f"{len(summaries) * SIGNS_PER_LESSON} sinais de {title.lower()}",
                        color=color,
                        icon=icon,
                        lessons=summaries,
                    )
                )

    def _lesson(self, unit_id: str, unit_title: str, number: int, chunk: list[dict], pool: list[dict]) -> Lesson:
        lesson_id = f"{unit_id}-{number}"
        rng = random.Random(lesson_id)
        wide_pool = pool if len(pool) >= 8 else self.signs
        exercises: list = []

        def new_id() -> str:
            return f"{lesson_id}-e{len(exercises) + 1}"

        for sign in chunk:
            exercises.append(
                LearnSign(id=new_id(), gloss=sign["gloss"], word_pt=_word(sign), forms=list(sign["pt"]))
            )
        for sign in chunk:
            options = _choices(rng, sign, wide_pool)
            ids = {s["gloss"]: chr(ord("a") + i) for i, s in enumerate(options)}
            exercises.append(
                SignToWord(
                    id=new_id(),
                    gloss=sign["gloss"],
                    options=[TextOption(id=ids[s["gloss"]], text=_word(s)) for s in options],
                    correct_option_id=ids[sign["gloss"]],
                )
            )
        for sign in chunk:
            options = _choices(rng, sign, wide_pool)
            ids = {s["gloss"]: chr(ord("a") + i) for i, s in enumerate(options)}
            exercises.append(
                WordToSign(
                    id=new_id(),
                    text=_word(sign),
                    options=[SignOption(id=ids[s["gloss"]], gloss=s["gloss"]) for s in options],
                    correct_option_id=ids[sign["gloss"]],
                )
            )
        pairs = [Pair(id=f"p{i + 1}", gloss=s["gloss"], text=_word(s)) for i, s in enumerate(chunk)]
        rng.shuffle(pairs)
        exercises.append(MatchPairs(id=new_id(), pairs=pairs))
        return Lesson(
            id=lesson_id,
            unit_id=unit_id,
            title=f"{unit_title} {number}",
            xp_reward=XP_PER_LESSON,
            exercises=exercises,
        )

    def path(self) -> PathResponse:
        return PathResponse(title="Trilha de Libras", disclaimer=DISCLAIMER, units=self.units)
