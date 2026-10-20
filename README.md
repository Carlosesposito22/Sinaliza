# Sinaliza

Projeto de Projetos 6 (Grupo 10). Tradução de **texto/fala em português para movimento de Libras**, exibido por um avatar.

> Esta é a fase 2 (código). O contexto da fase 1 (problema, personas, similares, requisitos) está na pasta `Documentos/`, e um resumo para quem vai trabalhar no código está em `references/`. O escopo mudou: **não** reconhecemos o sinal feito pelo usuário via câmera; o ML gera o movimento a partir do texto.

## Arquitetura

```
texto ──► api (FastAPI) ──► texto → glosas ──► gerador de poses ──► sequência de keypoints ──► web (avatar 3D)
                              (tabela + embeddings)       ▲
                                              model/ (treino, ainda stub)
                                                          ▲
                                       data/ (vídeos → YOLOv8 + MediaPipe → keypoints)
```

| Pasta | Papel | Estado |
| --- | --- | --- |
| `api/` | Serviço HTTP. Texto → glosas (tabela + embeddings) → poses. Frases de exemplo por categoria | Funcional com gerador **stub** |
| `web/` | Front (React + Vite + three.js). Envia texto, mostra como cada palavra virou sinal e anima o avatar | Funcional, avatar em esqueleto |
| `model/` | Treino do modelo sinal → pose, com linhas de base e métrica DTW; inspeção dos embeddings | Esqueleto testado com dados sintéticos |
| `data/` | Extração de keypoints: YOLOv8 recorta a pessoa, MediaPipe Holistic extrai pose e mãos | Pronto; ainda sem dataset real nem pesos do YOLOv8 baixados |
| `docs/` | Contrato do formato de pose e decisões | `pose-format.md`, `dados-e-vocabulario.md` |

O contrato entre `model/`, `api/` e `web/` é o **formato de pose** descrito em [`docs/pose-format.md`](docs/pose-format.md).

## Como rodar

### Tudo de uma vez (Docker)

```powershell
docker compose up --build
```

- Front: `http://localhost:5173`
- API: `http://localhost:8000` (documentação em `/docs`)

O front é servido pelo nginx e repassa `/api/*` para a API, então não há CORS. Para parar: `Ctrl+C` e `docker compose down`. O Docker Desktop precisa estar em execução. O contexto de build da API é a raiz do repositório, porque a imagem leva `data/vocabulary.json` e `data/phrases.json`.

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

Abre em `http://localhost:5173`. Para apontar para outra API, defina `VITE_API_URL`.

## Próximos passos

1. Baixar o subconjunto do MINDS-Libras (ver `data/README.md`) e extrair os keypoints com `data/extract_keypoints.py`.
2. Comparar as taxas de detecção de mão com e sem YOLOv8 (`--no-yolo`).
3. Treinar o primeiro modelo em `model/`, comparar com as linhas de base e plugar o vencedor no lugar do `StubGenerator`.
4. Trocar o esqueleto por um avatar com rig (GLB) e retargeting dos keypoints.
5. Validar os sinais e o vocabulário com alguém que saiba Libras.
