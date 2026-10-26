# Pipeline de dados (`data/`)

Transforma vídeos de sinais em sequências de keypoints no [formato de pose](08-formato-de-pose.md), usando **YOLOv8 (recorte da pessoa) + MediaPipe Holistic (pose e mãos)**.

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `extract_keypoints.py` | CLI com dois comandos: `video` (um vídeo → um `.npy`) e `zip` (um ZIP do MINDS-Libras → pasta de `.npy`). Contém `extract()`, `_reference()`, `_normalize()` |
| `person_crop.py` | `Box`, `union`, `expand`, `estimate_crop`, `YoloPersonDetector` (YOLOv8, classe `person`) |
| `hand_world.py` | `HandWorldTracker` (HandLandmarker do MediaPipe Tasks), `world_depth`, `assign_hands`, `merge_hand`, `apply_world_hands`: z das mãos pelos *world landmarks* (`--hand-world`) |
| `minds_libras.py` | Leitura dos ZIPs, parsing dos nomes, layout de saída, log de detecção, `process_zip()` |
| `vocabulary.json` | Os 20 sinais; usado para filtrar o que extrair |
| `phrases.json` | Frases de demonstração por categoria (gerado em `api/`; ver [`12-api.md`](12-api.md)) |
| `tests/` | `test_minds_libras.py`, `test_extract_keypoints.py`, `test_person_crop.py`, `test_extract_pipeline.py` — 20 testes, passam (Python 3.12) |
| `requirements.txt` | `mediapipe==0.10.21`, `opencv-python>=4.9,<5`, `numpy>=1.26,<2`, `ultralytics>=8.3,<9`, `pytest>=8,<9` |
| `raw/`, `processed/` | ZIPs e `.npy` (ignorados pelo git) |

## Lote do V-LIBRASIL (`vlibrasil.py`, 2026-10-20)

```powershell
python extract_keypoints.py vlibrasil "<pasta>/data" <saída> --workers 6
```

- Lê a **pasta de `.mp4`** `<Sinal>_Articulador<N>.mp4` (3 sinalizantes) e extrai **só os sinais do `vocabulary.json`** (campo `video_class`); o resto conta como `outside_vocabulary`.
- Padrões do comando: **sem YOLOv8** (a pessoa ocupa o quadro; ver abaixo), `--upper-body` (zera quadris, pernas e pés), `--target-fps 30` (vídeos de 60 fps processam 1 a cada 2 quadros) e **apara o repouso** do começo e do fim (`--no-trim` desliga).
- **Aparar o repouso** (`trim_rest`): os vídeos têm a pessoa subindo e baixando os braços. Usa a velocidade dos punhos (pose 15 e 16), limiar = 25% do 90º percentil do próprio vídeo (piso 0,004 larguras de ombro por quadro) e 3 quadros de folga. Conferido à vista em 2 vídeos reais (o trecho mantido cobre o movimento e corta o repouso); **sem verdade-terreno**.
- Saída `<saída>/<NN>/<GLOSA>_1.npy` (NN = 01..03; glosa sem acento, `_` entre palavras), mais `extraction_log.csv` (`frames_raw`, `frames_kept`, taxas de detecção). **Retomável**; um vídeo com erro não derruba o lote (conta em `failed`).
- `--workers N` usa processos em paralelo. **Mais processos não é sempre mais rápido**: cada processo do MediaPipe usa várias threads.
- `build_vocabulary.py` gera o `vocabulary.json` a partir de `annotations.csv` e da tabela de curadoria `CURATED`.

## Mãos com world landmarks (`--hand-world`, 2026-10-21)

O z das mãos do Holistic é **relativo ao punho e comprimido** (no V-LIBRASIL, o mesmo osso de dedo ia de 0,34 a 0,76 da palma em 3D), e o avatar herdava isso: dedos dobrando de lado. Com `--hand-world`, o **HandLandmarker** do MediaPipe Tasks (mesmo pacote `mediapipe==0.10.21`, modelo `hand_landmarker.task`, Apache 2.0, ~7,8 MB, ignorado pelo git) roda no mesmo quadro e devolve a mão em **3D métrico** (*world landmarks*). Para cada mão (`hand_world.py`):

- as duas detecções e os punhos próximos (até 8% da largura do recorte): **x e y do Holistic, z do world**, na escala da imagem (mínimos quadrados entre o xy do world e o do Holistic), relativo ao punho;
- só o HandLandmarker achou: x e y das landmarks de imagem dele, z do world;
- só o Holistic achou: fica como está.

A mão é atribuída ao lado pelo **punho da pose** mais próximo (15 esquerdo, 16 direito), não pela lateralidade do modelo (que supõe imagem espelhada). A pose, o aparo e o número de quadros não mudam.

