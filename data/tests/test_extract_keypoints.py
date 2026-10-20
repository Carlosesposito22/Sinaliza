from types import SimpleNamespace

import numpy as np

from extract_keypoints import (
    HAND_COUNT,
    LEFT_HIP,
    LEFT_SHOULDER,
    NUM_KEYPOINTS,
    POSE_COUNT,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    _landmarks_to_array,
    _normalize,
    _reference,
)


def landmarks(points):
    return SimpleNamespace(landmark=[SimpleNamespace(x=x, y=y, z=z) for x, y, z in points])


def pixel_frame() -> np.ndarray:
    """Quadro em pixels: ombros em x=300/500 (largura 200), quadris em y=700."""
    frame = np.zeros((NUM_KEYPOINTS, 3), dtype=np.float32)
    frame[LEFT_SHOULDER] = [500, 400, -20]
    frame[RIGHT_SHOULDER] = [300, 400, -20]
    frame[LEFT_HIP] = [460, 700, 0]
    frame[RIGHT_HIP] = [340, 700, 0]
    frame[POSE_COUNT] = [500, 300, 0]  # punho da mão esquerda, 100 px acima dos ombros
    return frame


def test_landmarks_to_array_converts_crop_coordinates_to_original_pixels():
    points = [(0.5, 0.25, 0.1)] * 2
    out = _landmarks_to_array(landmarks(points), 2, origin=(100, 50), size=(400, 800))
    np.testing.assert_allclose(out[0], [300, 250, 40])


def test_landmarks_to_array_missing_is_zero():
    assert not _landmarks_to_array(None, HAND_COUNT, (10, 10), (100, 100)).any()


def test_pixel_units_keep_proportions_between_axes():
    # Em coordenadas 0..1 de um quadro 16:9 o eixo y ficaria esticado em relação a x.
    # Ombros a 200 px um do outro e 300 px acima dos quadris: 1,5 larguras de ombro.
    frame = pixel_frame()
    out = _normalize(frame, _reference(frame))
    np.testing.assert_allclose(out[LEFT_SHOULDER], [0.5, 1.5, 0.1], atol=1e-5)
    np.testing.assert_allclose(out[RIGHT_SHOULDER], [-0.5, 1.5, 0.1], atol=1e-5)
    np.testing.assert_allclose(out[POSE_COUNT], [0.5, 2.0, 0.0], atol=1e-5)


def test_shoulder_width_is_one_after_normalizing():
    frame = pixel_frame()
    frame[LEFT_HIP] = [400, 600, 0]
    frame[RIGHT_HIP] = [400, 600, 0]
    out = _normalize(frame, _reference(frame))
    width = np.linalg.norm(out[LEFT_SHOULDER][:2] - out[RIGHT_SHOULDER][:2])
    assert abs(width - 1.0) < 1e-5
    np.testing.assert_allclose((out[LEFT_HIP] + out[RIGHT_HIP]) / 2, [0, 0, 0], atol=1e-5)
    assert out[LEFT_SHOULDER][1] > 0  # y para cima


def test_missing_points_stay_zero():
    frame = pixel_frame()
    out = _normalize(frame, _reference(frame))
    assert not out[POSE_COUNT + 1 :].any()


def test_reference_is_none_without_body_or_with_degenerate_shoulders():
    assert _reference(np.zeros((NUM_KEYPOINTS, 3), dtype=np.float32)) is None
    frame = pixel_frame()
    frame[LEFT_SHOULDER] = frame[RIGHT_SHOULDER]
    assert _reference(frame) is None


def test_frame_without_body_reuses_last_reference_and_is_zero_before_the_first():
    good = pixel_frame()
    hands_only = np.zeros_like(good)
    hands_only[POSE_COUNT] = [500, 300, 0]

    assert not _normalize(hands_only, None).any()

    reference = _reference(good)
    out = _normalize(hands_only, reference)
    np.testing.assert_allclose(out[POSE_COUNT], _normalize(good, reference)[POSE_COUNT])
    assert not out[:POSE_COUNT].any()
