"""Validação do T1: validação cruzada, curva de aprendizado, teste fora do domínio e teste final.

ETAPA: avaliação do ML nosso. Compara a Regressão Logística e o Random Forest otimizado (os dois
melhores da fase 5) quanto a estabilidade, sobreajuste e generalização. O teste final só roda uma vez,
para o modelo que o grupo escolher, depois que as demais análises estiverem prontas.
Uso: python -m textgloss.validate cv | curva | dominio | teste --modelo NOME
"""
import argparse
import json
import time

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold

from . import config, modeling, train

CV_FOLDS = 5
CV_SENTENCES = 40_000
CURVE_FRACTIONS = [0.02, 0.05, 0.10, 0.25, 0.50]
MODELS = ("regressao-logistica", "random-forest-otimizado")


def best_forest_params() -> dict:
    """Melhores parâmetros achados pelo Optuna, lidos da run do estudo no MLflow."""
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(train.EXPERIMENT).experiment_id
    study = client.search_runs(
        [experiment], filter_string="tags.modelo = 'optuna-estudo' and attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"],
    )[0]
    path = mlflow.artifacts.download_artifacts(
        artifact_uri=f"runs:/{study.info.run_id}/melhores_parametros.json", tracking_uri=train.TRACKING_URI
    )
    return json.load(open(path))


def build(name: str):
    if name == "regressao-logistica":
        return train.logistic_model()[0]
    params = best_forest_params()
    classifier = RandomForestClassifier(random_state=config.SEED, n_jobs=-1, **params)
    return modeling.make_pipeline(classifier, scale=False)


def score(model, frame: pd.DataFrame) -> dict:
    proba = model.predict_proba(frame[modeling.FEATURES])[:, 1]
    return modeling.evaluate(frame[modeling.TARGET], (proba >= 0.5).astype(int), proba)


def fit_score(name: str, fit: pd.DataFrame, evals: dict) -> tuple[dict, float]:
    """Treina um modelo novo em `fit` e devolve as métricas em cada conjunto de `evals` (+ tempo de treino)."""
    model = build(name)
    started = time.perf_counter()
    model.fit(fit[modeling.FEATURES], fit[modeling.TARGET])
    elapsed = time.perf_counter() - started
    return {label: score(model, frame) for label, frame in {"treino": fit, **evals}.items()}, elapsed


def cv(sentences: int = CV_SENTENCES, models: tuple = MODELS) -> pd.DataFrame:
    """Validação cruzada k=5 agrupada por frase, sobre uma amostra de frases do conjunto de treino."""
    mlflow.set_tracking_uri(train.TRACKING_URI)
    mlflow.set_experiment(train.EXPERIMENT)
    words = modeling.load_words()
    pool = words[words["split"] == "treino"]
    unique = pool["frase_id"].drop_duplicates()
    chosen = unique.sample(min(sentences, len(unique)), random_state=config.SEED)
    sample = pool[pool["frase_id"].isin(chosen)].reset_index(drop=True)
    y, groups = sample[modeling.TARGET].to_numpy(), sample["frase_id"].to_numpy()
    folds = list(StratifiedGroupKFold(n_splits=CV_FOLDS, shuffle=True, random_state=config.SEED).split(sample, y, groups))

    rows = []
    with mlflow.start_run(run_name="validacao-cruzada"):
        mlflow.set_tags({"etapa": "validacao", "modelo": "validacao-cruzada"})
        mlflow.log_params({"cv": f"StratifiedGroupKFold k={CV_FOLDS}", "agrupamento": "frase_id",
                           "n_frases": sentences, "n_palavras": len(sample), "modelos": ",".join(models)})
        for name in models:
            with mlflow.start_run(run_name=f"cv-{name}", nested=True):
                mlflow.set_tags({"etapa": "validacao", "modelo": f"cv-{name}"})
                for k, (train_idx, test_idx) in enumerate(folds):
                    result, elapsed = fit_score(name, sample.iloc[train_idx], {"val": sample.iloc[test_idx]})
                    row = {"modelo": name, "dobra": k, "f1_macro_val": result["val"]["f1_macro"],
                           "f1_macro_treino": result["treino"]["f1_macro"], "roc_auc_val": result["val"]["roc_auc"],
                           "pr_auc_val": result["val"]["pr_auc"], "recall_descartar_val": result["val"]["recall_descartar"],
                           "tempo_treino_s": elapsed}
                    rows.append(row)
                    mlflow.log_metrics({k_: v for k_, v in row.items() if k_ not in ("modelo", "dobra")}, step=k)
                    print(name, k, round(row["f1_macro_val"], 4), flush=True)
                part = pd.DataFrame([r for r in rows if r["modelo"] == name])
                mlflow.log_metrics({"f1_macro_media": part.f1_macro_val.mean(), "f1_macro_desvio": part.f1_macro_val.std(ddof=1),
                                    "f1_macro_min": part.f1_macro_val.min(), "f1_macro_max": part.f1_macro_val.max(),
                                    "gap_medio_treino_val": (part.f1_macro_treino - part.f1_macro_val).mean(),
                                    "roc_auc_media": part.roc_auc_val.mean()})
        table = pd.DataFrame(rows)
        mlflow.log_table(table, "dobras.json")
        fig, ax = plt.subplots(figsize=(7, 4))
        for name, part in table.groupby("modelo"):
            ax.plot(part["dobra"] + 1, part["f1_macro_val"], "o-", label=f"{name} ({part.f1_macro_val.mean():.4f} ± {part.f1_macro_val.std(ddof=1):.4f})")
        ax.set(xlabel="dobra", ylabel="F1-macro (validação da dobra)", title=f"Validação cruzada k={CV_FOLDS}, agrupada por frase")
        ax.set_xticks(range(1, CV_FOLDS + 1)); ax.legend()
        fig.tight_layout()
        train.log_figure(fig, "cv_por_dobra.png")
    return table