```powershell
curl.exe -L --fail -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
python extract_keypoints.py vlibrasil "<pasta>/data" "<pasta>/processed/v-librasil-world" --hand-world --workers 8
```

O modelo é passado ao MediaPipe pelo conteúdo, não pelo caminho: no Windows o MediaPipe 0.10.21 junta o caminho absoluto ao da instalação e falha (`errno=22`). Em saída por pipe no PowerShell/Git Bash, defina `PYTHONIOENCODING=utf-8` (o log usa "→").

**Piloto (16 arquivos, 5 sinais × 3 sinalizantes), comparado com a extração só com o Holistic:**

| Medida | Holistic | + world landmarks |
| --- | --- | --- |
| Quadros com a mão detectada | 92,2% | **97,4%** |
| Eixo de dobra da junta do meio alinhado ao anatômico (1 = perfeito) | 0,68 (~47° de erro) | **0,93 (~22°)** |
| Dobra para o lado da palma | 89,9% | 92,4% |
| Extensão do z da mão / palma | 0,59 (comprimido) | **0,97** |
| Variação do comprimento dos ossos (coef. de variação) | 0,207 | 0,196 |
| Variação de z de um quadro para o outro / palma | 0,025 | 0,041 |

Tempo: ~4 s por vídeo por processo (15 vídeos em 57 s com 5 processos).

**Lote completo (2026-10-25):** os 629 vídeos do vocabulário foram reextraídos para `processed/v-librasil-world` (sem falhas). Nos 616 arquivos comparáveis: mão detectada 92,5% → **96,0%**; alinhamento do eixo de dobra da junta do meio 0,66 → **0,91**; extensão do z da mão / palma 0,57 → **0,97**; coef. de variação dos ossos 0,198 → 0,190. O arquivo de movimentos novo está em `Datasets/motions-world/motions.npz` (o antigo, em `Datasets/motions/`, ficou intacto); para usá-lo no Docker, `SINALIZA_MOTIONS_DIR=<...>/Datasets/motions-world`. No avatar, a melhora é sutil à vista e não foi medida contra os sinais corretos.

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
- **V-LIBRASIL (2026-10-19), 9 vídeos reais (1080p, da cintura para cima):** MediaPipe sem YOLOv8 detectou corpo 100%, mão esquerda 97% e direita 96%; com YOLOv8, 100%, 97% e 94% e +1,3 s por vídeo. **O YOLOv8 não ajudou** porque a pessoa já ocupa o quadro; para este dataset usar `--no-yolo` (padrão do comando `vlibrasil`). Amostra pequena.
- **V-LIBRASIL, extração completa do vocabulário (2026-10-20):** **629 vídeos** (210 sinais; 210, 210 e 209 por sinalizante; o sinal **CRIANÇA** tem só 2 gravações, porque o vídeo do articulador 3 é um dos 3 que o `error.csv` lista como falha de download), 8 processos, cerca de 25 minutos (~28 vídeos/min), saída de 79 MB em `Projetos 6\Datasets\processed\v-librasil` (fora do repositório). Detecção média: corpo 100%, mão esquerda 91,5%, direita 93,5%; **70 gravações com a mão esquerda abaixo de 80% e 49 com a direita**, o que pode ser sinal de uma mão só (a outra fica parada fora do quadro) e **não foi investigado**. O aparo cortou, em média, 13% dos quadros (mediana de 158 para 134; mínimo 44).
- **Verificado:** 20 testes automatizados (extrator falso, normalização em pixels, recorte, detector YOLO com `YOLO` falso, `extract()` num vídeo sintético preto com e sem detector). `pip install -r requirements.txt` funcionou em Python 3.12 (mediapipe 0.10.21, numpy 1.26.4, ultralytics 8.4.183, torch 2.14.1).
- **Não verificado:**
  1. qualquer vídeo real do MINDS-Libras (download dos ZIPs incompleto; falta o `moov` do MP4);
  2. o **ganho** do recorte **no dataset real**: a medida acima é de um clipe de webcam e de uma simulação. Fazer o A/B com `--limit` pequeno e `--no-yolo` nos vídeos do MINDS-Libras é o primeiro experimento a rodar.
- Licença do Ultralytics (AGPL-3.0): uso offline na preparação dos dados; ver [`09-dados-e-vocabulario.md`](09-dados-e-vocabulario.md).
- Rosto não é extraído.
- Possível limitação: o recorte fixo assume câmera parada; se a pessoa sair da caixa, parte do corpo fica fora.

## Ambiente

Venv **próprio** de `data/`, com **Python 3.12** (`py -3.12 -m venv .venv`). O Python padrão desta máquina é 3.13, que não foi testado com `mediapipe==0.10.21`. `numpy<2` por causa do MediaPipe; `ultralytics` traz o PyTorch.
