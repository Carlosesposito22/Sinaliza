"""Texto em português → glosas, por tabela, lematização e, na falta delas, por embeddings.

Para cada palavra (ou grupo de até `max_words` palavras seguidas, como "dor de cabeça"),
nesta ordem:

1. `exact`: a forma (com acento, sem diferença de caixa) é uma das formas `pt` de um
   sinal; ou, se não for, o **lema** dela é (ex.: "aconteceu" → "acontecer"). Sem acento
   só vale se uma única glosa casar (assim "avó" e "avô" não se misturam).
2. `function`: artigo, preposição, conjunção ou palavra de até 2 letras sem sinal. Não é
   tratada como falha.
3. `approx`: a palavra não está na tabela, mas o embedding a aproxima de uma forma
   conhecida com similaridade >= limiar. É uma **proposta**: proximidade de escrita ou
   de sentido não garante que o sinal sirva.
4. `ignored`: sem correspondência. A interface precisa avisar o usuário.

Isto não é tradução para Libras: a saída é a sequência de sinais na ordem do texto.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .embeddings import Embedder
from .vocabulary import Vocabulary, slug

Kind = Literal["exact", "approx", "function", "ignored"]
Lemmatizer = Callable[[str], str]

FUNCTION_WORDS = frozenset(
    slug(w)
    for w in (
        "a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela pelos "
        "pelas para pra com sem sob sobre ao aos à às e ou mas que se como quando "
        "eu tu ele ela nós vós eles elas você vocês me te lhe nos lhes "
        "meu minha meus minhas teu tua seu sua seus suas nosso nossa nossos nossas "
        "isso isto aquilo esse essa esses essas este esta estes estas aquele aquela "
        "é são foi foram era eram ser sou somos está estão estou estamos estava estavam "
        "há já só também"
    ).split()
)

MIN_APPROX_LENGTH = 3


def default_lemmatizer() -> Lemmatizer | None:
    """Lematizador do simplemma para português; `None` se o pacote não estiver instalado."""
    try:
        import simplemma
    except ImportError:
        return None
    return lambda word: simplemma.lemmatize(word, lang="pt")


@dataclass(frozen=True)
class Match:
    word: str
    gloss: str | None
    kind: Kind
    score: float


class TextToGloss:
    def __init__(
        self,
        vocabulary: Vocabulary,
        embedder: Embedder,
        threshold: float | None = None,
        lemmatizer: Lemmatizer | None | str = "default",
    ):
        self.vocabulary = vocabulary
        self.embedder = embedder
        self.threshold = embedder.default_threshold if threshold is None else threshold
        self.lemmatizer = default_lemmatizer() if lemmatizer == "default" else lemmatizer
        self._form_vectors = embedder.embed(vocabulary.forms)
        if self.lemmatizer is not None:
            self.lemmatizer("casa")  # carrega os dicionários agora, não na primeira requisição

    def _known(self, text: str) -> str | None:
        gloss = self.vocabulary.lookup(text)
        if gloss is None and self.lemmatizer is not None and " " not in text:
            gloss = self.vocabulary.lookup(self.lemmatizer(text.lower()))
        return gloss

    def resolve(self, text: str) -> list[Match]:
        words = re.findall(r"\w+", text, re.UNICODE)
        matches: list[Match | None] = []
        unknown: list[tuple[int, str]] = []
        i = 0
        while i < len(words):
            taken = 0
            for size in range(min(self.vocabulary.max_words, len(words) - i), 1, -1):
                phrase = " ".join(words[i : i + size])
                gloss = self.vocabulary.lookup(phrase)
                if gloss is not None:
                    matches.append(Match(phrase, gloss, "exact", 1.0))
                    taken = size
                    break
            if taken:
                i += taken
                continue

            word = words[i]
            i += 1
            key = slug(word)
            gloss = self._known(word)
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
