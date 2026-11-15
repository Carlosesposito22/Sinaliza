# Validação cruzada e generalização (fase 6)

Entregável 6 do [checklist](23-checklist-requisitos-ml.md). Análise completa, com gráficos, em [`notebooks/05-validacao-e-generalizacao.ipynb`](../notebooks/05-validacao-e-generalizacao.ipynb). Modelos: [`25-baseline-t1.md`](25-baseline-t1.md), [`26-comparacao-de-modelos-t1.md`](26-comparacao-de-modelos-t1.md), [`27-otimizacao-random-forest.md`](27-otimizacao-random-forest.md).

**Onde está o ML:** avaliamos os dois melhores modelos treinados por nós, a **Regressão Logística** (0,876 na validação) e o **Random Forest otimizado** (0,884), quanto a estabilidade, sobreajuste e generalização. O teste final foi usado **uma única vez**, para o Random Forest otimizado (escolha do grupo, 2026-11-02).

## Estratégia de validação e por que ela foi escolhida

A especificação de AM pede holdout, validação cruzada (k-fold ou estratificada) e Leave-One-Out "quando aplicável", com a estratégia justificada. O que usamos em cada camada:

| Camada | O que é | Para quê |
| --- | --- | --- |
| **Holdout de teste** | 10% das **frases**, sorteadas dentro de cada domínio (geral e governo), semente 42 (`prepare.split_by_sentence`). 12.732 frases, 160.897 palavras | Estimativa final, usada **uma única vez** (o código recusa uma segunda execução) |
| **Holdout de validação** | 10% das frases do treino (`GroupShuffleSplit` por `frase_id`, semente 42). 1.309.032 palavras de ajuste, 145.336 de validação | Comparar modelos (fases 3 e 4) sem tocar no teste |
| **Validação cruzada** | `StratifiedGroupKFold`, k=5 (k=3 dentro do Optuna), agrupada por frase e estratificada pelo rótulo | Medir a estabilidade e escolher hiperparâmetros |
| **Fora do domínio** | Treina num domínio e avalia no outro (é um *leave-one-group-out* com os dois domínios como grupos) | Medir a generalização para texto de outro assunto |

**Por que agrupar por frase.** As palavras de uma mesma frase são muito parecidas entre si (mesma estrutura, mesmos vizinhos, mesmo `tam_frase`). Se a divisão fosse por palavra, o modelo veria no treino as vizinhas de cada palavra da validação e o resultado sairia otimista. Por isso **toda** divisão (teste, validação, dobras) é feita por frase.

**Por que estratificar.** As classes estão quase equilibradas (52,5% `MANTER`, notebook 01), mas a estratificação garante a mesma proporção em todas as dobras e reduz a variância da comparação entre elas sem custo extra.

**Por que k=5.** Com ~25 mil frases por amostra, cada dobra de validação tem ~5 mil frases (~64 mil palavras), o bastante para estimar o F1-macro com pouca variância, e 5 treinos do Random Forest otimizado cabem no tempo disponível. No Optuna usamos k=3 porque são 25 tentativas × k treinos.

**Por que não usamos Leave-One-Out (não se aplica).** O LOO treina um modelo por exemplo e testa só nele. Ele faz sentido em bases pequenas, onde cada exemplo deixado de fora pesa no treino. Aqui não se aplica por três motivos:

1. **Custo inviável.** São 1,3 milhão de palavras de ajuste, ou seja, 1,3 milhão de treinos. Só com a Regressão Logística (41 s por treino) seriam cerca de 1,7 ano de processamento; com o Random Forest otimizado (~25 min por treino), mais de 60 anos. Mesmo a versão por frase (*leave-one-sentence-out*, ~115 mil grupos) é inviável.
2. **Vazamento.** O LOO por palavra deixaria as outras palavras da mesma frase no treino, justamente o vazamento que o agrupamento evita.
3. **Sem ganho estatístico.** O LOO serve para reduzir o viés da estimativa quando há poucos dados. Com centenas de milhares de exemplos, o k-fold já tem viés e variância desprezíveis: o desvio entre dobras foi de **0,0013** (cerca de 0,15% da média) e o teste final (0,885) bateu com a validação (0,884).

O que a ideia do LOO traria (avaliar em algo que o modelo nunca viu, um grupo de cada vez) já está coberto, na escala certa, pelo agrupamento por frase e pelo teste **fora do domínio**, que é um *leave-one-group-out* com os domínios como grupos.

## Resultados

### Validação cruzada (k=5, `StratifiedGroupKFold` agrupada por frase)

| Modelo | F1-macro (média ± desvio) | Intervalo | ROC-AUC | PR-AUC | Gap treino − validação |
| --- | --- | --- | --- | --- | --- |
| Random Forest otimizado | **0,8789 ± 0,0013** | 0,8768 – 0,8804 | 0,9425 | 0,935 | 0,022 |
| Regressão Logística | 0,8747 ± 0,0014 | 0,8731 – 0,8759 | 0,9426 | 0,940 | 0,002 |

