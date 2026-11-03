# Checklist dos requisitos de ML (entregáveis CC)

Estes 10 entregáveis são os que **dão a nota** do projeto na parte de Machine Learning. O texto de cada um é o da disciplina, copiado sem alteração. Abaixo de cada um, os subitens são a nossa decomposição (proposta) e o mapeamento para as fases de [`22-plano-ml-texto-glosa.md`](22-plano-ml-texto-glosa.md).

**Como usar:** marque `[x]` só quando o item estiver feito **e verificável** (código no repositório, execução registrada, artefato existente). Ao marcar, anote a data e a evidência (arquivo, run do MLflow, commit). Mantenha o quadro-resumo em dia e reflita mudanças em [`15-estado-atual-e-proximos-passos.md`](15-estado-atual-e-proximos-passos.md).

## Fora do escopo: sistema embarcado e MQTT

**Decisão (Carlos, 2026-10-28; reconfirmada em 2026-11-02):** o requisito de **sistema embarcado** não faz parte do grupo, e por consequência o **broker MQTT** (que na rubrica serve só ao embarcado) também não entra. Motivo registrado: o embarcado não é do grupo; não foi dada outra justificativa técnica. A fonte de dados novos é a própria API (frases enviadas pela interface ou por um simulador de uso).

Nos textos dos entregáveis abaixo, os trechos ~~riscados~~ são os que ficam de fora. Não há subitens de embarcado/MQTT no checklist.

**Aprovado pelo orientador:** a abordagem por **glosa** (texto → glosa, com base no VLibras/VLibrasBD) é a forma mais adequada e é o caminho seguido, com base no nosso estudo.

## Orientação do orientador (reunião mais recente, anotada em 2026-11-02)

O orientador viu o relatório sobre português sinalizado e a melhor forma de converter português em Libras, **gostou muito** e **concordou em seguir a base de estudos do VLibras/VLibrasBD**. Deixou claro que:

1. devemos seguir os 10 requisitos acima;
2. o projeto tem que **mostrar com clareza onde aplicamos machine learning** e **documentar bem** como funciona a pipeline de ponta a ponta.

Isso vira um requisito transversal, o **R0**, que vale para todos os outros:

- [ ] **R0.1** (parcial: fases 1 e 2 em `24-pipeline-de-dados-ponta-a-ponta.md`; faltam treino, API e painel) Documento de arquitetura ponta a ponta (`references/` ou `docs/`): diagrama do fluxo texto → pré-processamento → classificador → glosa → avatar, com cada etapa dizendo se é **ML (treinado por nós)**, **regra/tabela** ou **externo** (ex.: player do VLibras, spaCy).
- [ ] **R0.2** Seção "Onde está o ML": qual tarefa de classificação, quais atributos, quais rótulos, quais modelos, onde o modelo decide algo na saída final.
- [ ] **R0.3** Cada etapa da pipeline com entrada, saída, onde roda (Airflow, notebook, API) e como reproduzir.
- [ ] **R0.4** README do repositório aponta para esse documento e para o checklist.
- [ ] **R0.5** (notebooks 01 a 04 feitos; faltam os DAGs) Notebooks e DAGs com texto explicando o que e por quê, não só código.
- [ ] **R0.6** Apresentação final percorre esse mesmo fluxo (liga com o entregável 10).

> Em 2026-11-02 o Carlos relatou que o orientador concordou que a glosa é a forma mais adequada. A formulação exata do modelo (classificação por palavra, T1) é escolha nossa dentro desse caminho e deve ser justificada no baseline (entregável 3).

## Quadro-resumo (atualizado em 2026-11-02, após as fases 1 e 2)

| # | Entregável | Fase do plano | Situação |
| --- | --- | --- | --- |
| 1 | Infraestrutura inicial + bootstrap dataset + persistência | 0, 1 | Parcial (corpus no Postgres; falta simulador de uso) |
| 2 | Pipeline de dados no Airflow + notebook de EDA e preparação | 1, 2, 7 | Parcial (notebooks e preparação prontos; falta Airflow e a conferência manual) |
| 3 | Modelo baseline + MLflow | 3 | **Feito** (2026-11-02): F1-macro 0,876 contra 0,822 da lista fixa |
| 4 | Três modelos comparados + gráficos + análise crítica | 4 | **Feito** (2026-11-02): Regressão Logística 0,876 > Árvore 0,870 > Random Forest 0,852 > KNN 0,846 |
| 5 | Otimização de hiperparâmetros (Optuna) | 5 | **Feito** (2026-11-02): Random Forest 0,852 → 0,884 |
| 6 | Validação cruzada e generalização | 6 | Não iniciado |
| 7 | Integração do modelo ao pipeline | 8 | Não iniciado |
| 8 | Conteinerização com Docker Compose | 9 | Parcial (`api`, `web`, `postgres` e `mlflow`) |
| 9 | Dashboard integrado | 10 | Não iniciado |
| 10 | Apresentação da solução completa | 11 | Não iniciado |

