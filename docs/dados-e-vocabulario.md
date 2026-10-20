# Fonte de dados e vocabulário do MVP

Decisão registrada em 2026-10-14. Licenças e tamanhos foram conferidos nas páginas de cada fonte nessa data.

## Decisão

1. **Dados de movimento (gloss → pose):** MINDS-Libras, usando os 20 sinais como vocabulário fechado do MVP.
2. **Expansão (decidida em 2026-10-19):** acrescentar o **V-LIBRASIL** (1.364 sinais, 3 sinalizantes; só pesquisa e ensino, sem redistribuição) ao MINDS-Libras. O Apoema-Libras560 foi descartado. **O Carlos baixou só o V-LIBRASIL** (o MINDS é pesado demais), que fica **só na máquina dele, fora do repositório** (`C:\Users\Carlos\Desktop\Projetos 6\Datasets`); não se versionam vídeos nem keypoints. Detalhes em `references/21-datasets-de-treino.md`.
3. **Texto → gloss:** no MVP, por tabela (`data/vocabulary.json`). O corpus `pt-br2libras-gloss` fica reservado para uma etapa seguinte, com modelo aprendido.

## Por que MINDS-Libras

| Critério | MINDS-Libras |
| --- | --- |
| Licença | CC BY 4.0, acesso aberto, sem cadastro. Permite uso e redistribuição com atribuição. |
| Conteúdo | 20 sinais, 12 sinalizantes, 5 repetições cada, fundo chroma key, MP4 1920×1080 a 30 fps |
| Tamanho | 12 arquivos ZIP, 64,8 GB no total (um por sinalizante, de 2,5 a 8,4 GB) |
| Ajuste ao projeto | Boa quantidade de repetições por sinal e vários sinalizantes, o que permite validar em sinalizante não visto no treino |
| Lacunas | Sinalizantes 3, 4 e 9 não gravaram todos os sinais; o 7 tem gravações extras |

Fonte: [Zenodo, registro 2667329](https://zenodo.org/records/2667329).

### Subconjunto inicial

Não é preciso baixar os 64,8 GB. Para começar, os sinalizantes **01, 02, 07 e 10** somam cerca de 16,3 GB (4,4 + 4,7 + 2,5 + 4,7) e dão quatro sinalizantes, o mínimo razoável para separar treino e validação por pessoa. Os demais entram se o tempo de processamento e o disco permitirem.

## Por que não as outras fontes (por enquanto)

| Fonte | Conteúdo | Motivo |
| --- | --- | --- |
| [V-LIBRASIL](https://ieee-dataport.org/documents/v-librasil-new-dataset-signs-brazilian-sign-language-libras) | 1.364 termos, 3 articuladores, 4.089 vídeos | Uso só para pesquisa e educação; **não pode ser redistribuído sem permissão**; uso comercial exige autorização. A página do IEEE DataPort pede assinatura; o site `libras.cin.ufpe.br` oferece a aba de download. Melhor candidato para ampliar o vocabulário. |
| [pt-br2libras-gloss](https://data.mendeley.com/datasets/ryj88ckjww/2) | 127.349 pares português ↔ gloss | CC BY-SA 4.0. É texto, não movimento. Serve para treinar texto → gloss. A convenção de glosas não é detalhada na página. |
| Libras-UFPel Corpus | 4.800 registros (2.400 frases e 2.400 sinais isolados), 4 sinalizantes surdos nativos | Não encontrei link de download nem licença. Vale pedir aos autores: é o único com frases. |
| LIBRAS-UFOP | 56 sinais com RGB-D e esqueleto | Não encontrei autores nem link de acesso. |

## Vocabulário do MVP

Os 20 sinais, em [`data/vocabulary.json`](../data/vocabulary.json), com formas em português e contextos:

| Contexto (proposta) | Sinais |
| --- | --- |
| Escola | ALUNO, BANHEIRO, FILHO |
| Saúde | VACINA, MEDO, RUIM, VONTADE, BANHEIRO, FILHO |
| Serviços | BANCO |
| Geral | ACONTECER, AMARELO, AMÉRICA, APROVEITAR, BALA, BARULHO, CINCO, CONHECER, ESPELHO, ESQUINA, MAÇÃ, SAPO |

Frases de demonstração que usam só esse vocabulário:

- "O filho tem medo da vacina" → FILHO MEDO VACINA
- "O aluno quer ir ao banheiro" → ALUNO BANHEIRO
- "Eu quero conhecer a América" → CONHECER AMÉRICA

## Limites que precisam ficar explícitos

- **Isso não é tradução para Libras.** Libras tem gramática própria (ordem, uso do espaço, expressão facial). O MVP converte palavras do português em uma sequência de sinais isolados na ordem do texto. Nas demonstrações, chamar de "sequência de sinais".
- **Palavras fora do vocabulário** são ignoradas (artigos, preposições e verbos de ligação nas frases acima). Definir o comportamento (aviso ao usuário ou soletração) antes de expor ao público.
- **Polissemia:** "banco" (financeiro ou de sentar) e "bala" (doce ou projétil). O sinal gravado é um só; o mapeamento por palavra acerta só um dos sentidos.
- **Validação linguística:** o grupo não tem falante de Libras. Os contextos e as formas em `vocabulary.json` são propostas. Quem validar isso (professor, intérprete, pessoa surda) precisa ser identificado antes da avaliação com usuários.
- **Licença dos derivados:**
  - MINDS-Libras (CC BY 4.0): keypoints extraídos podem ser versionados com atribuição.
  - V-LIBRASIL: não versionar vídeos nem keypoints derivados sem permissão.
  - pt-br2libras-gloss (CC BY-SA 4.0): confirmar com o professor o efeito do share-alike sobre modelos treinados nele.

## Ferramentas de extração e licença

A extração de keypoints usa **YOLOv8 + MediaPipe Holistic**: o YOLOv8 localiza a pessoa e recorta o vídeo, o MediaPipe extrai pose e mãos no recorte (ver [`data/README.md`](../data/README.md)).

- **Ultralytics (YOLOv8): AGPL-3.0**, com licença Enterprise paga como alternativa (conferido em github.com/ultralytics/ultralytics em 2026-10-19). Aqui ele roda **só offline, na preparação dos dados**; a API e o front não o usam. Os keypoints gerados são dados nossos, não código da Ultralytics. Se o projeto algum dia distribuir ou servir o Ultralytics (por exemplo, detecção na API), reavaliar a AGPL com o professor.
- **MediaPipe: Apache-2.0.** [conhecimento geral, não conferido nesta data]
- **Não usamos modelo de mãos do YOLO.** A Ultralytics tem um dataset de *hand keypoints* (21 pontos, CC BY-NC-SA 4.0), mas os rótulos dele foram gerados pelo próprio MediaPipe e não há modelo pré-treinado oficial: treinar um seria imitar o MediaPipe, com licença NC-SA. O YOLOv8 entra só como detector de **pessoa** (classe `person` do COCO, pesos `yolov8n.pt` pré-treinados).

## Como isso vira ML

Com 20 classes e cerca de 60 gravações por classe, o MVP treina um **gerador de movimento condicionado ao sinal**, validando em sinalizante que não apareceu no treino. A linha de base é a recuperação: tomar a gravação mais representativa de cada sinal e concatenar. O modelo só se justifica se superar essa linha de base em uma métrica objetiva (por exemplo, distância DTW para as gravações de um sinalizante não visto). Essa métrica mede fidelidade ao movimento gravado, **não** correção linguística.
