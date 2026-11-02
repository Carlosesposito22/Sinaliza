"""Treino do T1 no MLflow: baseline (fase 3) e comparação de modelos (fase 4).

ETAPA: ML nosso. Os classificadores aprendem, com os rótulos dos intérpretes, quais palavras
viram sinal. A lista fixa é a referência sem ML (o que a API faz hoje) e roda no mesmo conjunto.
Uso: python -m textgloss.train baseline | modelos | comparar
"""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from . import config, modeling

EXPERIMENT = "t1-manter-descartar"
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
KNN_SAMPLE = 200_000
MODEL_NAMES = ["regressao-logistica", "arvore-de-decisao", "random-forest", "knn"]


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


def log_importances(model: Pipeline, top: int = 20) -> None:
    names = model.named_steps["prep"].get_feature_names_out()
    importance = pd.Series(model.named_steps["clf"].feature_importances_, index=names).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7, 6))
    importance.head(top)[::-1].plot.barh(ax=ax, color="#4c78a8")
    ax.set(title=f"Importância dos {top} atributos mais usados", xlabel="importância")
    fig.tight_layout()
    log_figure(fig, "importancia_atributos.png")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "importancia_atributos.csv"
        importance.rename("importancia").to_csv(path)
        mlflow.log_artifact(str(path))


def log_coefficients(model: Pipeline) -> None:
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


def run_model(name: str, model: Pipeline, fit: pd.DataFrame, val: pd.DataFrame, params: dict,
              model_params: dict, etapa: str, extra) -> dict:
    """Treina, avalia em treino e validação e registra tudo em uma run do MLflow."""
    with mlflow.start_run(run_name=name):
        mlflow.set_tags({"etapa": etapa, "usa_ml": "sim", "modelo": name})
        mlflow.log_params({**params, **model_params, "n_palavras_ajuste": len(fit)})

        started = time.perf_counter()
        model.fit(fit[modeling.FEATURES], fit[modeling.TARGET])
        mlflow.log_metric("tempo_treino_s", time.perf_counter() - started)

        results = {}
        for part, frame in (("treino", fit), ("val", val)):
            started = time.perf_counter()
            proba = model.predict_proba(frame[modeling.FEATURES])[:, 1]
            if part == "val":
                mlflow.log_metric("tempo_predicao_val_s", time.perf_counter() - started)
            pred = (proba >= 0.5).astype(int)
            results[part] = modeling.evaluate(frame[modeling.TARGET], pred, proba)
            mlflow.log_metrics({f"{part}_{k}": v for k, v in results[part].items()})
            if part == "val":
                y, val_pred, val_proba = frame[modeling.TARGET], pred, proba
        mlflow.log_metric("gap_f1_macro_treino_val", results["treino"]["f1_macro"] - results["val"]["f1_macro"])

        log_figure(modeling.plot_confusion(y, val_pred, f"{name} · validação"), "matriz_confusao_validacao.png")
        log_figure(modeling.plot_curves(y, val_proba, "validação"), "curvas_roc_pr_validacao.png")
        extra(model)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predicoes_validacao.npy"
            np.save(path, val_proba.astype("float32"))
            mlflow.log_artifact(str(path))
        mlflow.sklearn.log_model(
            model,
            name="modelo",
            input_example=fit[modeling.FEATURES].head(3),
            skops_trusted_types=["sklearn.tree._tree.Tree"],
        )
    return results["val"]


def logistic_model(c: float = 1.0):
    classifier = LogisticRegression(C=c, class_weight="balanced", solver="lbfgs", max_iter=1000)
    spec = {"C": c, "class_weight": "balanced", "solver": "lbfgs", "max_iter": 1000,
            "n_lemas_one_hot": modeling.N_LEMMAS}
    return modeling.make_pipeline(classifier), spec


def tree_model():
    spec = {"max_depth": 25, "min_samples_leaf": 20, "class_weight": "balanced"}
    classifier = DecisionTreeClassifier(random_state=config.SEED, **spec)
    return modeling.make_pipeline(classifier, scale=False), spec


def forest_model():
    spec = {"n_estimators": 100, "max_depth": 30, "min_samples_leaf": 10, "max_features": "sqrt",
            "class_weight": "balanced"}
    classifier = RandomForestClassifier(random_state=config.SEED, n_jobs=-1, **spec)
    return modeling.make_pipeline(classifier, scale=False), spec


def knn_model():
    """KNN com atributos reduzidos por TruncatedSVD (50 componentes): vizinhos em 2.000+ colunas esparsas custam demais."""
    spec = {"n_neighbors": 25, "weights": "distance", "svd_componentes": 50, "amostra_treino": KNN_SAMPLE}
    pipeline = Pipeline(
        [
            ("prep", modeling.preprocessor()),
            ("svd", TruncatedSVD(n_components=50, random_state=config.SEED)),
            ("clf", KNeighborsClassifier(n_neighbors=25, weights="distance", n_jobs=-1)),
        ]
    )
    return pipeline, spec


