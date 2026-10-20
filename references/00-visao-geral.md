# Visão geral

## O que é

**Sinaliza** é um projeto da disciplina **Projetos 6** (Grupo 10, curso de Ciência da Computação). A versão atual é uma ferramenta que **recebe um texto em português e o traduz para movimento em Libras (Língua Brasileira de Sinais)**, exibido por um avatar na tela.

Tecnicamente: texto → sequência de glosas (sinais) → sequência de poses (keypoints de corpo e mãos) → animação de um avatar. O componente de ML é um gerador de movimento condicionado ao sinal, treinado em gravações reais de sinalizantes (dataset MINDS-Libras).

> Pivô importante: o projeto **nasceu** como um jogo que reconhece, pela câmera, o sinal feito pelo usuário. Esse escopo foi **reduzido**. Veja [`01-escopo-atual.md`](01-escopo-atual.md).

## Equipe (Grupo 10)

Amanda Montarroios, Bruno Assunção, Caio Ferreira, Carlos Espósito, Fabiana Souza Leão, Felipe Marques.

- Todos de Ciência da Computação; **não há Design no grupo**.
- **Ninguém da equipe sabe Libras.** Esse fato motivou a redução de escopo (ver abaixo) e é o principal limite de validação do projeto.
- Trabalho remoto, com reuniões presenciais eventuais; WhatsApp usado para registrar e compartilhar pesquisas.

## Linha do tempo

| Quando | O quê |
| --- | --- |
| Fase 1 (pesquisa) | Pesquisa documental, matriz de pesquisa, análise de similares, personas, jornadas, requisitos preliminares, ideação e proposta. Entregas em `Documentos/` |
| Fase 1 (apresentação) | Pesquisa com usuários (40+ respostas) e apresentação do Grupo 10 |
| Conversa com o professor | Decisão de reduzir o escopo para texto → Libras |
| 2026-10-14 | Todos os 5 commits do repositório: estrutura inicial, decisão de dados/vocabulário, esqueleto de treino, extração em lote, Docker |
| 2026-10-19 | Retomada em outra máquina; criação desta pasta `references/` |

## Mapa do repositório

```
Sinaliza/
  Documentos/     entregas da fase 1 (docx, pdf, xlsx) — NÃO versionadas ainda (untracked)
  api/            FastAPI: POST /translate, gerador stub
  web/            React + Vite + three.js: formulário + avatar em esqueleto
  model/          PyTorch: gerador sinal → pose, linhas de base, DTW
  data/           MediaPipe Holistic: vídeo → keypoints; vocabulary.json
  docs/           pose-format.md, dados-e-vocabulario.md
  references/     (esta pasta) contexto para o Claude
  docker-compose.yml, README.md, .gitignore
```

## Em uma frase para explicar a alguém

"Você digita uma frase em português, e um avatar mostra a sequência de sinais de Libras correspondentes — por enquanto só para 20 sinais, usando movimento aprendido de vídeos reais, e sem pretender ser uma tradução linguisticamente correta."
