# Pipeline ponta a ponta e onde o ML entra (R0)

Documento exigido pelo orientador (requisito R0 do [checklist](23-checklist-requisitos-ml.md)): deixar claro **onde aplicamos machine learning** e como a pipeline funciona **de ponta a ponta**. É o documento de referência da apresentação, que percorre este mesmo fluxo (roteiro em [`30-roteiro-da-demonstracao.md`](30-roteiro-da-demonstracao.md)). O treino e a validação estão detalhados em [`25`](25-baseline-t1.md) a [`28`](28-validacao-e-generalizacao-t1.md), a API em [`12`](12-api.md) e os comandos em [`14`](14-como-rodar-e-testar.md).

Legenda do tipo de cada etapa: **ML nosso** (treinado no nosso pipeline), **regra** (código determinístico nosso), **extração** (gera atributos, não decide), **externo** (terceiros, sem decisão de ML nossa), **estatística** (contas sobre dados já gerados, sem modelo novo), **infra** (dados e serviços).

## Visão geral

```
VLibrasBD (CSV, Mendeley)                          infra/externo
   │  download + conferência do SHA-256
   ▼
Postgres: corpus_bruto (127.349 pares)             infra            DAG vlibrasbd_ingestao · textgloss/ingest.py
   │  limpeza (vazias, duplicadas, glosa sem sinal)
   ▼
frases limpas                                      regra            DAG preparacao_t1 · textgloss/prepare.py
   │  spaCy: lema, classe gramatical, morfologia
   ▼
atributos por palavra                              extração         textgloss/features.py
   │  a palavra (ou o lema) aparece na glosa do intérprete?
   ▼
rótulo MANTER / DESCARTAR                          regra (gera o alvo do ML)     textgloss/align.py
   │  divisão 90% treino / 10% teste, por frase
   ▼
palavras_t1 (1,6 milhão de palavras)               infra
   │
   ▼  DAG treino_t1 (o MLflow registra parâmetros, métricas e artefatos de tudo)
Baseline (Regressão Logística)  →  Árvore, Random Forest, KNN  →  Optuna sobre o Random Forest  →  validação cruzada
   │                                                                                    ML nosso   textgloss/train.py, tune.py, validate.py
   ▼  teste final: 10% das frases, usado uma única vez
Model Registry do MLflow: sinaliza-t1              ML nosso (Random Forest otimizado)
   │  a API carrega em segundo plano; sem ele, volta à lista fixa
   ▼
texto digitado ─► spaCy ─► CLASSIFICADOR T1 ─► decisão por palavra: MANTER ou DESCARTAR, com a probabilidade
                 extração   ML NOSSO            │
                                                ├─ DESCARTAR: a palavra não vira sinal
                                                └─ MANTER: tabela do vocabulário, lema ou aproximação por embedding     regra / externo
                                                       ▼
                                        sequência de sinais (glosas)  ─►  player do VLibras (avatar)     externo (só toca)
   │  cada frase atendida pela API
   ▼
Postgres: inferencias ─► DAG monitoramento ─► indicadores_horarios ─► Painel (Streamlit)
                         estatística, sem ML novo                       visualização, sem ML novo
```

O que o usuário vê (a sequência de sinais) **depende do ML em um ponto**: o classificador T1 decide, palavra por palavra, o que entra. Todo o resto é regra, extração, infraestrutura ou externo.

## Onde está o ML (e onde não está)

