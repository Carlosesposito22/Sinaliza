"""Baseline do T1 no MLflow: lista fixa (sem ML) e Regressão Logística.

ETAPA: ML nosso. A Regressão Logística aprende, com os rótulos dos intérpretes, quais palavras
viram sinal. A lista fixa é a referência sem ML (o que a API faz hoje) e roda no mesmo conjunto.
Uso: python -m textgloss.train baseline
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.linear_model import LogisticRegression

from . import config, modeling

EXPERIMENT = "t1-manter-descartar"
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")


def dataset_params(fit: pd.DataFrame, val: pd.DataFrame) -> dict:
    return {
        "corpus_sha256": config.CSV_SHA256,
        "n_palavras_treino": len(fit),
        "n_palavras_validacao": len(val),
        "n_frases_treino": int(fit["frase_id"].nunique()),
        "n_frases_validacao": int(val["frase_id"].nunique()),
        "proporcao_manter_treino": round(float(fit[modeling.TARGET].mean()), 4),
        "semente": config.SEED,
        "atributos": ",".join(modeling.FEATURES),
    }


def log_figure(fig, name: str) -> None:
    mlflow.log_figure(fig, name)
    plt.close(fig)


def run_fixed_list(val: pd.DataFrame, params: dict) -> dict:
    y = val[modeling.TARGET]
    pred = modeling.fixed_list_predict(val)
    with mlflow.start_run(run_name="lista-fixa"):
        mlflow.set_tags({"etapa": "baseline", "usa_ml": "nao", "modelo": "lista-fixa"})
        mlflow.log_params({**params, "tamanho_lista": len(modeling.function_words())})
        metrics = modeling.evaluate(y, pred)
        mlflow.log_metrics({f"val_{k}": v for k, v in metrics.items()})
        log_figure(modeling.plot_confusion(y, pred, "Lista fixa · validação"), "matriz_confusao_validacao.png")
    return metrics


def run_logistic(fit: pd.DataFrame, val: pd.DataFrame, params: dict, c: float = 1.0) -> dict:
    classifier = LogisticRegression(C=c, class_weight="balanced", solver="lbfgs", max_iter=1000)
    model = modeling.make_pipeline(classifier)
    with mlflow.start_run(run_name="regressao-logistica"):
        mlflow.set_tags({"etapa": "baseline", "usa_ml": "sim", "modelo": "regressao-logistica"})
        mlflow.log_params(
            {**params, "C": c, "class_weight": "balanced", "solver": "lbfgs", "max_iter": 1000,
             "n_lemas_one_hot": modeling.N_LEMMAS}
        )
        model.fit(fit[modeling.FEATURES], fit[modeling.TARGET])

        results = {}
        for name, frame in (("treino", fit), ("val", val)):
            proba = model.predict_proba(frame[modeling.FEATURES])[:, 1]
            pred = (proba >= 0.5).astype(int)
            results[name] = modeling.evaluate(frame[modeling.TARGET], pred, proba)
            mlflow.log_metrics({f"{name}_{k}": v for k, v in results[name].items()})
            if name == "val":
                y, val_pred, val_proba = frame[modeling.TARGET], pred, proba
        mlflow.log_metric("gap_f1_macro_treino_val", results["treino"]["f1_macro"] - results["val"]["f1_macro"])

        log_figure(modeling.plot_confusion(y, val_pred, "Regressão Logística · validação"), "matriz_confusao_validacao.png")
        log_figure(modeling.plot_curves(y, val_proba, "validação"), "curvas_roc_pr_validacao.png")

        names = model.named_steps["prep"].get_feature_names_out()
        coefs = pd.Series(model.named_steps["clf"].coef_[0], index=names).sort_values()
        shown = pd.concat([coefs.head(15), coefs.tail(15)])
        fig, ax = plt.subplots(figsize=(7, 7))
        shown.plot.barh(ax=ax, color=["#e45756"] * 15 + ["#4c78a8"] * 15)
        ax.set(title="Coeficientes extremos (− descarta, + mantém)", xlabel="coeficiente")
        fig.tight_layout()
        log_figure(fig, "coeficientes.png")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coeficientes.csv"
            coefs.sort_values(ascending=False).rename("coeficiente").to_csv(path)
            mlflow.log_artifact(str(path))
        mlflow.sklearn.log_model(model, name="modelo", input_example=fit[modeling.FEATURES].head(3))
    return results["val"]


def baseline() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    words = modeling.load_words()
    fit, val = modeling.train_validation(words)
    params = dataset_params(fit, val)
    lista = run_fixed_list(val, params)
    logistica = run_logistic(fit, val, params)
    print(json.dumps({"lista_fixa": lista, "regressao_logistica": logistica}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("etapa", choices=["baseline"])
    args = parser.parse_args()
    {"baseline": baseline}[args.etapa]()


if __name__ == "__main__":
    main()
