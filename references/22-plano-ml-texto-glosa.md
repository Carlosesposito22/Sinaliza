# Plano de ML: texto → glosa por classificação

Decidido em **2026-10-28** pelo Carlos, depois da pesquisa sobre como converter português em Libras ([`Pesquisas/`](../Pesquisas/)) e da revisão dos requisitos de Machine Learning da disciplina. **[a confirmar com o professor]**: se as tarefas de classificação abaixo contam como "modelo adequado ao problema" e se o sistema embarcado e o MQTT ficam fora (ver a seção "Requisitos que não se aplicam").

Este arquivo é o plano de referência para a parte de ML. Ele substitui o gerador de movimento ([`11-modelo-ml.md`](11-modelo-ml.md)) como entrega principal de ML. O gerador continua no repositório como experimento.

## Por que o plano mudou

1. **A pesquisa mostrou que o problema está no texto → glosa.** O método atual (descartar palavras de uma lista fixa e tocar um sinal por palavra, na ordem do português) produz **português sinalizado**, que a literatura e a comunidade surda rejeitam. O caminho dos sistemas que funcionam, a começar pelo VLibras, é aprender a glosa com corpus feito por intérpretes. Relatório: [`Pesquisas/Relatório de Pesquisa - Texto para Libras.md`](../Pesquisas/Relatório%20de%20Pesquisa%20-%20Texto%20para%20Libras.md).
2. **O modelo de movimento não aparece mais no produto.** Desde 2026-10-25 o avatar é o player do VLibras, que toca os sinais dele. O gerador de movimento também não superou a média por sinal (ver [`11-modelo-ml.md`](11-modelo-ml.md)).
3. **A rubrica pede ML clássico rastreável:** baseline do tipo Regressão Logística ou Árvore de Decisão, três modelos comparados, matriz de confusão e ROC, Optuna, k-fold, MLflow, Airflow e painel. Um gerador de movimento ou só um seq2seq pré-treinado não cobrem isso.
4. **Evitar terceirizar o ML.** O modelo que decide a glosa tem que ser treinado por nós, no nosso pipeline.

## O que é e o que não é terceirização

| O que usamos | Papel | Terceiriza o ML? |
| --- | --- | --- |
| Player do VLibras (avatar) | Apresentação: toca as glosas | Não, desde que nenhuma decisão de ML dependa dele |
| Corpus VLibrasBD (`pt-br2libras-gloss`) | Bootstrap dataset, base pública rotulada por intérpretes | Não: passa pelo nosso pipeline (ingestão, EDA, preparação, treino) |
| spaCy (`pt_core_news_*`) | Pré-processamento: frases, lemas, classe gramatical, morfologia | Não: é extração de atributos, como o pandas |
| `vlibras-translate` (tradutor do VLibras) | **Só linha de base externa** na avaliação ponta a ponta | **Sim, se fosse usado como tradutor.** Não será |
| PTT5/ByT5 pré-treinado | Modelo avançado **opcional**, para comparação | Não, se ajustado por nós; mas não substitui os modelos clássicos |

## O problema de ML

O texto → glosa vira **tarefas de classificação supervisionada**, com rótulos extraídos automaticamente do VLibrasBD. A tarefa T1 sozinha cobre todos os requisitos de ML; T2 e T3 são extensões.

### T1 — manter ou descartar cada palavra (principal)

