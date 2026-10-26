"""Profundidade das mãos pelos world landmarks (hand_world.py), com dados de mentira."""

from pathlib import Path

import numpy as np
import pytest

from hand_world import DEFAULT_HAND_MODEL, apply_world_hands, assign_hands, merge_hand, world_depth

POSE_COUNT = 33


def hand(offset=(0.0, 0.0), scale=100.0, depth=None):
    """Mão de mentira: (imagem em pixels, world em metros). `depth`: z do world de cada ponto."""
    rng = np.random.default_rng(0)
    world = rng.normal(0, 0.03, (21, 3)).astype(np.float32)
    world[0] = 0
    if depth is not None:
        world[:, 2] = depth
    image = np.zeros((21, 3), dtype=np.float32)
    image[:, :2] = world[:, :2] * scale + np.array(offset)
    return image, world


def test_world_depth_usa_a_escala_do_xy_e_fica_relativo_ao_punho():
    image, world = hand(offset=(500, 300), scale=250.0)
    world[:, 2] += 0.5  # origem do world não importa
    depth = world_depth(image[:, :2], world)
    assert depth[0] == pytest.approx(0, abs=1e-5)
    np.testing.assert_allclose(depth, 250.0 * (world[:, 2] - world[0, 2]), rtol=1e-4, atol=1e-4)


def test_world_depth_sem_extensao_no_plano_devolve_zeros():
    world = np.zeros((21, 3), dtype=np.float32)
    assert not world_depth(np.zeros((21, 2)), world).any()


def test_assign_hands_pelo_punho_mais_proximo():
    wrists = [np.array([100.0, 100.0]), np.array([400.0, 100.0])]
    assert assign_hands(wrists, np.array([390.0, 110.0]), np.array([90.0, 95.0])) == {"left": 1, "right": 0}
    # uma detecção só: vai para o lado mais próximo
    assert assign_hands(wrists[:1], np.array([390.0, 110.0]), np.array([90.0, 95.0])) == {"right": 0}
    assert assign_hands(wrists, None, None) == {}


def test_merge_hand_troca_so_o_z_quando_e_a_mesma_mao():
    image, world = hand(offset=(200, 200))
    holistic = image.copy()
    holistic[:, 2] = 7.0  # z comprimido do Holistic
    merged = merge_hand(holistic, (image, world), near=50)
    np.testing.assert_array_equal(merged[:, :2], holistic[:, :2])
    np.testing.assert_allclose(merged[:, 2], world_depth(holistic[:, :2], world), atol=1e-4)


def test_merge_hand_outra_mao_ou_ausente():
    image, world = hand(offset=(200, 200))
    far = image.copy()
    far[:, :2] += 300
    assert merge_hand(far, (image, world), near=50) is far  # punhos longe: fica o Holistic
    holistic_missing = np.zeros((21, 3), dtype=np.float32)
    only_tracker = merge_hand(holistic_missing, (image, world), near=50)
    np.testing.assert_array_equal(only_tracker[:, :2], image[:, :2])
    assert merge_hand(image, None, near=50) is image


def test_apply_world_hands_coloca_cada_mao_no_seu_lado():
    frame = np.zeros((75, 3), dtype=np.float32)
    frame[15, :2] = (600, 400)  # punho esquerdo (aparece à direita da imagem)
    frame[16, :2] = (200, 400)
    left, left_world = hand(offset=(600, 400), depth=np.linspace(0, 0.02, 21))
    right, right_world = hand(offset=(200, 400), depth=np.linspace(0, -0.02, 21))
    out = apply_world_hands(frame, [(right, right_world), (left, left_world)], POSE_COUNT, crop_width=960)
    assert out[POSE_COUNT + 20, 2] > 0  # mão esquerda: z do world dela (positivo)
    assert out[POSE_COUNT + 21 + 20, 2] < 0
    np.testing.assert_array_equal(out[POSE_COUNT, :2], left[0, :2])


@pytest.mark.skipif(not DEFAULT_HAND_MODEL.exists(), reason="modelo hand_landmarker.task não baixado")
def test_extract_com_hand_world_roda_em_video_sintetico(tmp_path: Path):
    cv2 = pytest.importorskip("cv2")
    from extract_keypoints import extract

    path = tmp_path / "preto.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for _ in range(5):
        writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
    writer.release()
    out = extract(path, hand_model=DEFAULT_HAND_MODEL)
    assert out.shape == (5, 75, 3)
    assert not out.any()  # sem pessoa: tudo ausente
