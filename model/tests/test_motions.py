import json

import numpy as np
import pytest

from sinaliza_model.data import Sample, load_dataset
from sinaliza_model.motions import build_motions, save_motions, signer_ranking


def recording(frames: int, hands_every: int, value: float) -> np.ndarray:
    """Gravação em que as mãos só aparecem a cada `hands_every` quadros (zero nos demais)."""
    kp = np.full((frames, 75, 3), value, dtype=np.float32)
    kp[:, 33:] = 0.0
    kp[::hands_every, 33:] = value
    return kp


def samples() -> list[Sample]:
    return [
        Sample("CASA", "01", recording(10, 4, 1.0)),  # 01: mão em 3 de 10 quadros
        Sample("DIA", "01", recording(10, 4, 1.0)),
        Sample("CASA", "02", recording(10, 1, 2.0)),  # 02: mão em todos os quadros
        Sample("DIA", "02", recording(20, 1, 2.0)),
        Sample("SOL", "01", recording(8, 4, 3.0)),  # SOL só existe para o 01
    ]


def test_signer_ranking_puts_the_signer_with_more_hand_frames_first():
    assert signer_ranking(samples()) == ["02", "01"]


def test_recording_uses_the_same_signer_and_falls_back_when_a_sign_is_missing():
    motions, meta = build_motions(samples(), ["CASA", "DIA", "SOL", "LUA"])
    assert meta["signer"] == "02" and meta["method"] == "recording"
    assert meta["fallback_to_other_signer"] == ["SOL"]
    assert meta["missing"] == ["LUA"]
    assert set(motions) == {"CASA", "DIA", "SOL"}
    assert motions["CASA"].shape == (10, 75, 3) and motions["CASA"][0, 0, 0] == 2.0
    assert motions["DIA"].shape == (20, 75, 3)
    assert motions["SOL"][0, 0, 0] == 3.0


def test_recording_repeats_the_last_hand_so_it_does_not_blink():
    motions, _ = build_motions(samples(), ["CASA"], signer="01")
    assert (np.abs(motions["CASA"][:, 33:]).sum(axis=(1, 2)) > 0).all()


def test_preferred_signer_can_be_chosen_and_must_exist():
    _, meta = build_motions(samples(), ["CASA"], signer="01")
    assert meta["signer"] == "01"
    with pytest.raises(ValueError):
        build_motions(samples(), ["CASA"], signer="09")


def test_mean_method_averages_recordings_at_their_mean_length():
    motions, meta = build_motions(samples(), ["DIA"], method="mean")
    assert meta["method"] == "mean" and meta["signer"] is None
    assert motions["DIA"].shape == (15, 75, 3)  # (10 + 20) / 2
    np.testing.assert_allclose(motions["DIA"][:, 0, 0], 1.5)


def test_unknown_method_is_rejected():
    with pytest.raises(ValueError):
        build_motions(samples(), ["CASA"], method="rede")


def test_save_motions_roundtrip_keeps_arrays_and_metadata(tmp_path):
    motions, meta = build_motions(samples(), ["CASA", "DIA"])
    path = tmp_path / "out" / "motions.npz"
    save_motions(path, motions, meta)
    with np.load(path) as data:
        assert set(data.files) == {"CASA", "DIA", "_meta"}
        np.testing.assert_array_equal(data["CASA"], motions["CASA"])
        saved = json.loads(str(data["_meta"]))
    assert saved["signer"] == "02" and saved["fps"] == 30 and saved["num_keypoints"] == 75


def test_load_dataset_can_skip_hand_filling(tmp_path):
    folder = tmp_path / "01"
    folder.mkdir()
    np.save(folder / "CASA_1.npy", recording(6, 3, 1.0))
    raw = load_dataset(tmp_path, ["CASA"], fill=False)[0].keypoints
    filled = load_dataset(tmp_path, ["CASA"])[0].keypoints
    assert (np.abs(raw[:, 33:]).sum(axis=(1, 2)) == 0).any()
    assert (np.abs(filled[:, 33:]).sum(axis=(1, 2)) > 0).all()
