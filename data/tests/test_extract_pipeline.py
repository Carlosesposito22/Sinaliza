"""Fluxo de `extract()` com um vídeo sintético (preto). Exige OpenCV e MediaPipe."""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("mediapipe")

from extract_keypoints import NUM_KEYPOINTS, extract  # noqa: E402
from person_crop import Box  # noqa: E402


@pytest.fixture
def black_video(tmp_path):
    path = tmp_path / "preto.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240))
    for _ in range(8):
        writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
    writer.release()
    return path


def test_extract_with_and_without_detector_keeps_the_output_format(black_video):
    plain = extract(black_video, detector=None)
    assert plain.shape == (8, NUM_KEYPOINTS, 3)
    assert plain.dtype == np.float32

    seen = []

    def detector(frame):
        seen.append(frame.shape)
        return Box(40, 20, 280, 220)

    cropped = extract(black_video, detector=detector, crop_every=4)
    assert cropped.shape == (8, NUM_KEYPOINTS, 3)
    assert len(seen) == 2  # quadros 0 e 4


def test_extract_falls_back_to_full_frame_when_nobody_is_detected(black_video, capsys):
    out = extract(black_video, detector=lambda _: None)
    assert out.shape == (8, NUM_KEYPOINTS, 3)
    assert "pessoa não detectada" in capsys.readouterr().err
