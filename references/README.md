# references/ — contexto do projeto Sinaliza para o Claude

Esta pasta existe para que uma sessão nova do Claude (ou uma pessoa nova na equipe) entenda o projeto sem depender de memória de conversa. Foi montada em 2026-10-19 a partir de:

- `Documentos/` — as entregas da disciplina (Entrega 1, Ideação/Proposição, Personas, Jornadas, Análise de Similares, Requisitos, Matriz de Pesquisa, apresentação);
- o código e os docs do repositório (`api/`, `web/`, `model/`, `data/`, `docs/`, `README.md`);
- o histórico do git (5 commits de código, todos de 2026-10-14);
- as sugestões do orientador (YOLOv8, embeddings, geração de textos por categoria), implementadas em 2026-10-19 (ver `19-sugestoes-do-orientador.md`);
- a decisão de **reduzir o escopo**, tomada depois de conversa com o professor (relatada pelo Carlos).

## Leia primeiro

1. [`00-visao-geral.md`](00-visao-geral.md) — o que é o Sinaliza, em uma página.
2. [`01-escopo-atual.md`](01-escopo-atual.md) — **o escopo vigente** e o que mudou em relação às entregas. Onde houver conflito entre este arquivo e os docs da fase 1, vale este.
3. [`15-estado-atual-e-proximos-passos.md`](15-estado-atual-e-proximos-passos.md) — o que funciona, o que é stub, o que falta.
4. [`22-plano-ml-texto-glosa.md`](22-plano-ml-texto-glosa.md) — o plano de ML vigente e o que falta para cumprir os requisitos da disciplina. A pesquisa que o motivou está em [`../Pesquisas/`](../Pesquisas/).
5. [`17-convencoes-e-regras-para-claude.md`](17-convencoes-e-regras-para-claude.md) — como trabalhar neste repositório.

## Índice completo

### Contexto (fase 1: pesquisa e proposta)

| Arquivo | Conteúdo |
| --- | --- |
| [`00-visao-geral.md`](00-visao-geral.md) | Resumo do projeto, equipe, linha do tempo |
| [`01-escopo-atual.md`](01-escopo-atual.md) | Pivô de escopo: de "reconhecer o sinal do usuário" para "texto → Libras" |
| [`02-problema-e-contexto.md`](02-problema-e-contexto.md) | Problema, dados de pesquisa documental, lacunas |
| [`03-personas-e-jornadas.md`](03-personas-e-jornadas.md) | Júlia, Matheus, Helena e as jornadas atuais |
| [`04-analise-de-similares.md`](04-analise-de-similares.md) | Hand Talk, VLibras, ProDeaf, Libras Aventura |
| [`05-requisitos.md`](05-requisitos.md) | R01–R06 originais e como ficam no escopo atual |
| [`06-ideacao-e-decisoes.md`](06-ideacao-e-decisoes.md) | MoSCoW, funcionalidades selecionadas, backlog e cronograma originais, decisões |

### Engenharia (fase 2: código)

| Arquivo | Conteúdo |
| --- | --- |
| [`07-arquitetura.md`](07-arquitetura.md) | Componentes, fluxo de dados, decisões técnicas |
| [`08-formato-de-pose.md`](08-formato-de-pose.md) | O contrato único entre `model/`, `api/` e `web/` |
| [`09-dados-e-vocabulario.md`](09-dados-e-vocabulario.md) | MINDS-Libras, os 20 sinais, licenças, limites |
| [`10-pipeline-de-dados.md`](10-pipeline-de-dados.md) | `data/`: vídeo → keypoints |
| [`11-modelo-ml.md`](11-modelo-ml.md) | `model/`: gerador de movimento, linhas de base, métrica DTW (experimento; a entrega de ML agora é o 22) |
| [`22-plano-ml-texto-glosa.md`](22-plano-ml-texto-glosa.md) | **Plano de ML vigente:** texto → glosa por classificação no VLibrasBD, mapa dos requisitos de ML da disciplina e fases |
| [`12-api.md`](12-api.md) | `api/`: endpoints, gerador stub, como plugar o modelo |
| [`13-web.md`](13-web.md) | `web/`: front React e o avatar do VLibras (local) |
| [`14-como-rodar-e-testar.md`](14-como-rodar-e-testar.md) | Comandos, venvs, Docker, testes |

### Situação e trabalho

| Arquivo | Conteúdo |
| --- | --- |
| [`15-estado-atual-e-proximos-passos.md`](15-estado-atual-e-proximos-passos.md) | Estado real por componente e próximos passos |
| [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md) | O que ainda não sabemos ou não validamos |
| [`17-convencoes-e-regras-para-claude.md`](17-convencoes-e-regras-para-claude.md) | Idioma, commits, ambiente, honestidade sobre Libras |
| [`18-glossario.md`](18-glossario.md) | Termos de Libras, ML e do projeto |
| [`20-tcc-lisandra-cruz.md`](20-tcc-lisandra-cruz.md) | TCC indicado pelo orientador (reconhecimento de sinais estáticos): resumo, cautelas e o que aproveitar |
| [`21-datasets-de-treino.md`](21-datasets-de-treino.md) | Datasets de treino: V-LIBRASIL baixado (o que há nele, teste de extração), MINDS não baixado, Apoema descartado, decisões em aberto |
| [`19-sugestoes-do-orientador.md`](19-sugestoes-do-orientador.md) | YOLOv8, embeddings e geração de textos por categoria: interpretação adotada e o que foi implementado |

## Como manter

- Mudou o escopo, o formato de pose ou uma decisão de dados? Atualize o arquivo correspondente **e** `01-escopo-atual.md` / `15-estado-atual-e-proximos-passos.md`.
- Estes arquivos resumem; a fonte de verdade técnica continua sendo o código e `docs/`. Se divergirem, confira o código e corrija o resumo.
- Marque como **[inferido]** ou **[a confirmar]** o que não vier de um documento ou do código.
