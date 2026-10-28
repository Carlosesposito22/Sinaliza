# Modelo de ML (`model/`)

> **Desde 2026-10-28 este modelo não é a entrega principal de ML.** O avatar é o VLibras (os movimentos não vêm daqui), o modelo não superou a média por sinal e a rubrica pede classificadores rastreados. A entrega de ML passou a ser o texto → glosa por classificação: ver [`22-plano-ml-texto-glosa.md`](22-plano-ml-texto-glosa.md). O conteúdo abaixo continua válido como registro do experimento e da validação por sinalizante não visto.

Modelo **sinal (glosa) → sequência de poses**. Pacote Python `sinaliza_model`. Exercitado até agora **só com dados sintéticos**; os vídeos reais não foram processados.

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `sinaliza_model/data.py` | `Sample`, `load_vocabulary`, `load_dataset`, `resample`, `fill_missing_hands`, `split_by_signer`, `slug` |
| `sinaliza_model/network.py` | `MotionGenerator` |
| `sinaliza_model/baseline.py` | `MedoidBaseline`, `ClassMeanBaseline`, `GlobalMeanBaseline` |
| `sinaliza_model/metrics.py` | `dtw_distance` |
| `sinaliza_model/train.py` | `train_model`, `evaluate`, `run`, CLI |
| `sinaliza_model/synthetic.py` | `make_synthetic` (dados sintéticos) |
| `sinaliza_model/embeddings.py` | Inspeção dos embeddings de sinal (ver seção abaixo) |
| `tests/` | `test_data.py`, `test_metrics_baseline.py`, `test_train.py`, `test_embeddings.py` |
| `requirements.txt` | `numpy>=1.26,<3`, `torch>=2.2,<3`, `pytest>=8,<9` |

## Dados de entrada

`<raiz>/<sinalizante>/<SINAL>_<repetição>.npy`, `(frames, 75, 3)` float32. `load_dataset` casa o nome do arquivo com o vocabulário por `file_key` (sem acento, sem diferença de caixa, `_` no lugar de espaços: `MACA_1.npy` → MAÇÃ, `DOR_DE_CABECA_1.npy` → DOR DE CABEÇA), recusa duas glosas com a mesma chave, valida o formato (lança erro se não for `(frames, 75, 3)`) e aplica `fill_missing_hands`.

## Rede

`MotionGenerator(num_glosses, seq_len=32, hidden=128, layers=2)`:

1. `Embedding` do sinal (dim 128), somado a uma **consulta temporal aprendida** (`time_query`, `seq_len × hidden`);
2. `GRU` de 2 camadas;
3. `Linear` → 75×3 por instante → saída `(batch, seq_len, 75, 3)`.

Entrada: índice do sinal. Saída: **duração fixa de 32 frames**; a duração real "é decidida fora do modelo".

## Treino

- Alvos: gravações reamostradas (interpolação linear) para `seq_len`.
- Perda **MSE**, Adam `lr=1e-3`, 200 épocas, batch 32, semente 0.
- Divisão **por sinalizante**: `--val-signers 10` deixa o sinalizante 10 só para validação. Sem o argumento, usa o último sinalizante.
- Grava `checkpoints/model.pt` (state_dict, glosas, seq_len) e `checkpoints/metrics.json`.

## Avaliação

`evaluate` calcula o **DTW médio** entre o movimento gerado e cada gravação de validação (sinalizantes não vistos), por sinal e geral.

`dtw_distance(a, b)`: custo entre frames = distância euclidiana sobre todos os keypoints (unidade do formato: largura dos ombros = 1); normaliza por `len(a)+len(b)`. Implementação em Python puro (laço duplo) — fica lenta para sequências longas ou muitos pares.

### Linhas de base

| Nome | O que faz | Para que serve |
| --- | --- | --- |
| `global_mean` | Ignora o sinal; devolve a média de tudo | Se o modelo não superar, não aprendeu a condicionar no sinal |
| `class_mean` | Média das gravações de treino de cada sinal (normalizadas no tempo) | O que uma regressão MSE tende a aprender |
| `medoid` | A gravação de treino mais central (menor soma de DTW) de cada sinal — **recuperação** | A linha de base a bater |

Ordem esperada (do pior ao melhor): `global_mean > medoid ≳ class_mean ≈ model`.

**Critério de decisão:** o modelo só se justifica se superar `medoid` e `class_mean` **nos dados reais**. Nos sintéticos o resultado não vale como evidência. **Se não superar a recuperação, ficar com o medoide** — é mais simples e previsível.

## Resultado nos dados reais (V-LIBRASIL, 210 sinais, 3 folds leave-one-signer-out, 2026-10-20)

Duas medidas: **DTW médio** (premia borrão) e **recuperação** (`retrieval` em `train.py`: o movimento gerado para o sinal X se parece mais com a gravação de X do que com as dos outros sinais do mesmo sinalizante de validação; não premia borrão).

| Método | DTW médio (3 folds) | Recuperação top-1 | top-5 | Posição média do sinal certo (de 210) |
| --- | --- | --- | --- | --- |
| `global_mean` (ignora o sinal) | 2,178 | 0,5% (= acaso) | 2,4% (= acaso) | 105,3 (acaso 105,3) |
| `class_mean` (média das 2 gravações) | 2,168 | **7,6%** | **19,5%** | **55,6** |
| `medoid` (uma das 2 gravações) | 2,539 | 7,8% | 17,8% | 62,4 |
| `model` (GRU + embedding do sinal) | **2,125** | 6,7% | 17,3% | 57,6 |

