# Fonte de dados e vocabulário do MVP

Decisão inicial de 2026-10-14 (MINDS-Libras, 20 sinais), **revista em 2026-10-19/20**: o MINDS-Libras não foi baixado (64,8 GB) e o treino passou a usar o **V-LIBRASIL**, com um vocabulário curado. Detalhes e situação de acesso em [`references/21-datasets-de-treino.md`](../references/21-datasets-de-treino.md).

## Decisão

1. **Dados de movimento (glosa → pose):** **V-LIBRASIL** (UFPE): 1.364 sinais, 3 sinalizantes ("articuladores"), 4.086 vídeos baixados (faltam 3 que o portal listou como erro), 1080p, da cintura para cima. Uso **só para pesquisa e ensino**, **sem redistribuição**: os vídeos ficam só na máquina do Carlos, em `C:\Users\Carlos\Desktop\Projetos 6\Datasets`, fora do repositório, e **não se versionam vídeos nem keypoints derivados**.
2. **Vocabulário do MVP:** um **subconjunto curado de 210 sinais** do V-LIBRASIL, escolhidos pelas categorias do projeto (escola, saúde, serviços, trabalho, família, geral). A curadoria é só de **palavras em português**; os rótulos não foram validados por falante de Libras. Gerado por [`data/build_vocabulary.py`](../data/build_vocabulary.py) em [`data/vocabulary.json`](../data/vocabulary.json).
3. **Texto → glosa:** por tabela de formas em português, **lematizador** (simplemma) e, como último recurso, **embeddings** de palavra, sempre sinalizados ao usuário.
4. **Descartados:** o Apoema-Libras560 (decisão do grupo). Em reserva: o Libras-UFPel Corpus (ainda não liberado). O MINDS-Libras (CC BY 4.0, 20 sinais, 12 sinalizantes) segue como opção, e o vocabulário antigo está em `data/vocabulary-minds.json`.

## O V-LIBRASIL

| Item | Valor |
| --- | --- |
| Fonte | UFPE, `libras.cin.ufpe.br`; DOI 10.21227/v589-hn68; citar a dissertação de Ailton Rodrigues (2021) |
| Conteúdo | 1.364 sinais, 3 sinalizantes; 1.358 sinais com as 3 gravações, 6 com 2 |
| Origem dos termos | Extraídos do dataset de ASL (ASLLVD) e traduzidos: **não são, necessariamente, o léxico natural de Libras** |
| Vídeo | Quase todos 1920×1080, 30 a 60 fps, 3 a 9 s; enquadramento da cintura para cima |
| Variantes | 68 classes têm desambiguação entre parênteses (`Batida (ritmo)`); "Avó" e "Avô" colidem se o casamento ignorar acentos |
| Uso | Pesquisa e educação; **sem redistribuição**; sem uso comercial |

## Vocabulário do MVP (210 sinais)

Escola 37, saúde 37, serviços 36, trabalho 24, família 30, geral 72 (um sinal pode estar em mais de um contexto). Cada sinal tem a glosa, o nome da classe no V-LIBRASIL (`video_class`), as formas em português (`pt`), os contextos e, às vezes, uma nota. Formas de várias palavras ("dor de cabeça", "por favor", "com licença") são aceitas. Há **57 frases de exemplo** por categoria em [`data/phrases.json`](../data/phrases.json), geradas por modelos de frase e validadas contra o vocabulário.

Exemplos: "O filho está com dor de cabeça" → FILHO · DOR DE CABEÇA; "A médica pagou o remédio" → MÉDICO · PAGAR · MEDICAMENTO; "A criança tem medo do hospital" → CRIANÇA · TER · COM MEDO · HOSPITAL.

Os 20 sinais do MINDS-Libras que o MVP tinha antes **não** estão todos no V-LIBRASIL: só 7 têm o mesmo nome (ACONTECER, AMARELO, BANHEIRO, BARULHO, ESPELHO, FILHO e RUIM).

## Limites que precisam ficar explícitos

- **Isso não é tradução para Libras.** Libras tem gramática própria (ordem, uso do espaço, expressão facial). O MVP converte palavras do português em uma sequência de sinais isolados na ordem do texto. Nas demonstrações, chamar de "sequência de sinais".
- **Palavras fora do vocabulário:** cada palavra é classificada como `exact` (tabela ou lema), `approx` (embedding, sinalizado com "~"), `function` (artigo, preposição...) ou `ignored` (riscada, com aviso). Não há soletração: nem o V-LIBRASIL nem o MINDS têm o alfabeto manual como vídeos de movimento contínuo (o V-LIBRASIL tem as letras como classes, mas não as usamos).
- **Polissemia:** o sinal gravado é um só por classe; o mapeamento por palavra acerta só um dos sentidos ("sapo" vira RÃ; "medo" vira COM MEDO).
- **Verbos e conjugação:** "tem" vira o sinal TER, o que não corresponde à gramática de Libras.
- **Validação linguística:** o grupo não tem falante de Libras. As formas, os contextos e a escolha dos 210 sinais são propostas. Quem validar (professor, intérprete, pessoa surda) precisa ser identificado antes da avaliação com usuários.
- **Só 3 sinalizantes e uma gravação de cada por sinal:** serve para recuperação e vocabulário; validar em pessoa nova usa só 3 pessoas.
- **Licença dos derivados:** V-LIBRASIL: não versionar vídeos nem keypoints derivados; MINDS-Libras (CC BY 4.0, se for usado): keypoints podem ser versionados com atribuição; pt-br2libras-gloss (CC BY-SA 4.0, não usado ainda): confirmar com o professor o efeito do share-alike sobre modelos treinados nele.

## Ferramentas de extração e licença

A extração de keypoints usa **MediaPipe Holistic** e, **quando a pessoa é pequena no quadro**, o **YOLOv8** para recortá-la antes (ver [`data/README.md`](../data/README.md)). **No V-LIBRASIL o YOLOv8 não ajudou** (a pessoa já ocupa o quadro), e o padrão do comando é desligado.

- **Ultralytics (YOLOv8): AGPL-3.0**, com licença Enterprise paga como alternativa (conferido em github.com/ultralytics/ultralytics em 2026-10-19). Roda **só offline, na preparação dos dados**; a API e o front não o usam. Se o projeto algum dia distribuir ou servir o Ultralytics, reavaliar a AGPL com o professor.
- **MediaPipe: Apache-2.0.** [conhecimento geral, não conferido]
- **simplemma** (lematizador, usado na API): licença MIT. [conhecimento geral, não conferido]
- **Não usamos modelo de mãos do YOLO:** o dataset de *hand keypoints* da Ultralytics é CC BY-NC-SA 4.0 e os rótulos foram gerados pelo próprio MediaPipe.

## Como isso vira ML

Com 210 classes e 2 ou 3 gravações por classe (uma por sinalizante), o MVP compara **linhas de base de recuperação** (a gravação mais central, a média por sinal) com um **gerador de movimento condicionado ao sinal**, validando em um sinalizante deixado de fora. O modelo só se justifica se superar a recuperação em uma métrica objetiva (distância DTW). Essa métrica mede fidelidade ao movimento gravado, **não** correção linguística.
