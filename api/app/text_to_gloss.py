"""Texto em português → glosas, por tabela e, na falta dela, por embeddings.

Para cada palavra do texto, nesta ordem:

1. `exact`: a palavra (sem acento e caixa) é uma das formas `pt` de um sinal.
2. `function`: artigo, preposição, conjunção ou palavra de até 2 letras. Não tem
   sinal próprio no MVP e não é tratada como falha.
3. `approx`: a palavra não está na tabela, mas o embedding a aproxima de uma forma
   conhecida com similaridade >= limiar. É uma **proposta**: proximidade de
   escrita ou de sentido não garante que o sinal sirva.
4. `ignored`: sem correspondência. A interface precisa avisar o usuário.

Isto não é tradução para Libras: a saída é a sequência de sinais na ordem do texto.
"""

import re
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .embeddings import Embedder
from .vocabulary import Vocabulary, slug

Kind = Literal["exact", "approx", "function", "ignored"]

FUNCTION_WORDS = frozenset(
    slug(w)
    for w in (
        "a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela pelos "
        "pelas para pra com sem sob sobre ao aos à às e ou mas que se como quando"
    ).split()
)

MIN_APPROX_LENGTH = 3


@dataclass(frozen=True)
class Match:
    word: str
    gloss: str | None
    kind: Kind
    score: float


class TextToGloss:
    def __init__(self, vocabulary: Vocabulary, embedder: Embedder, threshold: float | None = None):
        self.vocabulary = vocabulary
        self.embedder = embedder
        self.threshold = embedder.default_threshold if threshold is None else threshold
        self._form_vectors = embedder.embed(vocabulary.forms)

    def resolve(self, text: str) -> list[Match]:
        words = re.findall(r"\w+", text, re.UNICODE)
        matches: list[Match | None] = []
        unknown: list[tuple[int, str]] = []
        for word in words:
            key = slug(word)
            gloss = self.vocabulary.by_form.get(key)
            if gloss is not None:
                matches.append(Match(word, gloss, "exact", 1.0))
            elif key in FUNCTION_WORDS or len(key) < MIN_APPROX_LENGTH:
                matches.append(Match(word, None, "function", 0.0))
            else:
                unknown.append((len(matches), word))
                matches.append(None)

        if unknown:
            vectors = self.embedder.embed([word for _, word in unknown])
            similarity = vectors @ self._form_vectors.T
            for (position, word), row in zip(unknown, similarity):
                best = int(np.argmax(row))
                score = float(row[best])
                if score >= self.threshold:
                    gloss = self.vocabulary.gloss_of_form[best]
                    matches[position] = Match(word, gloss, "approx", round(score, 3))
                else:
                    matches[position] = Match(word, None, "ignored", round(max(score, 0.0), 3))

        return [m for m in matches if m is not None]

    @staticmethod
    def glosses(matches: list[Match]) -> list[str]:
        return [m.gloss for m in matches if m.gloss is not None]
