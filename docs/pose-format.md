# Formato de pose

Contrato único entre o modelo (`model/`), a API (`api/`) e o avatar (`web/`).

## Keypoints

Cada frame tem **75 pontos**, cada ponto com `[x, y, z]`:

| Índices | Grupo | Origem |
| --- | --- | --- |
| 0–32 | `pose` (33 pontos do corpo) | MediaPipe Pose |
| 33–53 | `left_hand` (21 pontos) | MediaPipe Hands |
| 54–74 | `right_hand` (21 pontos) | MediaPipe Hands |

O rosto (468 pontos do Holistic) fica **fora** por enquanto. Quando houver expressão facial, será um grupo novo no fim do layout.

"Esquerda" e "direita" seguem o MediaPipe: são o lado do **sinalizante**. Visto de frente, a esquerda do sinalizante aparece à direita da tela (`x` positivo).

## Normalização

- Origem: ponto médio entre os **ombros** (índices 11 e 12). (Até 2026-10-20 era o meio dos quadris; os vídeos do V-LIBRASIL são da cintura para cima e os quadris ficam fora do quadro, então a posição estimada variava entre sinalizantes.)
- Unidade: largura entre os ombros (índices 11 e 12) = 1.
- Eixos: `x` para a direita da tela, `y` para cima, `z` em direção à câmera.
- Pontos não detectados são `[0, 0, 0]`.
- Em vídeos da cintura para cima, os índices **23–32** (quadris, joelhos, tornozelos, calcanhares e pés) são **zerados** (`--upper-body` na extração): o MediaPipe só os estima. Quem consome o formato deve tratar `[0, 0, 0]` como "ausente".
- A conta é feita em pixels do quadro original, não nas coordenadas 0–1 do MediaPipe (que esticam `y` em relação a `x` num quadro 16:9). Em quadro sem corpo detectado, as mãos usam a última referência válida; antes da primeira, o quadro fica zerado.

## Payload da API

`POST /translate` com `{"text": "..."}` devolve:

```json
{
  "text": "olá mundo",
  "glosses": ["OLÁ", "MUNDO"],
  "pose": {
    "fps": 15,
    "layout": {"pose": [0, 33], "left_hand": [33, 54], "right_hand": [54, 75]},
    "frames": [[[0.0, 0.6, 0.1], "... 75 pontos por frame ..."]]
  }
}
```

`layout` usa intervalos `[início, fim)` sobre o índice do ponto.

## Pontos em aberto

- Sinais em Libras usam expressão facial e movimento do tronco; o formato atual não cobre expressão.
- A escala de `z` do MediaPipe é aproximada; tratar como indicativa.
