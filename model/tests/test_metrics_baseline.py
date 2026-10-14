import numpy as np

from sinaliza_model.baseline import ClassMeanBaseline, GlobalMeanBaseline, MedoidBaseline
from sinaliza_model.data import resample
from sinaliza_model.metrics import dtw_distance
from sinaliza_model.synthetic import make_synthetic

GLOSSES = ["ALUNO", "BANCO", "VACINA"]


def test_dtw_is_zero_for_identical_and_symmetric():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(10, 75, 3)).astype(np.float32)
    b = rng.normal(size=(12, 75, 3)).astype(np.float32)
    assert dtw_distance(a, a) == 0
    assert np.isclose(dtw_distance(a, b), dtw_distance(b, a))


def test_dtw_tolerates_time_stretch_better_than_different_motion():
    samples = make_synthetic(GLOSSES, signers=1, repetitions=1)
    aluno = samples[0].keypoints
    stretched = resample(aluno, int(len(aluno) * 1.5))
    other = samples[1].keypoints
    assert dtw_distance(aluno, stretched) < dtw_distance(aluno, other)


def test_baselines_return_expected_shape():
    samples = make_synthetic(GLOSSES, signers=2, repetitions=2)
    for baseline in (MedoidBaseline(16), ClassMeanBaseline(16), GlobalMeanBaseline(16)):
        out = baseline.fit(samples).generate("ALUNO")
        assert out.shape == (16, 75, 3)


def test_medoid_is_one_of_the_training_recordings():
    samples = make_synthetic(GLOSSES, signers=2, repetitions=3)
    medoid = MedoidBaseline(16).fit(samples).generate("BANCO")
    candidates = [resample(s.keypoints, 16) for s in samples if s.gloss == "BANCO"]
    assert any(np.array_equal(medoid, c) for c in candidates)


def test_class_conditioning_beats_global_mean_on_synthetic():
    samples = make_synthetic(GLOSSES, signers=3, repetitions=3)
    train = [s for s in samples if s.signer != "03"]
    val = [s for s in samples if s.signer == "03"]
    class_mean = ClassMeanBaseline(16).fit(train)
    global_mean = GlobalMeanBaseline(16).fit(train)

    def mean_dtw(baseline):
        return np.mean(
            [dtw_distance(baseline.generate(s.gloss), resample(s.keypoints, 16)) for s in val]
        )

    assert mean_dtw(class_mean) < mean_dtw(global_mean)
