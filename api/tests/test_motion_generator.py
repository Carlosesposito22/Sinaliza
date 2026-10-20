import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import main
from app.generator import StubGenerator
from app.motion_generator import MotionPlayback, transition
from app.pose_format import NUM_KEYPOINTS


def motion(frames: int, value: float, hand: float | None = None) -> np.ndarray:
    kp = np.zeros((frames, NUM_KEYPOINTS, 3), dtype=np.float32)
    kp[:, :33] = value
    if hand is not None:
        kp[:, 33:] = hand
    return kp


def write_motions(path, motions, fps=30):
    np.savez_compressed(path, _meta=np.array(json.dumps({"fps": fps, "signer": "01"})), **motions)
    return path


@pytest.fixture
def playback():
    return MotionPlayback({"CASA": motion(10, 1.0), "DOR_DE_CABECA": motion(6, 3.0)}, transition_frames=4)


def test_transition_interpolates_with_smooth_ends_and_leaves_the_endpoints_out():
    last, first = motion(1, 1.0)[0], motion(1, 2.0)[0]  # 0 seria "ausente"
    out = transition(last, first, 3)
    assert out.shape == (3, NUM_KEYPOINTS, 3)
    weights = out[:, 0, 0] - 1.0
    assert (np.diff(weights) > 0).all() and 0 < weights[0] < 0.25 and 0.75 < weights[-1] < 1  # smoothstep
    assert transition(last, first, 0).shape == (0, NUM_KEYPOINTS, 3)


def test_transition_does_not_sweep_missing_points_from_the_origin():
    last = motion(1, 1.0, hand=2.0)[0]
    first = motion(1, 3.0, hand=None)[0]  # mãos ausentes ([0, 0, 0]) no começo do próximo sinal
    out = transition(last, first, 4)
    assert (out[:, 33:] == 2.0).all()  # a mão fica onde estava, não corre até a origem
    both_missing = transition(motion(1, 1.0)[0], motion(1, 2.0)[0], 2)
    assert not both_missing[:, 33:].any()


def test_generate_plays_signs_in_order_with_transitions_between_them(playback):
    pose = playback.generate(["CASA", "DOR DE CABEÇA"])
    assert pose.fps == 30
    assert len(pose.frames) == 10 + 4 + 6
    assert pose.frames[0][0][0] == 1.0 and pose.frames[-1][0][0] == 3.0
    middle = [frame[0][0] for frame in pose.frames[10:14]]
    assert middle == sorted(middle) and 1.0 < middle[0] < middle[-1] < 3.0


def test_generate_skips_signs_without_motion_and_fails_when_none_has_one(playback):
    assert len(playback.generate(["CASA", "SEM MOVIMENTO"]).frames) == 10
    assert playback.has("Dor de cabeça") and not playback.has("sem movimento")
    with pytest.raises(ValueError):
        playback.generate(["SEM MOVIMENTO"])


def test_generate_rounds_to_three_decimals_to_keep_the_payload_small():
    pose = MotionPlayback({"A": motion(2, 0.123456)}).generate(["A"])
    assert pose.frames[0][0][0] == 0.123


def test_load_reads_motions_fps_and_metadata(tmp_path):
    path = write_motions(tmp_path / "m.npz", {"CASA": motion(5, 1.0)}, fps=24)
    loaded = MotionPlayback.load(path)
    assert loaded.fps == 24 and loaded.meta["signer"] == "01" and loaded.has("casa")
    assert loaded.name == "playback"


def test_wrong_shape_is_rejected():
    with pytest.raises(ValueError):
        MotionPlayback({"A": np.zeros((5, 33, 3), dtype=np.float32)})


def test_create_generator_falls_back_to_the_stub_when_the_file_is_missing_or_invalid(tmp_path, caplog):
    assert isinstance(main.create_generator(None), StubGenerator)
    with caplog.at_level("WARNING", logger="sinaliza"):
        assert isinstance(main.create_generator(str(tmp_path / "nao-existe.npz")), StubGenerator)
    assert "usando o stub" in caplog.text
    broken = tmp_path / "quebrado.npz"
    broken.write_bytes(b"isto nao e um npz")
    assert isinstance(main.create_generator(str(broken)), StubGenerator)
    valid = write_motions(tmp_path / "ok.npz", {"CASA": motion(4, 1.0)})
    assert isinstance(main.create_generator(str(valid)), MotionPlayback)


def test_api_uses_the_playback_generator_and_reports_it(monkeypatch, tmp_path):
    path = write_motions(tmp_path / "m.npz", {"CASA": motion(10, 1.0), "ESCOLA": motion(6, 3.0)})
    monkeypatch.setattr(main, "generator", MotionPlayback.load(path, transition_frames=4))
    client = TestClient(main.app)

    body = client.post("/translate", json={"text": "A casa e a escola"}).json()
    assert body["generator"] == "playback"
    assert body["glosses"] == ["CASA", "ESCOLA"]
    assert len(body["pose"]["frames"]) == 10 + 4 + 6
    assert body["pose"]["fps"] == 30


def test_api_returns_422_when_no_sign_has_a_recorded_motion(monkeypatch, tmp_path):
    path = write_motions(tmp_path / "m.npz", {"CASA": motion(10, 1.0)})
    monkeypatch.setattr(main, "generator", MotionPlayback.load(path))
    response = TestClient(main.app).post("/translate", json={"text": "hospital"})
    assert response.status_code == 422
    assert "movimento" in response.json()["detail"]