def baseline() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    fit, val = modeling.train_validation(modeling.load_words())
    params = dataset_params(fit, val)
    lista = run_fixed_list(val, params)
    model, spec = logistic_model()
    logistica = run_model("regressao-logistica", model, fit, val, params, spec, "baseline", log_coefficients)
    print(json.dumps({"lista_fixa": lista, "regressao_logistica": logistica}, indent=2))


def modelos() -> None:
    """Fase 4: Árvore de Decisão, Random Forest e KNN, avaliados na mesma validação do baseline."""
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    fit, val = modeling.train_validation(modeling.load_words())
    params = dataset_params(fit, val)
    knn_fit = fit.sample(KNN_SAMPLE, random_state=config.SEED)
    out = {}
    for name, build, frame, extra in (
        ("arvore-de-decisao", tree_model, fit, log_importances),
        ("random-forest", forest_model, fit, log_importances),
        ("knn", knn_model, knn_fit, lambda model: None),
    ):
        model, spec = build()
        out[name] = run_model(name, model, frame, val, params, spec, "comparacao", extra)
        print(name, json.dumps({k: round(v, 4) for k, v in out[name].items() if k in ("f1_macro", "roc_auc")}))


def latest_runs() -> dict:
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT)
    runs = client.search_runs([experiment.experiment_id], filter_string="attributes.status = 'FINISHED'",
                              order_by=["attributes.start_time DESC"])
    found = {}
    for run in runs:
        found.setdefault(run.data.tags.get("modelo"), run)
    return found


def comparar() -> None:
    """Junta os modelos em uma run só: tabela de métricas e curvas ROC e PR sobrepostas."""
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    fit, val = modeling.train_validation(modeling.load_words())
    y = val[modeling.TARGET].to_numpy()
    runs = latest_runs()
    scores = {}
    for name in MODEL_NAMES:
        path = mlflow.artifacts.download_artifacts(
            artifact_uri=f"runs:/{runs[name].info.run_id}/predicoes_validacao.npy", tracking_uri=TRACKING_URI
        )
        scores[name] = np.load(path)

    rows = []
    for name in ["lista-fixa"] + MODEL_NAMES:
        m = runs[name].data.metrics
        rows.append({"modelo": name, **{k: m.get(f"val_{k}") for k in
                     ("f1_macro", "roc_auc", "pr_auc", "recall_descartar", "recall_manter")},
                     "gap_treino_val": m.get("gap_f1_macro_treino_val"),
                     "tempo_treino_s": m.get("tempo_treino_s"), "tempo_predicao_val_s": m.get("tempo_predicao_val_s")})
    table = pd.DataFrame(rows).round(4)

    fig, (roc_ax, pr_ax) = plt.subplots(1, 2, figsize=(11, 4.2))
    for name, score in scores.items():
        fpr, tpr, _ = roc_curve(y, score)
        roc_ax.plot(fpr, tpr, label=f"{name} ({roc_auc_score(y, score):.3f})")
        precision, recall, _ = precision_recall_curve(y, score)
        pr_ax.plot(recall, precision, label=f"{name} ({average_precision_score(y, score):.3f})")
    roc_ax.plot([0, 1], [0, 1], "--", color="gray")
    roc_ax.set(xlabel="falso positivo", ylabel="verdadeiro positivo", title="ROC (AUC) · validação")
    pr_ax.set(xlabel="revocação", ylabel="precisão", title="Precisão-revocação (AP) · validação")
    roc_ax.legend(loc="lower right"); pr_ax.legend(loc="lower left")
    fig.tight_layout()

    f1_fig, ax = plt.subplots(figsize=(7, 3.5))
    table.set_index("modelo")["f1_macro"].plot.barh(ax=ax, color="#4c78a8")
    ax.set(xlim=(0.7, 1.0), title="F1-macro na validação", xlabel="F1-macro")
    f1_fig.tight_layout()

    with mlflow.start_run(run_name="comparacao-modelos"):
        mlflow.set_tags({"etapa": "comparacao", "modelo": "resumo"})
        mlflow.log_params({"modelos": ",".join(["lista-fixa"] + MODEL_NAMES)})
        for row in table.itertuples():
            mlflow.log_metric(f"f1_macro__{row.modelo}", row.f1_macro)
        mlflow.log_table(table, "comparacao.json")
        log_figure(fig, "curvas_roc_pr_comparacao.png")
        log_figure(f1_fig, "f1_macro_comparacao.png")
    print(table.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("etapa", choices=["baseline", "modelos", "comparar"])
    args = parser.parse_args()
    {"baseline": baseline, "modelos": modelos, "comparar": comparar}[args.etapa]()


if __name__ == "__main__":
    main()
