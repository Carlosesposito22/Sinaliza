"""Linhas de base sem aprendizado. O modelo só se justifica se superá-las."""

import numpy as np

from .data import Sample, resample
from .metrics import dtw_distance


def _group(samples: list[Sample], seq_len: int) -> dict[str, list[np.ndarray]]:
    groups: dict[str, list[np.ndarray]] = {}
    for sample in samples:
        groups.setdefault(sample.gloss, []).append(resample(sample.keypoints, seq_len))
    return groups


def _medoid(sequences: list[np.ndarray]) -> np.ndarray:
    if len(sequences) == 1:
        return sequences[0]
    n = len(sequences)
    total = np.zeros(n)
    for i in range(n):
        for j in range(i + 1, n):
            d = dtw_distance(sequences[i], sequences[j])
            total[i] += d
            total[j] += d
    return sequences[int(np.argmin(total))]


class MedoidBaseline:
    """Para cada sinal, a gravação de treino mais central segundo o DTW (recuperação)."""

    def __init__(self, seq_len: int = 32):
        self.seq_len = seq_len
        self.table: dict[str, np.ndarray] = {}

    def fit(self, samples: list[Sample]) -> "MedoidBaseline":
        self.table = {g: _medoid(s) for g, s in _group(samples, self.seq_len).items()}
        return self

    def generate(self, gloss: str) -> np.ndarray:
        return self.table[gloss]


class ClassMeanBaseline:
    """Para cada sinal, a média das gravações de treino normalizadas no tempo."""

    def __init__(self, seq_len: int = 32):
        self.seq_len = seq_len
        self.table: dict[str, np.ndarray] = {}

    def fit(self, samples: list[Sample]) -> "ClassMeanBaseline":
        self.table = {
            g: np.mean(s, axis=0) for g, s in _group(samples, self.seq_len).items()
        }
        return self

    def generate(self, gloss: str) -> np.ndarray:
        return self.table[gloss]


class GlobalMeanBaseline:
    """Ignora o sinal e devolve a média de tudo. Se o modelo não superar isso, não aprendeu nada."""

    def __init__(self, seq_len: int = 32):
        self.seq_len = seq_len
        self.mean: np.ndarray | None = None

    def fit(self, samples: list[Sample]) -> "GlobalMeanBaseline":
        self.mean = np.mean(
            [resample(s.keypoints, self.seq_len) for s in samples], axis=0
        )
        return self

    def generate(self, gloss: str) -> np.ndarray:
        assert self.mean is not None, "chame fit() antes"
        return self.mean