| Pergunta | Resposta |
| --- | --- |
| Qual é a tarefa de ML? | **T1**: classificação binária por palavra, "essa palavra vira sinal na glosa do intérprete?" (`MANTER`/`DESCARTAR`) |
| Quais atributos o modelo usa? | Lema (2.000 mais frequentes), classe gramatical e dependência (spaCy), morfologia (gênero, número, tempo, modo, pessoa...), classes vizinhas, posição e tamanho da frase, tipo de frase, se é stopword (lista completa em `textgloss/modeling.py`) |
| De onde vêm os rótulos? | Da glosa feita à mão por intérpretes certificados no VLibrasBD, alinhada por lema. A **regra de alinhamento** só transforma essa anotação humana em exemplos; o que ela não consegue generalizar é o que o modelo aprende |
| Quais modelos foram treinados? | Regressão Logística (baseline), Árvore de Decisão, Random Forest e KNN; o Random Forest foi otimizado com Optuna e é o escolhido (`sinaliza-t1`) |
| Quão bom é? | **F1-macro 0,885** no teste final (10% das frases, uma única vez), contra **0,823** da lista fixa que a API usava antes; validação cruzada 0,879 ± 0,001; cai de 2 a 4 pontos fora do domínio. Ver [`28`](28-validacao-e-generalizacao-t1.md) |
| Onde o modelo decide algo na saída final? | Na API (`POST /translate`): para cada palavra, a probabilidade de `MANTER` define se ela segue para o vocabulário. Aparece na resposta (`decision`, `probability`, `model_version`) e na interface do painel |
| O que **não** é ML nosso? | O spaCy (extração de atributos), o simplemma e o embedding de caracteres (aproximação de palavras fora do vocabulário), a tabela do vocabulário, o player do VLibras (só toca as glosas) e o `vlibras-translate` (só linha de base de avaliação) |
| O que o ML não resolve? | A **ordem** dos sinais (o T1 mantém a ordem do português), a validação por pessoas surdas e o texto com várias frases (a API trata tudo como uma frase) |
| Contra o que o modelo foi comparado? | A lista fixa (`FUNCTION_WORDS`): F1-macro 0,822 na validação e 0,823 no teste. O modelo só se justificaria se a superasse, e superou por 6 pontos |
| Como o modelo falha? | Erra palavras que o spaCy classifica mal (ex.: "preciso" é descartado com probabilidade ~0,005) e que os intérpretes usam de formas diferentes (ex.: "eu"). O painel mostra as decisões de baixa confiança |

## Mapa das etapas: entrada, saída, onde roda e como reproduzir

Cada linha roda no Airflow (DAG), em notebook ou na API; o comando equivalente fora do Airflow está na última coluna (na raiz do repositório, com `textgloss/.venv`). Etapas de treino registram tudo no MLflow, experimento `t1-manter-descartar`.

| # | Etapa | Tipo | Entrada | Saída | Onde roda | Como reproduzir |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Ingestão | infra | CSV do VLibrasBD (31 MB, hash conferido) | tabela `corpus_bruto` | DAG `vlibrasbd_ingestao` | `python -m textgloss.ingest` |
| 2 | Análise exploratória | extração/estatística | `corpus_bruto` | decisões documentadas | notebook `01-eda-vlibrasbd` | `jupyter nbconvert --execute` |
| 3 | Limpeza e rotulagem | regra + extração | `corpus_bruto` | `palavras_t1`, `palavras.parquet`, `frases.parquet`, relatório, amostra de conferência | DAG `preparacao_t1`; notebook `02-preparacao` | `python -m textgloss.prepare --processos 4` |
| 4 | Conferência dos rótulos | estatística | `amostra_conferencia_200.csv` preenchida pela equipe | taxa de rótulo errado por classe, com intervalo | notebook `02-preparacao` (última célula) | `python -m textgloss.ruido` |
| 5 | Baseline | **ML nosso** | `palavras_t1` (treino) | Regressão Logística e lista fixa no MLflow | DAG `treino_t1`; [`25`](25-baseline-t1.md) | `python -m textgloss.train baseline` |
| 6 | Comparação de modelos | **ML nosso** | idem | Árvore, Random Forest, KNN; matrizes de confusão, ROC, erros | DAG `treino_t1`; notebook `03`; [`26`](26-comparacao-de-modelos-t1.md) | `python -m textgloss.train modelos` e `comparar` |
| 7 | Otimização | **ML nosso** | idem | 25 tentativas do Optuna e o melhor Random Forest | DAG `treino_t1`; notebook `04`; [`27`](27-otimizacao-random-forest.md) | `python -m textgloss.tune` |
| 8 | Validação | **ML nosso** | idem | validação cruzada agrupada por frase, curva de aprendizado, teste fora do domínio | DAG `treino_t1`; notebook `05`; [`28`](28-validacao-e-generalizacao-t1.md) | `python -m textgloss.validate cv`, `curva`, `dominio` |
| 9 | Teste final e registro | **ML nosso** | `palavras_t1` (teste, uma única vez) | `sinaliza-t1` no Model Registry | DAG `treino_t1` (`--se-pendente`) | `python -m textgloss.validate teste --modelo random-forest-otimizado` |
| 10 | Inferência | **ML nosso** + extração | texto do usuário | probabilidade de `MANTER` por palavra | API (`textgloss/infer.py`) | `docker compose up -d api` e `POST /translate` |
| 11 | Glosa final | regra / externo | palavras mantidas | sequência de sinais | API (`text_to_gloss.py`) | idem |
| 12 | Gravação | infra | resposta da API | linha em `inferencias` | API (`inference_log.py`) | idem |
| 13 | Dados novos | infra | `data/phrases.json` ou o conjunto de teste | frases enviadas à API | script | `python -m textgloss.simulador` |
| 14 | Consolidação | estatística | `inferencias` | `indicadores_horarios` | DAG `monitoramento` | `python -m textgloss.monitor` |
| 15 | Painel | visualização | Postgres, API, MLflow, Airflow | indicadores, inferências, modelo e serviços | serviço `dashboard` | `docker compose up -d --build dashboard` |

