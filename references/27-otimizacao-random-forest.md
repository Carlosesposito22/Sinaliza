# Otimização de hiperparâmetros: Random Forest com Optuna (fase 5)

Entregável 5 do [checklist](23-checklist-requisitos-ml.md). Análise completa, com gráficos, em [`notebooks/04-otimizacao-random-forest.ipynb`](../notebooks/04-otimizacao-random-forest.ipynb). Modelos anteriores: [`25-baseline-t1.md`](25-baseline-t1.md) e [`26-comparacao-de-modelos-t1.md`](26-comparacao-de-modelos-t1.md).

**Onde está o ML:** o Optuna escolhe configurações; o Random Forest é o modelo nosso que, treinado com os rótulos dos intérpretes, decide quais palavras viram sinal.

## Por que o Random Forest

Foi escolha do grupo (2026-11-02). Na comparação ele ficou em 0,852, atrás da regressão (0,876), mas com hiperparâmetros fixos e muitos a ajustar; a Regressão Logística só tem `C`.

## Estratégia

| Item | Valor |
| --- | --- |
| Método | Otimização bayesiana TPE (Optuna), semente 42 |
| Objetivo | F1-macro **médio** da validação cruzada |
| Validação cruzada | `StratifiedGroupKFold`, 3 dobras, agrupada por frase |
| Dados da busca | amostra de 6.000 frases inteiras (~76 mil palavras), do conjunto de ajuste |
| Limite | 25 tentativas ou 40 minutos (foram feitas 25) |
| Modelo final | refeito com os melhores parâmetros nas 1,3 milhão de palavras e avaliado na mesma validação dos demais |

Espaço de busca: `n_estimators` 50–200; `max_depth` 10–60; `min_samples_leaf` 1–30 (log); `max_features` `sqrt` ou fração 0,02–0,5 (log); `class_weight` `balanced`, `balanced_subsample` ou nenhum; `criterion` `gini` ou `entropy`.

## Resultado

Melhores parâmetros (tentativa 13): `n_estimators=154`, `max_depth=56`, `min_samples_leaf=3`, `max_features=0,151`, `class_weight="balanced"`, `criterion="gini"`. F1-macro na CV da amostra: **0,8712**.

| Modelo (validação) | F1-macro | ROC-AUC | PR-AUC | Rev. `DESCARTAR` | F1 treino | Treino | Prever 146 mil |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random Forest (padrão) | 0,852 | 0,921 | 0,911 | 0,770 | 0,853 | 98 s | 0,8 s |
| **Random Forest otimizado** | **0,884** | **0,947** | 0,939 | **0,832** | 0,900 | 1.520 s | 1,1 s |
| Regressão Logística | 0,876 | 0,944 | 0,942 | 0,824 | 0,877 | 41 s | 0,4 s |
| Árvore de Decisão | 0,870 | 0,914 | 0,884 | 0,813 | 0,880 | 86 s | 0,4 s |

## O que aprendemos

1. **+3,2 pontos de F1-macro** sobre o padrão; o modelo passa a ser o melhor da comparação.
2. O ganho vem sobretudo de **`max_features`**: o padrão `sqrt` (~2% das colunas) é ruim em one-hot esparso; frações de 10% a 40% dominam o topo. As 7 tentativas com `sqrt` ficaram entre 0,838 e 0,852; as 18 com fração, entre 0,851 e 0,871.
3. As dez melhores tentativas estão **empatadas** (0,867–0,871, desvio entre dobras 0,002–0,003): a configuração escolhida é uma boa região, não um ótimo único. Já a primeira tentativa (0,869) estava perto do melhor.
4. **Custo alto:** o treino final levou ~25 minutos (15 vezes o padrão). A predição segue barata.
5. **Sinal moderado de sobreajuste:** 0,900 no treino contra 0,884 na validação (0,016), contra 0,001 da regressão.

## Limites

- A vantagem sobre a Regressão Logística é de 0,8 ponto numa única validação; só a validação cruzada (fase 6) diz se é estável.
- A busca usou amostra (CV 0,871) e o modelo final usa o conjunto completo (0,884): os parâmetros ótimos podem diferir.
- Ruído de rótulo não medido (conferência manual pendente).
- O teste final (10% das frases) continua intocado.
- A escolha do modelo que vai para a API deve pesar estabilidade, custo e explicabilidade, não só o F1.

## No MLflow

Experimento `t1-manter-descartar`: run pai `optuna-random-forest` (parâmetros do estudo, espaço de busca, histórico, importância dos hiperparâmetros, tabela de tentativas e melhores parâmetros), 25 runs filhas `trial-000` a `trial-024` (parâmetros, F1 por dobra, média, desvio e tempo) e a run `random-forest-otimizado` (modelo final, métricas, curvas, importância de atributos).

## Como reproduzir

Com `docker compose up -d postgres mlflow` e a preparação feita (demora cerca de 40 minutos, quase todo no reajuste final):

```bash
textgloss/.venv/Scripts/python -m textgloss.tune
```
