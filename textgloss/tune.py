"""Otimização de hiperparâmetros do Random Forest com Optuna (TPE), tudo no MLflow.

ETAPA: ML nosso. O Optuna procura a configuração do Random Forest que maximiza o F1-macro médio
de uma validação cruzada agrupada por frase; depois o modelo é refeito com os melhores
parâmetros nos dados completos e avaliado na mesma validação dos demais modelos.
Uso: python -m textgloss.tune [--trials 25] [--amostra-frases 6000] [--timeout 2400]
"""
import argparse
import json
import time

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import optuna
from optuna.visualization import matplotlib as optuna_plots
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold

from . import config, modeling, train

OPTIMIZED = "random-forest-otimizado"
CV_FOLDS = 3

SEARCH_SPACE = {
    "n_estimators": "inteiro 50–200",
    "max_depth": "inteiro 10–60",
    "min_samples_leaf": "inteiro 1–30 (escala log)",
    "max_features": "decimal 0,02–0,5 (escala log) ou 'sqrt'",
    "class_weight": "balanced | balanced_subsample | nenhum",
    "criterion": "gini | entropy",
}


def suggest(trial: optuna.Trial) -> dict:
    max_features = trial.suggest_categorical("max_features_tipo", ["sqrt", "fracao"])
    if max_features == "fracao":
        max_features = trial.suggest_float("max_features_fracao", 0.02, 0.5, log=True)
    class_weight = trial.suggest_categorical("class_weight", ["balanced", "balanced_subsample", "nenhum"])
    return {
        "n_estimators": trial.suggest_int("n_estimators", 50, 200),
        "max_depth": trial.suggest_int("max_depth", 10, 60),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 30, log=True),
        "max_features": max_features,
        "class_weight": None if class_weight == "nenhum" else class_weight,
        "criterion": trial.suggest_categorical("criterion", ["gini", "entropy"]),
    }


def cv_sample(fit, n_sentences: int):
    """Amostra de FRASES inteiras (para o agrupamento fazer sentido) e dobras estratificadas por frase."""
    sentences = fit["frase_id"].drop_duplicates().sample(n_sentences, random_state=config.SEED)
    return fit[fit["frase_id"].isin(sentences)].reset_index(drop=True)


def make_objective(sample):
    X, y, groups = sample[modeling.FEATURES], sample[modeling.TARGET].to_numpy(), sample["frase_id"].to_numpy()
    folds = list(StratifiedGroupKFold(n_splits=CV_FOLDS, shuffle=True, random_state=config.SEED).split(X, y, groups))

    def objective(trial: optuna.Trial) -> float:
        params = suggest(trial)
        with mlflow.start_run(run_name=f"trial-{trial.number:03d}", nested=True):
            mlflow.set_tags({"etapa": "otimizacao", "modelo": "random-forest-trial"})
            mlflow.log_params({k: str(v) for k, v in params.items()})
            started = time.perf_counter()
            scores = []
            for step, (train_idx, test_idx) in enumerate(folds):
                model = modeling.make_pipeline(
                    RandomForestClassifier(random_state=config.SEED, n_jobs=-1, **params), scale=False
                )
                model.fit(X.iloc[train_idx], y[train_idx])
                scores.append(f1_score(y[test_idx], model.predict(X.iloc[test_idx]), average="macro"))
                mlflow.log_metric("f1_macro_dobra", scores[-1], step=step)
            mlflow.log_metrics(
                {"f1_macro_cv": float(np.mean(scores)), "f1_macro_cv_desvio": float(np.std(scores)),
                 "tempo_s": time.perf_counter() - started}
            )
        return float(np.mean(scores))

    return objective


def best_forest_params(study: optuna.Study) -> dict:
    """Converte os parâmetros do melhor trial para os argumentos reais do RandomForestClassifier."""
    best = study.best_trial.params
    max_features = best["max_features_fracao"] if best["max_features_tipo"] == "fracao" else "sqrt"
    return {
        "n_estimators": best["n_estimators"],
        "max_depth": best["max_depth"],
        "min_samples_leaf": best["min_samples_leaf"],
        "max_features": max_features,
        "class_weight": None if best["class_weight"] == "nenhum" else best["class_weight"],
        "criterion": best["criterion"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=25)
    parser.add_argument("--amostra-frases", type=int, default=6000)
    parser.add_argument("--timeout", type=int, default=2400, help="tempo máximo da busca, em segundos")
    args = parser.parse_args()

    mlflow.set_tracking_uri(train.TRACKING_URI)
    mlflow.set_experiment(train.EXPERIMENT)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    fit, val = modeling.train_validation(modeling.load_words())
    params = train.dataset_params(fit, val)
    sample = cv_sample(fit, args.amostra_frases)
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=config.SEED),
                                study_name="random-forest-t1")

    with mlflow.start_run(run_name="optuna-random-forest") as parent:
        mlflow.set_tags({"etapa": "otimizacao", "modelo": "optuna-estudo", "usa_ml": "sim"})
        mlflow.log_params({
            **params, "sampler": "TPE", "n_trials_max": args.trials, "timeout_s": args.timeout, "cv": f"StratifiedGroupKFold k={CV_FOLDS}",
            "objetivo": "f1_macro medio da validacao cruzada", "amostra_frases_cv": args.amostra_frases,
            "n_palavras_cv": len(sample), "espaco_de_busca": json.dumps(SEARCH_SPACE, ensure_ascii=False),
        })
        study.optimize(make_objective(sample), n_trials=args.trials, timeout=args.timeout)

        mlflow.log_metrics({"melhor_f1_macro_cv": study.best_value, "melhor_trial": study.best_trial.number})
        for name, plot in (("historico_otimizacao.png", optuna_plots.plot_optimization_history),
                           ("importancia_hiperparametros.png", optuna_plots.plot_param_importances)):
            plot(study)
            train.log_figure(plt.gcf(), name)
        trials = study.trials_dataframe()
        mlflow.log_table(trials.drop(columns=["datetime_start", "datetime_complete", "duration"]), "trials.json")
        best = best_forest_params(study)
        mlflow.log_dict(best, "melhores_parametros.json")
        parent_id = parent.info.run_id

    classifier = RandomForestClassifier(random_state=config.SEED, n_jobs=-1, **best)
    model = modeling.make_pipeline(classifier, scale=False)
    spec = {**{k: str(v) for k, v in best.items()}, "origem": f"optuna run {parent_id}"}
    result = train.run_model(OPTIMIZED, model, fit, val, params, spec, "otimizacao", train.log_importances)
    print(json.dumps({"melhores_parametros": best, "melhor_f1_cv": study.best_value, "validacao": result}, indent=2))


if __name__ == "__main__":
    main()
