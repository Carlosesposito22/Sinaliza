# Airflow (orquestrador) + um ambiente Python separado com o pacote `textgloss` (o ML do projeto).
# O ambiente do ML fica num venv à parte para as dependências dele (scikit-learn, spaCy, MLflow,
# Optuna) não brigarem com as do Airflow. As tarefas dos DAGs chamam /opt/airflow/venv-ml/bin/python.
# Contexto de build: a raiz do repositório.
FROM apache/airflow:3.1.5-python3.12

COPY textgloss/requirements.txt /tmp/requirements-ml.txt
# jupyter, nbconvert e pytest são só do notebook e dos testes locais.
RUN python -m venv /opt/airflow/venv-ml \
    && grep -viE '^(jupyter|nbconvert|pytest)' /tmp/requirements-ml.txt > /tmp/requirements-pipeline.txt \
    && /opt/airflow/venv-ml/bin/pip install --no-cache-dir -r /tmp/requirements-pipeline.txt \
    && /opt/airflow/venv-ml/bin/python -m spacy download pt_core_news_md

# Pasta de dados do pipeline (volume nomeado `dados` no compose): herda o dono `airflow`.
USER root
RUN mkdir -p /opt/sinaliza/data && chown -R airflow /opt/sinaliza
USER airflow

COPY --chown=airflow airflow/entrypoint.sh /entrypoint-sinaliza.sh
COPY --chown=airflow airflow/bootstrap.sh /opt/airflow/bootstrap.sh
RUN chmod +x /entrypoint-sinaliza.sh /opt/airflow/bootstrap.sh
ENTRYPOINT ["/entrypoint-sinaliza.sh"]
