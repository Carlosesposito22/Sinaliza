# Modelo de ML (`model/`)

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
| `tests/` | `test_data.py`, `test_metrics_baseline.py`, `test_train.py` |
| `requirements.txt` | `numpy>=1.26,<3`, `torch>=2.2,<3`, `pytest>=8,<9` |

## Dados de entrada

`<raiz>/<sinalizante>/<SINAL>_<repetição>.npy`, `(frames, 75, 3)` float32. `load_dataset` casa o nome do arquivo com o vocabulário ignorando acento e caixa (`MACA_1.npy` → MAÇÃ), valida o formato (lança erro se não for `(frames, 75, 3)`) e aplica `fill_missing_hands`.

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

## Limites (leia antes de afirmar qualquer coisa sobre o modelo)

- DTW mede **fidelidade à gravação, não correção linguística**. Um movimento próximo da referência ainda pode estar errado como sinal. Precisa de alguém que saiba Libras.
- **Duração não modelada nem avaliada** (DTW alinha no tempo; tudo reamostrado para 32 frames).
- **Rosto/expressão fora do formato.**
- Regressão com MSE tende a **suavizar** (média de movimentos); sinais têm formas de mão distintas e a média pode borrar a configuração de mão.
- ~60 gravações por sinal e poucos sinalizantes (4 no subconjunto inicial): a variação entre pessoas pode dominar.
- Sinais compostos em frase **não** são modelados: a concatenação e a **suavização de transições** são trabalho do gerador na API (ainda não feito).

## Testes existentes (20 `def test_*` no total entre `model/` e `data/`; não executados nesta sessão)

`test_data.py`: vocabulário com 20 glosas únicas; `slug`; reamostragem (extremos, 1 frame); preenchimento de mãos; carga e rejeição de formato errado; divisão sem sobreposição. `test_metrics_baseline.py`: DTW zero para iguais e simétrico, tolera esticamento temporal; formatos das linhas de base; medoide é uma gravação de treino. `test_train.py`: condicionar no sinal supera a média global (sintético); pipeline roda e aprende o rótulo.

## Próximos passos do modelo

1. Rodar a extração e conferir a taxa de mãos não detectadas.
2. Treinar nos dados reais e comparar com as linhas de base.
3. Se o modelo não superar a recuperação, ficar com o medoide.
4. Implementar um `PoseGenerator` (ver [`12-api.md`](12-api.md)) que use o modelo ou o medoide, **concatenando sinais e suavizando transições**.
5. Ideias além do MVP **[não decididas]**: perda DTW diferenciável (soft-DTW), modelar duração, condicionar em sinalizante/estilo, incluir rosto.
