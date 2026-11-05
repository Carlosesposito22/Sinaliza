"""Fluxo 4: monitoramento das inferências.

ETAPA: estatística (sem ML novo). A cada hora, lê as frases novas gravadas pela API em `inferencias`,
calcula por hora e versão do modelo: frases, taxa de palavras mantidas, taxa de palavras sem sinal,
probabilidade média e taxa de decisões incertas, latência (p50 e p95) e frases atendidas sem modelo,
e grava em `indicadores_horarios`, que o painel lê. Marca as frases como processadas.
Depois apaga o `texto` e as `palavras` das inferências processadas com mais de `SINALIZA_RETENCAO_DIAS` dias
(padrão 30, proposta ainda não confirmada pela equipe): os indicadores agregados ficam, o texto digitado não.
Reproduzir fora do Airflow: `python -m textgloss.monitor`.
"""
from datetime import datetime

from _comum import ARGS_PADRAO, tarefa_textgloss
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

with DAG(
    dag_id="monitoramento",
    description="Consolida as inferências novas em indicadores por hora para o painel",
    schedule="@hourly",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    is_paused_upon_creation=False,
    max_active_runs=1,
    default_args=ARGS_PADRAO,
    tags=["sinaliza", "monitoramento"],
    doc_md=__doc__,
) as dag:
    BashOperator(
        task_id="consolidar_inferencias",
        bash_command=tarefa_textgloss("monitor"),
        doc_md="Cria as tabelas `inferencias` e `indicadores_horarios` se faltarem, consolida as frases novas e expurga o texto vencido.",
    )
