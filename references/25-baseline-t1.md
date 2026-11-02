# Baseline do T1 (fase 3)

Entregável 3 do [checklist](23-checklist-requisitos-ml.md): modelo baseline, justificativa, métricas em validação e registro no MLflow. Contexto da pipeline em [`24-pipeline-de-dados-ponta-a-ponta.md`](24-pipeline-de-dados-ponta-a-ponta.md).

**Onde está o ML aqui:** a Regressão Logística é o primeiro modelo **treinado por nós**; ela aprende, com os rótulos extraídos das glosas dos intérpretes, quais palavras de uma frase viram sinal. A lista fixa é só a referência **sem ML** (o que a API faz hoje).

## Resultado (conjunto de validação)

Validação = 10% das frases do treino, sorteadas por frase (semente 42). **O conjunto de teste final continua intocado.** 1.309.032 palavras para ajuste, 145.336 para validação.

| Métrica | Lista fixa (sem ML) | Regressão Logística |
| --- | --- | --- |
| **F1-macro (principal)** | 0,822 | **0,876** |
| Acurácia | 0,826 | 0,877 |
| ROC-AUC | 0,821 | 0,944 |
| PR-AUC | 0,764 | 0,942 |
| F1 `MANTER` / `DESCARTAR` | 0,847 / 0,797 | 0,888 / 0,864 |
| Revocação `DESCARTAR` | 0,722 | 0,824 |

- A Regressão Logística supera a lista fixa em **+5,4 pontos de F1-macro**. O maior ganho está em `DESCARTAR`: a lista deixa passar palavras que os intérpretes descartam (revocação 0,72 → 0,82).
- ROC-AUC e PR-AUC da lista fixa são calculados sobre a decisão binária (não há pontuação contínua), então não são comparáveis em pé de igualdade com as do modelo.
- **Sem sinal de sobreajuste:** F1-macro de 0,877 no treino contra 0,876 na validação (diferença de 0,001). Por outro lado, o modelo é simples e pode estar **subajustado**; é o que a comparação da fase 4 vai mostrar.
- Os números são **proximidade às glosas dos intérpretes**, não correção linguística nem aprovação de pessoas surdas.

## Justificativa da escolha

- **Problema:** classificação binária por palavra com atributos majoritariamente categóricos (classe gramatical, morfologia, vizinhos, lema). A Regressão Logística é o baseline clássico para esse formato.
- **Interpretável:** os coeficientes mostram o que empurra uma palavra para `MANTER` ou `DESCARTAR`, o que ajuda a explicar o modelo na apresentação e a achar ruído nos rótulos.
- **Barata e estável:** treina em ~1 minuto com 1,3 milhão de exemplos; é a régua mínima que Árvore de Decisão, Random Forest e KNN (fase 4) precisam superar.
- **`class_weight="balanced"`:** as classes são quase equilibradas (52% `MANTER`), mas o peso evita que a classe maior domine sem custo.
- **Lista fixa como referência sem ML:** responde "o ML vale a pena?" com o comportamento real da API.

## Configuração

| Item | Valor |
| --- | --- |
| Modelo | `LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=1000)` |
| Atributos | 13 categóricos (one-hot), 4 numéricos (padronizados), lema (one-hot dos 2.000 mais frequentes + `infrequente`) |
| Pré-processamento | `ColumnTransformer` dentro de um `Pipeline`, ajustado só no treino |
| Experimento no MLflow | `t1-manter-descartar` (runs `lista-fixa` e `regressao-logistica`) |
| Registrado | parâmetros, hash do corpus, tamanhos, métricas de treino e validação, matriz de confusão, curvas ROC e PR, coeficientes (imagem e CSV), modelo |

Um primeiro treino com `max_iter=300` não convergiu; subimos para 1.000 e a run foi refeita (as runs antigas foram apagadas).

## O que os coeficientes mostram

Os maiores coeficientes negativos (empurram para `DESCARTAR`) incluem `para`, `art.`, `nº`, `°`, `i`, `iii`, `xix`, `d.` e `preciso`; os positivos incluem `tom`, `depois`, `consultar`, `antes`, `hoje`, `ontem`. Parte disso é linguisticamente razoável (símbolos, numerais romanos e abreviações de textos jurídicos são omitidos). Outra parte é **ruído de rótulo** esperado: `preciso` aparece porque o spaCy erra o lema e a glosa usa outro sinal. Isso reforça a conferência manual das 200 palavras, ainda pendente.

## Como reproduzir

Com o Postgres e o MLflow no ar (`docker compose up -d postgres mlflow`) e a preparação feita:

```bash
textgloss/.venv/Scripts/python -m textgloss.train baseline
```

A interface do MLflow fica em http://localhost:5000. A URL do servidor vem de `MLFLOW_TRACKING_URI` (padrão `http://localhost:5000`).

## Limites

- A validação é um único sorteio; a estabilidade entre dobras só vem na fase 6 (`StratifiedGroupKFold`).
- As métricas ainda carregam o ruído de rótulo da rotulagem automática, que não foi medido.
- O modelo não decide a **ordem** dos sinais.
