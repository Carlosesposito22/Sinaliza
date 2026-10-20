"""Treina o gerador, compara com as linhas de base e grava as métricas.

Dados sintéticos (para testar o pipeline):
    python -m sinaliza_model.train --synthetic

Dados reais, validando em sinalizantes que não entram no treino:
    python -m sinaliza_model.train --data-root ../data/processed/minds-libras --val-signers 10
"""

import argparse
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import torch

from .baseline import ClassMeanBaseline, GlobalMeanBaseline, MedoidBaseline
from .data import Sample, load_dataset, load_vocabulary, resample, split_by_signer
from .metrics import dtw_distance
from .network import MotionGenerator
from .synthetic import make_synthetic

DEFAULT_VOCABULARY = Path(__file__).resolve().parents[2] / "data" / "vocabulary.json"


def train_model(
    train: list[Sample],
    glosses: list[str],
    seq_len: int = 32,
    epochs: int = 200,
    lr: float = 1e-3,
    batch_size: int = 32,
    seed: int = 0,
) -> tuple[MotionGenerator, list[float]]:
    torch.manual_seed(seed)
    gloss_to_id = {g: i for i, g in enumerate(glosses)}
    ids = torch.tensor([gloss_to_id[s.gloss] for s in train])
    targets = torch.from_numpy(np.stack([resample(s.keypoints, seq_len) for s in train]))

    model = MotionGenerator(len(glosses), seq_len=seq_len)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: list[float] = []
    for _ in range(epochs):
        order = torch.randperm(len(ids))
        total = 0.0
        for start in range(0, len(order), batch_size):
            batch = order[start : start + batch_size]
            loss = torch.nn.functional.mse_loss(model(ids[batch]), targets[batch])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item() * len(batch)
        history.append(total / len(order))
    return model, history


def model_generator(
    model: MotionGenerator, glosses: list[str]
) -> Callable[[str], np.ndarray]:
    gloss_to_id = {g: i for i, g in enumerate(glosses)}

    def generate(gloss: str) -> np.ndarray:
        model.eval()
        with torch.no_grad():
            out = model(torch.tensor([gloss_to_id[gloss]]))
        return out[0].numpy()

    return generate


def evaluate(
    generate: Callable[[str], np.ndarray], val: list[Sample], seq_len: int
) -> dict:
    """DTW médio entre o movimento gerado e cada gravação de validação.

    Mede fidelidade à gravação, não correção linguística. A duração não é avaliada
    (o DTW alinha no tempo e as sequências são reamostradas para `seq_len`).
    """
    per_gloss: dict[str, list[float]] = {}
    for sample in val:
        reference = resample(sample.keypoints, seq_len)
        per_gloss.setdefault(sample.gloss, []).append(
            dtw_distance(generate(sample.gloss), reference)
        )
    all_values = [v for values in per_gloss.values() for v in values]
    return {
        "mean_dtw": float(np.mean(all_values)),
        "per_gloss": {g: float(np.mean(v)) for g, v in sorted(per_gloss.items())},
        "n_samples": len(all_values),
    }