O Random Forest vence em 5 de 5 dobras, por 0,0043 em média (desvio 0,0008). Amostra de 25.000 frases (~320 mil palavras), as mesmas dobras para os dois modelos.

### Curva de aprendizado (treino em 2% a 100% das frases, validação fixa)

| Palavras de treino | Regressão: treino / validação | Random Forest: treino / validação |
| --- | --- | --- |
| 26 mil (2%) | 0,880 / 0,866 | 0,900 / 0,865 |
| 130 mil (10%) | 0,879 / 0,874 | 0,902 / 0,877 |
| 328 mil (25%) | 0,876 / 0,875 | 0,901 / 0,881 |
| 653 mil (50%) | 0,876 / 0,875 | 0,901 / 0,883 |
| 1,3 milhão (100%) | 0,877 / 0,876 | 0,900 / 0,884 |

### Fora do domínio (treino em um domínio, avaliação em cada um)

| Avaliado em | Regressão: próprio → outro | Random Forest: próprio → outro |
| --- | --- | --- |
| geral | 0,873 → 0,852 (−0,021) | 0,886 → 0,854 (−0,032) |
| governo | 0,889 → 0,858 (−0,031) | 0,890 → 0,848 (−0,042) |

## Conclusões

1. **Estáveis:** o desvio entre dobras é de ~0,15% da média nos dois; a validação única das fases anteriores não era sorte.
2. **Random Forest melhor em F1 por pouco** (+0,4 ponto, consistente), mas **sem vantagem em ROC-AUC** e com PR-AUC menor.
3. **Regressão: subajuste leve.** Estaciona em 25% dos dados; mais dados não ajudam.
4. **Random Forest: sobreajuste moderado, ainda aprende com mais dados.** O gap cai de 0,035 para 0,016 e a validação segue subindo.
5. **Generalização fraca nos dois:** perdem de 2 a 4 pontos fora do domínio; a regressão perde menos (média 0,026 contra 0,037). Importa porque o produto recebe texto de qualquer assunto.
6. **Não há vencedor claro:** o Random Forest ganha em F1 dentro do domínio; a regressão é mais robusta, mais de 35 vezes mais rápida de treinar e explicável.

## Limites

CV em amostra (valores absolutos menores); Random Forest ajustado pelo Optuna com dados do mesmo conjunto de treino (leve vantagem), regressão não otimizada; ruído de rótulo não medido; a queda fora do domínio mistura mudança de domínio com metade dos dados; avaliação ponta a ponta (BLEU/chrF/WER contra o `vlibras-translate`) não feita.

## No MLflow

Runs `validacao-cruzada` (com `cv-<modelo>` filhas, F1 por dobra e `cv_por_dobra.png`), `curva-aprendizado` (`curva_aprendizado.png`) e `fora-do-dominio` (`fora_do_dominio.png`).

## Como reproduzir

```bash
textgloss/.venv/Scripts/python -m textgloss.validate cv --frases 25000
```

```bash
textgloss/.venv/Scripts/python -m textgloss.validate curva
```

```bash
textgloss/.venv/Scripts/python -m textgloss.validate dominio
```

Levam cerca de 1 hora no total (a curva e o domínio são lentos por causa do Random Forest).

## Teste final (feito)

Escolha do grupo: **Random Forest otimizado**. `python -m textgloss.validate teste --modelo random-forest-otimizado` treinou o modelo em **todo** o treino (1,45 milhão de palavras) e o avaliou nos 10% de frases separados (12.732 frases, 160.897 palavras). O código se recusa a rodar uma segunda vez.

| Conjunto de teste | Random Forest otimizado | Lista fixa (sem ML) |
| --- | --- | --- |
| **F1-macro** | **0,8849** | 0,8225 |
| Acurácia | 0,8859 | 0,8261 |
| ROC-AUC | 0,9474 | 0,8209* |
| PR-AUC | 0,9407 | 0,7653* |
| F1 `MANTER` / `DESCARTAR` | 0,896 / 0,874 | 0,848 / 0,797 |
| Revocação `DESCARTAR` | 0,836 | 0,722 |

\* decisão binária, não comparável em pé de igualdade.

- **O resultado confirma a validação:** 0,885 no teste contra 0,884 na validação e 0,879 na validação cruzada; não houve ajuste aos dados de validação.
- **O ganho sobre a lista fixa se mantém:** **+6,2 pontos de F1-macro**.
- O modelo está registrado no Model Registry do MLflow como `sinaliza-t1`, versão 1. Ele é o modelo que a API deve carregar na fase 8.
- Continuam valendo os limites acima, em especial o ruído de rótulo não medido e a queda fora do domínio. O teste mede proximidade às glosas dos intérpretes, não correção linguística.
