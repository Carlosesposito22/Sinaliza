import math

from sinaliza_model.data import split_by_signer
from sinaliza_model.synthetic import make_synthetic
from sinaliza_model.train import run

GLOSSES = ["ALUNO", "BANCO", "VACINA"]


def test_training_pipeline_runs_and_learns_the_label():
    samples = make_synthetic(GLOSSES, signers=3, repetitions=4)
    train, val = split_by_signer(samples, {"03"})

    model, results = run(train, val, GLOSSES, seq_len=16, epochs=150)

    first, last = results["train_loss_first_last"]
    assert last < first
    for name in ("global_mean", "class_mean", "medoid", "model"):
        assert math.isfinite(results[name]["mean_dtw"])
        assert set(results[name]["per_gloss"]) == set(GLOSSES)
    assert results["model"]["mean_dtw"] < results["global_mean"]["mean_dtw"]
    assert model.seq_len == 16


def test_retrieval_separates_methods_that_know_the_sign_from_the_global_mean():
    glosses = [f"SINAL{i}" for i in range(8)]
    samples = make_synthetic(glosses, signers=3, repetitions=3)
    train, val = split_by_signer(samples, {"03"})

    _, results = run(train, val, glosses, seq_len=16, epochs=60)

    chance = results["global_mean"]["retrieval"]
    assert chance["chance_top1"] == 1 / 8
    assert chance["top1"] <= 0.5  # sem saber o sinal, perto do acaso
    assert results["class_mean"]["retrieval"]["top1"] >= 0.75
    assert results["class_mean"]["retrieval"]["mean_rank"] < chance["mean_rank"]
    assert results["model"]["retrieval"]["n"] == len(set(s.gloss for s in val))
