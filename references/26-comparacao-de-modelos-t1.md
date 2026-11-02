# Comparação de modelos do T1 (fase 4)

Entregável 4 do [checklist](23-checklist-requisitos-ml.md): pelo menos três modelos comparados nas mesmas métricas, tudo no MLflow, com visualizações e análise crítica. A análise completa, com gráficos, está em [`notebooks/03-comparacao-modelos.ipynb`](../notebooks/03-comparacao-modelos.ipynb); o baseline em [`25-baseline-t1.md`](25-baseline-t1.md).

**Onde está o ML:** os quatro modelos abaixo são treinados por nós sobre os rótulos extraídos das glosas dos intérpretes. A lista fixa é a referência sem ML.

## Resultado (validação, mesma do baseline)

| Modelo | F1-macro | ROC-AUC | PR-AUC | Rev. `DESCARTAR` | F1 treino | Treino | Prever 146 mil palavras |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lista fixa (sem ML) | 0,822 | 0,821* | 0,764* | 0,722 | | | |
| **Regressão Logística** | **0,876** | **0,944** | **0,942** | **0,824** | 0,877 | 41 s | 0,4 s |
| Árvore de Decisão | 0,870 | 0,914 | 0,884 | 0,813 | 0,880 | 86 s | 0,4 s |
| Random Forest | 0,852 | 0,921 | 0,911 | 0,770 | 0,853 | 98 s | 0,8 s |
| KNN | 0,846 | 0,895 | 0,867 | 0,781 | 0,984 | 4 s | 25,6 s |

\* calculados sobre a decisão binária, não comparáveis em pé de igualdade.

Configurações (hiperparâmetros **fixos**, ainda sem busca):

- Regressão Logística: `C=1`, `class_weight="balanced"`, `lbfgs`, `max_iter=1000`.
- Árvore de Decisão: `max_depth=25`, `min_samples_leaf=20`, `class_weight="balanced"`.
- Random Forest: 100 árvores, `max_depth=30`, `min_samples_leaf=10`, `max_features="sqrt"`, `class_weight="balanced"`.
- KNN: 25 vizinhos, pesos por distância, atributos reduzidos por TruncatedSVD (50 componentes), treinado em amostra de 200 mil palavras.

## Análise crítica (resumo)

1. **O ML vale a pena**: todos superam a lista fixa, mas por 3 a 5 pontos de F1-macro, não por muito mais.
2. **A Regressão Logística é a melhor, a mais barata e a mais explicável.** A Árvore fica a 0,6 ponto e dá regras legíveis.
3. **O Random Forest ficou abaixo da árvore única**, provavelmente por `max_features="sqrt"` sobre 2.000+ colunas esparsas e hiperparâmetros fixos. É um resultado sem ajuste, que o Optuna pode mudar.
4. **O KNN sobreajusta** (0,984 no treino, 0,846 na validação) e é 60 vezes mais lento para prever: não serve para a API.
5. **Onde o ML ganha:** pronomes, verbos, advérbios, substantivos e adjetivos, classes que uma lista de palavras funcionais não cobre.
6. **Erros restantes:** os quatro modelos erram juntos em 7,6% das palavras, em geral lemas ambíguos (`eu`, `mais`, `ter`, `seu`, `ele`, `de`, `que`, `ou`), e há ruído de rótulo (`solicitar`).
7. **Limites:** validação de um único sorteio, hiperparâmetros fixos, ruído de rótulo não medido, KNN em amostra menor.

## Visualizações

No MLflow (run `comparacao-modelos` e uma run por modelo): matriz de confusão, curvas ROC e precisão-revocação (por modelo e sobrepostas), F1-macro comparado, importância de atributos (árvores) e coeficientes (regressão). No notebook 03: as mesmas, mais F1 por classe gramatical e exemplos de erros.

## Como reproduzir

Com `docker compose up -d postgres mlflow` e a preparação feita:

```bash
textgloss/.venv/Scripts/python -m textgloss.train modelos
```

```bash
textgloss/.venv/Scripts/python -m textgloss.train comparar
```

## Decisão em aberto para a fase 5

O plano manda otimizar "o melhor modelo". A regressão é a melhor hoje, mas só tem `C` para ajustar. A Árvore e o Random Forest têm muitos hiperparâmetros e estão provavelmente longe do seu limite. Escolher qual otimizar (ou os dois) é decisão do grupo.