---

## 1. Infraestrutura inicial e bootstrap dataset

> Implementação da infraestrutura inicial da solução. A equipe deverá disponibilizar um conjunto de dados inicial (bootstrap dataset) que permita o desenvolvimento e validação da solução desde as primeiras etapas do projeto, ~~além de implementar a infraestrutura de aquisição de dados utilizando um sistema embarcado físico ou simulado. A solução deverá demonstrar a publicação dos dados por meio de MQTT (ou tecnologia equivalente), bem como sua recepção~~ e persistência em um mecanismo de armazenamento adequado.

- [x] Abordagem por glosa validada com o orientador (reunião, relatada em 2026-11-02)
- [x] Baixar o VLibrasBD (bootstrap dataset) e registrar hash/licença (2026-11-02; SHA-256 conferido; créditos em `docs/creditos-e-licencas.md`)
- [x] Banco (Postgres) e tabela do corpus criados (serviço `postgres` no compose; `corpus_bruto`, 127.349 linhas)
- [x] Script de ingestão do corpus no banco (`textgloss/ingest.py`)
- [ ] Simulador de uso que envia frases novas à API (fonte de dados novos no lugar do embarcado)
- [ ] Persistência das frases recebidas no banco

## 2. Pipeline de dados (Airflow) e EDA

> Implementação do pipeline de dados. A equipe deverá desenvolver um fluxo automatizado utilizando Apache Airflow para orquestrar as etapas de ingestão, preparação e disponibilização dos dados para treinamento do modelo. A entrega deverá incluir um notebook contendo a análise exploratória (EDA) do bootstrap dataset, as etapas de preparação dos dados (limpeza, normalização, encoding, tratamento de valores ausentes etc.) e a justificativa das principais decisões adotadas.

- [ ] DAG de ingestão (`vlibrasbd_ingestao`)
- [ ] DAG de preparação (`preparacao_t1`)
- [x] Notebook 01: EDA do VLibrasBD (`notebooks/01-eda-vlibrasbd.ipynb`, executado)
- [x] Notebook 02: preparação (limpeza, normalização, encoding, ausentes) com justificativas (`notebooks/02-preparacao.ipynb`, executado)
- [x] Rotulagem T1 por alinhamento de lemas (`textgloss/align.py`)
- [ ] Conferência manual de 200 rótulos e taxa de ruído (`data/processed/vlibrasbd/amostra_conferencia_200.csv`, aguarda a equipe)
- [x] Divisão treino/teste agrupada por frase (90/10, por domínio, semente fixa)
- [x] Dados preparados disponibilizados para o treino (`palavras.parquet` e tabela `palavras_t1`)

## 3. Modelo baseline

> Treinamento de um modelo baseline adequado ao problema definido (ex.: KNN, Regressão Linear, Regressão Logística ou Árvore de Decisão). A equipe deverá justificar a escolha do modelo, apresentar as métricas obtidas em um conjunto de validação e registrar parâmetros, métricas e artefatos do experimento utilizando MLflow.

