# mlruns/

Artefatos do MLflow: modelos salvos, figuras, tabelas e predições de cada run (cerca de 2 GB). O servidor `mlflow`
do `docker-compose.yml` grava aqui (`--artifacts-destination /mlruns`, montado desta pasta). Parâmetros, métricas
e o registro de modelos ficam no Postgres (banco `mlflow`).

O conteúdo **não é versionado** (`.gitignore`): numa máquina limpa, o Airflow treina de novo e a pasta se enche
sozinha. Os experimentos são um por etapa: `sinaliza-t1-01-baseline`, `-02-comparacao-de-modelos`,
`-03-otimizacao-de-hiperparametros` e `-04-validacao-e-teste-final` (interface em http://localhost:5000).
