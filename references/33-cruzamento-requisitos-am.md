# Cruzamento: requisitos de AM × o que o Sinaliza já tem (2026-11-14)

Compara a especificação da cadeira de **Aprendizado de Máquina** ([`31-requisitos-cadeira-am.md`](31-requisitos-cadeira-am.md)) com os 10 entregáveis de **Projetos 6** ([`23-checklist-requisitos-ml.md`](23-checklist-requisitos-ml.md)) e com o estado do repositório em 2026-11-14 (commit `574f00c`).

Legenda: ✅ cumprido e verificável · 🟡 parcial ou a conferir · ❌ falta.

## Resumo

As duas listas técnicas são praticamente a mesma (o professor diz que a de AM "replica" a de Projetos 6). O que a de AM **acrescenta**: o **relatório no template SBC** (20% da nota, zero se fora do formato), **Leave-One-Out** e **Grid/Random Search** citados explicitamente, **mínimo de 5 visualizações**, **regras do README** e a **estrutura de repositório sugerida**. E ela torna mais difícil defender o corte do **embarcado + MQTT**, que aparece em 4 lugares: objetivos, critérios de avaliação, Docker Compose e apresentação final.

| Bloco (peso) | Situação | O que falta |
| --- | --- | --- |
| Análise de Dados (15%) | ✅ (2026-11-14) | Nada |
| Modelagem e Validação (30%) | ✅ completo (2026-11-14) | Nada técnico. Falta só levar ao relatório SBC |
| MLOps (25%) | 🟡 | **Embarcado simulado + MQTT** (broker no compose); conferir "múltiplos experimentos" no MLflow; perfil `completo` |
| Comunicação (20%) | ❌ | **Relatório no template SBC não existe** |
| (10% não declarados) | ? | Os pesos somam 90%; provavelmente a apresentação final. Perguntar ao professor |

## Item a item

### Dados e Análise

| Requisito de AM | Situação | Evidência / o que falta |
| --- | --- | --- |
| Leitura do bootstrap dataset | ✅ | VLibrasBD, 127.349 linhas no Postgres, hash conferido (`textgloss/ingest.py`, DAG `vlibrasbd_ingestao`) |
| EDA em notebook | ✅ | `notebooks/01-eda-vlibrasbd.ipynb` |
| Estatísticas descritivas | ✅ | Seção 1.1 do notebook 01 (2026-11-14): média, desvio, quartis, P95 e assimetria do tamanho das frases, das glosas e da compressão, por domínio; atributos numéricos e categóricos das palavras |
| Tratamento (limpeza, normalização, encoding, ausentes) com justificativa | ✅ | `notebooks/02-preparacao.ipynb` |
| Conferência dos rótulos (P6 item 2) | ✅ (2026-11-14) | 200 rótulos conferidos pela equipe: ruído geral 8,1% (IC 95% 4,6–11,7%), concentrado no rótulo `DESCARTAR` (16%). Seção 8 do notebook 02; planilha em `data/conferencia/` |

### Visualização (mínimo de 5, com interpretação)

| Situação | Evidência |
| --- | --- |
| ✅ (2026-11-14) | O notebook 01 tem agora **9 figuras numeradas**, cada uma com um parágrafo de leitura: 1 tamanhos, 2 palavras × sinais, 3 compressão por domínio, 4 rótulos, 5 MANTER por classe gramatical, 6 classe × vizinho seguinte (mapa de calor), 7 posição e tamanho da frase, 8 frequência × MANTER dos lemas, 9 morfologia ausente. Também são salvas em `reports/figuras/eda-*.png` (200 dpi) para o relatório. Os notebooks 03 a 05 somam mais 14 figuras da modelagem |

### Validação

| Requisito de AM | Situação | Evidência / o que falta |
| --- | --- | --- |
| Holdout | ✅ | Divisão 90/10 agrupada por frase, semente fixa; teste final usado uma vez (F1-macro 0,885) |
| Validação cruzada (k-fold / stratified) | ✅ | `StratifiedGroupKFold` k=5 (`28`, notebook 05) |
| Leave-One-Out (quando aplicável) | ✅ (justificado) | Não se aplica: custo (1,3 milhão de treinos), vazamento entre palavras da mesma frase e nenhum ganho estatístico com n grande. Justificativa escrita em 2026-11-14 na seção "Estratégia de validação" de `28` e na célula 0 do notebook 05, junto com o porquê do holdout por frase, da estratificação e do k=5 |
| Estabilidade, over/underfitting, generalização | ✅ | Média ± desvio entre dobras, curva de aprendizado, teste fora do domínio (`28`) |
| Otimização (Grid, Random e/ou Optuna) documentada | ✅ | Optuna TPE, 25 tentativas, espaço de busca e resultado (`27`). Escolha justificada em 2026-11-14 ("Por que Optuna" em `27` e célula 0 do notebook 04): grade de mais de 3.700 combinações (~20 h) inviável; Random Search viável mas sem aprender; com a ressalva de que o topo é plano |

