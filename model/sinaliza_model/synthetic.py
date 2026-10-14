"""Dados sintéticos para testar o pipeline sem os vídeos reais.

Cada sinal é uma trajetória distinta do punho direito. Cada "sinalizante" varia
duração, amplitude e ruído. Não representa Libras.
"""

import numpy as np

from .data import NUM_KEYPOINTS, Sample

RIGHT_WRIST = 16


def _template(index: int, frames: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, frames)
    sequence = np.zeros((frames, NUM_KEYPOINTS, 3), dtype=np.float32)
    sequence[:, RIGHT_WRIST, 0] = -0.6 + 0.4 * np.sin(2 * np.pi * (1 + index % 3) * t)
    sequence[:, RIGHT_WRIST, 1] = 0.5 + 0.5 * np.cos(2 * np.pi * (1 + index % 4) * t + index)
    sequence[:, RIGHT_WRIST, 2] = 0.1 * index / 20
    return sequence


def make_synthetic(
    glosses: list[str], signers: int = 4, repetitions: int = 5, seed: int = 0
) -> list[Sample]:
    rng = np.random.default_rng(seed)
    samples: list[Sample] = []
    for signer in range(signers):
        speed = rng.uniform(0.8, 1.25)
        scale = rng.uniform(0.9, 1.1)
        for index, gloss in enumerate(glosses):
            for _ in range(repetitions):
                frames = int(rng.integers(40, 80) * speed)
                sequence = _template(index, frames) * scale
                sequence += rng.normal(0, 0.01, sequence.shape).astype(np.float32)
                samples.append(Sample(gloss, f"{signer + 1:02d}", sequence))
    return samples