- **O sinal carrega informação**: `class_mean` acerta o sinal em 1º lugar em 7,6% (acaso 0,5%) e nos 5 primeiros em 19,5% (acaso 2,4%). É pouco: a variação entre os 3 sinalizantes pesa tanto quanto o sinal.
- **O modelo não supera a `class_mean`** na recuperação (6,7% contra 7,6% no top-1), e a vantagem dele no DTW médio (2%) é compatível com borrão (a `global_mean` fica a 0,5% da `class_mean`). **Pela regra do projeto, o modelo não se justifica**; ficar com a média por sinal.
- **`medoid` com 2 gravações** é só uma das duas (por isso o DTW 2,539, igual nos folds 01 e 02: é o mesmo par de gravações, DTW simétrico).
- Cautelas: 3 folds, sem teste estatístico, diferenças dentro do ruído, modelo sem ajuste de hiperparâmetros, métricas de fidelidade (não de correção linguística). Detalhes por fold em `model/checkpoints/val0N/metrics.json` (git-ignorado).

## Movimentos para a API (`sinaliza_model/motions.py`)

Como o modelo não superou a média por sinal, a API **toca gravações reais**. `python -m sinaliza_model.motions --data-root <processed/v-librasil> --out <Datasets/motions/motions.npz>` monta um `.npz` com um movimento `(frames, 75, 3)` por sinal (chave = `file_key` da glosa) e `_meta`. Métodos: `recording` (padrão: a gravação do **mesmo sinalizante** para todos os sinais, o com mais mão detectada; se faltar, a do próximo) e `mean` (média das gravações; borra as mãos). A repetição da última mão detectada (`fill_missing_hands`) é aplicada nos movimentos escolhidos, para a mão não piscar. Rodado nos dados reais: 210 movimentos, sinalizante 01, 20 MB, mediana de 134 quadros (mín 69, máx 265). **O arquivo é derivado do V-LIBRASIL: não versionar.** Testes em `tests/test_motions.py` (8).

## Embeddings de sinal (`sinaliza_model/embeddings.py`)

A primeira camada da rede é `nn.Embedding(num_glosses, hidden)`: cada sinal vira um vetor aprendido, e é ele que condiciona o movimento. O módulo `embeddings.py` inspeciona isso depois do treino:

- `gloss_embeddings(model)` / `checkpoint_embeddings(path)`: matriz `(20, 128)`;
- `nearest_neighbors(vectors, glosses, k)`: vizinhos por cosseno;
- `motion_distances(samples, glosses)`: DTW entre as **médias de movimento** de cada par de sinais;
- `embedding_vs_motion(vectors, distances)`: Spearman entre a distância no embedding e o DTW;
- CLI: `python -m sinaliza_model.embeddings checkpoints/model.pt [--data-root ...]`.

Leitura honesta: serve para **diagnosticar o treino** (embeddings colapsados, por exemplo). Com 20 sinais, vizinhança no embedding reflete o que o modelo precisou para reduzir o MSE, **não semelhança linguística**. Testado só com dados sintéticos; nunca rodado em dados reais.

Há **dois usos diferentes de "embedding" no projeto**: este (vetor do sinal, dentro do gerador de movimento, em `model/`) e o de **palavras** que aproxima palavras fora do vocabulário (em `api/app/embeddings.py`, ver [`12-api.md`](12-api.md)). Não se comunicam.

## Limites (leia antes de afirmar qualquer coisa sobre o modelo)

- DTW mede **fidelidade à gravação, não correção linguística**. Um movimento próximo da referência ainda pode estar errado como sinal. Precisa de alguém que saiba Libras.
- **Duração não modelada nem avaliada** (DTW alinha no tempo; tudo reamostrado para 32 frames).
- **Rosto/expressão fora do formato.**
- Regressão com MSE tende a **suavizar** (média de movimentos); sinais têm formas de mão distintas e a média pode borrar a configuração de mão.
- ~60 gravações por sinal e poucos sinalizantes (4 no subconjunto inicial): a variação entre pessoas pode dominar.
- Sinais compostos em frase **não** são modelados: a concatenação e a **suavização de transições** são trabalho do gerador na API (ainda não feito).

## Testes existentes (32 em `model/`, passam; rodados em 2026-10-20 no Python 3.12 do venv de `data/`, que tem torch; o venv próprio de `model/` não foi montado)

`test_data.py`: vocabulário com 20 glosas únicas; `slug`; reamostragem (extremos, 1 frame); preenchimento de mãos; carga e rejeição de formato errado; divisão sem sobreposição. `test_metrics_baseline.py`: DTW zero para iguais e simétrico, tolera esticamento temporal; formatos das linhas de base; medoide é uma gravação de treino. `test_train.py`: condicionar no sinal supera a média global (sintético); pipeline roda e aprende o rótulo.

## Próximos passos do modelo

1. Rodar a extração e conferir a taxa de mãos não detectadas.
2. Treinar nos dados reais e comparar com as linhas de base.
3. Se o modelo não superar a recuperação, ficar com o medoide.
4. Implementar um `PoseGenerator` (ver [`12-api.md`](12-api.md)) que use o modelo ou o medoide, **concatenando sinais e suavizando transições**.
5. Ideias além do MVP **[não decididas]**: perda DTW diferenciável (soft-DTW), modelar duração, condicionar em sinalizante/estilo, incluir rosto.
