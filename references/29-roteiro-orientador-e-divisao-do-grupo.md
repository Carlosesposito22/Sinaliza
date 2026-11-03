# Roteiro para o orientador e divisão do trabalho no grupo

Escrito em 2026-11-02, depois das fases 1 a 6 de ML. Tem duas partes:

1. **Roteiro da reunião** (o que foi feito, o que mostrar, o que dizer, perguntas prováveis, o que falta).
2. **Divisão em pacotes de trabalho independentes** para o grupo de 6 pessoas.

Estado detalhado e comandos para retomar: [`15-estado-atual-e-proximos-passos.md`](15-estado-atual-e-proximos-passos.md). Checklist da rubrica: [`23-checklist-requisitos-ml.md`](23-checklist-requisitos-ml.md).

---

# Parte 1 · Roteiro da reunião (cerca de 15 minutos)

## Antes de tudo: a ideia em uma frase

> "Hoje a API decide quais palavras viram sinal com uma **lista fixa** de palavras. Treinamos um modelo de machine learning que decide isso **aprendendo com 127 mil frases glosadas por intérpretes**, e ele acerta mais: **F1-macro 0,885 contra 0,823** da lista, num teste que só abrimos uma vez."

Se você só conseguir dizer uma coisa, diga essa.

## Glossário em português simples

| Termo | O que significa aqui |
| --- | --- |
| **Glosa** | A frase escrita com os sinais de Libras em ordem e forma de sinal (`QUALQUER CIDADÃO INTERESSAR`). Quem faz é um intérprete |
| **VLibrasBD** | Base pública com 127 mil frases em português e a glosa de cada uma, feita por intérpretes. É o nosso bootstrap dataset |
| **T1 (nossa tarefa de ML)** | Para cada palavra da frase, prever: ela vira sinal (`MANTER`) ou é descartada (`DESCARTAR`)? |
| **Lista fixa** | O que a API faz hoje, sem ML: descarta artigos, preposições etc. de uma lista escrita à mão. É a nossa "régua" |
| **F1-macro** | Nota de 0 a 1 que mistura acertos nas duas classes, sem deixar uma esconder a outra. Quanto mais perto de 1, melhor |
| **Baseline** | Primeiro modelo simples, só para ter com o que comparar |
| **Validação cruzada** | Treinar e testar 5 vezes em pedaços diferentes dos dados para ver se o resultado é estável |
| **Sobreajuste** | O modelo decora o treino e vai pior em dados novos |
| **Optuna** | Ferramenta que testa automaticamente configurações do modelo e acha uma boa |
| **MLflow** | Caderno de laboratório: guarda cada experimento (parâmetros, notas, gráficos, modelo) |
| **Airflow** | Agenda e encadeia os passos do pipeline (baixar, preparar, treinar) automaticamente |

## Roteiro passo a passo

Cada passo tem **o que dizer** e **o que mostrar**. Tenha o MLflow aberto em http://localhost:5000 (rode `docker compose up -d postgres mlflow`) e os notebooks na pasta `notebooks/`.

### 1. Onde o ML entra (1 min)

- **Dizer:** seguindo a orientação dele de deixar claro onde aplicamos ML: o modelo decide, palavra por palavra, se ela vira sinal. O resto (spaCy para lema e classe gramatical, o player do VLibras para tocar o sinal) não é decisão de ML nossa.
- **Mostrar:** o diagrama em [`24-pipeline-de-dados-ponta-a-ponta.md`](24-pipeline-de-dados-ponta-a-ponta.md), em que cada etapa está marcada como ML nosso, regra ou externo.

### 2. Os dados (2 min)

