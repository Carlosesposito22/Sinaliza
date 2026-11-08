# Como rodar e testar

Ambiente de desenvolvimento do projeto: **Windows + PowerShell**. Cada ferramenta Python tem **venv próprio** (`data/` precisa de `numpy<2`).

## Tudo de uma vez (Docker)

```powershell
docker compose up --build
```

- Front: http://localhost:5173
- API: http://localhost:8000 (docs em `/docs`)
- Parar: `Ctrl+C` e `docker compose down`. Docker Desktop precisa estar rodando.
- Num clone novo basta esse comando: o build do front baixa os sinais do VLibras do vocabulário (`npm run signs` dentro do `web/Dockerfile`, numa camada que fica em cache). Precisa de internet só nesse passo. **Verificado em 2026-10-25** com um clone limpo: 209 sinais baixados no build, API saudável, e o avatar toca "O filho está com dor de cabeça." com os sinais vindos do nginx.
- Sem `SINALIZA_MOTIONS_DIR`, a API usa o aceno de teste; isso não aparece na tela, porque o avatar do VLibras não usa a sequência de keypoints.
- `model/` e `data/` **não** entram no compose (são CLIs).
- Os builds da API e do front usam a **raiz do repositório** como contexto (`.dockerignore` na raiz; o front precisa de `data/vocabulary.json`). Histórico: o build da API usa a raiz (a imagem leva `data/vocabulary.json` e `data/phrases.json`). Verificado em 2026-10-19: `docker compose up --build` constrói as duas imagens (api 358 MB, web 103 MB), a API fica saudável e `/health`, `/translate`, `/vocabulary` e `/categories` respondem direto (porta 8000) e pelo proxy do nginx (`localhost:5173/api/...`); o front carrega as categorias. O primeiro build revelou que o `numpy` faltava no `api/requirements.txt` (nos testes locais ele vinha do Python do sistema); corrigido.

## Pipeline de ML (Postgres, MLflow e Airflow)

```powershell
docker compose up -d postgres mlflow airflow
```

- Airflow: http://localhost:8080 (sem login; só local). Os 4 DAGs (`vlibrasbd_ingestao`, `preparacao_t1`, `treino_t1`, `monitoramento`) já nascem ativos. MLflow: http://localhost:5000.
- **Primeira vez, do zero:** dispare `vlibrasbd_ingestao` na interface (ou `docker compose exec airflow airflow dags trigger vlibrasbd_ingestao`). Ela baixa o CSV (31 MB, hash conferido), carrega o Postgres e dispara `preparacao_t1`. Depois dispare `treino_t1` (manual). Descrição de cada DAG e dos parâmetros: [`24-pipeline-de-dados-ponta-a-ponta.md`](24-pipeline-de-dados-ponta-a-ponta.md).
- Os arquivos do pipeline ficam no volume `dados` (não em `data/` do host). O Airflow guarda o próprio estado no banco `airflow` do Postgres, criado pelo `airflow/entrypoint.sh` se faltar.
- **Recursos (medido em 2026-11-05, Docker com 2 CPUs e 3,8 GB):** o Airflow ocupa cerca de 1 GB parado; o MLflow ocupa ~0,4 GB (era 1,5 GB: desligamos `MLFLOW_SERVER_ENABLE_JOB_EXECUTION`, que subia ~8 processos de jobs, e usamos `--workers 1`). **A API com o modelo T1 é o serviço mais pesado:** o `sinaliza-t1` (Random Forest de 154 árvores, 864 MB) chega a **2,6 a 2,8 GB na carga** e fica em **~1,26 GB** depois (medido; a API devolve ao sistema a memória do pico). **Pilha completa em regime (medida em 2026-11-05, depois da correção do MLflow): API 1,25 GB + Airflow 0,95 GB + MLflow 0,39 GB + Postgres 0,09 GB = ~2,7 GB de 3,8 GB, e rodou simulador, API e DAG `monitoramento` juntos sem falha.** **A ORDEM IMPORTA:** o pico da carga do modelo (~2,8 GB) só cabe se o Airflow ainda não estiver de pé; o compose agora garante isso (o Airflow só sobe depois do `/ready` da API). Se subir os serviços à mão, espere `/ready` antes do Airflow. Num primeiro teste, com o MLflow ainda no padrão (1,5 GB) e o Airflow já rodando, a API foi morta (exit 137). **Não testado:** o `treino_t1` completo rodando ao mesmo tempo que a API carregada (o Random Forest usa todos os CPUs e muita memória; para isso, reserve mais memória ao Docker ou pare a API durante o treino). Com pouca memória, suba a API com `SINALIZA_USE_MODEL=false` (só lista fixa, ~0,4 GB). O treino do Random Forest usa todos os CPUs e deixa tudo lento (até os comandos `docker compose exec`). Num Docker com 2 CPUs, um único trial do Optuna sobre uma amostra de apenas ~2.400 frases levou 12 min. Para a execução completa (25 tentativas, 6.000 frases), reserve mais CPU e memória ao Docker (estimativa, não medida: 4 CPUs e 8 GB) ou use `amostra_frases` menor na demonstração. A execução completa dentro do Docker ainda não foi feita; os números do treino real de 2026-11-02 vieram do ambiente local. Mínimo para só subir o Airflow: 4 GB.
- A imagem `airflow` tem 4,6 GB (Airflow mais o ambiente de ML com spaCy, scikit-learn, MLflow e Optuna) e o primeiro build demora.
- Para testar os DAGs sem sujar os dados reais, aponte `SINALIZA_DATABASE_URL` para outro banco e `SINALIZA_MLFLOW_EXPERIMENT` para outro experimento (um `docker-compose.override` só com isso no serviço `airflow`) e passe `registrar_modelo=false` ao `treino_t1`.
- O MLflow roda com `--allowed-hosts` (versão 3.17 rejeita `Host: mlflow:5000` por padrão, o que quebrava as tarefas do Airflow com 403).
- Ambiente local do ML fora do Docker (notebooks, testes): `textgloss/.venv`; testes com `cd textgloss; .venv/Scripts/python -m pytest` (33 passam). Testes do painel: ver abaixo. Testes da API: `cd api; .venv/Scripts/python -m pytest` (63 passam; o venv é criado com `py -3.12 -m venv .venv` e `pip install -r requirements.txt`).

