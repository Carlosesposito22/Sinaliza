"""Geração de pose a partir de glosas.

`PoseGenerator` é a interface que o modelo treinado em `model/` deve implementar.
O texto vira glosas antes, em `text_to_gloss.py`.
`StubGenerator` produz uma animação de aceno só para validar o fluxo ponta a ponta;
não representa Libras.
"""

import math
from typing import Protocol

from .pose_format import HAND_COUNT, LAYOUT, NUM_KEYPOINTS, POSE_COUNT
from .schemas import PoseSequence

Point = list[float]


class PoseGenerator(Protocol):
    def generate(self, glosses: list[str]) -> PoseSequence: ...


def _rest_pose() -> list[Point]:
    pts: list[Point] = [[0.0, 0.0, 0.0] for _ in range(POSE_COUNT)]

    def put(index: int, x: float, y: float, z: float = 0.0) -> None:
        pts[index] = [x, y, z]

    def mirror(left: int, x: float, y: float, z: float = 0.0) -> None:
        put(left, x, y, z)
        put(left + 1, -x, y, z)

    put(0, 0.0, 1.85, 0.1)
    for base, (x, y) in ((1, (0.06, 1.92)), (2, (0.11, 1.93)), (3, (0.16, 1.92))):
        put(base, x, y, 0.05)
        put(base + 3, -x, y, 0.05)
    mirror(7, 0.28, 1.88)
    mirror(9, 0.07, 1.7, 0.08)
    mirror(11, 0.5, 1.25)
    mirror(13, 0.62, 0.52)
    mirror(15, 0.66, -0.12)
    mirror(17, 0.7, -0.3)
    mirror(19, 0.62, -0.32)
    mirror(21, 0.58, -0.2)
    mirror(23, 0.25, 0.0)
    mirror(25, 0.28, -1.1)
    mirror(27, 0.28, -2.2)
    mirror(29, 0.28, -2.3, -0.05)
    mirror(31, 0.3, -2.3, 0.2)
    return pts


_REST_POSE = _rest_pose()

_UPPER_ARM = 0.75
_FOREARM = 0.65

# (deslocamento lateral na base, distância da base ao punho, comprimento do segmento)
_FINGERS = [
    (0.09, 0.18, 0.12),
    (0.03, 0.2, 0.13),
    (-0.03, 0.18, 0.12),
    (-0.09, 0.15, 0.1),
]


def _hand(wrist: Point, direction: tuple[float, float]) -> list[Point]:
    ux, uy = direction
    vx, vy = -uy, ux
    z = wrist[2]

    def at(along: float, across: float) -> Point:
        return [
            round(wrist[0] + ux * along + vx * across, 4),
            round(wrist[1] + uy * along + vy * across, 4),
            z,
        ]

    pts: list[Point] = [list(wrist)]
    for k in range(1, 5):
        pts.append(at(0.05 + 0.09 * k, -0.1 - 0.05 * k))
    for lateral, base, seg in _FINGERS:
        for k in range(4):
            pts.append(at(base + seg * k, lateral))
    assert len(pts) == HAND_COUNT
    return pts


def _frame(t: float, freq: float) -> list[Point]:
    pose = [list(p) for p in _REST_POSE]

    sx, sy = pose[12][0], pose[12][1]
    upper = math.radians(80)
    fore = math.radians(150 + 25 * math.sin(2 * math.pi * freq * t))
    ex = sx - _UPPER_ARM * math.sin(upper)
    ey = sy - _UPPER_ARM * math.cos(upper)
    dx, dy = -math.sin(fore), -math.cos(fore)
    wx = ex + _FOREARM * dx
    wy = ey + _FOREARM * dy
    pose[14] = [round(ex, 4), round(ey, 4), 0.0]
    pose[16] = [round(wx, 4), round(wy, 4), 0.0]
    for index, offset in ((18, (-0.04, 0.1)), (20, (0.0, 0.18)), (22, (0.08, 0.06))):
        pose[index] = [
            round(wx + dx * offset[1] - dy * offset[0], 4),
            round(wy + dy * offset[1] + dx * offset[0], 4),
            0.0,
        ]

    left_wrist = pose[15]
    left_hand = _hand(left_wrist, (0.0, -1.0))
    right_hand = _hand(pose[16], (dx, dy))

    frame = pose + left_hand + right_hand
    assert len(frame) == NUM_KEYPOINTS
    return frame


class StubGenerator:
    fps = 15
    seconds_per_gloss = 1.0

    def generate(self, glosses: list[str]) -> PoseSequence:
        frames_per_gloss = int(self.fps * self.seconds_per_gloss)
        frames: list[list[Point]] = []
        for gloss in glosses:
            freq = 2 + sum(ord(c) for c in gloss) % 3
            for i in range(frames_per_gloss):
                frames.append(_frame(i / self.fps, freq))
        return PoseSequence(fps=self.fps, layout=dict(LAYOUT), frames=frames)
