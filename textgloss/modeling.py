"""Dados, pré-processamento e avaliação compartilhados por baseline, comparação e Optuna.

ETAPA: preparação para o ML (encoding) e avaliação. Nenhuma decisão é tomada aqui:
o que decide quais palavras viram sinal é o classificador treinado em train.py.
"""
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    ConfusionMatrixDisplay,
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config, corpus

TARGET = "rotulo"
CATEGORICAL = [
    "upos", "dep", "tipo_frase", "upos_anterior", "upos_seguinte",
    "m_Gender", "m_Number", "m_Tense", "m_VerbForm", "m_Mood", "m_Person", "m_Polarity", "m_PronType",
]
NUMERIC = ["pos", "pos_relativa", "tam_frase", "stop"]
LEMMA = "lema"
N_LEMMAS = 2000
FEATURES = CATEGORICAL + NUMERIC + [LEMMA]
CLASS_NAMES = ["DESCARTAR", "MANTER"]


def load_words() -> pd.DataFrame:
    return pd.read_parquet(config.PROCESSED_DIR / "palavras.parquet")


def train_validation(words: pd.DataFrame, fraction: float = 0.1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa uma validação de 10% das FRASES de treino. O teste (split == 'teste') não é tocado."""
    train = words[words["split"] == "treino"].reset_index(drop=True)
    splitter = GroupShuffleSplit(n_splits=1, test_size=fraction, random_state=config.SEED)
    fit_idx, val_idx = next(splitter.split(train, groups=train["frase_id"]))
    return train.iloc[fit_idx].reset_index(drop=True), train.iloc[val_idx].reset_index(drop=True)


def preprocessor(scale: bool = True) -> ColumnTransformer:
    """One-hot dos categóricos; lema limitado aos N_LEMMAS mais frequentes (o resto vira 'infrequente')."""
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            (
                "lema",
                OneHotEncoder(handle_unknown="infrequent_if_exist", max_categories=N_LEMMAS + 1),
                [LEMMA],
            ),
            ("num", StandardScaler() if scale else "passthrough", NUMERIC),
        ]
    )


def make_pipeline(classifier, scale: bool = True) -> Pipeline:
    return Pipeline([("prep", preprocessor(scale)), ("clf", classifier)])


def function_words() -> set[str]:
    """Lista fixa usada hoje pela API (api/app/text_to_gloss.py), lida do código-fonte."""
    source = (config.ROOT / "api" / "app" / "text_to_gloss.py").read_text(encoding="utf-8")
    block = re.search(r"FUNCTION_WORDS = frozenset\((.*?)\)\s*\n\n", source, re.S).group(1)
    return {corpus.slug(w) for text in re.findall(r'"([^"]+)"', block) for w in text.split()}


def fixed_list_predict(words: pd.DataFrame) -> np.ndarray:
    """1 (MANTER) se a palavra NÃO está na lista fixa; é o comportamento atual da API."""
    return (~words["palavra"].map(corpus.slug).isin(function_words())).astype(int).to_numpy()


def evaluate(y_true, y_pred, y_score=None) -> dict:
    """Métricas do T1. F1-macro é a principal; ROC-AUC e PR-AUC usam a pontuação contínua se houver."""
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=[0, 1], zero_division=0)
    metrics = {
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_manter": f1[1],
        "f1_descartar": f1[0],
        "precision_manter": precision[1],
        "recall_manter": recall[1],
        "precision_descartar": precision[0],
        "recall_descartar": recall[0],
    }
    score = y_pred if y_score is None else y_score
    metrics["roc_auc"] = roc_auc_score(y_true, score)
    metrics["pr_auc"] = average_precision_score(y_true, score)
    return {k: float(v) for k, v in metrics.items()}


def plot_confusion(y_true, y_pred, title: str):
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ConfusionMatrixDisplay.from_predictions(
        y_true, y_pred, display_labels=CLASS_NAMES, cmap="Blues", ax=ax, colorbar=False, values_format="d"
    )
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_curves(y_true, y_score, title: str):
    fig, (roc_ax, pr_ax) = plt.subplots(1, 2, figsize=(9, 3.8))
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_ax.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_true, y_score):.3f}")
    roc_ax.plot([0, 1], [0, 1], "--", color="gray")
    roc_ax.set(xlabel="falso positivo", ylabel="verdadeiro positivo", title=f"ROC · {title}")
    roc_ax.legend(loc="lower right")
    precision, recall, _ = precision_recall_curve(y_true, y_score)
    pr_ax.plot(recall, precision, label=f"AP = {average_precision_score(y_true, y_score):.3f}")
    pr_ax.set(xlabel="revocação", ylabel="precisão", title=f"Precisão-revocação · {title}")
    pr_ax.legend(loc="lower left")
    fig.tight_layout()
    return fig
