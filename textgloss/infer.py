"""Inferência do T1: dado um texto, decide MANTER ou DESCARTAR para cada palavra.

ETAPA: ML nosso, em produção. Carrega o Random Forest otimizado registrado no MLflow como `sinaliza-t1`
(treinado em `train`/`tune` e aprovado em `validate teste`), extrai os atributos com o spaCy
(`features.doc_rows`, o mesmo código do treino) e devolve a probabilidade de MANTER por palavra.
É usado pela API (`api/app/main.py`) no lugar da lista fixa `FUNCTION_WORDS`.

Os imports pesados (spaCy, pandas, MLflow) são feitos só quando precisam, para a API subir sem eles
(nesse caso ela volta à lista fixa).
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

MODEL_NAME = "sinaliza-t1"
# O modelo foi avaliado com este limiar (train.py e validate.py usam proba >= 0.5).
THRESHOLD = 0.5


@dataclass(frozen=True)
class WordDecision:
    """Decisão do modelo para uma palavra do texto, com a posição dela em caracteres."""

    start: int
    end: int
    word: str
    probability: float  # probabilidade da classe MANTER

    @property
    def keep(self) -> bool:
        return self.probability >= THRESHOLD


class T1Classifier:
    def __init__(self, model, nlp, version: str):
        self.model = model
        self.nlp = nlp
        self.version = version

    def decide(self, text: str) -> list[WordDecision]:
        """Uma decisão por palavra (pontuação e espaços ficam de fora, como no treino)."""
        import pandas as pd

        from . import features

        doc = self.nlp(text)
        tokens = [t for t in doc if not t.is_punct and not t.is_space]
        if not tokens:
            return []
        # features.doc_rows usa o mesmo filtro de tokens: a linha i corresponde a tokens[i].
        frame = pd.DataFrame(features.doc_rows(doc, 0))
        probabilities = self.model.predict_proba(frame)[:, 1]
        return [
            WordDecision(token.idx, token.idx + len(token.text), token.text, float(p))
            for token, p in zip(tokens, probabilities)
        ]


def latest_version(client, name: str = MODEL_NAME) -> int:
    versions = [int(v.version) for v in client.search_model_versions(f"name='{name}'")]
    if not versions:
        raise LookupError(f"o modelo {name} não tem nenhuma versão registrada no MLflow")
    return max(versions)


def _fetch_model(name: str, version: int, cache_dir: str | None) -> str:
    """Devolve o caminho local do modelo. Com `cache_dir`, baixa uma vez (o modelo tem centenas de MB)."""
    import mlflow

    uri = f"models:/{name}/{version}"
    if not cache_dir:
        return uri
    target = Path(cache_dir) / name / str(version)
    if (target / "MLmodel").exists():
        return str(target)
    partial = target.with_name(f"{version}.parcial")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    downloaded = Path(mlflow.artifacts.download_artifacts(artifact_uri=uri, dst_path=str(partial)))
    shutil.rmtree(target, ignore_errors=True)
    downloaded.replace(target)
    shutil.rmtree(partial, ignore_errors=True)
    return str(target)


def load_from_mlflow(
    tracking_uri: str | None = None,
    name: str = MODEL_NAME,
    version: int | None = None,
    cache_dir: str | None = None,
) -> T1Classifier:
    """Carrega o modelo registrado (a versão mais alta, se `version` não for dada) e o spaCy."""
    import mlflow
    import mlflow.sklearn

    from . import features

    mlflow.set_tracking_uri(tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    if version is None:
        version = latest_version(mlflow.MlflowClient(), name)
    path = _fetch_model(name, version, cache_dir)
    model = mlflow.sklearn.load_model(path)
    return T1Classifier(model, features.load_nlp(), f"{name}/{version}")
