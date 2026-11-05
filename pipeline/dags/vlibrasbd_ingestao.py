"""Fluxo 1: ingestão do VLibrasBD.

ETAPA: infraestrutura de dados (sem ML). Baixa o CSV, confere o SHA-256 publicado e carrega a tabela
`corpus_bruto` no Postgres. Ao terminar, dispara `preparacao_t1`.
Manual, ou na primeira subida do ambiente. Reproduzir fora do Airflow: `python -m textgloss.ingest`.
"""
from _comum import ARGS_PADRAO, tarefa_textgloss
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import DAG

with DAG(
    dag_id="vlibrasbd_ingestao",
    description="Baixa o VLibrasBD, confere o hash e carrega no Postgres (corpus_bruto)",
    schedule=None,
    start_date=None,
    catchup=False,
    is_paused_upon_creation=False,
    default_args=ARGS_PADRAO,
    tags=["sinaliza", "dados", "sem-ml"],
    doc_md=__doc__,
) as dag:
    ingerir = BashOperator(
        task_id="baixar_conferir_e_carregar",
        bash_command=tarefa_textgloss("ingest"),
        doc_md="Baixa o CSV (se ainda não está no volume), falha se o hash divergir e recria `corpus_bruto`.",
    )
    preparar = TriggerDagRunOperator(
        task_id="disparar_preparacao_t1",
        trigger_dag_id="preparacao_t1",
        wait_for_completion=False,
    )
    ingerir >> preparar