Tudo isso sobe com `docker compose up -d --build`; numa máquina limpa o Airflow roda sozinho as etapas 1 a 9 (perfil `demo` em minutos, `completo` em horas). A demonstração automática de ponta a ponta é `python -m textgloss.demo`.

## Etapas implementadas

### 1. Ingestão (`textgloss/ingest.py`) — infra

- **Entrada:** CSV do VLibrasBD (31 MB, DOI 10.17632/ryj88ckjww.2).
- **O que faz:** baixa se não existir, **confere o SHA-256** publicado pelo Mendeley (falha se divergir), carrega na tabela `corpus_bruto` do Postgres (127.349 linhas, chave `frase_id`) e registra a execução em `ingestoes`.
- **Saída:** tabela `corpus_bruto(frase_id, texto, glosa, governo, ingles)`.
- O CSV fica em `data/raw/vlibrasbd/` e **não é versionado**.

### 2. Preparação (`textgloss/prepare.py`) — regra + extração

| Passo | Tipo | O que faz |
| --- | --- | --- |
| Limpeza | regra | remove frases vazias, duplicatas exatas e glosas sem sinal (127.349 → 127.320 pares) |
| Notação da glosa | regra | `gloss_keys()`: remove marcas, `NÃO_X` → {NÃO, X}, `1S_X_2S` → X, `X&Y` → X, compostos inteiros e por partes |
| Atributos | extração | spaCy `pt_core_news_md`: lema, classe gramatical (UPOS), dependência, morfologia, stopword, posição e tamanho da frase, classes vizinhas, tipo de frase |
| Rotulagem | regra | `align.label_token()`: `MANTER` se lema, forma escrita, primeira parte de lema composto ou numeral-em-dígito aparece na glosa |
| Divisão | regra | 10% das **frases** para teste (estratificado por domínio, semente fixa); palavras da mesma frase nunca se separam |

- **Saídas:** `data/processed/vlibrasbd/palavras.parquet` e tabela `palavras_t1` (1.615.265 palavras, 52,5% `MANTER`), `frases.parquet`, `relatorio_preparacao.json` e `amostra_conferencia_200.csv`.
- **Justificativas** de cada decisão (limpeza, encoding, ausentes, desbalanceamento, divisão) estão em [`notebooks/02-preparacao.ipynb`](../notebooks/02-preparacao.ipynb); a análise exploratória em [`notebooks/01-eda-vlibrasbd.ipynb`](../notebooks/01-eda-vlibrasbd.ipynb).

### 3. Cobertura do dicionário (`textgloss/coverage.py`) — externo

Consulta (HEAD, sem baixar) quais dos 1.500 sinais mais frequentes do corpus existem no dicionário do VLibras: **95,3%** (96,0% das ocorrências). O vocabulário do Sinaliza pode crescer bem além dos 210 sinais de hoje.

## Achados que importam para as próximas fases

