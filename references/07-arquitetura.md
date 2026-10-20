# Arquitetura

## Fluxo

```
texto ──► api (FastAPI) ──► gerador de poses ──► sequência de keypoints ──► web (avatar three.js)
                                  ▲
                      model/ (treino; ainda NÃO plugado na api)
                                  ▲
                      data/ (vídeos MINDS-Libras → keypoints .npy)
```

Em tempo de **execução** só `web/` e `api/` participam. `model/` e `data/` são ferramentas de linha de comando usadas **offline** (extrair dados, treinar). Por isso ficam fora do `docker-compose.yml`.

## Componentes

| Pasta | Tecnologia | Papel | Estado (2026-10-19) |
| --- | --- | --- | --- |
| `api/` | Python 3.11, FastAPI, pydantic v2 | `POST /translate`: texto → glosas + pose | Funcional com `StubGenerator` (aceno, não é Libras) |
| `web/` | React 18, Vite 5, TypeScript 5.6, three.js 0.169 | Formulário de texto e avatar em esqueleto | Funcional |
| `model/` | PyTorch, NumPy | Treino do gerador sinal → pose; linhas de base; DTW | Esqueleto testado só com dados **sintéticos** |
| `data/` | MediaPipe Holistic 0.10.21, OpenCV, NumPy `<2` | Vídeo → keypoints normalizados; leitura dos ZIPs do MINDS-Libras | Script pronto; **nunca rodado em vídeo real do MINDS-Libras** |
| `docs/` | Markdown | Contrato do formato de pose; decisão de dados | Atualizados em 2026-10-14 |

## O contrato: formato de pose

É a única interface entre `model/`, `api/` e `web/`. 75 keypoints × 3 coordenadas por frame, normalizados. Detalhes em [`08-formato-de-pose.md`](08-formato-de-pose.md). **Mudar o formato obriga a mexer nos três componentes.**

Cada componente tem sua cópia das constantes (não há pacote compartilhado):

| Onde | Arquivo |
| --- | --- |
| API | `api/app/pose_format.py` |
| Front | `web/src/skeleton.ts` (+ tipos em `web/src/api.ts`) |
| Modelo | `model/sinaliza_model/data.py` (`NUM_KEYPOINTS`, `HAND_SLICES`) |
| Extração | `data/extract_keypoints.py`, `data/minds_libras.py` |

Ao alterar o layout, grep por `75`, `33`, `21` e `HAND_COUNT`.

## Pontos de extensão

- **`PoseGenerator`** (`api/app/generator.py`) — `Protocol` com `to_glosses(text) -> list[str]` e `generate(glosses) -> PoseSequence`. O modelo (ou o medoide) entra implementando isso e substituindo `generator` em `api/app/main.py`.
- **`Avatar`** (`web/src/Avatar.tsx`) — entrada única `PoseSequence`; trocar o esqueleto por um avatar com rig mantém a mesma entrada.
- **`vocabulary.json`** (`data/`) — fonte única do vocabulário; lido por `data/minds_libras.py` e `model/sinaliza_model/data.py`. **A API ainda não o lê** (ver [`12-api.md`](12-api.md)).

## Decisões técnicas e motivos

| Decisão | Motivo |
| --- | --- |
| Venvs separados para `data/` e `model/` | `mediapipe==0.10.21` exige `numpy<2`; o `model/` aceita `numpy<3` e usa torch |
| MediaPipe fixado em 0.10.21 | Versões novas (testada 0.10.35) removeram `mp.solutions.holistic`; migrar exigiria API de Tasks + modelo `.task` e reescrever `extract()` |
| Front servido por nginx com proxy `/api/` | Evita CORS e permite um único `docker compose up` |
| Rosto fora do formato | Reduz dimensão e escopo; expressão facial fica como grupo novo no fim do layout, no futuro |
| `y` para cima, origem nos quadris, ombros = 1 | Independe de câmera/enquadramento; fácil de usar em avatar 3D |
| Linhas de base antes de rede neural | Com ~60 gravações por sinal, a recuperação (medoide) pode vencer o modelo; evita construir complexidade sem ganho |
| Validação por sinalizante | Mede generalização a pessoas novas, não memorização |
| Reamostragem para `seq_len` fixo (32) | Simplifica o modelo; duração real fica fora do modelo (limitação conhecida) |

## Infra

- `docker-compose.yml`: serviços `api` (porta 8000, healthcheck em `/health`) e `web` (porta 5173 → 80 do nginx, `depends_on: api healthy`, `VITE_API_URL=/api`).
- `api/Dockerfile`: `python:3.11-slim`, copia só `app/`, roda `uvicorn` em `0.0.0.0:8000`.
- `web/Dockerfile`: build com `node:22-alpine`, serve com `nginx:alpine`; `nginx.conf` repassa `/api/` para `http://api:8000/` e faz fallback SPA para `index.html`.
- `.gitignore`: `data/raw/`, `data/processed/`, `model/checkpoints/`, `*.npy`, `*.pt`, `*.pth`, venvs, `node_modules/`, `.env*`.
- Sem CI, sem banco de dados, sem autenticação.
