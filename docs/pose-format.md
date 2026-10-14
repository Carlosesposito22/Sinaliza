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

- Origem: ponto médio entre os quadris (índices 23 e 24).
- Unidade: largura entre os ombros (índices 11 e 12) = 1.
- Eixos: `x` para a direita da tela, `y` para cima, `z` em direção à câmera.
- Pontos não detectados são `[0, 0, 0]`.

## Payload da API

`POST /translate` com `{"text": "..."}` devolve:

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

`layout` usa intervalos `[início, fim)` sobre o índice do ponto.

## Pontos em aberto

- Sinais em Libras usam expressão facial e movimento do tronco; o formato atual não cobre expressão.
- A escala de `z` do MediaPipe é aproximada; tratar como indicativa.
