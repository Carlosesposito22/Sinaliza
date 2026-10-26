# Sinaliza

Projeto de Projetos 6 (Grupo 10): ferramenta que recebe **texto em português** e mostra a **sequência de sinais de Libras** correspondente em um avatar. O ML gera movimento a partir do texto (dataset MINDS-Libras, vocabulário fechado de 20 sinais).

O escopo foi reduzido depois de conversa com o professor: o projeto **não** reconhece mais o sinal feito pelo usuário via câmera. As entregas em `Documentos/` descrevem o escopo antigo.

## Contexto

Leia `references/README.md` (índice). Para começar:

- `references/01-escopo-atual.md`: escopo vigente. Prevalece sobre `Documentos/`.
- `references/15-estado-atual-e-proximos-passos.md`: o que funciona, o que é stub, o que falta.
- `references/17-convencoes-e-regras-para-claude.md`: convenções completas.

## Regras principais

1. Nunca chame a saída de "tradução de Libras". Use "sequência de sinais". O MVP concatena sinais isolados, sem gramática nem expressão facial.
2. Ninguém da equipe sabe Libras. Não invente sinais, glosas ou regras linguísticas. Marque tudo como proposta não validada.
3. Só afirme que o modelo funciona com DTW em sinalizante não visto, em dados reais. Resultado em dados sintéticos não vale. Se o modelo não superar o medoide, fica o medoide.
4. O formato de pose (75 keypoints, normalizado) é o contrato entre `api/`, `web/`, `model/` e `data/`. Ao mudá-lo, atualize os quatro e `docs/pose-format.md`.
5. Respeite as licenças: MINDS-Libras é CC BY 4.0 (atribuir); V-LIBRASIL só para pesquisa e ensino, sem redistribuir, e fica só local em `C:\Users\Carlos\Desktop\Projetos 6\Datasets` (fora do repositório). Nunca versione vídeos de sinalizantes nem `data/raw/`, `data/processed/`, `*.npy`, `*.pt`. Ver `references/21-datasets-de-treino.md`.
6. A API toca gravações reais (`MotionPlayback`) quando `SINALIZA_MOTIONS` aponta para um `.npz`; senão usa o `StubGenerator` (aceno de teste). O `.npz` é derivado do V-LIBRASIL: não versione.
7. Aproximação de palavra por embedding nunca é silenciosa (`kind: "approx"` na API, "~" no front).
8. O YOLOv8 (Ultralytics, AGPL-3.0) fica só na extração offline em `data/`; não o leve para a API.
9. `data/vocabulary.json` vem de `data/build_vocabulary.py` (tabela `CURATED`); ao mudar ele ou `api/app/phrases.py`, rode `python -m app.phrases` e commite `data/phrases.json`.
10. Formato de pose: origem no meio dos **ombros**; índices 23–32 zerados em vídeo da cintura para cima; tratar `[0, 0, 0]` como ausente.
11. Avalie geração com a **recuperação** (`retrieval`), não só com o DTW médio: o DTW premia movimento borrado.
12. O avatar é o player do VLibras (LGPL-3.0) rodando **localmente** (`web/public/vlibras/`); os sinais vêm de `npm run signs` e **não são versionados** (`web/public/vlibras/signs/`). O avatar antigo (Rocketbox) está em `historico/avatar-rocketbox/` e não é compilado.

## Convenções

- Docs, commits e mensagens de erro em português do Brasil; nomes de código em inglês; glosas em MAIÚSCULAS, comparadas com `slug()`.
- Commits em Conventional Commits em português com escopo (`feat(data): ...`). Commite só quando o usuário pedir.
- Ambiente: Windows e PowerShell. Venvs separados em `api/`, `data/` e `model/` (`data/` exige `numpy<2` e Python 3.12). Veja `references/14-como-rodar-e-testar.md`.