### Modelagem

| Requisito de AM | Situação | Evidência |
| --- | --- | --- |
| Baseline adequado com justificativa e métricas em validação | ✅ | Regressão Logística, F1-macro 0,876 contra 0,822 da lista fixa (`25`) |
| ≥ 3 modelos da lista (KNN, Árvore, RF, AdaBoost, MLP) | ✅ | KNN, Árvore e Random Forest (+ Regressão). AdaBoost e MLP não são obrigatórios |
| Métricas definidas antes | ✅ | F1-macro principal, ROC-AUC, PR-AUC (`22`) |
| Visualizações da comparação e análise crítica | ✅ | Matriz de confusão, ROC/PR, F1 por classe, erros (`26`, notebook 03) |
| Modelo fora da disciplina validado com o professor | — | Não usamos |

### MLflow

| Requisito de AM | Situação | Evidência / o que falta |
| --- | --- | --- |
| Parâmetros, métricas, artefatos | ✅ | Experimento `t1-manter-descartar` |
| Múltiplos experimentos (baseline, comparação, otimização) | 🟡 | Os três existem como **runs** (inclusive o pai `optuna-random-forest` com 25 filhas). **A conferir** se estão num único experimento do MLflow. Se estiverem, ou separar em três experimentos, ou deixar claro no relatório com captura da tela do MLflow mostrando os três grupos |
| Salvamento do modelo | ✅ | Model Registry `sinaliza-t1` v1, usado pela API |

### Dashboard

| Requisito de AM | Situação | Evidência / o que falta |
| --- | --- | --- |
| Interface interativa integrada | ✅ | Streamlit, 4 abas, serviço `dashboard` no compose |
| Consumo da infraestrutura de aquisição (MQTT e/ou API) | ✅ / 🟡 | Hoje via API e banco. Se o MQTT entrar, mostrar também as mensagens recebidas pelo broker |
| Indicadores, métricas, inferências, monitoramento em tempo de execução | ✅ | Abas de indicadores, inferências, modelo e serviços |
| Métricas da solução de Projetos 6 | 🟡 | Já mostra frases, palavras sem sinal e latência. Pode ganhar métricas da trilha gamificada do web, se ela gravar algo |

### Aquisição de Dados e MQTT — **principal lacuna técnica**

| Requisito de AM | Situação |
| --- | --- |
| Sistema embarcado físico ou simulado | ❌ (temos um simulador de uso, `textgloss/simulador.py`, mas ele fala HTTP com a API, não é um "dispositivo") |
| Publicação via MQTT (ou equivalente) | ❌ |
| Recepção e persistência | ✅ (tabela `inferencias` no Postgres), mas a recepção é pela API, não por um assinante |

Em Projetos 6 o grupo decidiu deixar isso fora (`23`, decisão de 2026-10-28, motivo: "o embarcado não é do grupo"). Na especificação de AM, porém, MQTT aparece nos objetivos, num **critério de avaliação** próprio ("Infraestrutura de aquisição, comunicação MQTT e pipeline de dados"), na lista de serviços do Docker Compose e no roteiro da apresentação final. Defender "HTTP é tecnologia equivalente" é fraco: o MQTT está ali como mensageria publicador/assinante.

**Proposta [a decidir pelo grupo]:** o requisito aceita embarcado **simulado**, e quase tudo já existe. Custo estimado: pequeno.

