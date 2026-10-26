# Sinaliza

Projeto de Projetos 6 (Grupo 10). Tradução de **texto/fala em português para movimento de Libras**, exibido por um avatar.

> Esta é a fase 2 (código). O contexto da fase 1 (problema, personas, similares, requisitos) está na pasta `Documentos/`, e um resumo para quem vai trabalhar no código está em `references/`. O escopo mudou: **não** reconhecemos o sinal feito pelo usuário via câmera; o ML gera o movimento a partir do texto.

## Arquitetura

```
texto ──► api (FastAPI) ──► texto → glosas ──► gerador de poses ──► sequência de keypoints ──► web (avatar 3D)
                              (tabela + embeddings)       ▲
                                              model/ (treino, ainda stub)
                                                          ▲
                                       data/ (vídeos V-LIBRASIL → MediaPipe → keypoints)
```

| Pasta | Papel | Estado |
| --- | --- | --- |
| `api/` | Serviço HTTP. Texto → glosas (tabela + embeddings) → poses. Frases de exemplo por categoria | Funcional com gerador **stub** |
| `web/` | Front (React + Vite). Envia texto, mostra como cada palavra virou sinal e toca os sinais no avatar do VLibras | Funcional, avatar do VLibras rodando localmente |
| `model/` | Treino do modelo sinal → pose, com linhas de base e métrica DTW; inspeção dos embeddings | Esqueleto testado com dados sintéticos |
| `data/` | Vocabulário curado (210 sinais do V-LIBRASIL) e extração de keypoints com MediaPipe Holistic (YOLOv8 opcional) | Pronto; o V-LIBRASIL fica só local, fora do repositório (ver `references/21-datasets-de-treino.md`) |
| `docs/` | Contrato do formato de pose e decisões | `pose-format.md`, `dados-e-vocabulario.md` |

O contrato entre `model/`, `api/` e `web/` é o **formato de pose** descrito em [`docs/pose-format.md`](docs/pose-format.md).

## Como rodar

### Tudo de uma vez (Docker)

```powershell
docker compose up --build
```

Isso basta num clone novo: o build do front baixa sozinho os sinais do VLibras do vocabulário (precisa de internet no primeiro build; depois fica em cache).

Para a API tocar as gravações reais (e não o aceno de teste), aponte `SINALIZA_MOTIONS_DIR` para a pasta com o `motions.npz` (derivado do V-LIBRASIL, fora do repositório; ver `references/12-api.md`):

```powershell
$env:SINALIZA_MOTIONS_DIR = "C:\Users\Carlos\Desktop\Projetos 6\Datasets\motions"
docker compose up --build
```

- Front: `http://localhost:5173`
- API: `http://localhost:8000` (documentação em `/docs`)

O front é servido pelo nginx e repassa `/api/*` para a API, então não há CORS. Para parar: `Ctrl+C` e `docker compose down`. O Docker Desktop precisa estar em execução. O contexto de build da API e do front é a raiz do repositório: a API leva `data/vocabulary.json` e `data/phrases.json`, e o front usa o vocabulário para baixar os sinais.

Os serviços `model/` e `data/` não entram no compose: são ferramentas de linha de comando (treino e extração), não servidores.

### API

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000` (documentação em `/docs`). Testes: `python -m pytest`.

Endpoints: `POST /translate`, `GET /vocabulary`, `GET /categories`, `GET /health`.

Embeddings para palavras fora do vocabulário (variável `SINALIZA_EMBEDDER`):

- `char-ngram` (padrão): só NumPy; pega flexões e erros de digitação.
- `sentence-transformers` (opcional, `pip install -r requirements-semantic.txt`): pega sentido (sinônimos), baixa um modelo na primeira vez.

`SINALIZA_APPROX_THRESHOLD` muda o limiar de similaridade. Para regenerar as frases de exemplo: `python -m app.phrases`.

### Web

```powershell
cd web
npm install
npm run dev
```

Abre em `http://localhost:5173`. Para apontar para outra API, defina `VITE_API_URL`. Testes: `npm test`.

O avatar é o player do **VLibras** (Ícaro, Hosana ou Guga; `web/public/vlibras/`, LGPL-3.0), que toca as glosas. Ele e os sinais rodam localmente; os sinais ficam fora do git, então, fora do Docker, rode `npm run signs` em `web/` uma vez (só essa etapa precisa de internet); no Docker, o build já faz isso. Créditos e licenças em [`docs/creditos-e-licencas.md`](docs/creditos-e-licencas.md). O avatar anterior (Rocketbox) está em [`historico/avatar-rocketbox/`](historico/avatar-rocketbox/README.md).

## Próximos passos

1. Validar os sinais com alguém que saiba Libras e destacar a glosa em execução no avatar.
2. Decidir se entra um segundo dataset (mais sinalizantes ou gravações por sinal é o que mudaria o resultado do modelo).
3. Expressão facial do avatar, se houver dados (hoje mexem braços, mãos, dedos, cabeça e um pouco do peito).
