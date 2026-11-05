-- Executado só na primeira subida do volume. Em volume já criado: docker compose exec postgres createdb -U sinaliza mlflow
-- (o banco `airflow` o próprio serviço airflow cria, se faltar, em airflow/entrypoint.sh)
CREATE DATABASE mlflow;
