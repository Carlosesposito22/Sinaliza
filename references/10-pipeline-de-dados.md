# Pipeline de dados (`data/`)

Transforma vídeos de sinais em sequências de keypoints no [formato de pose](08-formato-de-pose.md).

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `extract_keypoints.py` | CLI com dois comandos: `video` (um vídeo → um `.npy`) e `zip` (um ZIP do MINDS-Libras → pasta de `.npy`). Contém `extract()` e `_normalize()` |
| `minds_libras.py` | Leitura dos ZIPs, parsing dos nomes, layout de saída, log de detecção, `process_zip()` |
| `vocabulary.json` | Os 20 sinais; usado para filtrar o que extrair |
| `tests/test_minds_libras.py` | Testes com extrator falso (não exigem MediaPipe) |
| `requirements.txt` | `mediapipe==0.10.21`, `opencv-python>=4.9,<5`, `numpy>=1.26,<2`, `pytest>=8,<9` |
| `raw/`, `processed/` | ZIPs e `.npy` (ignorados pelo git) |

## Como a extração funciona

1. `extract(video_path, max_width=960)` abre o vídeo com OpenCV; se o frame for mais largo que `max_width`, reduz.
2. Roda `mp.solutions.holistic.Holistic(model_complexity=1)` frame a frame.
3. Concatena pose (33) + mão esquerda (21) + mão direita (21); landmark ausente → zeros.
4. Normaliza (origem nos quadris, ombros = 1, `y` para cima, `z` para a câmera) e empilha em `(frames, 75, 3)` float32.

## Modo lote (`zip`)

```
python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras
```

- Lê os vídeos direto do ZIP, **um por vez**, copiando para um arquivo temporário (não descompacta tudo).
- Padrão de nome: `^\d{2}(?P<sign>.+?)Sinalizador(?P<signer>\d{2})-(?P<rep>\d+)\.mp4$`. Ignora `__MACOSX/`, arquivos que começam com `.` e pastas de câmera diferentes de `Canon` (`--camera ''` aceita todas).
- Só processa sinais cujo `slug` (sem acento, maiúsculas) está no `vocabulary.json`; os demais contam como `unknown_sign`.
- Saída: `processed/minds-libras/<NN>/<SINAL>_<rep>.npy` (ex.: `07/MACA_3.npy`).
- **Retomável:** pula `.npy` existentes; grava primeiro em `.part` e renomeia (atômico). Pode ser interrompido e repetido.
- `extraction_log.csv` na pasta de saída: `signer, sign, rep, frames, pose_rate, left_hand_rate, right_hand_rate, source` — a fração de frames com corpo e cada mão detectados. **Olhar antes de treinar.**
- Opções: `--limit N` (só N vídeos novos; bom para teste), `--camera`, `--max-width`, `--vocabulary`.

Retorno: contadores `processed / existing / unknown_sign / ignored`.

## Estado e pendências

- **Validação feita:** extração exercitada num vídeo gerado a partir de **uma foto** de pessoa (corpo 100% e mãos detectadas), pelos comandos `video` e `zip`; conferidos origem, escala, eixo `y` e leitura por `model/`.
- **Não validado:** nenhum vídeo real do MINDS-Libras. A estrutura de pastas do ZIP vem de cabeçalhos de ZIPs parcialmente baixados; uma câmera além de `Canon` pode existir.
- **Pendências práticas:**
  1. concluir o download dos ZIPs 01, 02, 07, 10;
  2. rodar o lote e inspecionar `extraction_log.csv` (mãos não detectadas viram zero);
  3. decidir tratamento de frames sem corpo (ver observação em [`08-formato-de-pose.md`](08-formato-de-pose.md#observações-do-código-lidas-não-testadas-em-dado-real)).
- **Rosto não é extraído.**
- Migrar para a API de Tasks do MediaPipe só se for preciso subir a versão.

## Ambiente

Venv **próprio** de `data/` (por causa do `numpy<2`). Windows/PowerShell nos exemplos do repositório.
