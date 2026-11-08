#!/bin/bash
# Cria o banco `airflow` se ainda não existir (o init do Postgres só roda em volume novo) e sobe o Airflow.
set -euo pipefail

python - <<'PY'
import os
import psycopg2
from urllib.parse import urlparse

url = urlparse(os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"].replace("postgresql+psycopg2", "postgresql"))
admin = psycopg2.connect(host=url.hostname, port=url.port, user=url.username, password=url.password, dbname="sinaliza")
admin.autocommit = True
cursor = admin.cursor()
cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'airflow'")
if cursor.fetchone() is None:
    cursor.execute("CREATE DATABASE airflow")
    print("banco airflow criado")
PY

# Primeira subida de máquina limpa: dispara ingestão → preparação → treino (ver bootstrap.sh). Em segundo plano.
/opt/airflow/bootstrap.sh &

# `standalone` (api-server, scheduler, dag-processor e triggerer num só container): suficiente para o projeto.
exec airflow standalone
