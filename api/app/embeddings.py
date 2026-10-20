"""Embeddings de palavras para mapear palavras fora do vocabulário ao sinal mais próximo.

Dois embedders, mesma interface (`embed(words) -> matriz de linhas unitárias`):

- `CharNgramEmbedder` (padrão): n-gramas de caracteres, só NumPy, sem download.
  Captura **forma**: flexões, plurais e erros de digitação ("vacna" → "vacina").
  Não captura **sentido**: não liga "garoto" a "filho".
- `SentenceTransformerEmbedder` (opcional): modelo multilíngue. Captura sentido
  (sinônimos, palavras relacionadas) e também erra por proximidade semântica.
  Exige `pip install -r requirements-semantic.txt` e baixa o modelo na primeira vez.

Escolha pela variável `SINALIZA_EMBEDDER` (`char-ngram` ou `sentence-transformers`).

Proximidade não é equivalência em Libras: o mapeamento aproximado é uma proposta,
mostrada ao usuário como tal (ver `text_to_gloss.py`).
"""

import os
import zlib
from collections.abc import Sequence
from typing import Protocol

import numpy as np

from .vocabulary import slug


class Embedder(Protocol):
    name: str
    default_threshold: float

    def embed(self, words: Sequence[str]) -> np.ndarray: ...


class CharNgramEmbedder:
    name = "char-ngram"
    # Calibrado à mão no vocabulário curado do V-LIBRASIL (210 sinais, 281 formas):
    # 0,7 pega erros de digitação ("escolla" 0,78) e não pega vizinhos de escrita
    # parecida ("banco" 0,64 → BRANCO, "irmao" 0,67 → IRMÃ, que é outra palavra).
    # Precisão antes de cobertura: o que passa vira sinal na tela. Com 63 formas (20
    # sinais) o limiar bom era 0,65; ele sobe com o tamanho do vocabulário.
    default_threshold = 0.7

    def __init__(self, dims: int = 1024, ngrams: tuple[int, ...] = (2, 3, 4)):
        self.dims = dims
        self.ngrams = ngrams

    def embed(self, words: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(words), self.dims), dtype=np.float32)
        for row, word in enumerate(words):
            padded = f"^{slug(word)}$"
            for n in self.ngrams:
                for start in range(len(padded) - n + 1):
                    # crc32 é estável entre execuções (o hash() do Python não é)
                    code = zlib.crc32(padded[start : start + n].encode("utf-8"))
                    out[row, code % self.dims] += 1.0 if (code >> 31) & 1 else -1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1.0, norms)


class SentenceTransformerEmbedder:
    name = "sentence-transformers"
    default_threshold = 0.7

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed(self, words: Sequence[str]) -> np.ndarray:
        vectors = self.model.encode([w.lower() for w in words], normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)


def build_embedder(name: str | None = None) -> Embedder:
    name = name or os.environ.get("SINALIZA_EMBEDDER", CharNgramEmbedder.name)
    if name == CharNgramEmbedder.name:
        return CharNgramEmbedder()
    if name == SentenceTransformerEmbedder.name:
        return SentenceTransformerEmbedder()
    raise ValueError(f"embedder desconhecido: {name!r}")
