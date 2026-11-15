"""Fluxo 1: ingestão do VLibrasBD.

ETAPA: infraestrutura de dados (sem ML). Baixa o CSV, confere o SHA-256 publicado e carrega a tabela
`corpus_bruto` no Postgres. Ao terminar, dispara `preparacao_t1`, repassando `limite` e `processos`.
Manual, ou sozinho na primeira subida de uma máquina limpa (`airflow/bootstrap.sh`).
Reproduzir fora do Airflow: `python -m textgloss.ingest`.

Parâmetros (só repassados à preparação): `limite` (só as N primeiras frases) e `processos` (núcleos do spaCy).
"""
from _comum import ARGS_PADRAO, tarefa_textgloss
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import DAG, Param

with DAG(
    dag_id="vlibrasbd_ingestao",
    description="Baixa o VLibrasBD, confere o hash e carrega no Postgres (corpus_bruto)",
    schedule=None,
    start_date=None,
    catchup=False,
    is_paused_upon_creation=False,
    default_args=ARGS_PADRAO,
    params={
        "limite": Param(None, type=["null", "integer"], description="Repassado à preparação: só as N primeiras frases"),
        "processos": Param(4, type="integer", minimum=1, description="Repassado à preparação: processos do spaCy"),
    },
    # Faz os valores de `conf` abaixo chegarem como número/None, e não como texto.
    render_template_as_native_obj=True,
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
        conf={"limite": "{{ params.limite }}", "processos": "{{ params.processos }}"},
        wait_for_completion=False,
    )
    ingerir >> preparar
