"""Fluxo 2: preparação dos dados do T1 (manter ou descartar cada palavra).

ETAPA: preparação para o ML (o spaCy só extrai atributos; quem decide é o classificador treinado depois).
Limpa o corpus, processa com o spaCy, rotula por alinhamento de lemas, divide treino e teste POR FRASE
(10% das frases, estratificado por domínio) e salva os conjuntos (`palavras.parquet` e a tabela `palavras_t1`).
Reproduzir fora do Airflow: `python -m textgloss.prepare --processos 4`.

Parâmetros: `limite` (só as N primeiras frases, para teste rápido) e `processos` (núcleos do spaCy).
"""
from _comum import ARGS_PADRAO, tarefa_textgloss
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

with DAG(
    dag_id="preparacao_t1",
    description="Limpa, processa com o spaCy, rotula, divide treino/teste e salva os conjuntos",
    schedule=None,
    start_date=None,
    catchup=False,
    is_paused_upon_creation=False,
    default_args=ARGS_PADRAO,
    params={
        "limite": Param(None, type=["null", "integer"], description="Só as N primeiras frases (vazio = todas)"),
        "processos": Param(4, type="integer", minimum=1, description="Processos do spaCy"),
    },
    tags=["sinaliza", "dados", "preparacao"],
    doc_md=__doc__,
) as dag:
    BashOperator(
        task_id="preparar_conjuntos",
        bash_command=tarefa_textgloss(
            "prepare",
            "--processos {{ params.processos }} {% if params.limite %}--limite {{ params.limite }}{% endif %}",
        ),
        doc_md=(
            "Escreve `data/processed/vlibrasbd/` (palavras, frases, relatório e a amostra de 200 rótulos "
            "para conferência manual) e a tabela `palavras_t1`."
        ),
    )
