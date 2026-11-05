"""Constantes e atalhos compartilhados pelos fluxos do Airflow.

As tarefas rodam o pacote `textgloss` no ambiente Python do ML (venv separado do Airflow),
sempre por linha de comando: o que cada tarefa faz é exatamente o que se reproduz fora do Airflow
(`python -m textgloss.<etapa>`; ver references/24-pipeline-de-dados-ponta-a-ponta.md).
"""
from datetime import timedelta

PYTHON_ML = "/opt/airflow/venv-ml/bin/python"
RAIZ = "/opt/sinaliza"

# O container monta ./textgloss em /opt/sinaliza/textgloss; as variáveis SINALIZA_* e MLFLOW_* vêm do compose.
ARGS_PADRAO = {
    "owner": "sinaliza",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def tarefa_textgloss(modulo: str, argumentos: str = "") -> str:
    """Comando de uma etapa do textgloss, executado na raiz do projeto."""
    return f"cd {RAIZ} && {PYTHON_ML} -m textgloss.{modulo} {argumentos}".strip()
