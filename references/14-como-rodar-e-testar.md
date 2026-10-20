# Como rodar e testar

Ambiente de desenvolvimento do projeto: **Windows + PowerShell** (os comandos do repositório são PowerShell). Cada ferramenta Python tem **venv próprio** (`data/` precisa de `numpy<2`).

## Tudo de uma vez (Docker)

```powershell
docker compose up --build
```

- Front: http://localhost:5173
- API: http://localhost:8000 (docs em `/docs`)
- Parar: `Ctrl+C` e `docker compose down`. Docker Desktop precisa estar rodando.
- `model/` e `data/` **não** entram no compose (são CLIs).

## API

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
python -m pytest
```

## Web

```powershell
cd web
npm install
npm run dev        # http://localhost:5173
npm run build      # tsc --noEmit && vite build
```

Para outra API: variável `VITE_API_URL`. CORS da API só libera `localhost:5173`/`127.0.0.1:5173`.

## Dados (`data/`)

```powershell
cd data
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest                                   # testes com extrator falso (sem MediaPipe)
python extract_keypoints.py video entrada.mp4 saida.npy
python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras
```

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
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
python -m sinaliza_model.train --synthetic                                        # demonstração
python -m sinaliza_model.train --data-root ../data/processed/minds-libras --val-signers 10
```

Saídas em `model/checkpoints/` (`model.pt`, `metrics.json`; ignorados pelo git). Imprime o DTW médio de `global_mean`, `class_mean`, `medoid` e `model`.

## Estado dos testes

Existem testes em `api/` (4), `data/` e `model/` (20 funções `test_*` somadas). **Não foram executados na sessão de 2026-10-19** (esta sessão só leu o código). Antes de afirmar que "passam", rode-os.

## Armadilhas

- Python no PATH desta máquina: 3.13. A imagem Docker da API usa 3.11. `mediapipe==0.10.21` pode **não ter wheel** para Python 3.13 — para `data/` talvez seja preciso 3.10–3.12. **[a verificar]**
- Não misture os venvs de `data/` e `model/`.
- `*.npy`, `*.pt` e `data/raw|processed` não são versionados.
- A pasta `Documentos/` ainda está **untracked** no git.
