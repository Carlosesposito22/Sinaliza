# Formato de pose

Resumo de `docs/pose-format.md` (fonte de verdade) com observações do código. É o contrato entre `model/`, `api/` e `web/`.

## Keypoints

Cada frame tem **75 pontos**, cada um `[x, y, z]`:

| Índices | Grupo | Origem |
| --- | --- | --- |
| 0–32 | `pose` (33 pontos do corpo) | MediaPipe Pose |
| 33–53 | `left_hand` (21 pontos) | MediaPipe Hands |
| 54–74 | `right_hand` (21 pontos) | MediaPipe Hands |

Sem rosto (os 468 pontos do Holistic ficam de fora). Se houver expressão facial, será um grupo novo no **fim** do layout (não reordenar os existentes).

"Esquerda/direita" = lado **do sinalizante** (convenção MediaPipe). Visto de frente, a esquerda do sinalizante aparece à direita da tela (`x` positivo).

### Índices úteis do corpo (MediaPipe Pose)

| Índice | Ponto | Índice | Ponto |
| --- | --- | --- | --- |
| 0 | nariz | 23 / 24 | quadril esq. / dir. |
| 11 / 12 | ombro esq. / dir. | 25 / 26 | joelho esq. / dir. |
| 13 / 14 | cotovelo esq. / dir. | 27 / 28 | tornozelo esq. / dir. |
| 15 / 16 | punho esq. / dir. | 7 / 8 | orelha esq. / dir. |

Mão (0–20, relativo ao grupo): 0 = punho; 1–4 polegar; 5–8 indicador; 9–12 médio; 13–16 anelar; 17–20 mínimo (ponta = último de cada dedo).

## Normalização (feita em `data/extract_keypoints.py`: `_reference` e `_normalize`)

- **Origem:** ponto médio entre os quadris (23 e 24).
- **Escala:** distância (no plano xy) entre os ombros (11 e 12) = 1.
- **Eixos:** `x` para a direita da tela; `y` **para cima** (a imagem tem y para baixo, então inverte); `z` em direção à câmera (inverte o z do MediaPipe).
- **Ausente = `[0, 0, 0]`.** Um ponto/mão não detectado vira zero.
- **A conta é feita em pixels do quadro original**, não nas coordenadas 0–1 do MediaPipe (que esticam `y` em relação a `x` num quadro 16:9). Com o recorte do YOLOv8, os landmarks voltam antes para pixels do quadro original; o recorte não muda o formato.

### Quadro sem corpo detectado

Se o corpo não é detectado num quadro (pose toda zero, ou largura dos ombros ~0), as mãos usam a **última referência válida** (origem e escala do último quadro com corpo). Antes da primeira referência, o quadro fica **zerado**. (Até 2026-10-19 esse caso devolvia as mãos em coordenadas brutas de imagem, fora do espaço normalizado; corrigido. `.npy` antigos não são comparáveis com os novos.)

### Observações

- O MediaPipe devolve `z` em escala aproximada (a de `x`); tratar como indicativo.
- `model/sinaliza_model/data.py::fill_missing_hands` repete a última mão detectada nos frames em que ela é zero; mão nunca detectada fica zero.

## Payload da API

`POST /translate` com `{"text": "..."}`:

```json
{
  "text": "olá mundo",
  "glosses": ["OLÁ", "MUNDO"],
  "pose": {
    "fps": 15,
    "layout": {"pose": [0, 33], "left_hand": [33, 54], "right_hand": [54, 75]},
    "frames": [[[0.0, 1.8, 0.0], "... 75 pontos por frame ..."]]
  }
}
```

`layout` usa intervalos `[início, fim)` sobre o índice do ponto. `frames` tem formato `frames × 75 × 3`.

Em disco (dados de treino): `.npy` float32 de formato `(frames, 75, 3)`, em `<raiz>/<sinalizante>/<SINAL>_<repetição>.npy`.

## Pontos em aberto

- Sinais em Libras usam **expressão facial** e movimento do tronco; o formato não cobre expressão. Isso limita o que o avatar pode mostrar (ex.: marcação de pergunta/negação, intensidade).
- Escala de `z` aproximada.
- `fps` do payload (15 no stub) vs. fps dos vídeos (30 no MINDS-Libras): o modelo reamostra para `seq_len` frames; falta decidir o fps de saída real.