def curva(models: tuple = MODELS) -> pd.DataFrame:
    """Curva de aprendizado: treino em frações crescentes das frases de ajuste, avaliação na validação fixa."""
    mlflow.set_tracking_uri(train.TRACKING_URI)
    mlflow.set_experiment(train.EXPERIMENT)
    fit, val = modeling.train_validation(modeling.load_words())
    sentences = fit["frase_id"].drop_duplicates().sample(frac=1.0, random_state=config.SEED).to_numpy()
    runs = train.latest_runs()
    rows = []
    with mlflow.start_run(run_name="curva-aprendizado"):
        mlflow.set_tags({"etapa": "validacao", "modelo": "curva-aprendizado"})
        mlflow.log_params({"fracoes": str(CURVE_FRACTIONS), "avaliacao": "validacao fixa do baseline", "modelos": ",".join(models)})
        for name in models:
            for fraction in CURVE_FRACTIONS:
                subset = fit[fit["frase_id"].isin(sentences[: int(len(sentences) * fraction)])]
                result, elapsed = fit_score(name, subset, {"val": val})
                rows.append({"modelo": name, "fracao": fraction, "n_palavras": len(subset),
                             "f1_macro_treino": result["treino"]["f1_macro"], "f1_macro_val": result["val"]["f1_macro"],
                             "tempo_treino_s": elapsed})
                print(name, fraction, round(rows[-1]["f1_macro_val"], 4), flush=True)
            m = runs[name].data.metrics
            rows.append({"modelo": name, "fracao": 1.0, "n_palavras": len(fit), "f1_macro_treino": m["treino_f1_macro"],
                         "f1_macro_val": m["val_f1_macro"], "tempo_treino_s": m["tempo_treino_s"]})
        table = pd.DataFrame(rows)
        mlflow.log_table(table, "curva.json")
        fig, axes = plt.subplots(1, len(models), figsize=(5.5 * len(models), 4), sharey=True)
        for ax, name in zip(np.atleast_1d(axes), models):
            part = table[table.modelo == name]
            ax.plot(part.n_palavras, part.f1_macro_treino, "o-", label="treino")
            ax.plot(part.n_palavras, part.f1_macro_val, "o-", label="validação")
            ax.set(xscale="log", xlabel="palavras de treino", title=name); ax.legend()
        np.atleast_1d(axes)[0].set_ylabel("F1-macro")
        fig.tight_layout()
        train.log_figure(fig, "curva_aprendizado.png")
    return table


def dominio(models: tuple = MODELS) -> pd.DataFrame:
    """Treina num domínio (geral ou governo) e avalia nos dois: mede a queda fora do domínio."""
    mlflow.set_tracking_uri(train.TRACKING_URI)
    mlflow.set_experiment(train.EXPERIMENT)
    fit, val = modeling.train_validation(modeling.load_words())
    names = {False: "geral", True: "governo"}
    rows = []
    with mlflow.start_run(run_name="fora-do-dominio"):
        mlflow.set_tags({"etapa": "validacao", "modelo": "fora-do-dominio"})
        mlflow.log_params({"modelos": ",".join(models), "avaliacao": "validacao fixa, separada por domínio"})
        for name in models:
            for source in (False, True):
                subset = fit[fit["governo"] == source]
                evals = {f"val_{names[t]}": val[val["governo"] == t] for t in (False, True)}
                result, elapsed = fit_score(name, subset, evals)
                for target in (False, True):
                    rows.append({"modelo": name, "treino_em": names[source], "avaliado_em": names[target],
                                 "dentro_do_dominio": source == target, "n_palavras_treino": len(subset),
                                 "f1_macro": result[f"val_{names[target]}"]["f1_macro"],
                                 "roc_auc": result[f"val_{names[target]}"]["roc_auc"]})
                print(name, names[source], [round(r["f1_macro"], 4) for r in rows[-2:]], flush=True)
        table = pd.DataFrame(rows)
        mlflow.log_table(table, "dominio.json")
        pivot = table.assign(par=table.treino_em + " → " + table.avaliado_em).pivot(index="par", columns="modelo", values="f1_macro")
        ax = pivot.plot.bar(figsize=(7.5, 4), rot=0)
        ax.set(ylim=(0.7, 0.95), ylabel="F1-macro", title="Dentro e fora do domínio (treino → avaliação)")
        ax.figure.tight_layout()
        train.log_figure(ax.figure, "fora_do_dominio.png")
    return table


