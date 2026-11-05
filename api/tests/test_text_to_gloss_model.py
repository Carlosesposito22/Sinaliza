"""`TextToGloss.resolve` com as decisões do classificador T1 (ML) e sem elas (lista fixa)."""
import re

import pytest

from app.embeddings import CharNgramEmbedder
from app.text_to_gloss import TextToGloss
from app.vocabulary import Vocabulary


class FakeVerdict:
    def __init__(self, start, end, probability):
        self.start, self.end, self.probability = start, end, probability

    @property
    def keep(self):
        return self.probability >= 0.5


def verdicts_for(text, probabilities):
    """Uma decisão por palavra do texto, na ordem, com a posição em caracteres."""
    return [FakeVerdict(m.start(), m.end(), p) for m, p in zip(re.finditer(r"\w+", text), probabilities)]


@pytest.fixture(scope="module")
def vocabulary():
    return Vocabulary.load()


@pytest.fixture(scope="module")
def resolver(vocabulary):
    return TextToGloss(vocabulary, CharNgramEmbedder())


def test_model_discard_overrides_vocabulary(resolver):
    text = "mãe escola vai"
    matches = resolver.resolve(text, verdicts_for(text, [0.97, 0.05, 0.9]))
    by_word = {m.word: m for m in matches}
    assert by_word["mãe"].gloss == "MÃE" and by_word["mãe"].decision == "MANTER"
    assert by_word["escola"].kind == "function" and by_word["escola"].gloss is None
    assert by_word["escola"].decision == "DESCARTAR" and by_word["escola"].probability == 0.05
    assert TextToGloss.glosses(matches) == ["MÃE", "IR"]  # "vai" é IR pelo lema; "escola" foi descartada


def test_model_keep_replaces_the_fixed_list(resolver):
    # "de" está na lista fixa; se o modelo mantiver, a palavra segue adiante e fica sem sinal.
    kept = resolver.resolve("de", verdicts_for("de", [0.9]))[0]
    assert kept.decision == "MANTER" and kept.kind == "ignored"
    assert resolver.resolve("de")[0].kind == "function"  # sem modelo: lista fixa


def test_without_model_decisions_come_from_the_fixed_list(resolver):
    by_word = {m.word: m for m in resolver.resolve("a mãe vai")}
    assert (by_word["a"].decision, by_word["a"].probability) == ("DESCARTAR", 0.0)
    assert (by_word["mãe"].decision, by_word["mãe"].probability) == ("MANTER", 1.0)


def test_model_discards_known_can_be_turned_off(vocabulary):
    soft = TextToGloss(vocabulary, CharNgramEmbedder(), model_discards_known=False)
    text = "escola banco"
    matches = {m.word: m for m in soft.resolve(text, verdicts_for(text, [0.05, 0.05]))}
    assert matches["escola"].kind == "exact" and matches["escola"].decision == "DESCARTAR"
    assert matches["banco"].kind == "function"  # desconhecida e descartada pelo modelo


def test_phrase_from_the_table_uses_the_mean_probability(resolver):
    text = "dor de cabeça"
    matches = resolver.resolve(text, verdicts_for(text, [0.9, 0.01, 0.8]))
    assert len(matches) == 1
    assert matches[0].gloss == "DOR DE CABEÇA" and matches[0].kind == "exact"
    assert matches[0].probability == pytest.approx(0.57, abs=0.001)
    assert matches[0].n_words == 3


def test_word_without_a_covering_decision_falls_back_to_the_fixed_list(resolver):
    matches = {m.word: m for m in resolver.resolve("a mãe", [FakeVerdict(2, 5, 0.9)])}
    assert matches["a"].kind == "function" and matches["a"].probability == 0.0
    assert matches["mãe"].probability == 0.9


def test_approximation_still_works_for_words_the_model_keeps(resolver):
    match = resolver.resolve("escolla", verdicts_for("escolla", [0.8]))[0]
    assert (match.kind, match.gloss, match.decision, match.probability) == ("approx", "ESCOLA", "MANTER", 0.8)
