import pandas as pd
import pytest

from textgloss import validate


def test_modelos_validos_e_constantes():
    assert validate.CV_FOLDS == 5
    assert set(validate.MODELS) == {"regressao-logistica", "random-forest-otimizado"}


def test_build_regressao_logistica_nao_precisa_do_mlflow():
    model = validate.build("regressao-logistica")
    assert model.named_steps["clf"].class_weight == "balanced"


def test_score_devolve_metricas_do_t1():
    class Fake:
        def predict_proba(self, X):
            import numpy as np
            return np.column_stack([1 - X["x"], X["x"]])

    frame = pd.DataFrame({"x": [0.9, 0.2, 0.8, 0.1], "rotulo": [1, 0, 1, 0]})
    validate.modeling.FEATURES, original = ["x"], validate.modeling.FEATURES
    try:
        result = validate.score(Fake(), frame)
    finally:
        validate.modeling.FEATURES = original
    assert result["f1_macro"] == 1.0
    assert result["roc_auc"] == 1.0
