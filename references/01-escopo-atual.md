# Escopo atual (vigente)

Este é o arquivo de referência quando houver dúvida sobre "o que estamos construindo". Ele **prevalece** sobre os documentos de `Documentos/`, que descrevem o escopo anterior.

## Escopo anterior (fase 1, em `Documentos/`)

Jogo interativo baseado em câmera:

1. o sistema mostra um sinal-alvo;
2. o usuário o reproduz diante da câmera;
3. MediaPipe Holistic extrai keypoints e um classificador (LSTM ou CNN, treinado no MINDS-Libras) reconhece o sinal;
4. feedback **acerto / quase lá / erro** por limiar de similaridade;
5. progressão por níveis (alfabeto → frases; trilhas escola, saúde, trabalho) e dicionário consultável;
6. tela de consentimento LGPD antes de qualquer captura.

A proposta se vendia como **bidirecional** e diferenciada dos tradutores unidirecionais (Hand Talk, VLibras, ProDeaf). A lista MoSCoW da fase 1 colocava "tradução unidirecional via avatar 3D" explicitamente em **Won't have**.

## Escopo atual

**Ferramenta que recebe texto e o traduz para sinais em Libras**, mostrados por um avatar. Direção: **português → Libras** (o inverso do escopo anterior).

### Por que mudou

Conversa com o professor, relatada pelo Carlos: **ninguém da equipe sabe Libras**, então não teríamos como avaliar se o reconhecimento de um sinal feito por um usuário está correto. No novo escopo o ML gera movimento a partir de texto e a avaliação é **objetiva e automática** (distância DTW contra gravações de sinalizantes não vistos no treino), sem exigir que a equipe julgue sinais.

> Nota de honestidade: o novo escopo não elimina a limitação de Libras, só a desloca. A métrica DTW mede fidelidade ao movimento gravado, **não correção linguística**. Ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md).

### Dentro do escopo

- Texto em português → sequência de glosas: por tabela em `data/vocabulary.json` e, para palavras fora dela, por aproximação com embeddings (sempre sinalizada ao usuário).
- Frases de exemplo por categoria (escola, saúde, serviços, trabalho, família, geral), só com o vocabulário.
- Extração dos dados com YOLOv8 (recorte da pessoa) + MediaPipe.
- Glosas → sequência de poses (corpo + mãos), por gerador (stub hoje; modelo ou medoide depois).
- Avatar que anima a sequência (desde 2026-10-25, o player do VLibras rodando localmente, tocando as nossas glosas com os sinais do dicionário do VLibras).
- Dados: MINDS-Libras, vocabulário fechado de **20 sinais**.
- Avaliação do modelo contra linhas de base, validando em **sinalizante não visto no treino**.

### Fora do escopo (agora)

- Reconhecimento do sinal feito pelo usuário via câmera; classificador LSTM/CNN; feedback acerto/quase lá/erro.
- Gamificação, níveis e trilhas; dicionário consultável.
- Tela de consentimento LGPD **para captura de câmera** (não há captura do usuário no novo escopo — ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md) para o que ainda se aplica à privacidade).
- Expressão facial e gramática de Libras (ordem, uso do espaço): o MVP concatena sinais isolados na ordem do texto.
- Expansão do vocabulário além dos 20 sinais (V-LIBRASIL fica como possibilidade futura, com restrições de licença).
- Texto → glosa por modelo aprendido (corpus `pt-br2libras-gloss` reservado para etapa seguinte).

### O que sobrevive da fase 1

| Item da fase 1 | Situação no escopo atual |
| --- | --- |
| Problema (comunicação surdos–ouvintes, escassez de intérpretes) | Continua como motivação |
| Pesquisa documental e dados (IBGE, Inep etc.) | Continua válida como contexto |
| Personas (Júlia, Matheus, Helena) | Precisam ser **revisitadas**: foram desenhadas para um jogo de prática com câmera. Uma ferramenta texto → Libras serve de outra forma (ex.: Helena escrevendo uma instrução para o aluno surdo; Matheus como quem lê o resultado). [a confirmar com a equipe] |
| Análise de similares | Agora os similares **diretos** são Hand Talk, VLibras, ProDeaf (antes eram "lacuna"). O diferencial muda — ver [`04-analise-de-similares.md`](04-analise-de-similares.md) |
| Requisitos R01–R06 | R01, R02, R06 e parte de R03 deixam de se aplicar como escritos. Ver [`05-requisitos.md`](05-requisitos.md) |
| MediaPipe Holistic | Continua, mas só como **ferramenta de extração de keypoints dos vídeos de treino**, não mais para captura ao vivo |
| MINDS-Libras | Continua como fonte de dados, agora para treinar a **geração** de movimento |

## Pendências de alinhamento

- O texto das entregas (Entrega 1, proposta) ainda descreve o escopo antigo. Se houver nova entrega à disciplina, ela precisa refletir o pivô. [a confirmar com o professor o que será cobrado]
- Falta uma declaração de problema/hipótese reescrita para o escopo novo. Proposta de rascunho em [`06-ideacao-e-decisoes.md`](06-ideacao-e-decisoes.md#rascunho-de-hipótese-para-o-escopo-atual).