- **Dizer:** baixamos o VLibrasBD (127.349 pares), conferimos o hash do arquivo, carregamos no Postgres e demos os créditos. Fizemos a análise exploratória e a preparação: limpeza, atributos do spaCy, rótulo `MANTER`/`DESCARTAR` por alinhamento com a glosa e divisão treino/teste por frase (palavras da mesma frase nunca se separam).
- **Números:** 1,6 milhão de palavras, 52% `MANTER`; 10% das frases separadas para um teste final que ninguém olhou.
- **Mostrar:** [`notebooks/01-eda-vlibrasbd.ipynb`](../notebooks/01-eda-vlibrasbd.ipynb): o gráfico de descarte por classe gramatical e as palavras que a lista fixa descarta mas os intérpretes mantêm (`você`, `eu`, `ele`, `ou`, `como`).
- **Achado bom de contar:** corrigimos a rotulagem depois da primeira EDA, porque `candidatar-se` e números por extenso saíam errados.

### 3. Baseline e comparação (3 min)

- **Dizer:** a lista fixa tem F1-macro 0,822. A Regressão Logística (baseline) chegou a 0,876. Comparamos também Árvore de Decisão, Random Forest e KNN, todos no MLflow, com matriz de confusão, curvas ROC e análise crítica.
- **Mostrar:** no MLflow, o experimento `t1-manter-descartar` e a run `comparacao-modelos` (curvas sobrepostas). No notebook 03, a tabela e o F1 por classe gramatical.

| Modelo | F1-macro (validação) | Comentário |
| --- | --- | --- |
| Lista fixa (sem ML) | 0,822 | a régua |
| Regressão Logística | 0,876 | simples, rápida, explicável |
| Árvore de Decisão | 0,870 | regras legíveis |
| Random Forest (padrão) | 0,852 | abaixo do esperado, mal configurado |
| KNN | 0,846 | sobreajusta (0,98 no treino) e é lento |

### 4. Otimização com Optuna (2 min)

- **Dizer:** o Random Forest era o que mais tinha a ganhar. O Optuna testou 25 configurações com validação cruzada e subiu o F1 de 0,852 para 0,884. O que mais pesou foi quantas colunas cada divisão da árvore considera.
- **Mostrar:** a run `optuna-random-forest` no MLflow (histórico e importância dos hiperparâmetros) ou o notebook 04.
- **Cuidado ao falar:** as dez melhores configurações estão empatadas; não diga "achamos a ótima", diga "achamos uma região boa".

### 5. Validação e generalização (3 min)

- **Estabilidade:** validação cruzada de 5 dobras agrupada por frase: Random Forest 0,879 ± 0,001, Regressão 0,875 ± 0,001. Resultado estável.
- **Sobreajuste:** a regressão estaciona (modelo simples demais); o Random Forest sobreajusta de leve, mas ainda melhora com mais dados.
- **Fora do domínio:** treinar em textos gerais e testar em textos do gov.br (e o inverso) derruba 2 a 4 pontos. É o principal limite.
- **Mostrar:** notebook 05, a curva de aprendizado e o gráfico de fora do domínio.

### 6. Teste final (1 min)

- **Dizer:** escolhemos o Random Forest otimizado. Treinamos em todo o treino e abrimos o teste uma única vez: **F1-macro 0,885** contra **0,823** da lista fixa (+6,2 pontos). Bateu com a validação, então não ajustamos o modelo ao conjunto de validação. O modelo está registrado no MLflow como `sinaliza-t1`.
- **Mostrar:** a run `teste-final-random-forest-otimizado` e o Model Registry.

### 7. Limites, com honestidade (1 min)

Diga você antes que ele pergunte:

- O ganho é de 3 a 6 pontos, não um salto.
- Os rótulos têm ruído (sinônimos, erros de lema) que ainda vamos medir com uma conferência manual de 200 palavras.
- O modelo decide **quais** sinais entram, **não a ordem**. A saída continua em ordem do português.
- Não houve validação por pessoas surdas. A saída é "sequência de sinais", não "tradução de Libras".
- Fora do domínio o desempenho cai.

### 8. O que falta e as perguntas para ele (2 min)

**O que falta** (é engenharia de integração, não pesquisa):

