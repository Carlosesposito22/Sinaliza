#!/bin/bash
# Primeira subida de uma máquina limpa: roda ingestão → preparação → treino sem ninguém clicar.
#
# Só age se (1) SINALIZA_AUTO_PIPELINE=true, (2) o banco ainda NÃO tem a tabela `corpus_bruto` e (3) esta
# rotina ainda não rodou neste volume. Um ambiente que já tem dados não é tocado.
# Perfil `demo`: amostra pequena (minutos, modelo só para demonstrar). Perfil `completo`: corpus todo (horas).
# Os parâmetros vão por `--conf` aos DAGs (os mesmos que se mudam na interface do Airflow).
set -u

log() { echo "[bootstrap] $*"; }

[ "${SINALIZA_AUTO_PIPELINE:-true}" = "true" ] || { log "desligado (SINALIZA_AUTO_PIPELINE != true)"; exit 0; }

MARCA=/opt/sinaliza/data/.bootstrap-feito
[ -f "$MARCA" ] && { log "já rodou neste volume; nada a fazer"; exit 0; }

case "${SINALIZA_PERFIL:-completo}" in
  demo)
    CONF_PREPARACAO='{"limite": 3000, "processos": 2}'
    CONF_TREINO='{"trials": 2, "timeout_s": 120, "amostra_frases": 300, "frases_cv": 1000, "registrar_modelo": true}'
    ;;
  completo)
    CONF_PREPARACAO='{"limite": null, "processos": 2}'
    CONF_TREINO='{"registrar_modelo": true}'
    ;;
  *) log "SINALIZA_PERFIL inválido: ${SINALIZA_PERFIL} (use demo ou completo)"; exit 1 ;;
esac

# Espera os DAGs aparecerem (o processador de DAGs registra cada arquivo em até ~30 s).
for _ in $(seq 1 90); do
  [ "$(airflow dags list 2>/dev/null | grep -c 'sinaliza')" -ge 4 ] && break
  sleep 5
done

TEM_CORPUS=$(python - <<'PY'
import os, psycopg2
url = os.environ["SINALIZA_DATABASE_URL"].replace("postgresql+psycopg", "postgresql")
with psycopg2.connect(url) as conn, conn.cursor() as cur:
    cur.execute("SELECT to_regclass('public.corpus_bruto') IS NOT NULL")
    print("sim" if cur.fetchone()[0] else "nao")
PY
)
[ "$TEM_CORPUS" = "nao" ] || { log "o banco já tem o corpus; nada a fazer"; exit 0; }

touch "$MARCA"
log "máquina limpa, perfil ${SINALIZA_PERFIL:-completo}: disparando ingestão (preparação: $CONF_PREPARACAO)"
until airflow dags trigger vlibrasbd_ingestao --conf "$CONF_PREPARACAO" >/dev/null 2>&1; do sleep 10; done

estado() {  # estado da run mais recente do DAG: running, success, failed ou vazio
  airflow dags list-runs "$1" -o json 2>/dev/null | python -c "import sys,json;r=json.load(sys.stdin);print(r[0]['state'] if r else '')"
}

log "esperando a preparação terminar"
while true; do
  case "$(estado preparacao_t1)" in
    success) break ;;
    failed) log "a preparação falhou; o treino não será disparado (veja os logs no Airflow)"; exit 1 ;;
  esac
  sleep 15
done

log "preparação concluída; disparando o treino (treino: $CONF_TREINO)"
until airflow dags trigger treino_t1 --conf "$CONF_TREINO" >/dev/null 2>&1; do sleep 10; done

while true; do
  case "$(estado treino_t1)" in
    success) log "treino concluído; a API pega o modelo sinaliza-t1 sozinha em até 30 s"; exit 0 ;;
    failed) log "o treino falhou (veja os logs no Airflow)"; exit 1 ;;
  esac
  sleep 20
done
