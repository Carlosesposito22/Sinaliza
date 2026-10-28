# model

> Desde 2026-10-28 este gerador de movimento é um experimento, não a entrega de ML do projeto. A entrega de ML é o texto → glosa por classificação: ver [`references/22-plano-ml-texto-glosa.md`](../references/22-plano-ml-texto-glosa.md).

Modelo sinal (gloss) → sequência de poses. O treino está pronto como esqueleto e foi exercitado só com **dados sintéticos**; os vídeos reais ainda não foram processados.

## Como rodar

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
```

Treino de demonstração, com dados sintéticos:

```powershell
python -m sinaliza_model.train --synthetic
```

Com os dados reais (depois de extrair os keypoints, ver [`data/README.md`](../data/README.md)):

```powershell
python -m sinaliza_model.train --data-root ../data/processed/minds-libras --val-signers 10
```

Grava `checkpoints/model.pt` e `checkpoints/metrics.json` (ignorados pelo git).

## Estrutura

| Arquivo | Papel |
| --- | --- |
| `sinaliza_model/data.py` | Carga de `<sinalizante>/<SINAL>_<n>.npy`, reamostragem, preenchimento de mãos não detectadas, split por sinalizante |
| `sinaliza_model/metrics.py` | DTW normalizado entre sequências de keypoints |
| `sinaliza_model/baseline.py` | Linhas de base: medoide (recuperação), média por sinal e média global |
| `sinaliza_model/network.py` | `MotionGenerator`: embedding do sinal + GRU → `seq_len` frames |
| `sinaliza_model/train.py` | Treino, avaliação contra as linhas de base e CLI |
| `sinaliza_model/synthetic.py` | Dados sintéticos para testar o pipeline |
| `sinaliza_model/embeddings.py` | Inspeção dos embeddings de sinal: vizinhos mais próximos e correlação com o DTW entre os movimentos |

## Convenção de dados

`<raiz>/<sinalizante>/<SINAL>_<repetição>.npy`, formato `(frames, 75, 3)` conforme [`docs/pose-format.md`](../docs/pose-format.md). O nome do sinal é comparado ao vocabulário sem acento e sem diferença de caixa. O script `data/extract_keypoints.py` precisa ser chamado para gerar esses arquivos (a estrutura interna dos ZIP do MINDS-Libras ainda não foi conferida).

## Avaliação

Treino e validação são **por sinalizante**: `--val-signers 03` deixa o sinalizante 03 só para validação. Para o V-LIBRASIL (3 sinalizantes) rode os três folds (`01`, `02`, `03`). Duas medidas, sobre as gravações de sinalizantes que **não entraram no treino**:

1. **DTW médio** entre o movimento gerado e cada gravação de validação. Mede fidelidade à gravação, mas **premia movimento borrado**: a média de tudo (`global_mean`) fica quase tão perto das gravações quanto a média do sinal.
2. **Recuperação** (`retrieval` em `train.py`): para cada sinal do sinalizante de validação, o movimento gerado se parece mais com a gravação **desse** sinal do que com as dos outros? Dá `top1`, `top5` e a posição média do sinal certo. **Não premia borrão**: quem devolve a mesma sequência para qualquer sinal (a `global_mean`) cai no acaso. É a medida que diz se a geração carrega a identidade do sinal.

- `global_mean` ignora o sinal; serve de piso (na recuperação, deve ficar no acaso).
- `medoid` é a recuperação: a gravação de treino mais central de cada sinal. **Com 2 gravações por sinal (V-LIBRASIL) não há "mais central": é só uma das duas.**
- `class_mean` é a média das gravações de cada sinal normalizadas no tempo.
- O modelo atual é regressão com MSE e tende a convergir para algo próximo da `class_mean`. Um modelo só se justifica se superar a `class_mean` e a `medoid` **nos dados reais**.

### Resultado nos dados reais (V-LIBRASIL, 210 sinais, 3 folds, 2026-10-20)

| Método | DTW médio (3 folds) | Recuperação top-1 | top-5 | Posição média do sinal certo (de 210) |
| --- | --- | --- | --- | --- |
| `global_mean` (ignora o sinal) | 2,178 | 0,5% (= acaso) | 2,4% (= acaso) | 105,3 (acaso 105,3) |
| `class_mean` (média das 2 gravações) | 2,168 | **7,6%** | **19,5%** | **55,6** |
| `medoid` (uma das 2 gravações) | 2,539 | 7,8% | 17,8% | 62,4 |
| `model` (GRU + embedding do sinal) | **2,125** | 6,7% | 17,3% | 57,6 |

Leitura:
- **O sinal carrega informação**: com `class_mean`, o sinal certo é o primeiro em 7,6% das vezes (acaso 0,5%, ou seja, ~15 vezes) e entra nos 5 primeiros em 19,5% (acaso 2,4%). Mas é pouco: em 92% dos casos há outro sinal mais parecido. Com 2 gravações por sinal e 3 pessoas, a variação entre sinalizantes pesa tanto quanto o sinal.
- **O modelo não supera a `class_mean`** na recuperação (6,7% contra 7,6% no top-1; posição média 57,6 contra 55,6), e a vantagem dele no DTW médio (2,125 contra 2,168, 2%) é do tipo que o borrão produz: a `global_mean` (2,178) fica a 0,5% da `class_mean`. Pela regra do projeto, **o modelo não se justifica**; ficamos com a média por sinal (ou o medoide, quando houver mais gravações), que é mais simples e previsível.
- **Cautelas:** só 3 folds sobre o mesmo conjunto de sinais; sem teste estatístico; as diferenças entre `class_mean`, `medoid` e `model` na recuperação estão dentro do ruído (variam mais entre folds do que entre métodos); o modelo é o esqueleto (GRU, MSE, 200 épocas) sem ajuste de hiperparâmetros. DTW e recuperação medem fidelidade à gravação, **não correção linguística**.

## Embeddings de sinal

A primeira camada do `MotionGenerator` é um `nn.Embedding(num_glosses, hidden)`: cada um dos sinais do vocabulário vira um vetor aprendido, e é ele que condiciona o movimento gerado. Para olhar essa geometria depois do treino:

```powershell
python -m sinaliza_model.embeddings checkpoints/model.pt
python -m sinaliza_model.embeddings checkpoints/model.pt --data-root ../data/processed/minds-libras
```

Mostra os vizinhos mais próximos de cada sinal (cosseno) e, com `--data-root`, a correlação de Spearman entre a distância no embedding e o DTW entre as médias de movimento. Serve para **diagnosticar o treino** (embeddings colapsados, por exemplo). Com poucos sinalizantes, vizinhança no embedding reflete o que o modelo precisou para reduzir o MSE, não semelhança linguística. Ainda não rodado em dados reais.

Os embeddings de **palavras** usados para aproximar palavras fora do vocabulário ficam na API (`api/app/embeddings.py`), não aqui.

## Limites

- DTW mede fidelidade à gravação, **não correção linguística**. Validar com alguém que saiba Libras.
- A duração não é modelada nem avaliada: a saída tem `seq_len` fixo e a duração real é decidida fora do modelo.
- O rosto e a expressão não fazem parte do formato.
- Com cerca de 60 gravações por sinal e poucos sinalizantes, a variação entre pessoas pode dominar o resultado.

## Próximos passos

1. Rodar a extração nos ZIPs e conferir a estrutura de arquivos e a taxa de mãos não detectadas.
2. Treinar nos dados reais e comparar com as linhas de base.
3. Se o modelo não superar a recuperação, ficar com o medoide: é mais simples e mais previsível.
4. Implementar um `PoseGenerator` (ver `api/app/generator.py`) que use o modelo ou o medoide, concatenando sinais e suavizando as transições.
