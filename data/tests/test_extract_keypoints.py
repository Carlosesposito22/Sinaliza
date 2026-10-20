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
    _drop_lower_body,
    _landmarks_to_array,
    _normalize,
    _reference,
    stride_for,
)


def landmarks(points):
    return SimpleNamespace(landmark=[SimpleNamespace(x=x, y=y, z=z) for x, y, z in points])


def pixel_frame() -> np.ndarray:
    """Quadro em pixels: ombros em x=300/500 (largura 200) e y=400; quadris em y=700."""
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
    # Origem no meio dos ombros (400, 400); ombros a 200 px um do outro = 1 unidade.
    frame = pixel_frame()
    out = _normalize(frame, _reference(frame))
    np.testing.assert_allclose(out[LEFT_SHOULDER], [0.5, 0.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(out[RIGHT_SHOULDER], [-0.5, 0.0, 0.0], atol=1e-5)
    # punho 100 px acima dos ombros (0,5 largura), z 20 px mais perto da câmera
    np.testing.assert_allclose(out[POSE_COUNT], [0.5, 0.5, -0.1], atol=1e-5)
    # quadril 300 px abaixo dos ombros: 1,5 larguras, y para baixo é negativo
    np.testing.assert_allclose(out[LEFT_HIP], [0.3, -1.5, -0.1], atol=1e-5)


def test_origin_is_the_shoulder_midpoint_and_does_not_depend_on_the_hips():
    frame = pixel_frame()
    moved = frame.copy()
    moved[LEFT_HIP] = [900, 1500, 0]  # quadril estimado em outro lugar (fora do quadro)
    moved[RIGHT_HIP] = [100, 1600, 0]
    a = _normalize(frame, _reference(frame))
    b = _normalize(moved, _reference(moved))
    np.testing.assert_allclose(a[:POSE_COUNT][[LEFT_SHOULDER, RIGHT_SHOULDER]], b[:POSE_COUNT][[LEFT_SHOULDER, RIGHT_SHOULDER]])
    np.testing.assert_allclose(a[POSE_COUNT], b[POSE_COUNT])


def test_shoulder_width_is_one_after_normalizing():
    frame = pixel_frame()
    out = _normalize(frame, _reference(frame))
    width = np.linalg.norm(out[LEFT_SHOULDER][:2] - out[RIGHT_SHOULDER][:2])
    assert abs(width - 1.0) < 1e-5
    np.testing.assert_allclose((out[LEFT_SHOULDER] + out[RIGHT_SHOULDER]) / 2, [0, 0, 0], atol=1e-5)
    assert out[POSE_COUNT][1] > 0  # mão acima dos ombros: y para cima


def test_drop_lower_body_zeroes_hips_legs_and_feet_only():
    frame = np.ones((NUM_KEYPOINTS, 3), dtype=np.float32)
    out = _drop_lower_body(frame)
    assert not out[23:33].any()
    assert out[:23].all() and out[33:].all()
    assert frame.all()  # não altera a entrada


def test_stride_for_target_fps():
    assert stride_for(60.0, 30.0) == 2
    assert stride_for(59.94, 30.0) == 2
    assert stride_for(29.97, 30.0) == 1
    assert stride_for(30.0, None) == 1
    assert stride_for(0.0, 30.0) == 1
    assert stride_for(120.0, 30.0) == 4


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