### Subir tudo com um comando (fase 9)

```powershell
docker compose up -d --build
```

(Para a demonstração rápida: `$env:SINALIZA_PERFIL="demo"; docker compose up -d --build`. As opções estão em `.env.example`; copie para `.env` para mudar.)

**Ordem de subida (garantida pelo compose com healthchecks):** `postgres` → `mlflow` → `api` → `airflow` e `web`. A API só fica saudável (`GET /ready`) depois da **primeira tentativa de carregar o modelo**, com ou sem sucesso; assim o pico de memória da carga (~2,8 GB) acontece antes de o Airflow subir. Uma máquina sem modelo registrado também fica pronta e atende com a lista fixa.

**Máquina limpa (banco sem `corpus_bruto`):** o Airflow roda sozinho `airflow/bootstrap.sh`: ingestão → preparação → treino, e a API pega o `sinaliza-t1` em até 30 s depois de registrado, sem reiniciar. Acompanhe com `docker compose logs -f airflow` (linhas `[bootstrap]`) ou na interface (http://localhost:8080).

| Perfil | Preparação | Treino | Duração | Para que serve |
| --- | --- | --- | --- | --- |
| `demo` | 3.000 frases, 2 processos | Optuna com 2 tentativas e 300 frases, validação com 1.000 frases | **~2 min medidos** (Docker com 2 CPUs) | demonstrar o fluxo; o modelo sai pior |
| `completo` (padrão) | corpus todo (127 mil frases), 2 processos | 25 tentativas, 6.000 frases, 40.000 na validação | **horas, não medido no Docker** (o primeiro trial do Optuna já levou 12 min com 2 CPUs) | o modelo de verdade |

- Só age se o banco **não** tem `corpus_bruto`, se `SINALIZA_AUTO_PIPELINE` não é `false` e se ainda não rodou naquele volume (marca em `/opt/sinaliza/data/.bootstrap-feito`). **Ambiente com dados (como o seu) não é tocado:** verificado, a mensagem foi "o banco já tem o corpus; nada a fazer", sem nenhuma execução criada. Se falhar no meio, ele não retoma sozinho: dispare os DAGs à mão no Airflow.
- Ambiente já existente precisa de `--build` depois de atualizar o repositório (o healthcheck da API agora chama `/ready`; uma imagem antiga deixa a API `unhealthy` e o Airflow nunca sobe).
- **Verificado em 2026-11-07 numa cópia limpa do repositório** (todos os arquivos versionados e novos, sem `data/`, sem venvs, projeto compose separado, volumes vazios, perfil `demo`): subida na ordem certa; ingestão, preparação (3.000 frases, parâmetro repassado pela cadeia) e treino com as 7 tarefas em `success`; `sinaliza-t1` v1 registrado; API passou a usar o modelo sozinha; simulador → API → DAG `monitoramento` consolidou 15 frases; `down` e `up` de novo: API carregou o modelo antes do Airflow e o bootstrap não repetiu nada. Pilha em regime: ~2,6 a 2,7 GB.
- **Não coberto:** o serviço `web` (o build do front falha na `main` por causa do merge do PR #1 do time do web; ver [`15`](15-estado-atual-e-proximos-passos.md)), o `dashboard` (fase 10) e o perfil `completo` inteiro.

### Painel (fase 10)

```powershell
docker compose up -d --build dashboard
```

- Painel: http://localhost:8501 (Streamlit, atualiza sozinho a cada 10 s; desligável na barra lateral; tema claro e escuro). Só precisa de `postgres` e `mlflow` de pé; o que a API ou o Airflow não responderem aparece como "fora do ar" na aba **Serviços**, sem derrubar o resto.
- Quatro abas: **Visão geral** (frases, % mantidas, % sem sinal, % incertas, latência p95; frases por hora; latência p50 e p95; sem sinal e incertas por hora), **Inferências** (últimas frases com a decisão de cada palavra e a sequência de sinais; histograma da probabilidade de MANTER; decisões de baixa confiança; palavras sem sinal no vocabulário), **Modelo** (versão na API e no MLflow, métricas do teste final, comparação dos modelos) e **Serviços** (API `/health` e `/ready`, Postgres, MLflow, Airflow; frescor dos dados).
- O painel lê só as tabelas `inferencias` e `indicadores_horarios`: os **indicadores dependem do DAG `monitoramento`** (a cada hora); frases ainda não consolidadas aparecem como "aguardando consolidação". O texto das frases só aparece onde a API o gravou (simulador ou opt-in).
- Para ver o painel cheio: suba a API, rode `python -m textgloss.simulador --n 60` e dispare o DAG `monitoramento` no Airflow (ou `python -m textgloss.monitor`).
- Variáveis (`dashboard/data.py`, `Config`): `SINALIZA_DATABASE_URL`, `SINALIZA_API_URL`, `MLFLOW_TRACKING_URI`, `SINALIZA_MLFLOW_PUBLIC_URL`, `SINALIZA_AIRFLOW_URL` (vazio = Airflow "não monitorado") e `SINALIZA_MLFLOW_EXPERIMENT`.
- Memória medida: ~0,16 GB. Com o painel, a pilha toda (postgres, mlflow, api com o modelo, airflow e painel) ficou em ~2,65 GB dos 3,8 GB do Docker.
- Rodar fora do Docker e testar: `cd dashboard; py -3.12 -m venv .venv; .venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt`; `.venv/Scripts/python -m streamlit run app.py`; `.venv/Scripts/python -m pytest` (24 passam).

### API com o modelo e simulador de uso (fase 8)

```powershell
docker compose up -d postgres mlflow
docker compose up -d --build api
```

- A API sobe na hora e atende com a lista fixa; o `sinaliza-t1` chega em 10 a 20 s (a primeira vez baixa 864 MB do MLflow para o volume `modelcache`). Acompanhe em `http://localhost:8000/health` (campo `model`).
- A API precisa do modelo já registrado no MLflow (`sinaliza-t1`, criado pelo teste final do `treino_t1`). Sem ele, ou se o MLflow estiver fora, ela segue com `model_version: "lista-fixa"` e tenta de novo a cada 30 s.
- **Memória:** pico de ~2,8 GB na carga e ~1,26 GB depois. Suba a API **antes** do Airflow (ver a ordem e as medidas acima). Sem memória para o pico, use `SINALIZA_USE_MODEL=false`.
- Simulador (no host, com o venv do ML): `textgloss/.venv/Scripts/python -m textgloss.simulador --n 30 --intervalo 1` (opções: `--url`, `--fonte frases|corpus`). Depois `docker compose exec airflow airflow dags trigger monitoramento` (ou `python -m textgloss.monitor` com `SINALIZA_DATABASE_URL`) consolida em `indicadores_horarios`.
- O texto das frases só é gravado para o simulador; para os demais, só números. Ver [`16`](16-riscos-e-questoes-abertas.md).

## API

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
python -m pytest                      # 40 testes
python -m app.phrases                 # regera data/phrases.json
python -m app.phrases --check         # falha se estiver desatualizado
```

Opcional, embeddings semânticos (PyTorch + download do modelo na primeira vez; **não testado com o modelo real**):

```powershell
pip install -r requirements-semantic.txt
$env:SINALIZA_EMBEDDER = "sentence-transformers"
```

Variáveis: `SINALIZA_EMBEDDER` (`char-ngram` padrão), `SINALIZA_APPROX_THRESHOLD`, `SINALIZA_VOCABULARY`, `SINALIZA_PHRASES`.

Os testes da API rodaram no Python 3.13 do sistema (fastapi, httpx, numpy, pytest instalados).

## Web

```powershell
cd web
npm install
npm run signs      # uma vez: baixa os sinais do vocabulário para public/vlibras/signs/ (fora do git)
npm run dev        # http://localhost:5173
npm run build      # tsc --noEmit && vite build (passa)
npm test           # vitest: 3 testes do mapeamento das glosas (passam)
```

Para outra API: `VITE_API_URL`. CORS da API só libera `localhost:5173`/`127.0.0.1:5173`. Para ver o front funcionando, suba a API (porta 8000) e o `npm run dev`.

## Dados (`data/`)

Use **Python 3.12** (`py -3.12`). `mediapipe==0.10.21` e `ultralytics` foram instalados e testados nele.

```powershell
cd data
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt                     # traz o PyTorch (centenas de MB)
python -m pytest                                    # 35 testes (sem baixar pesos do YOLO)
python build_vocabulary.py "<pasta do V-LIBRASIL>/annotations.csv"   # regera vocabulary.json (curadoria em CURATED)
python extract_keypoints.py video entrada.mp4 saida.npy
python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras --limit 5
python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras --no-yolo --limit 5   # sem recorte, para comparar
```

O YOLOv8 vem ligado; os pesos `yolov8n.pt` são baixados pelo Ultralytics na **primeira execução real**. Nesta máquina o download pelo Python falhou (`CERTIFICATE_VERIFY_FAILED`); o arquivo foi baixado com `curl.exe` e está em `data/yolov8n.pt` (ignorado pelo git). Ver `data/README.md`.

Download do subconjunto inicial (sinalizantes 01, 02, 07, 10; ~16,3 GB; `-C -` retoma):

```powershell
New-Item -ItemType Directory -Force raw/minds-libras
foreach ($i in 1, 2, 7, 10) {
  $nome = "Sinalizador{0:00}.zip" -f $i
  curl.exe -L -C - --retry 20 --retry-all-errors -o "raw/minds-libras/$nome" "https://zenodo.org/records/2667329/files/${nome}?download=1"
}
```

## Modelo (`model/`)

```powershell
cd model
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest                                                                  # 32 testes
python -m sinaliza_model.motions --data-root "<...>/processed/v-librasil" --out "<...>/Datasets/motions/motions.npz"   # movimentos que a API toca
python -m sinaliza_model.train --synthetic                                        # demonstração
python -m sinaliza_model.train --data-root ../data/processed/minds-libras --val-signers 10
python -m sinaliza_model.embeddings checkpoints/model.pt                          # vizinhos no embedding
```

Saídas em `model/checkpoints/` (`model.pt`, `metrics.json`; ignorados pelo git).

Os testes de `model/` rodaram em 2026-10-19 com o Python do venv de `data/` (que já tem torch), sem montar o venv de `model/`.

## Estado dos testes (2026-10-19)

| Pasta | Testes | Resultado |
| --- | --- | --- |
| `api/` | 24 | passam |
| `data/` | 20 | passam |
| `model/` | 19 | passam |
| `web/` | — | sem testes; `npm run build` passa |

## Armadilhas

- Python padrão desta máquina: 3.13 (também há 3.12). Use 3.12 para `data/` e `model/`.
- Não misture os venvs de `data/` e `model/` (o de `data/` tem `numpy<2`).
- `*.npy`, `*.pt` e `data/raw|processed` não são versionados; `data/.venv` e `web/node_modules` também não.
- O primeiro uso do YOLOv8 e do `sentence-transformers` baixa pesos da internet.
