from pathlib import Path

import numpy as np
import pytest

from sinaliza_model.data import (
    Sample,
    fill_missing_hands,
    load_dataset,
    load_vocabulary,
    resample,
    slug,
    split_by_signer,
)

VOCABULARY = Path(__file__).resolve().parents[2] / "data" / "vocabulary.json"


def test_vocabulary_has_20_unique_glosses():
    glosses = load_vocabulary(VOCABULARY)
    assert len(glosses) == 20
    assert len(set(glosses)) == 20


def test_slug_removes_accents_and_case():
    assert slug("Maçã") == "MACA"
    assert slug("américa") == "AMERICA"


def test_resample_keeps_endpoints_and_length():
    seq = np.arange(10, dtype=np.float32)[:, None, None] * np.ones((1, 75, 3), np.float32)
    out = resample(seq, 4)
    assert out.shape == (4, 75, 3)
    assert out[0, 0, 0] == 0
    assert out[-1, 0, 0] == 9


def test_resample_single_frame():
    seq = np.ones((1, 75, 3), np.float32)
    assert resample(seq, 5).shape == (5, 75, 3)


def test_fill_missing_hands_repeats_last_detection():
    seq = np.zeros((4, 75, 3), np.float32)
    seq[0, 54:75] = 1.0
    seq[1, 54:75] = 2.0
    out = fill_missing_hands(seq)
    assert (out[2, 54:75] == 2.0).all()
    assert (out[3, 54:75] == 2.0).all()
    assert (out[:, 33:54] == 0).all()


def test_fill_missing_hands_fills_leading_frames():
    seq = np.zeros((3, 75, 3), np.float32)
    seq[2, 33:54] = 5.0
    assert (fill_missing_hands(seq)[0, 33:54] == 5.0).all()


def test_load_dataset_matches_vocabulary_and_skips_unknown(tmp_path):
    seq = np.ones((6, 75, 3), np.float32)
    for name in ("MACA_1.npy", "ALUNO_2.npy", "OUTRO_1.npy"):
        folder = tmp_path / "01"
        folder.mkdir(exist_ok=True)
        np.save(folder / name, seq)
    samples = load_dataset(tmp_path, ["MAÇÃ", "ALUNO"])
    assert sorted(s.gloss for s in samples) == ["ALUNO", "MAÇÃ"]
    assert {s.signer for s in samples} == {"01"}


def test_load_dataset_rejects_wrong_shape(tmp_path):
    folder = tmp_path / "01"
    folder.mkdir()
    np.save(folder / "ALUNO_1.npy", np.ones((6, 33, 3), np.float32))
    with pytest.raises(ValueError):
        load_dataset(tmp_path, ["ALUNO"])


def test_split_by_signer_has_no_overlap():
    seq = np.zeros((2, 75, 3), np.float32)
    samples = [Sample("A", "01", seq), Sample("A", "02", seq), Sample("B", "02", seq)]
    train, val = split_by_signer(samples, {"02"})
    assert [s.signer for s in train] == ["01"]
    assert [s.signer for s in val] == ["02", "02"]
