import pytest

from app import phrases
from app.embeddings import CharNgramEmbedder
from app.text_to_gloss import TextToGloss
from app.vocabulary import Vocabulary


@pytest.fixture(scope="module")
def vocabulary():
    return Vocabulary.load()


@pytest.fixture(scope="module")
def resolver(vocabulary):
    return TextToGloss(vocabulary, CharNgramEmbedder())


def test_committed_phrases_file_is_up_to_date(vocabulary, resolver):
    expected = phrases.dumps(phrases.generate(vocabulary, resolver))
    assert phrases.DEFAULT_PATH.read_text(encoding="utf-8") == expected


def test_every_category_has_phrases_with_two_signs_and_a_sign_of_its_context(vocabulary):
    for category in phrases.load(phrases.DEFAULT_PATH):
        assert category["phrases"], category["label"]
        for phrase in category["phrases"]:
            assert len(phrase["glosses"]) >= 2
            if category["label"] != "geral":
                assert any(category["label"] in vocabulary.by_gloss[g].contexts for g in phrase["glosses"])


def test_expand_fills_slots_in_declared_order():
    assert phrases.expand("{a} e {b}", {"a": ["x", "y"], "b": ["1", "2"]}) == ["x e 1", "x e 2", "y e 1", "y e 2"]
    assert phrases.expand("sem lacunas", {}) == ["sem lacunas"]


def test_generate_rejects_a_phrase_that_needs_embedding_approximation(vocabulary, resolver, monkeypatch):
    templates = {k: list(v) for k, v in phrases.TEMPLATES.items()}
    templates["escola"].append(("O alunoss viu o sapo.", {}))
    monkeypatch.setattr(phrases, "TEMPLATES", templates)
    with pytest.raises(ValueError, match="aproximada por embedding"):
        phrases.generate(vocabulary, resolver)


def test_generate_rejects_phrase_without_a_sign_of_the_category(vocabulary, resolver, monkeypatch):
    templates = {k: list(v) for k, v in phrases.TEMPLATES.items()}
    templates["escola"].append(("O sapo amarelo viu a esquina.", {}))
    monkeypatch.setattr(phrases, "TEMPLATES", templates)
    with pytest.raises(ValueError, match="contexto 'escola'"):
        phrases.generate(vocabulary, resolver)


def test_load_returns_empty_when_file_is_missing(tmp_path):
    assert phrases.load(tmp_path / "nao-existe.json") == []
