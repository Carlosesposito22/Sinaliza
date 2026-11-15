# Requisitos da cadeira de Aprendizado de Máquina (AM), 2026.6, unidade 2

O Sinaliza é orientado por duas cadeiras: **Projetos 6** (requisitos de ML em [`23-checklist-requisitos-ml.md`](23-checklist-requisitos-ml.md), recebidos no onboarding) e **Aprendizado de Máquina** (este arquivo, recebido em 2026-11-14). O cruzamento entre os dois e o que falta estão em [`33-cruzamento-requisitos-am.md`](33-cruzamento-requisitos-am.md). As regras de formatação do relatório estão em [`32-template-sbc.md`](32-template-sbc.md).

Fontes (originais, guardados no repositório):

- [`../Documentos/Aprendizado de Maquina/AM - Especificacao de Projeto (2026.6, unidade 2).pdf`](../Documentos/Aprendizado%20de%20Maquina/) — especificação do projeto (4 páginas).
- [`../Documentos/Aprendizado de Maquina/sbc_template.pdf`](../Documentos/Aprendizado%20de%20Maquina/) — modelo do relatório (template SBC).

O texto abaixo é a transcrição fiel dos dois. Nada foi resumido nem alterado; só a formatação virou Markdown.

---

## Mensagem do professor (enviada com os anexos)

> Pessoal,
>
> De acordo com o plano de ensino, 60% da nota da unidade será composta pelos entregáveis do Projeto 6, que consiste na construção de uma solução completa de Machine Learning, incluindo etapas de análise de dados, modelagem e integração com práticas de MLOps.
>
> Para quem está matriculado em Projeto 6, este documento replica a lista de requisitos definidos ainda no onboarding. Para quem não está em Projeto 6, este documento serve como especificação para desenvolvimento do projeto.
>
> É fundamental que vocês estejam atentos aos requisitos definidos no enunciado do projeto, especialmente no que diz respeito à integração da solução. Componentes como rastreamento de experimentos com MLflow, disponibilização via dashboard (ex: Streamlit ou Dash) e execução em ambiente Docker são obrigatórios e condicionam a validade da entrega.
>
> Reforço que não será avaliada apenas a presença desses elementos, mas principalmente a qualidade da implementação, a coerência metodológica e a integração entre as etapas do projeto.
>
> Importante: estudantes que não estiverem cursando o Projeto 6 desenvolverão a atividade a partir de um tema pré-definido, devendo atender aos mesmos requisitos técnicos e critérios de avaliação.
>
> Em anexo, segue também o modelo do relatório.
>
> Informes
>
> - Informe 1: Segue em anexo o documento com os critérios de avaliação e requisitos adicionais da disciplina.
> - Informe 2: Os requisitos de Projeto 6 foram previamente disponibilizado pelos orientadores de projetos. Qualquer dúvida, me reportem.
>
> Em caso de dúvidas, tragam para discussão em sala. ;)

---

## Especificação de Projeto

**DISCIPLINA:** Aprendizado de Máquina · **PERÍODO:** 2026.6 · **UNIDADE:** 2a · CESAR School

### 1. Introdução

Este projeto visa o desenvolvimento de uma solução completa de aprendizado de máquina, contemplando desde a análise exploratória de dados até a disponibilização da solução em ambiente replicável.

O objetivo é aplicar conceitos de modelagem, validação e análise de dados, aliados a práticas de MLOps, incluindo rastreamento de experimentos, deploy de modelos e reprodutibilidade do ambiente.

O projeto deverá ser desenvolvido em grupos e corresponde a 60% da nota da segunda unidade, sendo avaliado com base na qualidade técnica da solução e na apresentação final.

### 2. Objetivos

Desenvolver uma solução de Machine Learning que atenda aos seguintes requisitos:

- Leitura e análise exploratória de dados (EDA)
- Construção de visualizações analíticas
- Aplicação de estratégias de validação
- Treinamento e comparação de modelos de ML
- Rastreamento de experimentos com MLflow
- Infraestrutura de aquisição de dados com sistema embarcado (físico ou simulado) e comunicação via MQTT
- Orquestração do pipeline de dados com Apache Airflow
- Integração do modelo ao pipeline e disponibilização de inferências por meio de API
- Desenvolvimento de dashboard interativo (ex: Streamlit, Dash, Google Looker)
- Conteinerização da solução com Docker

### 3. Avaliação

#### 3.1. Critérios de Avaliação

A avaliação do projeto será baseada nos seguintes critérios:

- Qualidade da análise de dados (EDA)
- Clareza e relevância das visualizações
- Correção metodológica das estratégias de validação
- Qualidade da modelagem e escolha de métricas
- Uso adequado de ferramentas de MLOps
- Funcionalidade do dashboard
- Infraestrutura de aquisição, comunicação MQTT e pipeline de dados (Airflow)
- Integração do modelo ao pipeline e disponibilização de inferências via API
- Reprodutibilidade via Docker
- Clareza e organização do relatório (**uso obrigatório do template SBC anexo**)

> **ATENÇÃO! Relatórios entregues fora do formato SBC (template anexo) não serão aceitos, penalizando com nota 0 no item Comunicação.**

Dessa forma, a nota final será calculada com base nos seguintes blocos e respectivos pesos:

