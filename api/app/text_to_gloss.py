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

Quem decide se a palavra vira sinal (MANTER ou DESCARTAR) é o **classificador T1** (ML nosso, ver
`textgloss/infer.py`), quando a API o recebe em `decisions`. Sem ele, vale a lista fixa `FUNCTION_WORDS`
(plano B, `model_version: "lista-fixa"`). Com o modelo, as etapas ficam assim:

0. frases da tabela com mais de uma palavra ("dor de cabeça") vencem o modelo (regra, não ML);
1. DESCARTAR do modelo → `function` (sem sinal), mesmo que a palavra esteja no vocabulário, a não ser
   que `model_discards_known=False`;
2. as demais seguem para tabela/lema (`exact`), aproximação (`approx`) ou `ignored`.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

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


class Verdict(Protocol):
    """Decisão do classificador para uma palavra (ver `textgloss.infer.WordDecision`)."""

    start: int
    end: int
    probability: float
    keep: bool


@dataclass(frozen=True)
class Match:
    word: str
    gloss: str | None
    kind: Kind
    score: float
    # O que o classificador decidiu (MANTER/DESCARTAR) e a probabilidade de MANTER. Sem modelo, vêm da
    # lista fixa: DESCARTAR/0 para palavra de função, MANTER/1 para o resto.
    decision: Literal["MANTER", "DESCARTAR"] = "MANTER"
    probability: float = 1.0

    @property
    def n_words(self) -> int:
        return len(self.word.split())


class TextToGloss:
    def __init__(
        self,
        vocabulary: Vocabulary,
        embedder: Embedder,
        threshold: float | None = None,
        lemmatizer: Lemmatizer | None | str = "default",
        model_discards_known: bool = True,
    ):
        self.vocabulary = vocabulary
        self.embedder = embedder
        self.threshold = embedder.default_threshold if threshold is None else threshold
        self.model_discards_known = model_discards_known
        self.lemmatizer = default_lemmatizer() if lemmatizer == "default" else lemmatizer
        self._form_vectors = embedder.embed(vocabulary.forms)
        if self.lemmatizer is not None:
            self.lemmatizer("casa")  # carrega os dicionários agora, não na primeira requisição

    def _known(self, text: str) -> str | None:
        gloss = self.vocabulary.lookup(text)
        if gloss is None and self.lemmatizer is not None and " " not in text:
            gloss = self.vocabulary.lookup(self.lemmatizer(text.lower()))
        return gloss

    @staticmethod
    def _verdict_at(position: int, decisions: Sequence[Verdict] | None) -> Verdict | None:
        """Decisão do token do classificador que cobre o caractere `position` (None se nenhum cobre)."""
        for decision in decisions or ():
            if decision.start <= position < decision.end:
                return decision
        return None

    def resolve(self, text: str, decisions: Sequence[Verdict] | None = None) -> list[Match]:
        found = list(re.finditer(r"\w+", text, re.UNICODE))
        words = [m.group() for m in found]
        verdicts = [self._verdict_at(m.start(), decisions) for m in found]
        matches: list[Match | None] = []
        unknown: list[tuple[int, str, Verdict | None]] = []
        i = 0
        while i < len(words):
            taken = 0
            for size in range(min(self.vocabulary.max_words, len(words) - i), 1, -1):
                phrase = " ".join(words[i : i + size])
                gloss = self.vocabulary.lookup(phrase)
                if gloss is not None:
                    probabilities = [v.probability for v in verdicts[i : i + size] if v is not None]
                    mean = sum(probabilities) / len(probabilities) if probabilities else 1.0
                    decision = "MANTER" if mean >= 0.5 else "DESCARTAR"
                    matches.append(Match(phrase, gloss, "exact", 1.0, decision, round(mean, 4)))
                    taken = size
                    break
            if taken:
                i += taken
                continue

            word, verdict = words[i], verdicts[i]
            i += 1
            key = slug(word)
            if verdict is not None and not verdict.keep and self.model_discards_known:
                matches.append(Match(word, None, "function", 0.0, "DESCARTAR", round(verdict.probability, 4)))
                continue
            gloss = self._known(word)
            if gloss is not None:
                matches.append(self._with_verdict(Match(word, gloss, "exact", 1.0), verdict))
            elif verdict is None and key in FUNCTION_WORDS:
                matches.append(Match(word, None, "function", 0.0, "DESCARTAR", 0.0))
            elif verdict is not None and not verdict.keep:
                matches.append(Match(word, None, "function", 0.0, "DESCARTAR", round(verdict.probability, 4)))
            elif len(key) < MIN_APPROX_LENGTH:
                if verdict is None:
                    matches.append(Match(word, None, "function", 0.0, "DESCARTAR", 0.0))
                else:
                    matches.append(self._with_verdict(Match(word, None, "ignored", 0.0), verdict))
            else:
                unknown.append((len(matches), word, verdict))
                matches.append(None)

        if unknown:
            vectors = self.embedder.embed([word for _, word, _ in unknown])
            similarity = vectors @ self._form_vectors.T
            for (position, word, verdict), row in zip(unknown, similarity):
                best = int(np.argmax(row))
                score = float(row[best])
                if score >= self.threshold:
                    gloss = self.vocabulary.gloss_of_form[best]
                    match = Match(word, gloss, "approx", round(score, 3))
                else:
                    match = Match(word, None, "ignored", round(max(score, 0.0), 3))
                matches[position] = self._with_verdict(match, verdict)

        return [m for m in matches if m is not None]

    @staticmethod
    def _with_verdict(match: Match, verdict: Verdict | None) -> Match:
        """Anexa a decisão do modelo; sem ela, a palavra segue como MANTER (regra da lista fixa)."""
        if verdict is None:
            return match
        decision = "MANTER" if verdict.keep else "DESCARTAR"
        return Match(match.word, match.gloss, match.kind, match.score, decision, round(verdict.probability, 4))

    @staticmethod
    def glosses(matches: list[Match]) -> list[str]:
        return [m.gloss for m in matches if m.gloss is not None]
