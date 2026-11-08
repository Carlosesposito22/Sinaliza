# Pipeline de dados e onde o ML entra (fases 1 e 2)

Documento exigido pelo orientador (requisito R0 do [checklist](23-checklist-requisitos-ml.md)): deixar claro **onde aplicamos machine learning** e como a pipeline funciona de ponta a ponta. Este arquivo cobre o que existe hoje (ingestão e preparação); as fases 3 em diante acrescentam as seções de treino, API e painel.

Legenda do tipo de cada etapa: **ML nosso** (treinado no nosso pipeline), **regra** (código determinístico nosso), **extração** (gera atributos, não decide), **externo** (terceiros, sem decisão de ML nossa), **infra** (dados e serviços).

## Visão geral

```
VLibrasBD (CSV, Mendeley)          infra/externo
   │  download + conferência do SHA-256
   ▼
Postgres: corpus_bruto             infra            textgloss/ingest.py
   │  limpeza (vazias, duplicadas)
   ▼
frases limpas                      regra            textgloss/prepare.py · clean()
   │  spaCy: lema, classe gramatical, morfologia
   ▼
atributos por palavra              extração         textgloss/features.py
   │  glosa → chaves; palavra ∈ glosa?
   ▼
rótulo MANTER / DESCARTAR          regra (gera o   textgloss/corpus.py · align.py
   │                               alvo do ML)
   ▼
divisão treino 90% / teste 10%     regra            prepare.split_by_sentence()
(por frase, estratificada)
   │
   ▼  ─ ─ ─ fases 3 a 6 ─ ─ ─
CLASSIFICADOR: a palavra vira      ML nosso         textgloss/train.py (baseline feito: ver 25)
sinal?                             Regressão Logística ✔ → Árvore ✔, Random Forest ✔, KNN ✔ (ver 26) → Optuna ✔ (ver 27)
   │
   ▼  ─ ─ ─ fase 8 ─ ─ ─
API /translate  →  glosa  →  player do VLibras (avatar)      externo (só toca os sinais)
```

## Onde está o ML (e onde não está)

| Pergunta | Resposta |
| --- | --- |
| Qual é a tarefa de ML? | **T1**: classificação binária por palavra, "essa palavra vira sinal na glosa do intérprete?" (`MANTER`/`DESCARTAR`) |
| De onde vêm os rótulos? | Da glosa feita à mão por intérpretes certificados no VLibrasBD, alinhada por lema. A **regra de alinhamento** só transforma essa anotação humana em exemplos; o que ela não consegue generalizar é o que o modelo aprende |
| O que o modelo vai decidir? | Quais palavras de uma frase **nova** viram sinal, no lugar da lista fixa `FUNCTION_WORDS` da API |
| O que **não** é ML nosso? | O spaCy (extração de atributos), o player do VLibras (apenas toca as glosas) e o `vlibras-translate` (só linha de base de avaliação) |
| O que o ML não resolve? | A **ordem** dos sinais (T1 mantém a ordem do português) e a validação por pessoas surdas |
| Contra o que o modelo é comparado? | A lista fixa atual: **F1-macro 0,822** no corpus inteiro (EDA, seção 5). O modelo só se justifica se superar isso no teste |

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

- **Conferência manual** das 200 palavras de `data/processed/vlibrasbd/amostra_conferencia_200.csv` (preencher `rotulo_correto` e rodar a última célula do notebook 02). Sem ela não há taxa de ruído medida; o plano exige isso antes de treinar.

## Créditos

VLibrasBD / `pt-br2libras-gloss` (Lima et al., 2025, *Data in Brief*), CC BY-SA 4.0. Ver [`docs/creditos-e-licencas.md`](../docs/creditos-e-licencas.md).