| Bloco | Peso |
| --- | --- |
| Análise de Dados | 15% |
| Modelagem e Validação | 30% |
| MLOps (integração) | 25% |
| Comunicação (clareza no relatório) | 20% |

> Observação nossa (não está no PDF): os pesos somam 90%. Perguntar ao professor de onde vêm os 10% restantes (provavelmente a apresentação final, citada na Introdução).

### 4. Requisitos Técnicos

O projeto deverá atender aos seguintes requisitos:

- **Dados e Análise**: Leitura de base de dados (bootstrap dataset); EDA em notebook; Estatísticas descritivas; Tratamento de dados (limpeza, normalização, encoding, valores ausentes etc.) com justificativa das decisões.
- **Visualização**: Mínimo de 5 visualizações com interpretação
- **Validação**: Holdout; Validação cruzada (k-fold ou stratified k-fold, quando aplicável); Leave-One-Out (quando aplicável), com análise de estabilidade dos resultados, de overfitting/underfitting e da capacidade de generalização. Otimização de hiperparâmetros com Grid Search, Random Search e/ou Optuna, documentando estratégia, parâmetros avaliados e resultados. Deve ser justificada a estratégia escolhida.
- **Modelagem**: Treinamento de um modelo baseline adequado ao problema (ex.: KNN, Regressão Linear, Regressão Logística ou Árvore de Decisão), com justificativa e métricas em conjunto de validação; e treinamento e comparação de pelo menos três modelos distintos usando métricas apropriadas e previamente definidas: KNN; Árvore de Decisão; Random Forest, AdaBoost, Multilayer Perceptron. A comparação deve incluir visualizações adequadas ao problema (matriz de confusão, metricas para classificação, regressão ou agrupamentos, gráficos de erro, resíduos etc.) e análise crítica. É permitido usar um modelo adicional não discutido na disciplina **(importante validar com o professor antes).**
- **MLflow**: Registro de parâmetros; Registro de métricas; Registro de artefatos; Múltiplos experimentos (baseline, comparação de modelos e otimização de hiperparâmetros); Salvamento do modelo.
- **Dashboard**: Interface interativa integrada à solução; Consumo de dados da infraestrutura de aquisição (via MQTT e/ou API); Indicadores relevantes da aplicação; Visualização de métricas; Visualização das previsões/inferências do modelo; Monitoramento do funcionamento da solução em tempo de execução. Não só podem como devem incluir métricas relacionadas à solução apresentada em Projeto 6.
- **Aquisição de Dados e MQTT**: Sistema embarcado físico ou simulado; Publicação dos dados via MQTT (ou tecnologia equivalente); Recepção e persistência em mecanismo de armazenamento adequado.
- **Pipeline de Dados**: Fluxo automatizado com Apache Airflow (ingestão, preparação e disponibilização dos dados para treinamento); Notebook com EDA do bootstrap dataset e das etapas de preparação.
- **Integração e API**: Integração do modelo validado ao pipeline, com consumo automático de novos dados, processamento e geração de inferências; Disponibilização das inferências por meio de API.
- **Conteinerização**: Docker Compose com os principais serviços (broker MQTT, banco de dados, Airflow, MLflow, API, dashboard e demais componentes), com execução completa por meio de um único comando.
- **Apresentação Final**: Demonstração do funcionamento integrado de toda a arquitetura (aquisição pelo sistema embarcado, comunicação via MQTT, armazenamento, orquestração com Airflow, treinamento e rastreamento com MLflow, implantação com Docker Compose, inferências via API e visualização no dashboard), com justificativa das principais decisões técnicas e discussão das limitações da solução.

### 5. Relatório

O relatório do projeto deverá documentar a solução desenvolvida, as decisões técnicas tomadas e os resultados obtidos, incluindo as limitações da solução.

Formato obrigatório: SBC. O relatório deve ser elaborado obrigatoriamente no template da Sociedade Brasileira de Computação (SBC) anexo a esta especificação, sem alterações de margens, fontes, espaçamento ou número de colunas. Será considerado fora do formato SBC qualquer relatório que não utilize o template anexo, inclusive documentos em formato livre (Word, Google Docs etc.).

### 6. Estrutura do Repositório

A estrutura sugerida de pastas para o repositório no Github é apresentada a seguir. No entanto, ajustes podem ser aplicados para atender a proposta de cada grupo:

```
/
├── data/                # Dados
├── notebooks/           # EDA e experimentos
├── src/                 # Código de treinamento
├── embedded/            # Firmware ou simulador do sistema embarcado
├── dags/                # DAGs do Apache Airflow
├── api/                 # API de inferência
├── app/                 # Dashboard
├── mlruns/              # MLflow
├── Dockerfile
├── docker-compose.yml   # Execução completa da solução (um único comando)
├── reports/             # Relatório em PDF (formato SBC)
├── requirements.txt
├── README.md
```

O arquivo `README.md` deverá conter as seguintes informações:

1. Nome e sobrenome dos membros do projeto e seus respectivos **usuários no GitHub (@fulano, @beltrano, @sicrano)**.
2. Nome da solução desenvolvida (sejam criativos).
3. Instruções detalhadas para compilar e executar.
4. Breve descrição da solução, incluindo link para o Google Sites do projeto.

**Bom trabalho!**
