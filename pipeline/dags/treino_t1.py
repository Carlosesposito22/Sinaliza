"""Fluxo 3: treino do T1 e registro do modelo no MLflow.

ETAPA: ML nosso. Os classificadores aprendem, com os rótulos dos intérpretes do corpus, quais palavras
viram sinal. Tudo é registrado no MLflow (experimento `t1-manter-descartar`).

Ordem: baseline (Regressão Logística + lista fixa) → comparação (Árvore, Random Forest, KNN) → Optuna sobre
o Random Forest → validação cruzada agrupada por frase → teste final e registro de `sinaliza-t1`.
As tarefas são sequenciais de propósito: o Random Forest usa todos os núcleos.

O TESTE FINAL SÓ PODE RODAR UMA VEZ por MLflow. A tarefa dele usa `--se-pendente`: se já existe a run
`teste-final`, ela não faz nada e termina com sucesso (não treina nem registra nada de novo).

Parâmetros: `trials`, `timeout_s` e `amostra_frases` do Optuna, `frases_cv` da validação cruzada e `registrar_modelo`.
Manual (dura de 1 a 2 horas com todos os parâmetros padrão). Reproduzir fora do Airflow: ver references/14.
"""
from _comum import ARGS_PADRAO, tarefa_textgloss
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param
from airflow.providers.standard.operators.python import ShortCircuitOperator

MODELO_FINAL = "random-forest-otimizado"

with DAG(
    dag_id="treino_t1",
    description="Baseline, comparação, Optuna, validação cruzada e registro do modelo no MLflow",
    schedule=None,
    start_date=None,
    catchup=False,
    is_paused_upon_creation=False,
    default_args={**ARGS_PADRAO, "retries": 0},
    params={
        "trials": Param(25, type="integer", minimum=1, description="Tentativas do Optuna"),
        "timeout_s": Param(2400, type="integer", minimum=60, description="Tempo máximo do Optuna, em segundos"),
        "amostra_frases": Param(6000, type="integer", minimum=200, description="Frases na amostra de cada tentativa do Optuna"),
        "frases_cv": Param(40000, type="integer", minimum=1000, description="Frases usadas na validação cruzada"),
        "registrar_modelo": Param(True, type="boolean", description="Rodar o teste final e registrar sinaliza-t1 (uma única vez)"),
    },
    tags=["sinaliza", "ml", "mlflow"],
    doc_md=__doc__,
) as dag:
    baseline = BashOperator(task_id="baseline", bash_command=tarefa_textgloss("train", "baseline"))
    modelos = BashOperator(task_id="comparar_modelos", bash_command=tarefa_textgloss("train", "modelos"))
    graficos = BashOperator(task_id="graficos_da_comparacao", bash_command=tarefa_textgloss("train", "comparar"))
    otimizar = BashOperator(
        task_id="otimizar_random_forest",
        bash_command=tarefa_textgloss("tune", "--trials {{ params.trials }} --timeout {{ params.timeout_s }} --amostra-frases {{ params.amostra_frases }}"),
    )
    validar = BashOperator(
        task_id="validacao_cruzada",
        bash_command=tarefa_textgloss("validate", "cv --frases {{ params.frases_cv }}"),
    )
    quer_registrar = ShortCircuitOperator(
        task_id="registrar_modelo_ligado",
        python_callable=lambda **contexto: bool(contexto["params"]["registrar_modelo"]),
    )
    registrar = BashOperator(
        task_id="teste_final_e_registro",
        bash_command=tarefa_textgloss("validate", f"teste --modelo {MODELO_FINAL} --se-pendente"),
        doc_md="Treina em todo o treino, avalia nos 10% de frases separados e registra `sinaliza-t1`. Roda uma única vez.",
    )
    baseline >> modelos >> graficos >> otimizar >> validar >> quer_registrar >> registrar