| Falta | Entregável da rubrica |
| --- | --- |
| Airflow orquestrando ingestão, preparação e treino | 2 |
| A API passa a usar o modelo `sinaliza-t1` e grava as frases recebidas | 7 |
| Docker Compose completo (um comando sobe tudo) | 8 |
| Painel com indicadores e inferências | 9 |
| Apresentação ponta a ponta | 10 |

**Perguntas para levar:**

1. O **simulador de uso** (um script que envia frases à API, no lugar do sistema embarcado e do MQTT) é aceito como fonte de dados novos?
2. Ele prefere que a API use o Random Forest (melhor em F1) ou a Regressão Logística (generaliza melhor fora do domínio, é mais rápida e explicável)? Hoje o registrado é o Random Forest.
3. Há restrição da universidade sobre gravar texto digitado por usuários no banco (privacidade)?

## Perguntas que ele pode fazer

| Pergunta | Resposta curta |
| --- | --- |
| "Isso é tradução para Libras?" | Não. É a escolha de quais palavras viram sinal, com base no que intérpretes fizeram. A saída é uma sequência de sinais, sem gramática de Libras nem expressão facial |
| "Por que não usar o tradutor do VLibras pronto?" | Porque o modelo que decide tem que ser treinado por nós. O VLibras entra só para tocar o sinal (avatar) e, depois, como comparação |
| "Por que o F1-macro?" | Porque mistura acerto nas duas classes sem uma esconder a outra |
| "0,885 é bom?" | É 6 pontos acima da lista que usávamos. O teto é limitado por ruído nos rótulos e por sinônimos |
| "Como sabem que não é sorte?" | Validação cruzada com desvio de 0,001 e teste final que bateu com a validação |
| "O que é o ruído de rótulo?" | O alinhamento automático marca `DESCARTAR` quando o intérprete usou outro sinal para a mesma ideia. Vamos medir com uma amostra de 200 palavras |
| "E o embarcado/MQTT?" | O embarcado não é do grupo. A fonte de dados novos é um simulador que envia frases à API |
| "O que muda para o usuário?" | Hoje palavras como `você` e `eu` são descartadas sempre; o modelo mantém quando os intérpretes mantêm |

---

# Parte 2 · Divisão do grupo (versão vigente, 2026-11-02)

> **Esta é a divisão decidida pelo grupo.** Ela substitui a divisão em 6 pacotes mais abaixo, que fica só como detalhe das tarefas de ML e infraestrutura.

| Quem | Responsabilidade |
| --- | --- |
| **2 pessoas** | Atualizar o **Google Sites** com o que foi feito (usar a Parte 1 e os documentos `25` a `28` como fonte) |
| **1 pessoa (Carlos)** | **ML e API**: texto → glosa, e o que a rubrica pede (Airflow, integração do modelo, banco, Docker Compose, painel, apresentação) |
| **2 pessoas** | **Web**: trilha de aprendizado de Libras gamificada, inspirada no Duolingo |

ML e web andam independentes pelo **contrato de API** em [`docs/contrato-api-web.md`](../docs/contrato-api-web.md) e pelo **mock** em [`mock-api/`](../mock-api/README.md), que o web usa enquanto o ML não termina. Na hora de juntar, o web troca só `VITE_API_URL`.

**Pontos de atenção:**

- **Carga do ML:** os entregáveis 2, 7, 8 e 9 (Airflow, integração do modelo na API com gravação das frases, Compose completo, painel) mais a apresentação ficam com uma pessoa. É o maior risco de prazo. Quando o Google Sites estiver pronto, vale as duas pessoas dele ajudarem (por exemplo, painel e conferência das 200 palavras).
- **Sexto membro:** a divisão acima soma 5 pessoas e o grupo tem 6. Definir onde entra a sexta pessoa (sugestão: painel ou Compose).
- **Quem implementa `/learn/*` na API real:** proposta no contrato, seção 5: as duas pessoas do web, num módulo próprio `api/app/learn/`, para não editarem os mesmos arquivos do ML.

