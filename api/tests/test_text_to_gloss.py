import sys
from types import ModuleType

import numpy as np
import pytest

from app.embeddings import CharNgramEmbedder, SentenceTransformerEmbedder, build_embedder
from app.text_to_gloss import TextToGloss
from app.vocabulary import Vocabulary, slug


@pytest.fixture(scope="module")
def vocabulary():
    return Vocabulary.load()


@pytest.fixture(scope="module")
def resolver(vocabulary):
    return TextToGloss(vocabulary, CharNgramEmbedder())


def kinds(matches):
    return [(m.word, m.kind, m.gloss) for m in matches]


def test_vocabulary_forms_are_unique_and_cover_every_sign(vocabulary):
    assert len(vocabulary.signs) == 20
    assert len(vocabulary.by_form) == len({slug(f) for f in vocabulary.forms})
    for sign in vocabulary.signs:
        assert all(vocabulary.by_form[slug(f)] == sign.gloss for f in sign.forms)
    assert set(vocabulary.gloss_of_form) == set(vocabulary.by_gloss)
    assert vocabulary.contexts == ["geral", "escola", "serviços", "saúde", "trabalho", "família"]


def test_exact_match_ignores_accents_and_case_and_keeps_text_order(resolver):
    matches = resolver.resolve("MAÇA e américa, 5 alunas")
    assert kinds(matches) == [
        ("MAÇA", "exact", "MAÇÃ"),
        ("e", "function", None),
        ("américa", "exact", "AMÉRICA"),
        ("5", "exact", "CINCO"),
        ("alunas", "exact", "ALUNO"),
    ]
    assert TextToGloss.glosses(matches) == ["MAÇÃ", "AMÉRICA", "CINCO", "ALUNO"]


def test_function_and_short_words_are_not_failures(resolver):
    matches = resolver.resolve("o de ir eu pra")
    assert {m.kind for m in matches} == {"function"}


def test_approximation_catches_inflection_and_typos_but_not_look_alikes(resolver):
    approx = {m.word: m.gloss for m in resolver.resolve("alunoss vacinando americas baneiro") if m.kind == "approx"}
    assert approx == {
        "alunoss": "ALUNO",
        "vacinando": "VACINA",
        "americas": "AMÉRICA",
        "baneiro": "BANHEIRO",
    }
    rejected = resolver.resolve("banca maquina casa hospital")
    assert {m.kind for m in rejected} == {"ignored"}
    assert all(m.gloss is None for m in rejected)


def test_threshold_controls_approximation(vocabulary):
    strict = TextToGloss(vocabulary, CharNgramEmbedder(), threshold=0.99)
    assert strict.resolve("alunoss")[0].kind == "ignored"
    loose = TextToGloss(vocabulary, CharNgramEmbedder(), threshold=0.1)
    assert loose.resolve("banca")[0].kind == "approx"


def test_empty_text_has_no_matches(resolver):
    assert resolver.resolve("?!... ,") == []


class FakeSemanticEmbedder:
    """Sinônimo de FILHO fica no eixo de FILHO; formas dos outros sinais, em outro; palavras alheias, em um terceiro."""

    name = "fake"
    default_threshold = 0.8

    def embed(self, words):
        rows = []
        for word in words:
            vector = np.zeros(3, dtype=np.float32)
            if slug(word) in {"FILHO", "FILHOS", "FILHA", "FILHAS", "GAROTO", "CRIANCA"}:
                vector[0] = 1.0
            elif slug(word) == "MESA":
                vector[2] = 1.0
            else:
                vector[1] = 1.0
            rows.append(vector)
        return np.array(rows)


def test_any_embedder_plugs_in_and_semantic_synonym_is_flagged_as_approx(vocabulary):
    resolver = TextToGloss(vocabulary, FakeSemanticEmbedder())
    assert resolver.threshold == 0.8
    garoto = resolver.resolve("garoto")[0]
    assert (garoto.kind, garoto.gloss) == ("approx", "FILHO")
    assert garoto.score == pytest.approx(1.0)
    assert resolver.resolve("mesa")[0].kind == "ignored"


def test_char_ngram_embedder_is_deterministic_normalized_and_form_sensitive():
    embedder = CharNgramEmbedder()
    a = embedder.embed(["vacina", "vacina", "vacinas", "sapo"])
    np.testing.assert_array_equal(a[0], a[1])
    np.testing.assert_allclose(np.linalg.norm(a, axis=1), 1.0, atol=1e-5)
    assert a[0] @ a[2] > 0.7 > a[0] @ a[3]


def test_build_embedder_selects_by_name_and_rejects_unknown(monkeypatch):
    assert isinstance(build_embedder("char-ngram"), CharNgramEmbedder)
    monkeypatch.setenv("SINALIZA_EMBEDDER", "char-ngram")
    assert isinstance(build_embedder(), CharNgramEmbedder)
    with pytest.raises(ValueError):
        build_embedder("word2vec")


def test_sentence_transformer_adapter_lowercases_and_returns_float32(monkeypatch):
    class FakeModel:
        def __init__(self, name):
            self.name = name

        def encode(self, words, normalize_embeddings):
            assert normalize_embeddings
            self.seen = words
            return [[1.0, 0.0]] * len(words)

    module = ModuleType("sentence_transformers")
    module.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    embedder = SentenceTransformerEmbedder("modelo-x")
    out = embedder.embed(["Garoto", "MENINA"])
    assert embedder.model.seen == ["garoto", "menina"]
    assert out.dtype == np.float32 and out.shape == (2, 2)