- A lista fixa já acerta bastante (F1-macro 0,822), então o ganho do ML será medido em pontos, não em saltos. O espaço está nos **69 lemas frequentes ambíguos** (ex.: `eu`, `ou`, `seu`, `ter`, `como`), que os intérpretes ora mantêm e ora descartam.
- A lista fixa descarta `você`, `eu`, `seu`, `de`, `que`, `ele`, `ou`, `como`, `sobre`, `também` mesmo quando os intérpretes os **mantêm**: é a raiz do "português sinalizado" que o modelo deve corrigir.
- **Ruído de rótulo:** o spaCy erra alguns lemas (`preciso`, `haver`) e intérpretes usam sinônimos (`solicitar` ↔ `PEDIR`). A taxa real será medida pela conferência manual das 200 palavras (pendente, ver abaixo).
- O domínio geral tem boa parte de frases de coleções de exemplos (`TOM`, `MARIA`); só **20,5%** dos lemas são comuns aos dois domínios, então o teste fora do domínio (fase 6) será exigente.
- T2 (homônimos): 189 lemas com ≥2 sentidos de ≥30 exemplos. T3: 10,2% das glosas têm negação incorporada e só 1,5% têm intensidade.

## Como reproduzir

Pré-requisitos: Docker e Python 3.12. Na raiz do repositório:

```bash
docker compose up -d postgres
py -3.12 -m venv textgloss/.venv
textgloss/.venv/Scripts/python -m pip install -r textgloss/requirements.txt
textgloss/.venv/Scripts/python -m pip install https://github.com/explosion/spacy-models/releases/download/pt_core_news_md-3.8.0/pt_core_news_md-3.8.0-py3-none-any.whl
```

```bash
textgloss/.venv/Scripts/python -m textgloss.ingest
```

```bash
textgloss/.venv/Scripts/python -m textgloss.prepare --processos 4
```

```bash
textgloss/.venv/Scripts/python -m textgloss.coverage --top 1500
```

Testes: `cd textgloss && .venv/Scripts/python -m pytest`. Notebooks: `jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb` (ou abrir no Jupyter).

A conexão usa `SINALIZA_DATABASE_URL` (padrão `postgresql+psycopg://sinaliza:sinaliza@localhost:5432/sinaliza`).

## Orquestração no Airflow (fase 7)

