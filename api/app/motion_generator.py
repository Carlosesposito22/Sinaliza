"""Gerador que **toca gravações** (do arquivo montado por `model/sinaliza_model/motions.py`).

Cada glosa vira a gravação real de um sinalizante do V-LIBRASIL (sinais isolados). Entre dois
sinais, o gerador cria uma **transição** de alguns quadros que interpola, com suavização
(smoothstep), do último quadro de um sinal ao primeiro do seguinte. **Isto não é tradução para
Libras**: é a sequência de sinais isolados na ordem do texto, sem gramática, sem expressão
facial e sem coarticulação aprendida; as transições são só uma interpolação.

O arquivo de movimentos é derivado de dados que não podem ser redistribuídos: fica fora do
repositório e é indicado por `SINALIZA_MOTIONS`.
"""

import json
from pathlib import Path

import numpy as np

from .pose_format import LAYOUT, NUM_KEYPOINTS
from .schemas import PoseSequence
from .vocabulary import file_key

DEFAULT_FPS = 30
DEFAULT_TRANSITION_FRAMES = 8


def smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def transition(last: np.ndarray, first: np.ndarray, frames: int) -> np.ndarray:
    """`frames` quadros entre `last` e `first` (que ficam de fora). Forma `(frames, 75, 3)`.

    Ponto ausente (`[0, 0, 0]`) em uma das pontas não é interpolado (varreria a tela até a
    origem): fica na posição do outro lado. Ausente nas duas, continua ausente.
    """
    if frames <= 0:
        return np.zeros((0,) + last.shape, dtype=np.float32)
    weights = smoothstep(np.arange(1, frames + 1, dtype=np.float32) / (frames + 1))[:, None, None]
    blended = last[None] + (first - last)[None] * weights
    in_last = last.any(axis=1)[None, :, None]
    in_first = first.any(axis=1)[None, :, None]
    out = np.where(in_last & in_first, blended, np.where(in_last, last[None], np.where(in_first, first[None], 0.0)))
    return out.astype(np.float32)


class MotionPlayback:
    name = "playback"

    def __init__(
        self,
        motions: dict[str, np.ndarray],
        fps: int = DEFAULT_FPS,
        transition_frames: int = DEFAULT_TRANSITION_FRAMES,
        meta: dict | None = None,
    ):
        for key, motion in motions.items():
            if motion.ndim != 3 or motion.shape[1:] != (NUM_KEYPOINTS, 3):
                raise ValueError(f"{key}: formato {motion.shape}, esperado (frames, {NUM_KEYPOINTS}, 3)")
        self.motions = motions
        self.fps = fps
        self.transition_frames = transition_frames
        self.meta = meta or {}

    @classmethod
    def load(cls, path: Path, transition_frames: int = DEFAULT_TRANSITION_FRAMES) -> "MotionPlayback":
        with np.load(Path(path)) as data:
            meta = json.loads(str(data["_meta"])) if "_meta" in data.files else {}
            motions = {key: data[key].astype(np.float32) for key in data.files if key != "_meta"}
        return cls(motions, int(meta.get("fps", DEFAULT_FPS)), transition_frames, meta)

    def has(self, gloss: str) -> bool:
        return file_key(gloss) in self.motions

    def generate(self, glosses: list[str]) -> PoseSequence:
        parts: list[np.ndarray] = []
        for gloss in glosses:
            motion = self.motions.get(file_key(gloss))
            if motion is None:
                continue
            if parts:
                parts.append(transition(parts[-1][-1], motion[0], self.transition_frames))
            parts.append(motion)
        if not parts:
            raise ValueError("nenhum dos sinais tem movimento gravado")
        # em float64: arredondar em float32 deixaria casas longas (0.12300000339...) no JSON
        frames = np.round(np.concatenate(parts).astype(np.float64), 3).tolist()
        return PoseSequence(fps=self.fps, layout=dict(LAYOUT), frames=frames)