- [x] Servidor MLflow no ar (serviço `mlflow` no compose, backend Postgres, http://localhost:5000)
- [x] Regressão Logística treinada (e lista fixa como referência sem ML): `python -m textgloss.train baseline`
- [x] Justificativa escrita da escolha (`references/25-baseline-t1.md`)
- [x] Métricas em conjunto de validação (F1-macro 0,876; ROC-AUC 0,944)
- [x] Parâmetros, métricas e artefatos registrados no MLflow (experimento `t1-manter-descartar`)

## 4. Comparação de modelos

> Treinamento e comparação de, no mínimo, três modelos distintos, utilizando as métricas previamente definidas. Todos os experimentos deverão ser registrados no MLflow. A entrega deverá incluir visualizações adequadas ao problema (matriz de confusão, curvas ROC/AUC, gráficos de erro, resíduos etc.) e uma análise crítica comparando o desempenho dos modelos avaliados.

- [x] Métricas definidas antes dos experimentos (F1-macro principal; ROC-AUC, PR-AUC, revocação por classe; definidas em `22-plano-ml-texto-glosa.md`)
- [x] Árvore de Decisão treinada e registrada
- [x] Random Forest treinado e registrado
- [x] KNN treinado e registrado
- [x] Matriz de confusão por modelo
- [x] Curvas ROC/AUC (e PR)
- [x] Gráficos de erro (F1 por classe gramatical, lemas e exemplos de erro, coincidência de erros entre modelos)
- [x] Notebook 03: análise crítica comparando os modelos (`notebooks/03-comparacao-modelos.ipynb`; resumo em `26-comparacao-de-modelos-t1.md`)

## 5. Otimização de hiperparâmetros

> Aplicação de técnicas de otimização de hiperparâmetros (Grid Search, Random Search ou Otimização Bayesiana com Optuna) sobre o modelo selecionado. A equipe deverá documentar a estratégia adotada, os parâmetros avaliados, os resultados obtidos e registrar todos os experimentos no MLflow.

- [x] Modelo a otimizar escolhido (Random Forest, decisão do grupo em 2026-11-02: mais hiperparâmetros e longe do limite)
- [x] Estudo Optuna rodado (TPE, 25 tentativas, CV agrupada de 3 dobras)
- [x] Todos os trials registrados no MLflow (run pai `optuna-random-forest` e 25 filhas)
- [x] Documento: estratégia, espaço de busca, resultados (`27-otimizacao-random-forest.md` e `notebooks/04-otimizacao-random-forest.ipynb`)

## 6. Validação cruzada e generalização

> Avaliação do modelo utilizando validação cruzada (k-fold ou stratified k-fold, quando aplicável), acompanhada de análise da estabilidade dos resultados, identificação de evidências de overfitting ou underfitting e discussão da capacidade de generalização do modelo.

- [ ] `StratifiedGroupKFold` (agrupado por frase) executado
- [ ] Estabilidade entre dobras (média, desvio)
- [ ] Curva de aprendizado / evidências de overfitting ou underfitting
- [ ] Teste fora do domínio
- [ ] Teste final no conjunto separado
- [ ] Discussão escrita de generalização

## 7. Integração do modelo ao pipeline

> Integração do modelo treinado à infraestrutura de aquisição de dados. A equipe deverá integrar o modelo treinado à infraestrutura de aquisição de dados, demonstrando que o pipeline é capaz de consumir automaticamente novos dados ~~provenientes do sistema embarcado (ou~~ simulador~~)~~, executar as etapas de processamento necessárias e produzir inferências utilizando o modelo validado.

- [ ] Modelo carregado do MLflow pela API
- [ ] Classificador em `textgloss/infer.py` usado no `/translate`
- [ ] Frases novas (do simulador) gravadas no banco
- [ ] DAG `monitoramento` consome novas frases, processa e grava inferências
- [ ] Demonstração automática ponta a ponta

## 8. Conteinerização (Docker Compose)

> Conteinerização da solução utilizando Docker Compose. A equipe deverá disponibilizar um ambiente reproduzível contendo os principais serviços da arquitetura (~~broker MQTT,~~ banco de dados, Airflow, MLflow, API e demais componentes necessários), permitindo a execução completa da solução por meio de um único comando.

- [x] Serviços `api` e `web` (verificado em 2026-10-19; falta reverificar com a versão final)
- [x] `postgres` (compose, healthcheck; 2026-11-02)
- [x] `mlflow` (compose, backend no Postgres; 2026-11-02)
- [ ] `airflow`
- [ ] `dashboard`
- [ ] Um único comando sobe tudo, testado em máquina limpa

## 9. Dashboard

> Desenvolvimento de um dashboard integrado à solução, capaz de consumir dados provenientes da infraestrutura de aquisição (~~via MQTT e/ou~~ API), apresentar indicadores relevantes da aplicação, visualizar as inferências realizadas pelo modelo e monitorar o funcionamento da solução em tempo de execução.

- [ ] Painel (Streamlit) consumindo API e banco
- [ ] Indicadores relevantes da aplicação
- [ ] Visualização das inferências do modelo
- [ ] Versão do modelo e métricas do último treino (lidas do MLflow)
- [ ] Estado dos serviços (API, banco, MLflow) em tempo de execução

## 10. Apresentação da solução completa

> Apresentação da solução completa, demonstrando o funcionamento integrado de toda a arquitetura: ~~aquisição dos dados pelo sistema embarcado, comunicação via MQTT,~~ armazenamento, orquestração do pipeline com Apache Airflow, treinamento e rastreamento de experimentos com MLflow, implantação da solução utilizando Docker Compose, disponibilização das inferências por meio da API e visualização dos resultados no dashboard. A equipe deverá justificar as principais decisões técnicas e discutir as limitações da solução.

- [ ] Roteiro da demonstração ponta a ponta
- [ ] Ensaio com `docker compose up` do zero
- [ ] Justificativa das decisões técnicas
- [ ] Limitações discutidas (ordem dos sinais, ausência de validação por pessoas surdas, ruído da rotulagem, escopo sem embarcado/MQTT e o porquê)
- [ ] Slides/apresentação pronta
