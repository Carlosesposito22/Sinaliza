"""Correção da prova do tema (regra, não ML). Funções puras: a API real deve seguir as mesmas regras.

A pessoa vê o avatar sinalizar (sem legenda) e escreve o que entendeu. A correção é por sinal:

1. Normaliza a resposta: minúsculas, sem acento, sem pontuação, separada em palavras.
2. Para cada glosa da questão, procura na resposta uma das formas aceitas daquele sinal
   (`accept` em data/trilha.json; ex.: PODER aceita "posso", "pode"...). Cada palavra da resposta
   só vale para um sinal. A ordem não importa: a sequência segue o português e não afirmamos nada
   sobre a ordem dos sinais em Libras.
3. Palavras que sobram contam como erro (para não valer escrever todas as palavras do tema), exceto
   palavras sem sinal próprio: as palavras funcionais (artigos, preposições...) e as da frase esperada
   que não viraram sinal (ex.: "precisa" em "O doente precisa dormir").
4. Nota da questão = sinais acertados / (sinais da questão + palavras que sobraram), de 0 a 1.
   Nota da prova = média das questões.
"""

import re
import unicodedata
from dataclasses import dataclass

# Palavras sem sinal próprio nas frases da trilha. Comparadas já sem acento.
FUNCTION_WORDS = frozenset(
    "a o as os um uma uns umas de do da dos das em no na nos nas ao aos para pra pro por pelo pela "
    "com e ou que se me te lhe eu ele ela voce esta estou sao".split()
)

_WORD = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """Minúsculas e sem acento: "Mãe" → "mae"."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def words(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


@dataclass(frozen=True)
class SignMatch:
    gloss: str
    correct: bool


@dataclass(frozen=True)
class Grade:
    score: float
    signs: list[SignMatch]
    extra_words: list[str]


def grade_answer(answer: str, glosses: list[str], accept: dict[str, list[str]], expected_text: str = "") -> Grade:
    """Corrige uma resposta. `accept` leva cada glosa às suas formas aceitas (com ou sem acento)."""
    tokens = words(answer)
    used = [False] * len(tokens)
    results: list[SignMatch] = []
    for gloss in glosses:
        forms = sorted({tuple(words(form)) for form in accept.get(gloss, [])} - {()}, key=len, reverse=True)
        results.append(SignMatch(gloss=gloss, correct=_consume(tokens, used, forms)))

    free = FUNCTION_WORDS | set(words(expected_text))
    extra = [t for t, u in zip(tokens, used) if not u and t not in free]
    matched = sum(r.correct for r in results)
    denominator = len(glosses) + len(extra)
    score = matched / denominator if denominator else 0.0
    return Grade(score=round(score, 4), signs=results, extra_words=extra)


def _consume(tokens: list[str], used: list[bool], forms: list[tuple[str, ...]]) -> bool:
    """Marca como usada a primeira ocorrência livre de alguma forma (as mais longas primeiro)."""
    for form in forms:
        size = len(form)
        for start in range(len(tokens) - size + 1):
            window = range(start, start + size)
            if not any(used[i] for i in window) and tuple(tokens[i] for i in window) == form:
                for i in window:
                    used[i] = True
                return True
    return False


def exam_score(question_scores: list[float]) -> float:
    return round(sum(question_scores) / len(question_scores), 4) if question_scores else 0.0
