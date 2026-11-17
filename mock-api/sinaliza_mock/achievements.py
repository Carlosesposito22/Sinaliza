"""Conquistas (medalhas e troféus) da trilha. Regra, não ML.

Cada conquista olha para números simples do progresso (`Stats`) e diz se foi alcançada e, quando é de
contagem, quanto falta (`current`/`target`). O `Store` avalia todas depois de cada aula ou prova e guarda
a data da primeira vez; conquista ganha nunca é perdida.

Para criar uma conquista nova: acrescente um `Achievement` em `catalog()` com um `id` estável (o front e
o progresso guardado usam o id) e um teste em tests/test_achievements.py.
"""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stats:
    lessons_done: int = 0  # aulas feitas ao menos uma vez
    perfect_lessons: int = 0  # aulas com 100% de acerto
    exams_taken: int = 0  # provas entregues (todas as tentativas)
    themes_passed: int = 0
    perfect_exams: int = 0  # temas com nota 100% na prova
    first_try_passes: int = 0  # temas aprovados na primeira tentativa
    comebacks: int = 0  # temas aprovados depois de reprovar
    passed_theme_ids: frozenset[str] = field(default_factory=frozenset)
    best_streak: int = 0
    level: int = 1
    reviews_done: int = 0  # revisões dos erros aprovadas
    challenges_done: int = 0  # desafios do dia aprovados (um por dia)


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    description: str
    kind: str  # "medal" ou "trophy"
    tier: str  # "bronze", "silver" ou "gold"
    category: str  # "provas", "temas", "aulas" ou "habito"
    icon: str  # nome curto; o front escolhe o desenho
    measure: Callable[[Stats], int]
    target: int = 1

    def check(self, stats: Stats) -> tuple[bool, int]:
        current = min(self.measure(stats), self.target)
        return current >= self.target, current


def catalog(themes: list[tuple[str, str]]) -> list[Achievement]:
    """`themes`: (id, título) de cada tema, na ordem da trilha. Cada tema ganha um troféu próprio."""
    items = [
        # ---- provas
        Achievement("primeira-prova", "Primeira prova", "Entregue a sua primeira prova de tema.",
                    "medal", "bronze", "provas", "exam", lambda s: s.exams_taken),
        Achievement("aprovado", "Aprovado!", "Passe na prova de um tema.",
                    "medal", "silver", "provas", "check", lambda s: s.themes_passed),
        Achievement("nota-maxima", "Nota máxima", "Tire 100% numa prova de tema.",
                    "trophy", "gold", "provas", "star", lambda s: s.perfect_exams),
        Achievement("de-primeira", "De primeira", "Passe numa prova na primeira tentativa.",
                    "medal", "silver", "provas", "rocket", lambda s: s.first_try_passes),
        Achievement("volta-por-cima", "Volta por cima", "Passe numa prova depois de ter reprovado nela.",
                    "medal", "gold", "provas", "comeback", lambda s: s.comebacks),
        Achievement("persistente", "Persistente", "Entregue 5 provas.",
                    "medal", "silver", "provas", "exam", lambda s: s.exams_taken, target=5),
        # ---- aulas
        Achievement("primeira-aula", "Primeiro sinal", "Conclua a sua primeira aula.",
                    "medal", "bronze", "aulas", "hand", lambda s: s.lessons_done),
        Achievement("aula-perfeita", "Aula perfeita", "Acerte tudo numa aula.",
                    "medal", "bronze", "aulas", "star", lambda s: s.perfect_lessons),
        Achievement("caprichoso", "Capricho", "Acerte tudo em 5 aulas diferentes.",
                    "medal", "silver", "aulas", "star", lambda s: s.perfect_lessons, target=5),
        Achievement("dez-aulas", "Dez aulas", "Conclua 10 aulas diferentes.",
                    "medal", "silver", "aulas", "book", lambda s: s.lessons_done, target=10),
        # ---- hábito
        Achievement("sequencia-3", "Três dias seguidos", "Estude 3 dias seguidos.",
                    "medal", "bronze", "habito", "flame", lambda s: s.best_streak, target=3),
        Achievement("sequencia-7", "Uma semana seguida", "Estude 7 dias seguidos.",
                    "trophy", "gold", "habito", "flame", lambda s: s.best_streak, target=7),
        Achievement("nivel-3", "Nível 3", "Chegue ao nível 3.",
                    "medal", "silver", "habito", "level", lambda s: s.level, target=3),
        Achievement("revisor", "Revisor", "Termine uma revisão dos seus erros.",
                    "medal", "bronze", "habito", "review", lambda s: s.reviews_done),
        Achievement("desafio-do-dia", "Desafio aceito", "Passe no desafio do dia.",
                    "medal", "bronze", "habito", "bolt", lambda s: s.challenges_done),
        Achievement("desafio-5", "Cinco desafios", "Passe no desafio do dia 5 vezes.",
                    "trophy", "silver", "habito", "bolt", lambda s: s.challenges_done, target=5),
    ]
    # ---- temas: um troféu por tema e um para a trilha inteira
    for theme_id, title in themes:
        items.append(
            Achievement(f"tema-{theme_id}", f"Tema {title}", f"Passe na prova do tema {title}.",
                        "trophy", "bronze", "temas", "trophy",
                        lambda s, tid=theme_id: int(tid in s.passed_theme_ids))
        )
    items.append(
        Achievement("trilha-completa", "Trilha completa", "Passe na prova de todos os temas.",
                    "trophy", "gold", "temas", "crown", lambda s: s.themes_passed, target=max(1, len(themes)))
    )
    return items