def teste_final_executado() -> bool:
    """True se já existe uma run do teste final no experimento (ele só pode rodar uma vez)."""
    mlflow.set_tracking_uri(train.TRACKING_URI)
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(train.EXPERIMENT)
    if experiment is None:
        return False
    return bool(client.search_runs([experiment.experiment_id], filter_string="tags.etapa = 'teste-final'", max_results=1))


def teste_final(name: str) -> dict:
    """Teste final: treina o modelo escolhido em TODO o treino e avalia no teste (10% das frases), uma única vez.

    A lista fixa roda no mesmo conjunto. O modelo é registrado no Model Registry do MLflow.
    """
    mlflow.set_tracking_uri(train.TRACKING_URI)
    mlflow.set_experiment(train.EXPERIMENT)
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(train.EXPERIMENT).experiment_id
    done = client.search_runs([experiment], filter_string="tags.etapa = 'teste-final'")
    if done:
        raise SystemExit("O teste final já foi executado; ele só pode rodar uma vez (run " + done[0].info.run_id + ").")

    words = modeling.load_words()
    full_train, test = words[words["split"] == "treino"], words[words["split"] == "teste"]
    params = train.dataset_params(full_train, test)
    model = build(name)
    with mlflow.start_run(run_name=f"teste-final-{name}"):
        mlflow.set_tags({"etapa": "teste-final", "modelo": f"teste-final-{name}", "usa_ml": "sim"})
        mlflow.log_params({**params, "modelo_escolhido": name, "treino": "todas as frases de treino (ajuste + validação)",
                           "avaliacao": "10% de frases separadas, usadas uma única vez"})
        started = time.perf_counter()
        model.fit(full_train[modeling.FEATURES], full_train[modeling.TARGET])
        mlflow.log_metric("tempo_treino_s", time.perf_counter() - started)
        proba = model.predict_proba(test[modeling.FEATURES])[:, 1]
        pred = (proba >= 0.5).astype(int)
        result = modeling.evaluate(test[modeling.TARGET], pred, proba)
        baseline = modeling.evaluate(test[modeling.TARGET], modeling.fixed_list_predict(test))
        mlflow.log_metrics({f"teste_{k}": v for k, v in result.items()})
        mlflow.log_metrics({f"teste_lista_fixa_{k}": v for k, v in baseline.items()})
        train.log_figure(modeling.plot_confusion(test[modeling.TARGET], pred, f"{name} · teste final"), "matriz_confusao_teste.png")
        train.log_figure(modeling.plot_curves(test[modeling.TARGET], proba, "teste final"), "curvas_roc_pr_teste.png")
        info = mlflow.sklearn.log_model(
            model, name="modelo", input_example=full_train[modeling.FEATURES].head(3),
            skops_trusted_types=["sklearn.tree._tree.Tree"], registered_model_name="sinaliza-t1",
        )
        mlflow.set_tag("modelo_registrado", info.model_uri)
    return {"modelo": name, "teste": result, "lista_fixa": baseline}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("etapa", choices=["cv", "curva", "dominio", "teste"])
    parser.add_argument("--frases", type=int, default=CV_SENTENCES)
    parser.add_argument("--modelo", choices=MODELS)
    parser.add_argument("--se-pendente", action="store_true",
                        help="no teste final: se já foi executado, não faz nada e sai com sucesso (uso nos DAGs)")
    args = parser.parse_args()
    if args.etapa == "teste":
        if not args.modelo:
            raise SystemExit("Informe --modelo.")
        if args.se_pendente and teste_final_executado():
            print("O teste final já foi executado neste MLflow; nada a fazer.")
            return
        print(json.dumps(teste_final(args.modelo), indent=2))
    elif args.etapa == "cv":
        print(cv(args.frases).groupby("modelo").f1_macro_val.agg(["mean", "std"]))
    elif args.etapa == "curva":
        print(curva().round(4).to_string(index=False))
    else:
        print(dominio().round(4).to_string(index=False))


if __name__ == "__main__":
    main()
