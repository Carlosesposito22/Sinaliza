# model

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

O DTW médio é calculado entre o movimento gerado e cada gravação de **sinalizantes que não entraram no treino**. A ordem esperada é:

```
global_mean  >  medoid  ≳  class_mean  ≈  model
```

- `global_mean` ignora o sinal. Se o modelo não o superar, não aprendeu a condicionar no sinal.
- `medoid` é a recuperação: a melhor gravação de treino de cada sinal.
- `class_mean` é a média das gravações de cada sinal normalizadas no tempo.
- O modelo atual é regressão com MSE e tende a convergir para algo próximo da `class_mean`. Um modelo só se justifica se superar a `medoid` e a `class_mean` **nos dados reais**. Nos sintéticos esse resultado não vale como evidência.

## Embeddings de sinal

A primeira camada do `MotionGenerator` é um `nn.Embedding(num_glosses, hidden)`: cada um dos 20 sinais vira um vetor aprendido, e é ele que condiciona o movimento gerado. Para olhar essa geometria depois do treino:

```powershell
python -m sinaliza_model.embeddings checkpoints/model.pt
python -m sinaliza_model.embeddings checkpoints/model.pt --data-root ../data/processed/minds-libras
```

Mostra os vizinhos mais próximos de cada sinal (cosseno) e, com `--data-root`, a correlação de Spearman entre a distância no embedding e o DTW entre as médias de movimento. Serve para **diagnosticar o treino** (embeddings colapsados, por exemplo). Com 20 sinais e poucos sinalizantes, vizinhança no embedding reflete o que o modelo precisou para reduzir o MSE, não semelhança linguística. Ainda não rodado em dados reais.

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
