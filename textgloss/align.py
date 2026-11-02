"""Rotulagem automática da tarefa T1 (manter ou descartar cada palavra).

ETAPA: regra de alinhamento que GERA os rótulos do ML. A decisão aprendida vem depois (train);
aqui só se transforma o trabalho dos intérpretes (glosa) em exemplos supervisionados.
"""
from . import corpus

MANTER = 1
DESCARTAR = 0

# Os intérpretes escrevem numerais em dígitos ("sete" → 7); sem isso, "sete" seria falso DESCARTAR.
_NUMBERS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "treze": 13, "quatorze": 14, "catorze": 14, "quinze": 15, "dezesseis": 16,
    "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
    "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80,
    "noventa": 90, "cem": 100, "cento": 100, "mil": 1000,
}


def candidate_keys(text: str, lemma: str) -> set[str]:
    """Chaves `slug()` que, se estiverem na glosa, indicam que a palavra virou sinal.

    O spaCy devolve lemas compostos para clíticos e contrações ("candidatar-se" → "candidatar se",
    "em o"); nesses casos vale também a primeira parte, que é o que o intérprete glosa.
    """
    keys = {corpus.slug(lemma), corpus.slug(text)}
    first = lemma.split()[0] if lemma.split() else ""
    keys.add(corpus.slug(first))
    number = _NUMBERS.get(corpus.slug(text))
    if number is not None:
        keys.add(str(number))
    keys.discard("")
    return keys


def label_token(text: str, lemma: str, gloss_key_set: set[str]) -> int:
    """MANTER se alguma chave candidata da palavra aparece entre os sinais da glosa."""
    if candidate_keys(text, lemma) & gloss_key_set:
        return MANTER
    return DESCARTAR