## Divisão anterior em 6 pacotes (detalhe das tarefas)

Grupo de 6 pessoas (você e mais 5). O que falta é separado em **6 pacotes**. Para que ninguém fique esperando, os pacotes se conectam por **4 contratos** definidos abaixo: cada um trabalha contra o contrato, sem depender do código do outro.

## Visão geral

```
                 ┌──────────────┐
  VLibrasBD ───▶ │ 1 Airflow    │───▶ treina e registra sinaliza-t1 (já existe v1)
                 └──────────────┘
                        │ contrato A (modelo no MLflow)
                        ▼
                 ┌──────────────┐  contrato B   ┌──────────────┐
  usuário/sim. ─▶│ 2 API + ML   │──────────────▶│ 3 Banco +    │
                 │              │  (tabela)     │   simulador  │
                 └──────────────┘               └──────┬───────┘
                        │ contrato C (JSON)            │ contrato B
                        ▼                              ▼
                 ┌──────────────┐               ┌──────────────┐
                 │ front (web)  │               │ 4 Painel     │
                 └──────────────┘               └──────────────┘
        5 Infra/Compose  ←── contrato D (serviços) ──→  todos
        6 Documentação, rótulos e apresentação (transversal)
```

## Os 4 contratos (decidir primeiro, 30 minutos em grupo)

Estes são **propostas** para o grupo fechar na primeira reunião. Depois de acordados, cada pacote trabalha sozinho.

### Contrato A · Modelo no MLflow (já existe)

