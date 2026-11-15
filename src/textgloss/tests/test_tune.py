import optuna
import pandas as pd

from textgloss import tune


def test_suggest_converte_nenhum_em_none_e_fracao_em_float():
    trial = optuna.trial.FixedTrial(
        {"max_features_tipo": "fracao", "max_features_fracao": 0.2, "class_weight": "nenhum",
         "n_estimators": 60, "max_depth": 20, "min_samples_leaf": 3, "criterion": "gini"}
    )
    params = tune.suggest(trial)
    assert params["class_weight"] is None
    assert params["max_features"] == 0.2


def test_suggest_sqrt():
    trial = optuna.trial.FixedTrial(
        {"max_features_tipo": "sqrt", "class_weight": "balanced", "n_estimators": 60,
         "max_depth": 20, "min_samples_leaf": 3, "criterion": "entropy"}
    )
    assert tune.suggest(trial)["max_features"] == "sqrt"


def test_cv_sample_mantem_frases_inteiras():
    fit = pd.DataFrame({"frase_id": [i // 5 for i in range(500)], "x": range(500)})
    sample = tune.cv_sample(fit, 20)
    assert sample["frase_id"].nunique() == 20
    assert (sample.groupby("frase_id").size() == 5).all()
