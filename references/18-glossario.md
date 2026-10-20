# Glossário

## Libras e linguística

| Termo | Significado no projeto |
| --- | --- |
| **Libras** | Língua Brasileira de Sinais. Língua com gramática própria (não é português sinalizado) |
| **Sinal** | Unidade lexical de Libras (equivalente aproximado a uma palavra) |
| **Glosa (gloss)** | Rótulo escrito, em maiúsculas, que representa um sinal (`FILHO`). É a etapa intermediária entre texto e movimento. Não é tradução: é um nome de sinal |
| **Datilologia** | Soletração letra a letra com o alfabeto manual. Usada por tradutores para palavras sem sinal; considerada tradução de menor qualidade quando abusada |
| **Sinalizante (signer)** | Pessoa que faz os sinais num vídeo do dataset (12 no MINDS-Libras) |
| **Surdo / deficiente auditivo** | A documentação usa "surdos" e "pessoas com deficiência auditiva". Tratar com cuidado: nem toda pessoa com dificuldade para ouvir usa Libras (só 2,6% declaram saber) |
| **Expressão facial / não manual** | Parte da gramática de Libras (negação, pergunta, intensidade). **Fora** do formato de pose atual |
| **Letramento** | Domínio da língua escrita; surdos frequentemente têm o português como segunda língua |
| **Intérprete** | Profissional que traduz entre Libras e português; escasso em escolas, saúde e trabalho |

## Sistemas e produtos

| Termo | Significado |
| --- | --- |
| **Hand Talk, VLibras, ProDeaf** | Tradutores texto/voz → Libras com avatar 3D. Ver [`04-analise-de-similares.md`](04-analise-de-similares.md) |
| **Libras Aventura** | Jogo que reconhece o alfabeto com sensores de movimento |
| **MINDS-Libras** | Dataset aberto (CC BY 4.0): 20 sinais, 12 sinalizantes, 5 repetições, 1080p/30 fps |
| **V-LIBRASIL** | Dataset de 1.364 sinais; uso restrito (sem redistribuição) |
| **pt-br2libras-gloss** | Corpus de 127.349 pares português ↔ glosa (texto) |
| **E.I.T.A! Recife / Summer Job** | Programas de inovação aberta da Prefeitura do Recife citados na pesquisa documental |

## ML e visão computacional

| Termo | Significado |
| --- | --- |
| **MediaPipe Holistic** | Biblioteca do Google que extrai pose (33), mãos (21+21) e rosto (468) de vídeo. Aqui usada **só na extração dos dados de treino** (versão 0.10.21) |
| **Keypoint / landmark** | Ponto articular com coordenadas `(x, y, z)` |
| **Formato de pose** | Contrato do projeto: 75 keypoints por frame, normalizados. Ver [`08-formato-de-pose.md`](08-formato-de-pose.md) |
| **Normalização** | Origem nos quadris, largura dos ombros = 1, `y` para cima |
| **DTW (Dynamic Time Warping)** | Distância entre sequências que tolera diferenças de velocidade. Métrica de avaliação do projeto; mede fidelidade ao movimento gravado, não correção linguística |
| **Medoide** | Dentre as gravações de um sinal, a mais central (menor soma de DTW às demais). Linha de base de **recuperação** |
| **Linha de base (baseline)** | Método simples sem (ou com pouco) aprendizado que o modelo precisa superar para se justificar |
| **Recuperação (retrieval)** | Em vez de gerar, devolver uma gravação existente |
| **Split por sinalizante** | Validar em pessoas que não aparecem no treino, para medir generalização |
| **Gerador de movimento** | Modelo que, dado um sinal, produz a sequência de keypoints (`MotionGenerator`) |
| **GRU** | Rede recorrente usada no gerador |
| **Retargeting** | Mapear keypoints para os ossos de um avatar com rig |
| **GLB** | Formato de modelo 3D (glTF binário) para o avatar futuro |
| **Stub** | Implementação provisória (`StubGenerator`): valida o fluxo, não tem conteúdo real |
| **Coarticulação** | Influência de um sinal sobre o início/fim do vizinho; é o que torna "concatenar" artificial |

## Disciplina e metodologia

| Termo | Significado |
| --- | --- |
| **Projetos 6** | Disciplina do curso; Grupo 10 |
| **Protopersona** | Persona-hipótese, a validar com usuários reais |
| **MoSCoW** | Must / Should / Could / Won't — priorização usada na ideação |
| **CSD** | Certezas / Suposições / Dúvidas — classificação da Matriz de Pesquisa |
| **LGPD** | Lei Geral de Proteção de Dados; trata dado biométrico como sensível |
| **MVP** | Versão mínima: 20 sinais, texto → sequência de sinais por avatar |