- Modelo registrado: `models:/sinaliza-t1/1` no MLflow (http://mlflow:5000 dentro do compose).
- Entrada: um `DataFrame` com as colunas de `textgloss.modeling.FEATURES` (`upos`, `dep`, `tipo_frase`, `upos_anterior`, `upos_seguinte`, `m_Gender`, `m_Number`, `m_Tense`, `m_VerbForm`, `m_Mood`, `m_Person`, `m_Polarity`, `m_PronType`, `pos`, `pos_relativa`, `tam_frase`, `stop`, `lema`).
- Saída: probabilidade da classe `MANTER`; corte em 0,5.
- Quem produz as colunas: `textgloss.features.doc_rows` (spaCy `pt_core_news_md`).

### Contrato B · Tabela de frases recebidas (Postgres)

Tabela `inferencias` no banco `sinaliza`:

| Coluna | Tipo | Conteúdo |
| --- | --- | --- |
| `id` | serial | chave |
| `recebido_em` | timestamptz | quando chegou |
| `texto` | text | frase enviada |
| `origem` | text | `web` ou `simulador` |
| `palavras` | jsonb | lista de `{palavra, lema, decisao, probabilidade}` |
| `glosa` | text | glosa final |
| `modelo_versao` | text | ex.: `sinaliza-t1/1` ou `lista-fixa` |
| `latencia_ms` | int | tempo total |
| `n_sem_sinal` | int | palavras mantidas sem sinal no vocabulário |

### Contrato C · Resposta da API `/translate`

Hoje a resposta tem `text`, `glosses`, `matches` (`word`, `gloss`, `kind`, `score`), `generator`, `pose`. Proposta: **acrescentar campos, sem remover nenhum**, para o front atual continuar funcionando:

- `matches[].decision` (`"MANTER"` ou `"DESCARTAR"`) e `matches[].probability` (0 a 1);
- `model_version` (`"sinaliza-t1/1"` ou `"lista-fixa"`);
- `latency_ms`.

### Contrato D · Serviços do compose

| Serviço | Porta | Variáveis principais |
| --- | --- | --- |
| `postgres` | 5432 | `POSTGRES_PASSWORD` (já existe) |
| `mlflow` | 5000 | já existe |
| `airflow` | 8080 | `AIRFLOW__DATABASE__...` apontando para um banco `airflow` no Postgres |
| `api` | 8000 | `SINALIZA_DATABASE_URL`, `MLFLOW_TRACKING_URI`, `SINALIZA_MODEL_URI` |
| `web` | 5173 | já existe |
| `dashboard` | 8501 | `SINALIZA_DATABASE_URL`, `API_URL`, `MLFLOW_TRACKING_URI` |

## Os 6 pacotes

Tamanhos são estimativas relativas (P, M, G), não horas.

### Pacote 1 · Airflow e DAGs (Fase 7, entregável 2) · tamanho M

- **O que fazer:** criar `pipeline/dags/` com `vlibrasbd_ingestao`, `preparacao_t1`, `treino_t1` e `monitoramento`, chamando `textgloss.ingest`, `textgloss.prepare`, `textgloss.train` e `textgloss.tune`.
- **Entrega:** DAGs que rodam de ponta a ponta no Airflow; imagem do Airflow com as dependências de `textgloss/` (inclui o modelo spaCy).
- **Depende de:** nada (os módulos já existem). Só combina com o Pacote 5 o serviço `airflow` do compose.
- **Arquivos que mexe:** `pipeline/`, uma `Dockerfile` do Airflow. **Não mexe** em `textgloss/` além de pequenos ajustes de parâmetros.
- **Pronto quando:** `docker compose up` sobe o Airflow, o DAG de ingestão e preparação roda sozinho e o de treino registra uma nova versão no MLflow.

### Pacote 2 · API usa o modelo (Fase 8, parte ML, entregável 7) · tamanho G

- **O que fazer:** a API carrega `sinaliza-t1` do MLflow, extrai os atributos com o spaCy, decide `MANTER`/`DESCARTAR` por palavra no lugar de `FUNCTION_WORDS` (`api/app/text_to_gloss.py`) e devolve o contrato C. Sem modelo disponível, volta à lista fixa e avisa em `model_version`.
- **Entrega:** `/translate` com decisões e probabilidades; testes; Dockerfile da API com spaCy e dependências do modelo (a API hoje não tem sklearn nem spaCy).
- **Depende de:** contrato A (já pronto). Para gravar no banco usa a função `save_inference(...)` do Pacote 3; até lá, deixe-a como no-op.
- **Cuidados:** latência (o modelo tem 154 árvores profundas); tamanho da imagem; manter o modo atual funcionando.
- **Arquivos que mexe:** `api/` (dono de `api/app/main.py`). Reaproveitar `textgloss/features.py` copiando-o ou instalando `textgloss` como pacote.
- **Pronto quando:** frase nova → resposta com decisão por palavra e versão do modelo, sem quebrar o front.

### Pacote 3 · Banco de inferências, simulador e privacidade (Fase 8, parte dados, entregáveis 1 e 7) · tamanho M

- **O que fazer:** criar a tabela `inferencias` (contrato B) com script SQL de migração; módulo `api/app/storage.py` com `save_inference(...)`; **simulador de uso**, um script que envia frases (do VLibrasBD e de `data/phrases.json`) à API em ritmo configurável; definir **finalidade, retenção e aviso de privacidade** do texto gravado.
- **Entrega:** tabela criada na subida do banco, simulador funcionando contra a API atual, texto de privacidade para a interface.
- **Depende de:** contrato B (é quem o define). O simulador funciona contra a API de hoje.
- **Arquivos que mexe:** `postgres/`, `api/app/storage.py` (novo), `simulador/` (novo).
- **Pronto quando:** rodar o simulador por 1 minuto enche a tabela e o Pacote 4 consegue ler.

### Pacote 4 · Painel (Fase 10, entregável 9) · tamanho M

- **O que fazer:** painel em Streamlit com: frases por hora e latência; palavras sem sinal e taxa de descarte; distribuição das probabilidades e casos de baixa confiança; últimas inferências (frase, decisão por palavra, glosa); versão do modelo e métricas do último treino (lidas do MLflow); estado dos serviços (API, banco, MLflow).
- **Entrega:** `dashboard/` com Dockerfile.
- **Depende de:** contrato B. **Começa com dados falsos** no mesmo formato e troca pelo banco quando o Pacote 3 entregar.
- **Arquivos que mexe:** `dashboard/` (novo).
- **Pronto quando:** abre em http://localhost:8501 e mostra os indicadores com o simulador rodando.

### Pacote 5 · Docker Compose e infraestrutura (Fase 9, entregável 8) · tamanho M

- **O que fazer:** integrar no `docker-compose.yml` os serviços `airflow` e `dashboard` (contrato D), healthchecks, ordem de subida, `.env.example`, memória mínima documentada em [`14-como-rodar-e-testar.md`](14-como-rodar-e-testar.md) e teste em máquina limpa.
- **Entrega:** um único `docker compose up` sobe tudo; guia de uso.
- **Depende de:** os Pacotes 1 e 4 entregarem suas imagens. Antes disso, ele pode: montar o esqueleto do Airflow, criar o banco `airflow`, padronizar variáveis e fazer um teste de fumaça de todos os serviços.
- **Arquivos que mexe:** `docker-compose.yml`, `postgres/`, `.env.example`, `references/14-como-rodar-e-testar.md`.
- **Pronto quando:** em uma máquina sem nada instalado além do Docker, o projeto sobe e a demonstração funciona.

### Pacote 6 · Documentação, rótulos, front e apresentação (Fase 11, R0, entregável 10) · tamanho M (distribuído)

- **Conferência manual das 200 palavras** (pode ser dividida entre os 6: cerca de 33 linhas cada). Abrir `data/processed/vlibrasbd/amostra_conferencia_200.csv`, preencher `rotulo_correto` com 1 (`MANTER`) ou 0 (`DESCARTAR`). Não exige saber Libras: é ver se a palavra, ou algo equivalente, está na glosa. Depois rodar a última célula do notebook 02 e anotar a taxa de ruído.
- **Front (`web/`):** mostrar a decisão e a probabilidade de cada palavra, a versão do modelo e o aviso de privacidade (depende do contrato C).
- **Documento R0:** completar [`24-pipeline-de-dados-ponta-a-ponta.md`](24-pipeline-de-dados-ponta-a-ponta.md) com treino, API e painel.
- **Apresentação:** roteiro da demonstração ponta a ponta, slides, decisões técnicas e limitações.
- **Depende de:** o front e os slides finais dependem dos outros pacotes; o resto começa já.
- **Pronto quando:** a apresentação percorre aquisição → banco → Airflow → MLflow → Compose → API → painel, com as limitações ditas em voz alta.

## Ordem e dependências

| Etapa | Pacotes que podem rodar ao mesmo tempo |
| --- | --- |
| Semana 1 | 1, 2, 3, 4 (com dados falsos), 5 (esqueleto) e 6 (rótulos e documentos) — todos independentes, via contratos |
| Semana 2 | 2 grava no banco (liga com 3); 4 passa a ler o banco real; 5 integra 1 e 4; 6 fecha o front |
| Fim | teste em máquina limpa (5), ensaio da demonstração (6) |

Os pontos de ligação são só três: **2 ↔ 3** (função `save_inference`), **3 ↔ 4** (tabela `inferencias`) e **1, 4 → 5** (imagens no compose).

## Regras para o grupo não esbarrar

- Cada pacote tem **dono dos arquivos** listados acima. Se precisar mexer em arquivo de outro, combine antes.
- Um branch por pacote; juntar no compose só quando a imagem estiver pronta.
- Não commitar dados (`data/raw`, `data/processed`), nem `*.npy`, nem vídeos. Ver `.gitignore`.
- **O teste final já foi usado.** Quem for retreinar (Pacote 1) não deve avaliar nele nem ajustar nada olhando para ele.
- Antes de mexer em `textgloss/`, rodar os testes: `cd textgloss && .venv/Scripts/python -m pytest`.
- Todo documento ou código novo diz se a etapa é **ML nosso**, regra ou externo (pedido do orientador).
- Chamar a saída de "sequência de sinais", nunca "tradução de Libras".