1. Serviço `mosquitto` (broker MQTT) no `docker-compose.yml`.
2. `embedded/` (pasta sugerida pela especificação): simulador de um "totem de atendimento" que publica frases num tópico, por exemplo `sinaliza/frases`, reaproveitando as frases do `textgloss/simulador.py`.
3. Assinante (serviço pequeno ou dentro da API) que recebe do tópico, chama a inferência do modelo e grava em `inferencias` com a origem `mqtt`.
4. Painel mostra as mensagens recebidas pelo MQTT; `textgloss.demo` ganha uma etapa "publicou no MQTT → apareceu no banco".
5. Atualizar `23` (tirar os riscados), `24`, `30` e o deck.

Alternativa: perguntar ao professor de AM se aceita o corte. Arriscado, porque o critério tem peso dentro dos 25% de MLOps.

### Pipeline de Dados (Airflow)

| Requisito de AM | Situação | Evidência |
| --- | --- | --- |
| Ingestão, preparação e disponibilização automatizadas | ✅ | DAGs `vlibrasbd_ingestao`, `preparacao_t1`, `treino_t1`, `monitoramento` |
| Notebook com EDA e preparação | ✅ | Notebooks 01 e 02 |

### Integração e API

| Requisito de AM | Situação | Evidência |
| --- | --- | --- |
| Modelo validado no pipeline, consumo automático de dados novos, inferências | ✅ | API usa `sinaliza-t1`; DAG `monitoramento` consolida as frases novas; demonstração 7/7 |
| Inferências por API | ✅ | `/translate` com `decision`, `probability`, `model_version` |

### Conteinerização

| Requisito de AM | Situação | Evidência / o que falta |
| --- | --- | --- |
| Compose com broker MQTT, banco, Airflow, MLflow, API, dashboard | 🟡 | Tudo menos o **broker MQTT** |
| Execução completa com um único comando | ✅ | `docker compose up -d --build`, testado em cópia limpa (perfil `demo`). Perfil `completo` ainda sem resultado registrado |

### Apresentação final

| Situação | O que falta |
| --- | --- |
| 🟡 | Deck de 14 slides e roteiro `30` prontos. Faltam: etapa de embarcado/MQTT (se entrar), 3 números do slide 5, ensaio |

### Relatório (template SBC) — **principal lacuna de nota**

| Situação | O que falta |
| --- | --- |
| ❌ | Não existe. Vale 20% e zera se sair do formato. Regras e esqueleto em [`32-template-sbc.md`](32-template-sbc.md). Quase todo o conteúdo já está escrito em `22` a `30` e nos notebooks; o trabalho é condensar, pôr figuras e respeitar o template. Abstract + Resumo (≤ 10 linhas cada) na 1ª página. PDF final em `reports/` |

### README e estrutura do repositório

| Requisito de AM | Situação | O que falta |
| --- | --- | --- |
| Nomes e sobrenomes dos membros + usuários do GitHub | ❌ | O README não lista a equipe (ela está em `00-visao-geral.md`, sem os @ do GitHub) |
| Nome da solução | ✅ | Sinaliza |
| Instruções detalhadas para compilar e executar | 🟡 | Estão em `14-como-rodar-e-testar.md`; trazer o essencial (um comando + pré-requisitos) para o README |
| Descrição + link do Google Sites | 🟡 | Descrição existe; **falta o link do Google Sites** |
| Estrutura de pastas sugerida | 🟡 (é sugestão, ajustes permitidos) | Temos `textgloss/` (≈ `src/`), `pipeline/dags/` (≈ `dags/`), `dashboard/` (≈ `app/`). Faltam `reports/` e, com o MQTT, `embedded/`. Basta uma tabela no README mapeando nossa estrutura para a sugerida. Não há `requirements.txt` na raiz (cada componente tem o seu); explicar no README |

## Prioridades sugeridas

1. **Relatório SBC** (20%, ❌, nada começado). Maior risco de nota.
2. **Decidir o MQTT**: implementar o embarcado simulado (recomendado) ou obter o aceite do professor por escrito.
3. ~~EDA: ≥ 5 visualizações e estatísticas descritivas~~ (feito em 2026-11-14).
4. ~~Justificativas de LOO e Optuna~~ (feito em 2026-11-14). Resta conferir os experimentos no MLflow (bloco MLOps).
5. **README**: membros com @ do GitHub, link do Google Sites, como executar, mapa de pastas; criar `reports/`.
6. Pendências antigas que seguem valendo: perfil `completo`, ensaio, 3 números do slide 5 (1%, 16% e 8,1%).
7. Perguntar ao professor: os 10% que faltam nos pesos; se o template no Google Docs exportado em PDF é aceito.
