# Pipeline de dados (`data/`)

Transforma vídeos de sinais em sequências de keypoints no [formato de pose](08-formato-de-pose.md), usando **YOLOv8 (recorte da pessoa) + MediaPipe Holistic (pose e mãos)**.

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `extract_keypoints.py` | CLI com dois comandos: `video` (um vídeo → um `.npy`) e `zip` (um ZIP do MINDS-Libras → pasta de `.npy`). Contém `extract()`, `_reference()`, `_normalize()` |
| `person_crop.py` | `Box`, `union`, `expand`, `estimate_crop`, `YoloPersonDetector` (YOLOv8, classe `person`) |
| `minds_libras.py` | Leitura dos ZIPs, parsing dos nomes, layout de saída, log de detecção, `process_zip()` |
| `vocabulary.json` | Os 20 sinais; usado para filtrar o que extrair |
| `phrases.json` | Frases de demonstração por categoria (gerado em `api/`; ver [`12-api.md`](12-api.md)) |
| `tests/` | `test_minds_libras.py`, `test_extract_keypoints.py`, `test_person_crop.py`, `test_extract_pipeline.py` — 20 testes, passam (Python 3.12) |
| `requirements.txt` | `mediapipe==0.10.21`, `opencv-python>=4.9,<5`, `numpy>=1.26,<2`, `ultralytics>=8.3,<9`, `pytest>=8,<9` |
| `raw/`, `processed/` | ZIPs e `.npy` (ignorados pelo git) |

## Por que YOLOv8 aqui

Os vídeos do MINDS-Libras são 1920×1080 e o sinalizante ocupa só parte do quadro. Reduzir o quadro inteiro a ~960 px de largura encolhe as mãos e o MediaPipe perde a mão. O YOLOv8 localiza a pessoa; o vídeo é recortado em volta dela e o MediaPipe roda no recorte com mais pixels nas mãos. **O YOLOv8 só localiza a pessoa**; os keypoints continuam sendo do MediaPipe. Foi sugestão do orientador ([`19-sugestoes-do-orientador.md`](19-sugestoes-do-orientador.md)).

## Como a extração funciona

1. **Recorte (por vídeo):** `_sampled_frames` lê 1 quadro a cada `--crop-every` (15) pulando a decodificação dos demais; `YoloPersonDetector` devolve a **maior** caixa de `person` (confiança ≥ `--yolo-confidence`, 0,4); `estimate_crop` faz a **união** das caixas e `expand` soma `--crop-margin` (15%) dentro do quadro. O recorte é **fixo no vídeo** (câmera parada; uma caixa que mudasse a cada quadro mexeria no enquadramento do MediaPipe).
2. Sem pessoa detectada em nenhuma amostra → quadro inteiro + aviso em `stderr`.
3. Cada quadro é recortado e reduzido a `--max-width` (960) se mais largo; `Holistic(model_complexity=1)` processa o recorte.
4. `_landmarks_to_array` converte os landmarks (0–1 no recorte) para **pixels do quadro original** (`z` na escala de `x`, como o MediaPipe define); ausente → zero.
5. `_reference` (origem = meio dos quadris, escala = largura dos ombros, em pixels) e `_normalize`. **Sem corpo no quadro, as mãos usam a última referência válida**; antes da primeira, o quadro fica zerado.
6. Empilha em `(frames, 75, 3)` float32.

`--no-yolo` roda o MediaPipe no quadro inteiro. O YOLOv8 vem **ligado por padrão**. No modo lote, o detector é criado **uma vez** e reutilizado em todos os vídeos.

## Mudanças no cálculo (2026-10-19) [leia se for comparar com extrações antigas]

- A normalização antes usava as coordenadas 0–1 do MediaPipe diretamente: num quadro 16:9, `y` ficava esticado em relação a `x` (e a escala dos ombros também). Agora tudo é calculado em **pixels do quadro original**, o que é necessário para o recorte e corrige essa distorção. **`.npy` gerados com a versão anterior não são comparáveis** com os novos; reextraia.
- Quadro sem corpo detectado: antes, as mãos ficavam em coordenadas brutas de imagem (fora do espaço normalizado); agora usam a última referência válida.

## Modo lote (`zip`)

```
python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras
```

- Lê os vídeos direto do ZIP, **um por vez**, copiando para um arquivo temporário.
- Padrão de nome: `^\d{2}(?P<sign>.+?)Sinalizador(?P<signer>\d{2})-(?P<rep>\d+)\.mp4$`. Ignora `__MACOSX/`, arquivos que começam com `.` e pastas de câmera diferentes de `Canon` (`--camera ''` aceita todas).
- Só processa sinais cujo `slug` está no `vocabulary.json`; os demais contam como `unknown_sign`.
- Saída: `processed/minds-libras/<NN>/<SINAL>_<rep>.npy`. **Retomável** (pula `.npy` existentes; grava em `.part` e renomeia).
- `extraction_log.csv`: `signer, sign, rep, frames, pose_rate, left_hand_rate, right_hand_rate, source`. **Olhar antes de treinar.** O log não registra a caixa de recorte usada.
- Opções: `--limit N`, `--camera`, `--vocabulary`, `--max-width`, `--yolo/--no-yolo`, `--yolo-model`, `--yolo-confidence`, `--yolo-device`, `--crop-margin`, `--crop-every`.

## Estado e pendências

- **YOLOv8 com pesos reais (2026-10-19):** `yolov8n.pt` baixado (6,25 MB; o download pelo Python falhou por `CERTIFICATE_VERIFY_FAILED`, foi feito com `curl.exe`; ver `data/README.md`) e rodou de ponta a ponta. Em 150 quadros de webcam (uma pessoa): sem diferença quando a pessoa ocupa o quadro (mãos 20/34% → 20/35%); em simulação com a pessoa a 50% e a 35% num quadro 1920×1080: sem ganho a 50% (39/44% → 37/45%) e **ganho pequeno a 35%** (mãos 25/40% → 33/46%, corpo 97% → 99%). Um clipe, sem repetição: **indício, não conclusão**.
- **Verificado:** 20 testes automatizados (extrator falso, normalização em pixels, recorte, detector YOLO com `YOLO` falso, `extract()` num vídeo sintético preto com e sem detector). `pip install -r requirements.txt` funcionou em Python 3.12 (mediapipe 0.10.21, numpy 1.26.4, ultralytics 8.4.183, torch 2.14.1).
- **Não verificado:**
  1. qualquer vídeo real do MINDS-Libras (download dos ZIPs incompleto; falta o `moov` do MP4);
  2. o **ganho** do recorte **no dataset real**: a medida acima é de um clipe de webcam e de uma simulação. Fazer o A/B com `--limit` pequeno e `--no-yolo` nos vídeos do MINDS-Libras é o primeiro experimento a rodar.
- Licença do Ultralytics (AGPL-3.0): uso offline na preparação dos dados; ver [`09-dados-e-vocabulario.md`](09-dados-e-vocabulario.md).
- Rosto não é extraído.
- Possível limitação: o recorte fixo assume câmera parada; se a pessoa sair da caixa, parte do corpo fica fora.

## Ambiente

Venv **próprio** de `data/`, com **Python 3.12** (`py -3.12 -m venv .venv`). O Python padrão desta máquina é 3.13, que não foi testado com `mediapipe==0.10.21`. `numpy<2` por causa do MediaPipe; `ultralytics` traz o PyTorch.
