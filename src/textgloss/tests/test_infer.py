import numpy as np
import pytest

from textgloss import infer, modeling

spacy = pytest.importorskip("spacy")


@pytest.fixture(scope="module")
def nlp():
    from textgloss import features

    try:
        return features.load_nlp()
    except OSError:
        pytest.skip("modelo pt_core_news_md do spaCy não instalado")


class RuleModel:
    """Modelo de mentira: descarta artigos, preposições e auxiliares. Confere as colunas do treino."""

    def predict_proba(self, frame):
        missing = set(modeling.FEATURES) - set(frame.columns)
        assert not missing, missing
        keep = ~frame["upos"].isin(["DET", "ADP", "AUX"])
        p = np.where(keep, 0.9, 0.05)
        return np.column_stack([1 - p, p])


def test_decide_gives_one_decision_per_word_with_character_offsets(nlp):
    text = "O filho está com dor de cabeça."
    decisions = infer.T1Classifier(RuleModel(), nlp, "sinaliza-t1/9").decide(text)
    assert [d.word for d in decisions] == ["O", "filho", "está", "com", "dor", "de", "cabeça"]
    assert all(text[d.start : d.end] == d.word for d in decisions)
    kept = {d.word: d.keep for d in decisions}
    assert kept["filho"] and kept["dor"] and not kept["O"] and not kept["de"]
    assert all(0.0 <= d.probability <= 1.0 for d in decisions)


def test_decide_on_text_without_words_is_empty(nlp):
    assert infer.T1Classifier(RuleModel(), nlp, "x/1").decide("... ?!") == []


def test_threshold_is_the_one_used_in_validation():
    assert infer.THRESHOLD == 0.5
    assert infer.WordDecision(0, 1, "a", 0.5).keep and not infer.WordDecision(0, 1, "a", 0.4999).keep


def test_latest_version_picks_the_highest_registered():
    class Version:
        def __init__(self, v):
            self.version = v

    class Client:
        def __init__(self, versions):
            self.versions = versions

        def search_model_versions(self, query):
            return [Version(v) for v in self.versions]

    assert infer.latest_version(Client(["1", "10", "2"])) == 10
    with pytest.raises(LookupError):
        infer.latest_version(Client([]))
