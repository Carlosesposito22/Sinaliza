"""Separa as runs do antigo experimento único (`t1-manter-descartar`) em um experimento do MLflow por etapa.

ETAPA: organização do MLflow (sem ML novo, sem retreino). A especificação de AM pede "múltiplos experimentos
(baseline, comparação de modelos e otimização de hiperparâmetros)". Até 2026-11-14 tudo ficava num experimento só,
separado pela tag `etapa`. Este script move cada run para o experimento da sua etapa (ver `train.STAGES`):

    tag etapa                 →  experimento
    baseline                  →  sinaliza-t1-01-baseline
    comparacao                →  sinaliza-t1-02-comparacao-de-modelos
    otimizacao                →  sinaliza-t1-03-otimizacao-de-hiperparametros (run pai do Optuna, 25 filhas, modelo otimizado)
    validacao, teste-final    →  sinaliza-t1-04-validacao-e-teste-final

Como: o MLflow não tem "mover run", então o script altera `experiment_id` direto no banco do MLflow (tabela `runs`
e as dos modelos registrados com `log_model`). Nada mais muda: os ids das runs, métricas com histórico, parâmetros,
tags, relação pai/filha, artefatos (o caminho fica gravado em cada run) e o Model Registry (`sinaliza-t1` aponta
para o modelo, não para o experimento). Runs já apagadas ficam no experimento antigo, que é apagado (de forma
reversível, `lifecycle_stage = deleted`) quando não sobra nenhuma run ativa nele.

Idempotente: rodar de novo não faz nada. Faça backup antes (`pg_dump`) e rode primeiro sem `--aplicar`.

Uso: python -m textgloss.separar_experimentos [--aplicar] [--banco postgresql+psycopg://.../mlflow]
"""
from __future__ import annotations

import argparse
import os
from collections import Counter

import mlflow
from sqlalchemy import create_engine, text

from . import train

STAGE_OF_TAG = {"baseline": "baseline", "comparacao": "comparacao", "otimizacao": "otimizacao",
                "validacao": "validacao", "teste-final": "validacao"}
DEFAULT_DB = os.environ.get("SINALIZA_MLFLOW_DATABASE_URL", "postgresql+psycopg://sinaliza:sinaliza@localhost:5432/mlflow")


def plan(client: mlflow.MlflowClient, legacy_id: str) -> tuple[dict[str, list[str]], list[str]]:
    """Runs ativas do experimento antigo agrupadas pela etapa de destino, e as que não têm etapa conhecida."""
    runs, token = [], None
    while True:
        page = client.search_runs([legacy_id], max_results=1000, page_token=token)
        runs += list(page)
        token = page.token
        if not token:
            break
    moves: dict[str, list[str]] = {stage: [] for stage in train.STAGES}
    unknown = []
    for run in runs:
        stage = STAGE_OF_TAG.get(run.data.tags.get("etapa", ""))
        (moves[stage] if stage else unknown).append(run.info.run_id)
    return moves, unknown


def apply(engine, moves: dict[str, list[str]], targets: dict[str, str]) -> Counter:
    done = Counter()
    with engine.begin() as conn:
        tables = {r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.columns WHERE column_name = 'experiment_id'"))}
        for stage, run_ids in moves.items():
            if not run_ids:
                continue
            target = int(targets[stage])
            done[f"runs → {stage}"] = conn.execute(
                text("UPDATE runs SET experiment_id = :e WHERE run_uuid = ANY(:ids)"), {"e": target, "ids": run_ids}
            ).rowcount
            if "logged_models" in tables:
                model_ids = [r[0] for r in conn.execute(
                    text("SELECT model_id FROM logged_models WHERE source_run_id = ANY(:ids)"), {"ids": run_ids})]
                if model_ids:
                    for table in ("logged_models", "logged_model_metrics", "logged_model_params", "logged_model_tags"):
                        if table in tables:
                            done[f"{table} → {stage}"] += conn.execute(
                                text(f"UPDATE {table} SET experiment_id = :e WHERE model_id = ANY(:m)"),
                                {"e": target, "m": model_ids}).rowcount
    return done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--aplicar", action="store_true", help="sem isto, só mostra o que faria")
    parser.add_argument("--banco", default=DEFAULT_DB, help="banco do MLflow (não o do Sinaliza)")
    args = parser.parse_args()

    mlflow.set_tracking_uri(train.TRACKING_URI)
    client = mlflow.MlflowClient()
    legacy = client.get_experiment_by_name(train.LEGACY_EXPERIMENT)
    if legacy is None or legacy.lifecycle_stage == "deleted":
        print(f"Nada a fazer: o experimento antigo `{train.LEGACY_EXPERIMENT}` não existe ou já foi separado.")
        return
    moves, unknown = plan(client, legacy.experiment_id)
    for stage, run_ids in moves.items():
        print(f"{len(run_ids):3d} runs → {train.experiment_name(stage)}")
    if unknown:
        print(f"{len(unknown)} runs sem etapa conhecida ficam em `{train.LEGACY_EXPERIMENT}`: {unknown}")
    if not args.aplicar:
        print("\nSimulação. Para aplicar: --aplicar (faça backup do banco do MLflow antes).")
        return

    targets = {}
    for stage in train.STAGES:
        train.use_experiment(stage)
        targets[stage] = client.get_experiment_by_name(train.experiment_name(stage)).experiment_id
    for change, count in apply(create_engine(args.banco), moves, targets).items():
        print(f"  {change}: {count}")
    if not unknown and not client.search_runs([legacy.experiment_id], max_results=1):
        client.delete_experiment(legacy.experiment_id)  # reversível: restore_experiment
        print(f"Experimento antigo `{train.LEGACY_EXPERIMENT}` apagado (reversível; só tinha runs já apagadas).")


if __name__ == "__main__":
    main()
