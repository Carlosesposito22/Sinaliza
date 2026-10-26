"""Profundidade das mãos pelos *world landmarks* do HandLandmarker (MediaPipe Tasks).

O Holistic dá, para cada mão, x e y bons, mas um z relativo ao punho que é comprimido: no
V-LIBRASIL o mesmo osso de dedo variava de 0,34 a 0,76 da palma em 3D. O HandLandmarker devolve
também a mão em 3D métrico (*world landmarks*, em metros, com a origem no centro da mão), com
comprimentos de osso coerentes. Aqui ele roda no mesmo quadro que o Holistic e, para cada mão:

- com as duas detecções (mesma mão: punhos próximos), x e y continuam os do Holistic e o z vem do
  world, na escala da imagem (ajustada por mínimos quadrados entre o xy do world e o da imagem);
- só o HandLandmarker achou: x e y das landmarks de imagem dele e z do world;
- só o Holistic achou: fica como está.

A mão é atribuída ao lado pelo punho da pose (15 esquerdo, 16 direito) mais próximo, e não pela
classificação de lateralidade do modelo (que supõe imagem espelhada de selfie).

Modelo: `hand_landmarker.task` (Apache 2.0), baixado à parte; ver data/README.md.
"""

from pathlib import Path

import numpy as np

HAND_COUNT = 21
LEFT_WRIST, RIGHT_WRIST = 15, 16
DEFAULT_HAND_MODEL = Path(__file__).resolve().parent / "hand_landmarker.task"

# Punhos a mais que isto (fração da largura do recorte) não são a mesma mão.
SAME_HAND_DISTANCE = 0.08


def world_depth(image_xy: np.ndarray, world: np.ndarray) -> np.ndarray:
    """z de cada ponto (em pixels, relativo ao punho) a partir do world, na escala de `image_xy`.

    `image_xy` (21, 2) em pixels; `world` (21, 3) em metros, eixos como os da imagem (x para a
    direita, y para baixo, z para longe da câmera). A escala é a que melhor leva o xy do world
    ao da imagem (mínimos quadrados, sem rotação).
    """
    target = image_xy - image_xy.mean(axis=0)
    source = world[:, :2] - world[:, :2].mean(axis=0)
    denominator = float((source * source).sum())
    if denominator < 1e-12:
        return np.zeros(len(world), dtype=np.float32)
    scale = float((target * source).sum()) / denominator
    return (scale * (world[:, 2] - world[0, 2])).astype(np.float32)


def assign_hands(wrists: list[np.ndarray], pose_left: np.ndarray | None, pose_right: np.ndarray | None) -> dict[str, int]:
    """Índice da detecção para cada lado (`left`/`right`), pelo punho da pose mais próximo.

    `wrists`: posição (x, y) do punho de cada detecção. Sem pose, não atribui nada.
    """
    sides = {side: point for side, point in (("left", pose_left), ("right", pose_right)) if point is not None}
    pairs = sorted(
        (float(np.linalg.norm(wrist - point)), side, index)
        for index, wrist in enumerate(wrists)
        for side, point in sides.items()
    )
    assigned: dict[str, int] = {}
    used: set[int] = set()
    for _, side, index in pairs:
        if side in assigned or index in used:
            continue
        assigned[side] = index
        used.add(index)
    return assigned


def merge_hand(holistic: np.ndarray, detected: tuple[np.ndarray, np.ndarray] | None, near: float) -> np.ndarray:
    """Mão final (21, 3) em pixels: ver o docstring do módulo. `near`: distância máxima entre punhos."""
    if detected is None:
        return holistic
    image, world = detected
    if holistic.any():
        if np.linalg.norm(holistic[0, :2] - image[0, :2]) > near:
            return holistic  # o HandLandmarker achou outra coisa: fica o Holistic
        out = holistic.copy()
        out[:, 2] = world_depth(holistic[:, :2], world)
        return out
    out = image.copy()
    out[:, 2] = world_depth(image[:, :2], world)
    return out


class HandWorldTracker:
    """HandLandmarker em modo vídeo (até duas mãos), devolvendo pontos em pixels do quadro original."""

    def __init__(self, model_path: Path = DEFAULT_HAND_MODEL):
        from mediapipe.tasks.python import BaseOptions, vision

        if not Path(model_path).exists():
            raise FileNotFoundError(f"modelo do HandLandmarker não encontrado em {model_path} (ver data/README.md)")
        # o conteúdo, não o caminho: no Windows o MediaPipe junta caminho absoluto ao da instalação
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(model_path).read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> "HandWorldTracker":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def detect(self, rgb: np.ndarray, timestamp_ms: int, origin: tuple[int, int], size: tuple[int, int]) -> list[tuple[np.ndarray, np.ndarray]]:
        """[(imagem (21, 3) em pixels do quadro original, world (21, 3) em metros)] de cada mão achada."""
        import mediapipe as mp

        result = self._landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
        hands = []
        for image, world in zip(result.hand_landmarks, result.hand_world_landmarks):
            points = np.array([[p.x * size[0] + origin[0], p.y * size[1] + origin[1], p.z * size[0]] for p in image], dtype=np.float32)
            hands.append((points, np.array([[p.x, p.y, p.z] for p in world], dtype=np.float32)))
        return hands


def apply_world_hands(
    frame: np.ndarray,
    hands: list[tuple[np.ndarray, np.ndarray]],
    pose_count: int,
    crop_width: int,
) -> np.ndarray:
    """Troca o z das mãos de `frame` (75, 3, em pixels) pelo dos world landmarks, quando houver."""
    pose = frame[:pose_count]
    present = pose.any(axis=1)
    left = pose[LEFT_WRIST, :2] if present[LEFT_WRIST] else None
    right = pose[RIGHT_WRIST, :2] if present[RIGHT_WRIST] else None
    assigned = assign_hands([image[0, :2] for image, _ in hands], left, right)
    out = frame.copy()
    near = SAME_HAND_DISTANCE * crop_width
    for side, start in (("left", pose_count), ("right", pose_count + HAND_COUNT)):
        index = assigned.get(side)
        detected = hands[index] if index is not None else None
        out[start : start + HAND_COUNT] = merge_hand(frame[start : start + HAND_COUNT], detected, near)
    return out