def retrieval(
    generate: Callable[[str], np.ndarray], val: list[Sample], seq_len: int
) -> dict:
    """O movimento gerado para um sinal se parece mais com a gravação desse sinal do que com as dos outros?

    Para cada sinalizante de validação e cada sinal dele, gera o movimento e mede o DTW até
    as gravações **desse mesmo sinalizante** (a melhor de cada sinal). A posição do sinal
    certo nessa lista vira `top1`, `top5` e `mean_rank` (1 = o certo é o mais parecido).

    Ao contrário do DTW médio, **não premia movimento borrado**: um método que devolve a
    mesma sequência para qualquer sinal (a média global) cai no acaso (`chance_top1`).
    Mede se a geração carrega a identidade do sinal, não correção linguística.
    """
    by_signer: dict[str, list[Sample]] = {}
    for sample in val:
        by_signer.setdefault(sample.signer, []).append(sample)

    ranks: list[int] = []
    n_candidates: list[int] = []
    for samples in by_signer.values():
        references: dict[str, list[np.ndarray]] = {}
        for sample in samples:
            references.setdefault(sample.gloss, []).append(resample(sample.keypoints, seq_len))
        glosses = sorted(references)
        for gloss in glosses:
            generated = generate(gloss)
            distance = {
                g: min(dtw_distance(generated, ref) for ref in refs) for g, refs in references.items()
            }
            target = distance[gloss]
            # empates repartidos: o método que devolve sempre a mesma sequência não ganha por ordem alfabética
            better = sum(d < target for g, d in distance.items() if g != gloss)
            ties = sum(d == target for g, d in distance.items() if g != gloss)
            ranks.append(1 + better + int(round(ties / 2)))
            n_candidates.append(len(glosses))
    ranks_array = np.array(ranks)
    return {
        "top1": float(np.mean(ranks_array <= 1)),
        "top5": float(np.mean(ranks_array <= 5)),
        "mean_rank": float(np.mean(ranks_array)),
        "chance_top1": float(np.mean(1.0 / np.array(n_candidates))),
        "chance_mean_rank": float(np.mean((np.array(n_candidates) + 1) / 2)),
        "n": len(ranks),
    }


def run(
    train: list[Sample],
    val: list[Sample],
    glosses: list[str],
    seq_len: int,
    epochs: int,
) -> tuple[MotionGenerator, dict]:
    model, history = train_model(train, glosses, seq_len=seq_len, epochs=epochs)
    methods: dict[str, Callable[[str], np.ndarray]] = {
        "global_mean": GlobalMeanBaseline(seq_len).fit(train).generate,
        "class_mean": ClassMeanBaseline(seq_len).fit(train).generate,
        "medoid": MedoidBaseline(seq_len).fit(train).generate,
        "model": model_generator(model, glosses),
    }
    results = {name: evaluate(fn, val, seq_len) for name, fn in methods.items()}
    for name, fn in methods.items():
        results[name]["retrieval"] = retrieval(fn, val, seq_len)
    results["train_loss_first_last"] = [history[0], history[-1]]
    results["n_train"] = len(train)
    return model, results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--data-root", type=Path, help="pasta com <sinalizante>/<SINAL>_<n>.npy")
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--val-signers", default="", help="sinalizantes de validação, separados por vírgula")
    parser.add_argument("--synthetic", action="store_true", help="usa dados sintéticos")
    parser.add_argument("--seq-len", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--out-dir", type=Path, default=Path("checkpoints"))
    args = parser.parse_args()

    glosses = load_vocabulary(args.vocabulary)
    if args.synthetic:
        samples = make_synthetic(glosses)
    elif args.data_root:
        samples = load_dataset(args.data_root, glosses)
    else:
        parser.error("informe --data-root ou --synthetic")
    if not samples:
        parser.error("nenhuma amostra encontrada")

    signers = sorted({s.signer for s in samples})
    val_signers = {s for s in args.val_signers.split(",") if s} or {signers[-1]}
    unknown = val_signers - set(signers)
    if unknown:
        parser.error(f"sinalizantes de validação inexistentes: {sorted(unknown)}")
    train, val = split_by_signer(samples, val_signers)
    if not train or not val:
        parser.error("é preciso ter pelo menos um sinalizante em treino e um em validação")

    model, results = run(train, val, glosses, args.seq_len, args.epochs)
    results["val_signers"] = sorted(val_signers)
    results["train_signers"] = [s for s in signers if s not in val_signers]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": model.state_dict(), "glosses": glosses, "seq_len": args.seq_len},
        args.out_dir / "model.pt",
    )
    (args.out_dir / "metrics.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    chance = results["global_mean"]["retrieval"]
    print(f"(acaso: top1 {chance['chance_top1']:.1%}, posição média {chance['chance_mean_rank']:.0f})")
    for name in ("global_mean", "class_mean", "medoid", "model"):
        r = results[name]["retrieval"]
        print(
            f"{name:12s} DTW médio = {results[name]['mean_dtw']:.4f} | "
            f"recuperação: top1 {r['top1']:.1%}, top5 {r['top5']:.1%}, posição média {r['mean_rank']:.1f}"
        )


if __name__ == "__main__":
    main()