- **Unidade:** cada palavra (token) da frase em português.
- **Pergunta:** essa palavra vira sinal na glosa do intérprete?
- **Classes:** `MANTER` (1) e `DESCARTAR` (0). Binária: permite matriz de confusão, ROC/AUC e curva precisão-revocação.
- **O que substitui:** a lista fixa `FUNCTION_WORDS` de `api/app/text_to_gloss.py`, que hoje decide sozinha o que descartar e é a raiz do português sinalizado. A decisão passa a vir do que os intérpretes fizeram em 127 mil frases.
- **Rotulagem automática (alinhamento por lema):**
  1. Processar a frase em português com o spaCy: lema e classe de cada palavra.
  2. Quebrar a glosa em sinais e normalizar cada um com a notação do corpus ([relatório técnico do VLibrasBD](https://zenodo.org/records/15399589)): remover `[PONTO]`, `[INTERROGAÇÃO]`, `[EXCLAMAÇÃO]` e `(+)`/`(-)`; `NÃO_X` vira {`NÃO`, `X`}; `1S_X_2S` vira `X`; `X&Y` vira `X`; compostos com `_` contam inteiros e por partes.
  3. Comparar com `slug()` (sem acento, maiúsculas): a palavra é `MANTER` se o lema ou a forma escrita aparece entre os sinais da glosa; senão, `DESCARTAR`.
- **Ruído conhecido:** quando o intérprete usou um sinal com outro nome (sinônimo, paráfrase), a palavra sai `DESCARTAR` sem ter sido descartada de fato. **Medir antes de treinar:** a equipe confere uma amostra de 200 palavras e registra a taxa de rótulo errado no notebook de preparação. Não exige saber Libras: é conferir se a glosa contém a palavra.
- **Atributos (do spaCy e da frase):** classe gramatical (UPOS), morfologia (gênero, número, tempo, forma verbal, `Polarity`, `PronType`), relação de dependência, se é stopword, posição relativa na frase, tamanho da frase, classe gramatical das palavras vizinhas, tipo de frase (pela pontuação) e o lema (one-hot dos ~2.000 mais frequentes + "outro").
- **Métrica principal:** F1-macro, por causa do desbalanceamento esperado entre as classes. **Secundárias:** ROC-AUC, PR-AUC, acurácia por classe gramatical.
- **Linha de base sem ML:** a lista fixa atual, avaliada no mesmo conjunto de teste. O modelo só se justifica se superá-la.

### T2 — desambiguar homônimos (extensão)

- **Unidade:** palavra cujo lema aparece no corpus com dois ou mais sentidos marcados com `&` (ex.: `BANCO&DINHEIRO`, `BANCO&ASSENTO`).
- **Classes:** o sentido (multiclasse, por lema ou com o lema como atributo).
- **Atributos:** palavras do contexto (janela de ±5, TF-IDF) e classe gramatical.
- **Viabilidade:** a EDA conta quantos lemas têm exemplos suficientes por sentido. Se forem poucos, T2 fica como estudo de caso de 3 a 5 lemas.

### T3 — negação e intensidade (extensão)

- **Negação:** para cada verbo precedido de "não", prever se a glosa usa a forma incorporada (`NÃO_X`) ou `NÃO` separado.
- **Intensidade:** para cada adjetivo ou advérbio modificado ("muito", "pouco"), prever se a glosa usa `(+)` ou `(-)`.
- **Viabilidade:** depende das contagens na EDA e de o player do VLibras interpretar essas marcas (a testar).

### O que estas tarefas não resolvem

- **Ordem dos sinais.** T1 a T3 decidem **quais** sinais entram e **com que marca**, mas mantêm a ordem do português. A ordem fica para o modelo avançado opcional (PTT5/ByT5 ajustado no corpus) ou para trabalho futuro. Isso precisa constar na apresentação.
- **Uso do espaço e expressões não manuais** além das marcas da notação: dependem do player.
- **Correção linguística.** As métricas medem proximidade às glosas dos intérpretes, não aprovação de pessoas surdas. Continua valendo a regra de chamar a saída de "sequência de sinais".

## Dados

| Item | Valor |
| --- | --- |
| Dataset | VLibrasBD / `pt-br2libras-gloss`, Mendeley Data, DOI [10.17632/ryj88ckjww.2](https://data.mendeley.com/datasets/ryj88ckjww/2) |
| Tamanho | 127.349 pares (72.312 de domínio geral e ~55.037 de textos do gov.br) |
| Formato | CSV UTF-8 com colunas `pt-br`, `libras-gloss`, `is_government_source`, `english_translation` |
| Produção | Glosado à mão por intérpretes certificados ([Lima et al., 2025, *Data in Brief*](https://pmc.ncbi.nlm.nih.gov/articles/PMC12341731/)) |
| Licença | **CC BY-SA 4.0**: atribuição obrigatória; derivados do dataset seguem a mesma licença. **[a confirmar com o professor]** o efeito do share-alike nos modelos treinados |
| Versionamento | O CSV **não entra no git** (tamanho). A tarefa de ingestão baixa o arquivo e confere o hash |

- **Divisão:** separar **10% das frases** como teste final, intocado até o fim. Os 90% restantes vão para a validação cruzada.
- **Agrupar por frase:** palavras da mesma frase nunca ficam em dobras diferentes (`StratifiedGroupKFold`, grupo = id da frase). Sem isso, há vazamento entre treino e validação.
- **Fora do domínio:** a coluna `is_government_source` permite treinar num domínio e testar no outro. Mede generalização.
- **Tamanho para treino:** ~127 mil frases × ~13 palavras ≈ 1,6 milhão de palavras. Random Forest e, sobretudo, KNN e Optuna ficam caros nesse volume. Usar uma **amostra estratificada** (ex.: 200 mil palavras) para KNN e para a busca de hiperparâmetros, e registrar a decisão no notebook.

### Notebook de EDA (`notebooks/01-eda-vlibrasbd.ipynb`)

- Tamanho das frases e das glosas; razão palavras/sinais (o artigo dá 12,83 e 7,61 em média).
- Distribuição de `MANTER`/`DESCARTAR`, no total e por classe gramatical.
- Palavras mais descartadas e mais mantidas; comparação com a lista `FUNCTION_WORDS`.
- Contagem de marcas: `&`, `NÃO_`, `(+)`, `(-)`, direcionais, tipos de frase.
- Diferenças entre o domínio geral e o do governo.
- **Cobertura do player:** quantos sinais do corpus existem no dicionário do VLibras. Decide se o vocabulário do Sinaliza cresce além dos 210 sinais.

### Notebook de preparação (`notebooks/02-preparacao.ipynb`)

Limpeza (frases vazias, duplicadas, glosas com marcas desconhecidas), normalização (`slug()`, notação das glosas), rotulagem T1, encoding dos atributos, valores ausentes (palavra sem lema ou classe gramatical vira categoria própria), desbalanceamento (`class_weight` contra reamostragem) e a **justificativa** de cada decisão. Inclui a conferência manual da amostra de 200 rótulos.

## Modelos e experimentos (T1)

| Etapa | O que fazer | Registro no MLflow |
| --- | --- | --- |
| Baseline | **Regressão Logística** (`class_weight="balanced"`). Justificativa: atributos categóricos, problema binário, modelo interpretável (os coeficientes mostram quais classes gramaticais os intérpretes descartam) | Parâmetros, F1-macro, ROC-AUC, PR-AUC, matriz de confusão, modelo |
| Linha de base sem ML | Lista fixa atual (`FUNCTION_WORDS`) no mesmo teste | Mesmas métricas, como run separada |
| Comparação | **Árvore de Decisão, Random Forest e KNN** (KNN com atributos reduzidos, ex.: TruncatedSVD) | Um run por modelo; matriz de confusão, curvas ROC e PR sobrepostas, importância de atributos (árvores) |
| Análise crítica | Erros por classe gramatical, exemplos de falsos positivos e negativos, custo de cada modelo | Notebook ou relatório como artefato |
| Otimização | **Optuna** (TPE) sobre o melhor modelo, otimizando o F1-macro médio da validação cruzada; espaço de busca documentado (ex.: Random Forest: `n_estimators`, `max_depth`, `min_samples_leaf`, `max_features`, `class_weight`) | Um run por tentativa (aninhados num run pai) e gráficos do Optuna (histórico, importância dos hiperparâmetros) |
| Validação cruzada | `StratifiedGroupKFold` com k=5, agrupado por frase; média e desvio-padrão por dobra; curva de aprendizado; F1 de treino contra validação (sobreajuste); teste fora do domínio (geral → governo) | Métricas por dobra e agregadas |
| Teste final | Melhor modelo nos 10% separados, uma única vez | Run final, registrado no Model Registry |

### Avaliação ponta a ponta (texto → glosa)

No conjunto de teste, comparar três sistemas contra as glosas dos intérpretes:

1. o pipeline atual (lista fixa);
2. o pipeline com o classificador T1 (mais T2 e T3, se prontos);
3. o `vlibras-translate` local (linha de base externa; precisa de Docker ou WSL por causa do hunspell).

Métricas: **SacreBLEU com tokenização desligada**, chrF e WER, como recomendam [Müller et al. (2023)](https://aclanthology.org/2023.acl-short.60/). O resultado deve ser descrito como "proximidade às glosas dos intérpretes".

O **PTT5/ByT5** ajustado no corpus entra aqui como quarto sistema, **só se houver tempo e GPU**. É o único dos quatro que poderia mudar a ordem dos sinais.

## Integração com a solução

- **API (`POST /translate`):** a análise passa a usar o spaCy. O classificador T1 decide quais palavras viram sinal, no lugar de `FUNCTION_WORDS`. As palavras mantidas seguem para o vocabulário (tabela, lema, aproximação sinalizada). T2 escolhe o sentido dos homônimos. A resposta passa a trazer a probabilidade de cada decisão e a versão do modelo.
- **Modelo carregado do MLflow:** a API carrega o modelo registrado (por exemplo, o estágio "Production" do Model Registry, ou o artefato exportado). Sem modelo disponível, volta à lista fixa e avisa na resposta.
- **Glosas restritas ao player:** só saem glosas que existem no dicionário do VLibras baixado localmente; as demais são sinalizadas na interface, como hoje.
- **Consumo de dados novos:** cada frase enviada à API é gravada no banco (texto, palavras, decisões, probabilidades, latência, versão do modelo). Um DAG do Airflow processa periodicamente as frases novas e calcula indicadores para o painel. Um script simulador de uso envia frases à API durante a demonstração. Ele faz o papel de "fonte de dados novos" que a rubrica atribui ao sistema embarcado.
- **Privacidade:** o texto digitado pode conter dado pessoal (inclusive de saúde, pelo contexto de uso). Antes de gravar, definir finalidade, prazo de retenção e aviso na interface (ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md)).

## Pipeline no Airflow

| DAG | Tarefas | Quando roda |
| --- | --- | --- |
| `vlibrasbd_ingestao` | baixar o CSV → conferir o hash → carregar no banco (tabela bruta) | Manual ou na subida do ambiente |
| `preparacao_t1` | limpar → processar com o spaCy → rotular → gerar atributos → dividir treino/teste → salvar os conjuntos | Depois da ingestão |
| `treino_t1` | treinar os modelos → registrar no MLflow → registrar o melhor no Model Registry | Manual (ou depois da preparação) |
| `monitoramento` | ler as frases novas do banco → indicadores (taxa de palavras sem sinal, distribuição das probabilidades, latência, versão do modelo) → tabela do painel | A cada hora |

## Infraestrutura (Docker Compose)

Um único `docker compose up` sobe:

| Serviço | Papel |
| --- | --- |
| `postgres` | Banco da aplicação (corpus, conjuntos preparados, frases recebidas, indicadores) e backend do MLflow e do Airflow (bancos separados) |
| `mlflow` | Tracking server e Model Registry, com volume para artefatos |
| `airflow` | Scheduler e interface (modo standalone ou LocalExecutor) com os DAGs montados |
| `api` | FastAPI, já existe; passa a carregar o modelo do MLflow e a gravar as frases |
| `web` | Front e player do VLibras, já existe |
| `dashboard` | Painel (proposta: Streamlit) |

Atenção ao consumo de memória: o Airflow sozinho pede alguns GB. Documentar o mínimo em [`14-como-rodar-e-testar.md`](14-como-rodar-e-testar.md) quando estiver montado. **Versões a definir na implementação.**

## Painel

Painel (proposta: Streamlit, lendo o banco e a API) com:

- frases recebidas por hora e latência da API;
- palavras sem sinal no vocabulário e taxa de descarte;
- distribuição das probabilidades do modelo e casos de baixa confiança;
- últimas inferências (frase, decisões por palavra, glosa final);
- versão do modelo em uso e métricas do último treino (lidas do MLflow);
- estado dos serviços (API, banco, MLflow).

## Mapa: requisito → entrega

| Requisito da disciplina | Entrega no Sinaliza | Situação em 2026-10-28 |
| --- | --- | --- |
| Bootstrap dataset + persistência | VLibrasBD ingerido no Postgres | Falta |
| Aquisição por sistema embarcado + MQTT | **Não se aplica ao grupo** (ver abaixo) | — |
| Pipeline no Airflow + EDA + preparação | DAGs `vlibrasbd_ingestao` e `preparacao_t1`; notebooks 01 e 02 | Falta |
| Baseline com justificativa no MLflow | Regressão Logística em T1, mais a lista fixa como referência sem ML | Falta |
| Três modelos comparados, com gráficos | Árvore de Decisão, Random Forest e KNN; matriz de confusão, ROC, PR | Falta |
| Otimização de hiperparâmetros | Optuna sobre o melhor modelo | Falta |
| Validação cruzada e generalização | `StratifiedGroupKFold` por frase, curva de aprendizado, teste fora do domínio | Falta (a ideia de validar em dado não visto já existe no modelo de movimento) |
| Modelo integrado ao pipeline | API com o classificador; frases gravadas e processadas pelo DAG `monitoramento` | Falta |
| Docker Compose com tudo | `postgres`, `mlflow`, `airflow`, `api`, `web`, `dashboard` | Parcial: só `api` e `web` |
| Painel | Streamlit com indicadores e inferências | Falta |
| Apresentação integrada | Demonstração ponta a ponta com o simulador de uso | Falta |

## Requisitos que não se aplicam

O Carlos informou em 2026-10-28 que **o requisito de sistema embarcado não é do grupo**. Por consequência, este plano também deixa de fora o **broker MQTT**, que na rubrica serve ao embarcado. A fonte de dados novos passa a ser a própria API (frases enviadas pela interface ou pelo simulador). **[a confirmar com o professor]**: se o broker MQTT também é dispensado no Docker Compose e no painel.

## Fases (ordem sugerida)

Cada fase termina com algo demonstrável. As fases 7 a 10 podem começar em paralelo com as primeiras.

- [ ] **0. Validar com o professor:** classificação texto → glosa como problema de ML; embarcado e MQTT fora; licença CC BY-SA do corpus.
- [ ] **1. Dados:** baixar o VLibrasBD, script de ingestão com hash, tabela no Postgres, notebook de EDA.
- [ ] **2. Rotulagem e preparação:** alinhamento por lema (T1), conferência manual de 200 rótulos, atributos, divisão treino/teste agrupada por frase, notebook de preparação com justificativas.
- [ ] **3. Baseline:** Regressão Logística e lista fixa, ambas no MLflow.
- [ ] **4. Comparação:** Árvore de Decisão, Random Forest e KNN no MLflow; gráficos; análise crítica.
- [ ] **5. Otimização:** Optuna sobre o melhor modelo, todos os trials no MLflow.
- [ ] **6. Validação:** k-fold agrupado, estabilidade entre dobras, sobreajuste, fora do domínio, teste final; avaliação ponta a ponta contra a lista fixa e o `vlibras-translate`.
- [ ] **7. Airflow:** os quatro DAGs.
- [ ] **8. Integração:** classificador na API, modelo vindo do MLflow, frases gravadas no banco, simulador de uso.
- [ ] **9. Docker Compose completo.**
- [ ] **10. Painel.**
- [ ] **11. Apresentação:** demonstração ponta a ponta, decisões técnicas e limitações (ordem dos sinais, ausência de validação surda, ruído da rotulagem).
- [ ] **Extensões, se houver tempo:** T2, T3 e o PTT5/ByT5 como quarto sistema.

## Estrutura de pastas (proposta)

```
Sinaliza/
  textgloss/            pacote Python do ML texto → glosa
    corpus.py           leitura e normalização do VLibrasBD
    align.py            rotulagem T1 (e T2/T3) a partir das glosas
    features.py         atributos do spaCy
    train.py            treino, MLflow, Optuna, validação cruzada
    infer.py            carregamento do modelo e decisão por palavra (usado pela API)
    tests/
  pipeline/dags/        DAGs do Airflow
  notebooks/            01-eda-vlibrasbd.ipynb, 02-preparacao.ipynb, 03-analise-modelos.ipynb
  dashboard/            painel
  model/                gerador de movimento (experimento anterior, mantido)
```

## Riscos

| Risco | Mitigação |
| --- | --- |
| Rótulos ruidosos na rotulagem por lema (sinônimos do intérprete) | Medir na amostra de 200; reportar a taxa; considerar a lista de sinônimos do próprio VLibras |
| Classes desbalanceadas | F1-macro, `class_weight`, PR-AUC |
| Volume grande para KNN, Random Forest e Optuna | Amostra estratificada documentada |
| Vazamento entre dobras (palavras da mesma frase) | Agrupar por frase |
| O classificador melhora a escolha das palavras, mas a ordem continua a do português | Declarar o limite; PTT5 como extensão |
| Share-alike (CC BY-SA) e atribuição | Atribuir na interface e no README; confirmar com o professor |
| Peso da infraestrutura (Airflow, MLflow, Postgres) na máquina da equipe | Documentar a memória mínima; LocalExecutor ou standalone |
| Sem validação por pessoa surda | Continua sendo o maior risco do projeto (ver `16-riscos-e-questoes-abertas.md`) |

## Relação com o relatório de pesquisa

A conclusão do relatório ([`Pesquisas/`](../Pesquisas/) e a aba "Relatório de Pesquisa" do documento do G10) descreve o **PTT5 como peça central** do método. Com este plano, o núcleo de ML passa a ser a classificação, e o PTT5 vira extensão opcional. **A conclusão do relatório precisa ser ajustada** para ficar coerente.
