"""Recorte da pessoa com YOLOv8 antes do MediaPipe.

Os vídeos do MINDS-Libras são 1920x1080 e o sinalizante ocupa só uma parte do
quadro. Reduzir o quadro inteiro para ~960 px de largura reduz as mãos a poucos
pixels e o Holistic perde a mão. Aqui o YOLOv8 (classe `person`) acha a pessoa,
o vídeo é recortado em volta dela e o MediaPipe roda no recorte, com mais pixels
nas mãos.

O recorte é **fixo por vídeo**: a união das caixas detectadas em quadros
amostrados, mais uma margem. Uma caixa que muda a cada quadro mexeria no
enquadramento do MediaPipe e adicionaria ruído à pose.

O YOLOv8 só localiza a pessoa. Os keypoints continuam vindo do MediaPipe, e os
valores são convertidos de volta para o quadro original antes da normalização
(ver `extract_keypoints.py`), então o recorte não altera o formato de pose.

Licença: o Ultralytics é AGPL-3.0 (ou licença Enterprise). Aqui ele só roda
offline, na preparação dos dados; a API não o usa. Ver docs/dados-e-vocabulario.md.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np

PERSON_CLASS = 0
DEFAULT_MODEL = "yolov8n.pt"


@dataclass(frozen=True)
class Box:
    """Caixa em pixels do quadro original; `x1` e `y1` são exclusivos."""

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def area(self) -> int:
        return self.width * self.height


Detector = Callable[[np.ndarray], Box | None]


def union(boxes: Iterable[Box]) -> Box | None:
    boxes = list(boxes)
    if not boxes:
        return None
    return Box(
        min(b.x0 for b in boxes),
        min(b.y0 for b in boxes),
        max(b.x1 for b in boxes),
        max(b.y1 for b in boxes),
    )


def expand(box: Box, margin: float, frame_width: int, frame_height: int) -> Box:
    """Aumenta a caixa em `margin` (fração do tamanho) por lado, dentro do quadro."""
    dx = round(box.width * margin)
    dy = round(box.height * margin)
    return Box(
        max(0, box.x0 - dx),
        max(0, box.y0 - dy),
        min(frame_width, box.x1 + dx),
        min(frame_height, box.y1 + dy),
    )


def estimate_crop(
    frames: Iterable[np.ndarray],
    detector: Detector,
    margin: float = 0.15,
) -> Box | None:
    """Recorte fixo para um vídeo: união das detecções nos quadros dados + margem.

    `frames` já vem amostrado (ex.: um a cada 15). Devolve `None` se a pessoa não
    for detectada em nenhum deles; o chamador deve então usar o quadro inteiro.
    """
    boxes: list[Box] = []
    frame_width = frame_height = 0
    for frame in frames:
        frame_height, frame_width = frame.shape[:2]
        box = detector(frame)
        if box is not None:
            boxes.append(box)
    merged = union(boxes)
    if merged is None:
        return None
    return expand(merged, margin, frame_width, frame_height)


class YoloPersonDetector:
    """Devolve a maior pessoa do quadro (a caixa de maior área) ou `None`."""

    def __init__(self, model: str = DEFAULT_MODEL, confidence: float = 0.4, device: str | None = None):
        from ultralytics import YOLO

        self.model = YOLO(model)
        self.confidence = confidence
        self.device = device

    def __call__(self, frame_bgr: np.ndarray) -> Box | None:
        results = self.model.predict(
            frame_bgr,
            classes=[PERSON_CLASS],
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )
        height, width = frame_bgr.shape[:2]
        best: Box | None = None
        for xyxy in results[0].boxes.xyxy.cpu().numpy():
            box = Box(
                max(0, int(np.floor(xyxy[0]))),
                max(0, int(np.floor(xyxy[1]))),
                min(width, int(np.ceil(xyxy[2]))),
                min(height, int(np.ceil(xyxy[3]))),
            )
            if box.area > 0 and (best is None or box.area > best.area):
                best = box
        return best
