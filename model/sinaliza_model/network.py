import torch
from torch import nn

from .data import NUM_KEYPOINTS


class MotionGenerator(nn.Module):
    """Gera `seq_len` frames de keypoints a partir do índice do sinal.

    Embedding do sinal + consulta aprendida por instante → GRU → keypoints.
    A saída tem duração fixa; a duração real é decidida fora do modelo.
    """

    def __init__(
        self, num_glosses: int, seq_len: int = 32, hidden: int = 128, layers: int = 2
    ):
        super().__init__()
        self.seq_len = seq_len
        self.embedding = nn.Embedding(num_glosses, hidden)
        self.time_query = nn.Parameter(torch.randn(seq_len, hidden) * 0.02)
        self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        self.head = nn.Linear(hidden, NUM_KEYPOINTS * 3)

    def forward(self, gloss_ids: torch.Tensor) -> torch.Tensor:
        x = self.embedding(gloss_ids)[:, None, :] + self.time_query[None]
        hidden, _ = self.gru(x)
        out = self.head(hidden)
        return out.view(len(gloss_ids), self.seq_len, NUM_KEYPOINTS, 3)
