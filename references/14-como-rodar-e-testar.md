# Como rodar e testar

Ambiente de desenvolvimento do projeto: **Windows + PowerShell**. Cada ferramenta Python tem **venv próprio** (`data/` precisa de `numpy<2`).

## Tudo de uma vez (Docker)

```powershell
docker compose up --build
```

- Front: http://localhost:5173
- API: http://localhost:8000 (docs em `/docs`)
- Parar: `Ctrl+C` e `docker compose down`. Docker Desktop precisa estar rodando.
- `model/` e `data/` **não** entram no compose (são CLIs).
- O build da API usa a **raiz do repositório** como contexto (a imagem leva `data/vocabulary.json` e `data/phrases.json`). Verificado em 2026-10-19: `docker compose up --build` constrói as duas imagens (api 358 MB, web 103 MB), a API fica saudável e `/health`, `/translate`, `/vocabulary` e `/categories` respondem direto (porta 8000) e pelo proxy do nginx (`localhost:5173/api/...`); o front carrega as categorias. O primeiro build revelou que o `numpy` faltava no `api/requirements.txt` (nos testes locais ele vinha do Python do sistema); corrigido.

## API

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
python -m pytest                      # 24 testes
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
npm run dev        # http://localhost:5173
npm run build      # tsc --noEmit && vite build (passa)
```

Para outra API: `VITE_API_URL`. CORS da API só libera `localhost:5173`/`127.0.0.1:5173`. Para ver o front funcionando, suba a API (porta 8000) e o `npm run dev`.

## Dados (`data/`)

Use **Python 3.12** (`py -3.12`). `mediapipe==0.10.21` e `ultralytics` foram instalados e testados nele.

```powershell
cd data
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt                     # traz o PyTorch (centenas de MB)
python -m pytest                                    # 20 testes (sem baixar pesos do YOLO)
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
python -m pytest                                                                  # 19 testes
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
