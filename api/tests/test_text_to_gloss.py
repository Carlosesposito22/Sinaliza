import sys
from types import ModuleType

import numpy as np
import pytest

from app.embeddings import CharNgramEmbedder, SentenceTransformerEmbedder, build_embedder
from app.text_to_gloss import TextToGloss
from app.vocabulary import Sign, Vocabulary, fold, slug


@pytest.fixture(scope="module")
def vocabulary():
    return Vocabulary.load()


@pytest.fixture(scope="module")
def resolver(vocabulary):
    return TextToGloss(vocabulary, CharNgramEmbedder())


def kinds(matches):
    return [(m.word, m.kind, m.gloss) for m in matches]


def test_vocabulary_is_curated_unique_and_covers_the_six_contexts(vocabulary):
    assert 100 <= len(vocabulary.signs) <= 260
    assert set(vocabulary.contexts) == {"escola", "saúde", "serviços", "trabalho", "família", "geral"}
    assert len(vocabulary.by_gloss) == len(vocabulary.signs)
    assert all(sign.video_class for sign in vocabulary.signs)
    owners = {}
    for sign in vocabulary.signs:
        for form in sign.forms:
            assert owners.setdefault(fold(form), sign.gloss) == sign.gloss, form


def test_lookup_keeps_accents_and_falls_back_to_unaccented_only_when_unique():
    vocab = Vocabulary(
        [
            Sign("AVÓ", ("avó",), ("família",)),
            Sign("AVÔ", ("avô",), ("família",)),
            Sign("MAÇÃ", ("maçã",), ("geral",)),
        ]
    )
    assert vocab.lookup("avó") == "AVÓ"
    assert vocab.lookup("AVÔ") == "AVÔ"
    assert vocab.lookup("avo") is None  # ambíguo: não escolhe um dos dois
    assert vocab.lookup("maca") == "MAÇÃ"  # único sem acento: aceita
    assert slug("avó") == slug("avô")


def test_exact_match_ignores_case_and_keeps_text_order(resolver):
    matches = resolver.resolve("HOSPITAL e Escola, médica")
    assert kinds(matches) == [
        ("HOSPITAL", "exact", "HOSPITAL"),
        ("e", "function", None),
        ("Escola", "exact", "ESCOLA"),
        ("médica", "exact", "MÉDICO"),
    ]
    assert TextToGloss.glosses(matches) == ["HOSPITAL", "ESCOLA", "MÉDICO"]


def test_multiword_forms_match_before_single_words(resolver):
    matches = resolver.resolve("Estou com dor de cabeça, por favor")
    assert [(m.word, m.gloss) for m in matches if m.gloss] == [
        ("dor de cabeça", "DOR DE CABEÇA"),
        ("por favor", "POR FAVOR"),
    ]


def test_lemmatizer_maps_inflected_words(resolver):
    matches = resolver.resolve("aconteceram comprando pagou")
    assert TextToGloss.glosses(matches) == ["ACONTECER", "COMPRAR", "PAGAR"]
    assert {m.kind for m in matches} == {"exact"}


def test_lemmatizer_can_be_replaced_or_disabled(vocabulary):
    without = TextToGloss(vocabulary, CharNgramEmbedder(), lemmatizer=None)
    assert without.resolve("aconteceram")[0].kind != "exact"
    fake = TextToGloss(vocabulary, CharNgramEmbedder(), lemmatizer=lambda w: "hospital")
    assert fake.resolve("clínica")[0].gloss == "HOSPITAL"


def test_function_and_short_words_are_not_failures(resolver):
    matches = resolver.resolve("o de eu pra está são")
    assert {m.kind for m in matches} == {"function"}


def test_approximation_catches_typos_but_not_look_alikes(resolver):
    approx = {m.word: m.gloss for m in resolver.resolve("escolla hospitall") if m.kind == "approx"}
    assert approx == {"escolla": "ESCOLA", "hospitall": "HOSPITAL"}
    rejected = resolver.resolve("banco caderno vacina cinema")
    assert {m.kind for m in rejected} == {"ignored"}
    assert all(m.gloss is None for m in rejected)


def test_threshold_controls_approximation(vocabulary):
    strict = TextToGloss(vocabulary, CharNgramEmbedder(), threshold=0.99)
    assert strict.resolve("escolla")[0].kind == "ignored"
    loose = TextToGloss(vocabulary, CharNgramEmbedder(), threshold=0.1)
    assert loose.resolve("banco")[0].kind == "approx"


def test_empty_text_has_no_matches(resolver):
    assert resolver.resolve("?!... ,") == []


class FakeSemanticEmbedder:
    """Sinônimo de GAROTO fica no eixo de GAROTO; formas dos outros sinais, em outro; palavras alheias, em um terceiro."""

    name = "fake"
    default_threshold = 0.8

    def embed(self, words):
        rows = []
        for word in words:
            vector = np.zeros(3, dtype=np.float32)
            if slug(word) in {"GAROTO", "GAROTOS", "MENINO", "MENINOS", "GURI"}:
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
    guri = resolver.resolve("guri")[0]
    assert (guri.kind, guri.gloss) == ("approx", "GAROTO")
    assert guri.score == pytest.approx(1.0)
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
