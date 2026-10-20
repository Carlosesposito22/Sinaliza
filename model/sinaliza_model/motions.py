"""Monta o arquivo de movimentos por sinal que a API toca no avatar.

A geração do MVP é **reprodução de gravação**, não geração por rede: no primeiro teste em
dado real (3 folds, V-LIBRASIL) o modelo não superou a média por sinal, e uma gravação
real é mais nítida que uma média (que borra as mãos). Duas formas:

- `recording` (padrão): para todos os sinais, a gravação do **mesmo sinalizante**, para o
  avatar não "trocar de pessoa" de um sinal para o outro. Por padrão, o sinalizante com mais
  quadros com mão detectada; se faltar a gravação dele para um sinal, usa a do próximo.
- `mean`: a média das gravações de cada sinal, reamostradas para o comprimento médio.
  Fica borrada (as mãos principalmente), mas não depende de uma pessoa só.

Saída: um `.npz` com um array `(frames, 75, 3)` por sinal (chave = `file_key` da glosa) e
`_meta` (JSON com o método, o sinalizante, o fps e o formato). **Contém movimento derivado
de dados que não podem ser redistribuídos (V-LIBRASIL): não versione.**

    python -m sinaliza_model.motions --data-root "<...>/processed/v-librasil" \\
        --out "<...>/Datasets/motions/motions.npz"
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .data import HAND_SLICES, Sample, file_key, fill_missing_hands, load_dataset, load_vocabulary, resample

DEFAULT_VOCABULARY = Path(__file__).resolve().parents[2] / "data" / "vocabulary.json"
DEFAULT_FPS = 30


def _hand_presence(keypoints: np.ndarray) -> float:
    """Fração de quadros com pelo menos uma mão detectada (antes de repetir a última mão)."""
    present = np.zeros(len(keypoints), dtype=bool)
    for hand in HAND_SLICES:
        present |= np.abs(keypoints[:, hand]).sum(axis=(1, 2)) > 0
    return float(present.mean())


def signer_ranking(samples: list[Sample]) -> list[str]:
    """Sinalizantes do que tem mais mão detectada para o que tem menos.

    Precisa dos `Sample` **crus** (`load_dataset(..., fill=False)`): depois de repetir a
    última mão nos quadros sem detecção, todos parecem ter mão em todos os quadros.
    """
    scores: dict[str, list[float]] = defaultdict(list)
    for sample in samples:
        scores[sample.signer].append(_hand_presence(sample.keypoints))
    return sorted(scores, key=lambda s: (-float(np.mean(scores[s])), s))


def build_motions(
    samples: list[Sample],
    glosses: list[str],
    method: str = "recording",
    signer: str | None = None,
) -> tuple[dict[str, np.ndarray], dict]:
    """Um movimento por glosa. Devolve (`file_key` → array, metadados).

    `samples` são os crus (sem repetir a última mão); a repetição é aplicada nos movimentos
    escolhidos, para a mão não piscar no avatar.
    """
    if method not in ("recording", "mean"):
        raise ValueError(f"método desconhecido: {method!r}")
    by_gloss: dict[str, dict[str, Sample]] = defaultdict(dict)
    for sample in samples:
        by_gloss[sample.gloss].setdefault(sample.signer, sample)

    ranking = signer_ranking(samples)
    if signer is not None:
        if signer not in ranking:
            raise ValueError(f"sinalizante inexistente: {signer!r} (há {ranking})")
        ranking = [signer] + [s for s in ranking if s != signer]

    motions: dict[str, np.ndarray] = {}
    fallback: list[str] = []
    missing: list[str] = []
    for gloss in glosses:
        recordings = by_gloss.get(gloss, {})
        if not recordings:
            missing.append(gloss)
            continue
        if method == "recording":
            chosen = next(s for s in ranking if s in recordings)
            if chosen != ranking[0]:
                fallback.append(gloss)
            motion = fill_missing_hands(recordings[chosen].keypoints)
        else:
            length = int(round(np.mean([len(r.keypoints) for r in recordings.values()])))
            motion = np.mean(
                [resample(fill_missing_hands(r.keypoints), length) for r in recordings.values()], axis=0
            )
        motions[file_key(gloss)] = np.asarray(motion, dtype=np.float32)

    meta = {
        "method": method,
        "signer": ranking[0] if method == "recording" else None,
        "signer_ranking": ranking,
        "fps": DEFAULT_FPS,
        "num_keypoints": 75,
        "n_motions": len(motions),
        "fallback_to_other_signer": fallback,
        "missing": missing,
    }
    return motions, meta


def save_motions(path: Path, motions: dict[str, np.ndarray], meta: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, _meta=np.array(json.dumps(meta, ensure_ascii=False)), **motions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--data-root", type=Path, required=True, help="pasta com <sinalizante>/<SINAL>_<n>.npy")
    parser.add_argument("--out", type=Path, required=True, help="arquivo .npz de saída (fora do repositório)")
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--method", choices=("recording", "mean"), default="recording")
    parser.add_argument("--signer", help="sinalizante preferido (padrão: o com mais mão detectada)")
    args = parser.parse_args()

    glosses = load_vocabulary(args.vocabulary)
    samples = load_dataset(args.data_root, glosses, fill=False)
    if not samples:
        parser.error("nenhuma amostra encontrada")
    motions, meta = build_motions(samples, glosses, args.method, args.signer)
    save_motions(args.out, motions, meta)

    frames = [len(m) for m in motions.values()]
    print(f"{len(motions)} movimentos em {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    print(f"método {meta['method']}, sinalizante {meta['signer']}, ranking {meta['signer_ranking']}")
    print(f"quadros por sinal: mediana {int(np.median(frames))}, mín {min(frames)}, máx {max(frames)}")
    if meta["fallback_to_other_signer"]:
        print("sem gravação do sinalizante preferido:", meta["fallback_to_other_signer"])
    if meta["missing"]:
        print("sem nenhuma gravação:", meta["missing"])


if __name__ == "__main__":
    main()