Os quatro fluxos ficam em `pipeline/dags/` e **só chamam os módulos do `textgloss` por linha de comando**: o que roda no Airflow é exatamente o que se reproduz à mão. O serviço `airflow` do compose (`airflow/Dockerfile`, Airflow 3.1.5 em modo `standalone`, interface em http://localhost:8080, sem login, só local) monta os DAGs e o `textgloss` e usa um ambiente Python à parte (`/opt/airflow/venv-ml`) para as dependências do ML não conflitarem com as do Airflow. Os arquivos gerados ficam no volume `dados` (dentro do container, `/opt/sinaliza/data`), separado de `data/` do host.

| DAG | O que faz | Etapa | Comando equivalente | Quando roda |
| --- | --- | --- | --- | --- |
| `vlibrasbd_ingestao` | baixa o CSV, confere o SHA-256, recria `corpus_bruto`; dispara `preparacao_t1` | infra (sem ML) | `python -m textgloss.ingest` | manual |
| `preparacao_t1` | limpa, spaCy, rotula, divide treino/teste por frase, salva `palavras.parquet` e `palavras_t1` | preparação para o ML | `python -m textgloss.prepare --processos 4` | depois da ingestão (parâmetros `limite` e `processos`) |
| `treino_t1` | baseline → comparação → Optuna → validação cruzada → teste final e registro de `sinaliza-t1` | **ML nosso** | `train baseline`, `train modelos`, `train comparar`, `tune`, `validate cv`, `validate teste` | manual (parâmetros `trials`, `timeout_s`, `frases_cv`, `registrar_modelo`) |
| `monitoramento` | consolida as inferências novas (`inferencias`) em `indicadores_horarios` | estatística (sem ML novo) | `python -m textgloss.monitor` | a cada hora |

**Primeira subida de uma máquina limpa:** `airflow/bootstrap.sh` (em segundo plano no container) dispara `vlibrasbd_ingestao` com `limite`/`processos` conforme `SINALIZA_PERFIL` (`demo` ou `completo`), espera a `preparacao_t1` e dispara o `treino_t1`. Só age se o banco não tem `corpus_bruto`. Detalhes e verificação em [`14`](14-como-rodar-e-testar.md). O `vlibrasbd_ingestao` repassa `limite` e `processos` à preparação.

Cuidados:

- **O teste final roda uma única vez por MLflow.** A tarefa dele usa `--se-pendente`: se a run `teste-final` já existe, não treina nem registra nada e termina com sucesso. Num MLflow vazio (máquina limpa), o primeiro `treino_t1` completo cria o `sinaliza-t1` v1.
- `SINALIZA_MLFLOW_EXPERIMENT` troca o experimento (útil para testar os DAGs sem sujar `t1-manter-descartar`).
- A tabela `inferencias` é o **contrato com a API da fase 8**: uma linha por frase recebida (colunas em `textgloss/monitor.py`), com `processada = false`. Só o `monitoramento` a marca como processada. Texto de usuário só pode ser gravado depois de definidos finalidade, retenção e aviso de privacidade.

## Do modelo à resposta: integração na API e dados novos (fase 8)

Esta é a parte do fluxo em que o ML **decide algo na saída final**. Detalhes da API em [`12-api.md`](12-api.md).

| Etapa | O que faz | Tipo | Onde | Como reproduzir |
| --- | --- | --- | --- | --- |
| Simulador de uso | envia frases à API com `X-Origem: simulador` (faz o papel de fonte de dados novos no lugar do embarcado) | sem ML | `textgloss/simulador.py` | `python -m textgloss.simulador --n 30 --intervalo 1` |
| spaCy | extrai os atributos de cada palavra (os mesmos do treino) | externo | `textgloss/features.py`, chamado por `infer.py` | automático na API |
| **Classificador T1** | probabilidade de MANTER por palavra; `>= 0,5` mantém | **ML nosso** (`sinaliza-t1`, Random Forest otimizado) | `textgloss/infer.py`, carregado do MLflow em `api/app/model_provider.py` | `docker compose up -d api` |
| Tabela, lema, aproximação | transforma palavra mantida em glosa do vocabulário | regra / externo (simplemma, embedding) | `api/app/text_to_gloss.py` | idem |
| Gravação | uma linha em `inferencias` por frase | sem ML | `api/app/inference_log.py` | idem (`SINALIZA_LOG_DATABASE_URL`) |
| Consolidação | indicadores por hora e versão em `indicadores_horarios`; apaga texto vencido | estatística | DAG `monitoramento` (`textgloss/monitor.py`) | `python -m textgloss.monitor` |
| Painel | mostra indicadores, inferências, versão e métricas do modelo e o estado dos serviços | visualização (sem ML novo) | `dashboard/` (Streamlit), lê `inferencias`, `indicadores_horarios`, API, MLflow e Airflow | `docker compose up -d --build dashboard` |

Verificado em 2026-11-05 (banco descartável, já removido): 25 frases do simulador passaram pelo `sinaliza-t1/1` real (latência média 186 ms), foram gravadas com texto (origem `simulador`) e consolidadas (138 palavras: 60,9% mantidas, 5,1% sem sinal, 7,2% de decisões incertas entre 0,4 e 0,6, p50 178 ms e p95 225 ms). Uma requisição sem `X-Origem` foi gravada **sem texto e sem palavras**. Sem o modelo, a API atende com a lista fixa e `model_version: "lista-fixa"`.

Repetido com a pilha completa de pé (postgres, mlflow, api com o modelo e airflow, ~2,7 GB): 20 frases do simulador, DAG `monitoramento` do Airflow com sucesso, 109 palavras (63,3% mantidas, 5,5% sem sinal, p95 145 ms).

Limites: o modelo foi treinado em frases isoladas e a API o aplica ao texto inteiro como uma única frase (textos com várias frases perdem a posição relativa); o modelo erra (ex.: "preciso" é descartado); o `sinaliza-t1` exige ~2,8 GB na carga (ver [`14`](14-como-rodar-e-testar.md)).

## Pendente nesta etapa

- **Conferência manual** das 200 palavras: a equipe informou que já conferiu, mas **a planilha preenchida não está neste repositório** (`data/processed/vlibrasbd/amostra_conferencia_200.csv` ainda está com `rotulo_correto` vazio). Com o arquivo preenchido, `python -m textgloss.ruido` (ou a última célula do notebook 02) calcula a taxa de rótulo errado por classe, com intervalo de confiança e ponderada pela proporção real das classes; ferramenta pronta e testada, falta só o arquivo.

## Créditos

VLibrasBD / `pt-br2libras-gloss` (Lima et al., 2025, *Data in Brief*), CC BY-SA 4.0. Ver [`docs/creditos-e-licencas.md`](../docs/creditos-e-licencas.md).
