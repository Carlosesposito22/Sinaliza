# Mock da API (contrato v1)

Servidor de mentira, no formato final, para o time do web trabalhar sem esperar o ML. Quem vai fazer o web começa pelo [`guia-web-trilha.md`](../docs/guia-web-trilha.md). Contrato completo, regras e exemplos: [`docs/contrato-api-web.md`](../docs/contrato-api-web.md).

```bash
docker compose --profile mock up --build mock-api
```

Sem Docker (nesta pasta):

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m uvicorn sinaliza_mock.server:app --port 8000
.venv/Scripts/python -m pytest
```

- `/docs` mostra todos os endpoints para testar no navegador. Porta 8000, a mesma da API real (suba uma ou outra).
- A trilha (`/learn/*`) é real: conteúdo gerado de `data/vocabulary.json` e regras de XP/estrelas/sequência em `sinaliza_mock/store.py`. O progresso fica em memória e some ao reiniciar.
- O tradutor (`/translate`) é falso: decide `MANTER`/`DESCARTAR` por regra simples e responde `model_version: "mock"`.
- Mudou `sinaliza_mock/schemas.py`? Atualize o contrato, `web/src/contract.ts` e rode `python -m sinaliza_mock.export_openapi`.
