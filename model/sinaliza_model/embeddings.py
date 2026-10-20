"""Inspeção dos embeddings de sinal que o `MotionGenerator` aprende.

A primeira camada do gerador é `nn.Embedding(num_glosses, hidden)`: cada sinal vira
um vetor, e é esse vetor que condiciona o movimento gerado. Aqui dá para olhar essa
geometria:

- quais sinais ficaram **próximos** no espaço aprendido (similaridade de cosseno);
- se essa proximidade acompanha a **proximidade de movimento** medida em DTW entre
  a média das gravações de cada sinal (correlação de postos de Spearman).

Leitura honesta: com 20 sinais e poucos sinalizantes, vizinhança no embedding
reflete o que o modelo precisou para reduzir o MSE, não semelhança linguística entre
os sinais. Serve para diagnosticar o treino (embeddings colapsados, por exemplo),
não para afirmar nada sobre Libras.

    python -m sinaliza_model.embeddings checkpoints/model.pt
    python -m sinaliza_model.embeddings checkpoints/model.pt --data-root ../data/processed/minds-libras
"""

import argparse
from pathlib import Path

import numpy as np
import torch

from .baseline import ClassMeanBaseline
from .data import Sample, load_dataset
from .metrics import dtw_distance


def gloss_embeddings(model: torch.nn.Module) -> np.ndarray:
    """Matriz (num_glosses, hidden) do `nn.Embedding` do modelo."""
    return model.embedding.weight.detach().cpu().numpy()


def checkpoint_embeddings(path: Path) -> tuple[list[str], np.ndarray]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    return checkpoint["glosses"], checkpoint["state_dict"]["embedding.weight"].numpy()


def cosine_similarity(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    unit = vectors / np.where(norms == 0, 1.0, norms)
    return unit @ unit.T


def nearest_neighbors(vectors: np.ndarray, glosses: list[str], k: int = 3) -> dict[str, list[tuple[str, float]]]:
    similarity = cosine_similarity(vectors)
    result: dict[str, list[tuple[str, float]]] = {}
    for i, gloss in enumerate(glosses):
        order = [j for j in np.argsort(-similarity[i]) if j != i][:k]
        result[gloss] = [(glosses[j], float(similarity[i, j])) for j in order]
    return result


def motion_distances(samples: list[Sample], glosses: list[str], seq_len: int = 32) -> np.ndarray:
    """DTW entre as médias de movimento de cada par de sinais (matriz simétrica)."""
    means = ClassMeanBaseline(seq_len).fit(samples)
    n = len(glosses)
    out = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            out[i, j] = out[j, i] = dtw_distance(means.generate(glosses[i]), means.generate(glosses[j]))
    return out


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values))
    ranks[order] = np.arange(len(values))
    # empates recebem o posto médio
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = _ranks(np.asarray(a, dtype=float)), _ranks(np.asarray(b, dtype=float))
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def embedding_vs_motion(vectors: np.ndarray, distances: np.ndarray) -> float:
    """Spearman entre a distância de cosseno dos embeddings e o DTW, sobre os pares de sinais.

    Positivo e alto: sinais com movimento parecido ficaram perto no embedding.
    """
    n = len(vectors)
    upper = np.triu_indices(n, k=1)
    cosine_distance = 1.0 - cosine_similarity(vectors)
    return spearman(cosine_distance[upper], distances[upper])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--neighbors", type=int, default=3)
    parser.add_argument("--data-root", type=Path, help="se informado, compara com o DTW entre as médias de movimento")
    args = parser.parse_args()

    glosses, vectors = checkpoint_embeddings(args.checkpoint)
    for gloss, neighbors in nearest_neighbors(vectors, glosses, args.neighbors).items():
        print(f"{gloss:12s} " + "  ".join(f"{g} ({s:.2f})" for g, s in neighbors))

    if args.data_root:
        samples = load_dataset(args.data_root, glosses)
        if not samples:
            parser.error("nenhuma amostra encontrada em --data-root")
        rho = embedding_vs_motion(vectors, motion_distances(samples, glosses, seq_len=32))
        print(f"\nSpearman (distância no embedding x DTW entre médias de movimento): {rho:.3f}")


if __name__ == "__main__":
    main()
