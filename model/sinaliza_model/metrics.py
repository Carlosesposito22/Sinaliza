"""Métricas objetivas de fidelidade ao movimento gravado.

Elas NÃO medem correção linguística: um movimento próximo da gravação de
referência ainda pode estar errado como sinal.
"""

import numpy as np


def dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """DTW entre duas sequências (frames, 75, 3), normalizado por (len(a) + len(b)).

    O custo entre frames é a distância euclidiana sobre todos os keypoints, na
    unidade do formato de pose (largura entre ombros = 1).
    """
    flat_a = a.reshape(len(a), -1).astype(np.float64)
    flat_b = b.reshape(len(b), -1).astype(np.float64)
    cost = np.sqrt(((flat_a[:, None, :] - flat_b[None, :, :]) ** 2).sum(axis=-1)).tolist()

    inf = float("inf")
    n, m = len(cost), len(cost[0])
    previous = [inf] * (m + 1)
    previous[0] = 0.0
    for i in range(n):
        current = [inf] * (m + 1)
        row = cost[i]
        for j in range(m):
            current[j + 1] = row[j] + min(previous[j + 1], current[j], previous[j])
        previous = current
    return previous[m] / (n + m)
