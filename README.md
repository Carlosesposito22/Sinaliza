# Sinaliza

Projeto de Projetos 6 (Grupo 10). Tradução de **texto/fala em português para movimento de Libras**, exibido por um avatar.

> Esta é a fase 2 (código). O contexto da fase 1 (problema, personas, similares, requisitos) está na pasta `pesquisas/` do repositório raiz da disciplina. O escopo mudou: **não** reconhecemos o sinal feito pelo usuário via câmera; o ML gera o movimento a partir do texto.

## Arquitetura

```
texto ──► api (FastAPI) ──► gerador de poses ──► sequência de keypoints ──► web (avatar 3D)
                                  ▲
                      model/ (treino, ainda stub)
                                  ▲
                      data/ (vídeos → keypoints)
```

| Pasta | Papel | Estado |
| --- | --- | --- |
| `api/` | Serviço HTTP. Recebe texto e devolve a sequência de poses | Funcional com gerador **stub** |
| `web/` | Front (React + Vite + three.js). Envia texto e anima o avatar | Funcional, avatar em esqueleto |
| `model/` | Treino do modelo sinal → pose, com linhas de base e métrica DTW | Esqueleto testado com dados sintéticos |
| `data/` | Extração de keypoints com MediaPipe Holistic | Script inicial, sem dataset |
| `docs/` | Contrato do formato de pose e decisões | `pose-format.md` |

O contrato entre `model/`, `api/` e `web/` é o **formato de pose** descrito em [`docs/pose-format.md`](docs/pose-format.md).

## Como rodar

### API

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000` (documentação em `/docs`). Testes: `python -m pytest`.

### Web

```powershell
cd web
npm install
npm run dev
```

Abre em `http://localhost:5173`. Para apontar para outra API, defina `VITE_API_URL`.

## Próximos passos

1. Escolher e baixar a(s) fonte(s) de dados de sinais (ver `data/README.md`).
2. Gerar keypoints com `data/extract_keypoints.py`.
3. Definir o vocabulário inicial de sinais (MVP).
4. Treinar o primeiro modelo em `model/` e plugá-lo no lugar do `StubGenerator`.
5. Trocar o esqueleto por um avatar com rig (GLB) e retargeting dos keypoints.
