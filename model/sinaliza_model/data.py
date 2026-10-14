"""Carga e pré-processamento dos keypoints.

Convenção de arquivos (saída do pipeline de data/):

    <raiz>/<sinalizante>/<SINAL>_<repetição>.npy      float32, formato (frames, 75, 3)

O nome do sinal é comparado ao vocabulário sem acento e sem diferença de caixa
(`MACA_1.npy` casa com MAÇÃ).
"""

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np

NUM_KEYPOINTS = 75
HAND_SLICES = (slice(33, 54), slice(54, 75))


@dataclass(frozen=True)
class Sample:
    gloss: str
    signer: str
    keypoints: np.ndarray


def slug(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


def load_vocabulary(path: Path) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [sign["gloss"] for sign in data["signs"]]


def resample(sequence: np.ndarray, length: int) -> np.ndarray:
    """Reamostra no tempo por interpolação linear, para `length` frames."""
    n = len(sequence)
    if n == length:
        return sequence.copy()
    if n == 1:
        return np.repeat(sequence, length, axis=0)
    source = np.linspace(0, n - 1, length)
    low = np.floor(source).astype(int)
    high = np.minimum(low + 1, n - 1)
    weight = (source - low)[:, None, None].astype(sequence.dtype)
    return sequence[low] * (1 - weight) + sequence[high] * weight


def fill_missing_hands(sequence: np.ndarray) -> np.ndarray:
    """Repete a última mão detectada nos frames em que a mão não foi detectada.

    Frames sem detecção são `0`. Mãos nunca detectadas ficam em zero.
    """
    out = sequence.copy()
    for hand in HAND_SLICES:
        present = np.abs(out[:, hand]).sum(axis=(1, 2)) > 0
        if present.all() or not present.any():
            continue
        last_seen = np.maximum.accumulate(np.where(present, np.arange(len(out)), -1))
        last_seen[last_seen < 0] = int(np.argmax(present))
        out[:, hand] = out[last_seen, hand]
    return out


def load_dataset(root: Path, glosses: list[str]) -> list[Sample]:
    by_slug = {slug(g): g for g in glosses}
    samples: list[Sample] = []
    for signer_dir in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        for path in sorted(signer_dir.glob("*.npy")):
            gloss = by_slug.get(slug(path.stem.rsplit("_", 1)[0]))
            if gloss is None:
                continue
            array = np.load(path).astype(np.float32)
            if array.ndim != 3 or array.shape[1:] != (NUM_KEYPOINTS, 3):
                raise ValueError(f"{path}: formato {array.shape}, esperado (frames, 75, 3)")
            samples.append(Sample(gloss, signer_dir.name, fill_missing_hands(array)))
    return samples


def split_by_signer(
    samples: list[Sample], val_signers: set[str]
) -> tuple[list[Sample], list[Sample]]:
    train = [s for s in samples if s.signer not in val_signers]
    val = [s for s in samples if s.signer in val_signers]
    return train, val
