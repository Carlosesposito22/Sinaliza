# Convenções e regras para o Claude neste repositório

## Idioma

- **Português do Brasil** em docs, mensagens de commit, mensagens de erro da API (`"o texto não contém palavras"`), textos de UI e comentários/docstrings do código existente.
- Nomes de código (variáveis, funções, classes) em **inglês** (`StubGenerator`, `to_glosses`, `process_zip`).
- Glosas em **MAIÚSCULAS** (`FILHO`, `AMÉRICA`). Comparações usam `slug()` (sem acento, maiúsculas) — não compare strings cruas.

## Estilo de código

- Python: tipagem moderna (`list[str]`, `X | None`), `dataclass(frozen=True)`, docstrings curtas que explicam **limites e porquês** (ver `metrics.py`, `data/README.md`). Poucos comentários, só onde o motivo não é óbvio.
- TypeScript: componentes funcionais com hooks, tipos explícitos em `api.ts`; sem biblioteca de estado.
- Testes com `pytest`; extratores e dados falsos em vez de dependências pesadas (MediaPipe não é exigido pelos testes de `data/`).
- Escreva código que **parece com o que já existe** em vez de impor outro estilo.

## Git

- Histórico segue **Conventional Commits em português** com escopo: `feat(data): ...`, `feat(model): ...`, `docs: ...`, `build: ...`.
- Commit/push **somente quando o usuário pedir.** A branch é `main`.
- Termine mensagens de commit com a linha de atribuição indicada pelo ambiente.
- Não versione: `data/raw/`, `data/processed/`, `model/checkpoints/`, `*.npy`, `*.pt`, venvs, `node_modules/`, `.env*`.

## Regras de domínio (importantes)

1. **Nunca chame a saída de "tradução de Libras".** Use "sequência de sinais". Libras tem gramática, uso do espaço e expressão facial; o MVP concatena sinais isolados.
2. **Não afirme que o modelo funciona** sem DTW em **sinalizante não visto** nos **dados reais**. Resultado em dados sintéticos não é evidência.
3. **Não invente conteúdo de Libras** (sinais, glosas, regras gramaticais, significados). O grupo não tem falante; qualquer afirmação linguística deve ser marcada como **proposta não validada**.
4. **Não mude o formato de pose** sem propagar para `api/`, `web/`, `model/` e `data/` e atualizar `docs/pose-format.md` e [`08-formato-de-pose.md`](08-formato-de-pose.md).
5. **Respeite licenças:** MINDS-Libras CC BY 4.0 (atribuir); V-LIBRASIL sem redistribuição; pt-br2libras-gloss CC BY-SA 4.0 (consultar o professor sobre share-alike).
6. **Não versione vídeos de sinalizantes** (dados pessoais).
7. Se o `StubGenerator` for substituído, **atualize `api/tests/test_api.py`** (ele assume 1 s por glosa: `len(frames) == 3 * fps` para 3 glosas).
8. Mapeamento aproximado por embedding **nunca é silencioso**: a API devolve `kind: "approx"` e o front marca. Não esconda nem promova uma aproximação a `exact`.
9. Ao mudar `data/vocabulary.json` ou os modelos de frase em `api/app/phrases.py`, rode `python -m app.phrases` e commite `data/phrases.json` (um teste confere).
10. O YOLOv8 (Ultralytics, **AGPL-3.0**) fica só na extração offline em `data/`; não o coloque na API nem na imagem Docker sem reavaliar a licença com o professor.
11. Distinga **fato verificado**, **inferido** e **a confirmar** ao resumir — como fazem estes arquivos.

## Ambiente

- Windows 11, PowerShell como shell principal (Bash também disponível).
- Venvs separados: `api/.venv`, `data/.venv`, `model/.venv`.
- Pasta de trabalho do Claude Code nesta máquina: `C:\Users\Carlos\Desktop\Projetos 6\Sinaliza` (o repositório é `Sinaliza/`; `Projetos 6/` é a pasta-mãe).
- O desenvolvimento acontecia em outra máquina; esta é uma retomada (2026-10-19) — não presuma que venvs, dados baixados ou `node_modules/` existam aqui.

## Quando for pedir algo ao usuário (Carlos)

Perguntas que valem a pena, porque o código não responde:

- o que o professor pediu para a próxima entrega e quando;
- quem poderia validar os sinais;
- se o download dos ZIPs está em andamento na outra máquina e onde estão os arquivos;
- se há mais documentos (ata da conversa com o professor, formulário da pesquisa de 40+ respostas).

## Onde está cada coisa (atalhos)

| Preciso de… | Vá para |
| --- | --- |
| Entender o que mudou | [`01-escopo-atual.md`](01-escopo-atual.md) |
| Contrato de dados | [`08-formato-de-pose.md`](08-formato-de-pose.md), `docs/pose-format.md` |
| Lista dos 20 sinais | `data/vocabulary.json`, [`09-dados-e-vocabulario.md`](09-dados-e-vocabulario.md) |
| Plugar o modelo na API | [`12-api.md`](12-api.md) |
| Rodar algo | [`14-como-rodar-e-testar.md`](14-como-rodar-e-testar.md) |
| O que falta | [`15-estado-atual-e-proximos-passos.md`](15-estado-atual-e-proximos-passos.md) |
