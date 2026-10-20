# data

Preparação dos dados de treino: vídeos de sinais → sequências de keypoints no [formato de pose](../docs/pose-format.md).

## Estrutura

```
data/
  raw/                    ZIPs e vídeos originais (não versionado)
  processed/              arrays .npy gerados (não versionado)
  vocabulary.json         os 20 sinais do MVP
  phrases.json            frases de demonstração por categoria (gerado por api/app/phrases.py)
  extract_keypoints.py    extração: YOLOv8 (recorte) + MediaPipe Holistic (um vídeo ou lote)
  person_crop.py          detector de pessoa com YOLOv8 e cálculo do recorte
  minds_libras.py         leitura dos ZIPs do MINDS-Libras e layout de saída
  tests/
```

## Fonte e vocabulário

Decididos em [`docs/dados-e-vocabulario.md`](../docs/dados-e-vocabulario.md): MINDS-Libras (CC BY 4.0) com os 20 sinais listados em [`vocabulary.json`](vocabulary.json).

## Download do subconjunto inicial

Sinalizantes 01, 02, 07 e 10, cerca de 16,3 GB no total, de [zenodo.org/records/2667329](https://zenodo.org/records/2667329):

```powershell
New-Item -ItemType Directory -Force raw/minds-libras
foreach ($i in 1, 2, 7, 10) {
  $nome = "Sinalizador{0:00}.zip" -f $i
  curl.exe -L -C - --retry 20 --retry-all-errors -o "raw/minds-libras/$nome" "https://zenodo.org/records/2667329/files/${nome}?download=1"
}
```

`-C -` retoma downloads interrompidos. Na rede em que testamos, o Zenodo serviu cerca de 130–210 KB/s (algo como um dia para os 16,3 GB), e conexões em paralelo não ajudaram.

Os vídeos de sinalizantes são dados pessoais. Citar o dataset conforme a página do Zenodo e não versionar o conteúdo bruto (`raw/` está no `.gitignore`).

## Extração

Python **3.12** (o `mediapipe==0.10.21` e o `ultralytics` foram instalados e testados nele; 3.13 não foi testado).

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

O `requirements.txt` inclui `ultralytics` (traz o PyTorch, algumas centenas de MB).

### Como funciona (YOLOv8 + MediaPipe)

Os vídeos do MINDS-Libras são 1920×1080 e o sinalizante ocupa só parte do quadro. Reduzir o quadro inteiro para ~960 px encolhe as mãos e o MediaPipe perde a mão. Por isso:

1. O **YOLOv8** (`yolov8n.pt`, classe `person`) detecta a pessoa em um quadro a cada 15 (`--crop-every`).
2. O recorte é a **união** das caixas detectadas mais uma margem de 15% (`--crop-margin`). É **fixo por vídeo**: uma caixa que muda a cada quadro mexeria no enquadramento do MediaPipe e adicionaria ruído.
3. O **MediaPipe Holistic** roda no recorte (reduzido a `--max-width`, 960 por padrão), com mais pixels nas mãos.
4. Os landmarks voltam para **pixels do quadro original** antes de normalizar. O recorte não altera o formato de saída.
5. Se o YOLOv8 não achar ninguém, usa o quadro inteiro e avisa em `stderr`.

O YOLOv8 vem **ligado por padrão**; `--no-yolo` roda o MediaPipe no quadro inteiro (útil para comparar as taxas do `extraction_log.csv` com e sem recorte).

**Pesos:** o Ultralytics baixa o `yolov8n.pt` (6,25 MB) na primeira execução. Se falhar com `CERTIFICATE_VERIFY_FAILED` (rede com proxy ou antivírus que intercepta HTTPS; aconteceu nesta máquina), baixe pelo Windows, que usa o repositório de certificados do sistema, e rode a partir de `data/` (ou passe `--yolo-model caminho\yolov8n.pt`):

```powershell
curl.exe -L --fail -o yolov8n.pt https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt
```

`*.pt` está no `.gitignore`. **Não** desative a verificação de certificado. Licença do Ultralytics (AGPL-3.0): ver [`docs/dados-e-vocabulario.md`](../docs/dados-e-vocabulario.md).

### Um vídeo

```powershell
python extract_keypoints.py video entrada.mp4 saida.npy
```

### Lote (um ZIP do MINDS-Libras)

```powershell
python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras
```

- Lê os vídeos direto do ZIP, um por vez, sem descompactar tudo.
- Estrutura esperada dentro do ZIP: `SinalizadorNN/Canon/<II><Sinal>SinalizadorNN-<repetição>.mp4` (observada nos cabeçalhos dos arquivos baixados). `__MACOSX/` e `.DS_Store` são ignorados.
- Saída: `processed/minds-libras/<NN>/<SINAL>_<repetição>.npy`, com o nome do sinal sem acento e em maiúsculas. É o layout lido por [`model/`](../model/README.md).
- **Retomável:** pula os `.npy` que já existem. Pode ser interrompido e rodado de novo.
- Grava `extraction_log.csv` na pasta de saída, com a taxa de frames em que corpo, mão esquerda e mão direita foram detectados por vídeo. Vale olhar antes de treinar: mão não detectada vira zero (o treino repete a última mão detectada).
- Opções: `--limit N` (processa só N vídeos novos, bom para testar), `--camera ''` (todas as pastas de câmera), `--max-width`, `--no-yolo`, `--yolo-model`, `--yolo-confidence`, `--yolo-device`, `--crop-margin`, `--crop-every`.

### Normalização

Origem no meio dos quadris, largura dos ombros = 1, `y` para cima. A conta é feita em **pixels do quadro original** (não em coordenadas 0–1 do MediaPipe, que esticam o eixo `y` em relação a `x` num quadro 16:9). Quando o corpo não é detectado em um quadro, as mãos usam a **última referência válida** (origem e escala); antes da primeira referência, o quadro fica zerado.

### Testes

```powershell
python -m pytest
```

Cobrem a leitura do ZIP, o layout de saída, a retomada e as taxas de detecção (com extrator falso), a normalização, o cálculo do recorte e o detector YOLO (com um `YOLO` falso). `tests/test_extract_pipeline.py` roda `extract()` num vídeo sintético preto e exige OpenCV e MediaPipe (pula se não estiverem instalados).

## Versão do MediaPipe

O `requirements.txt` fixa `mediapipe==0.10.21`. As versões mais novas (testada: 0.10.35) removeram a API `mp.solutions.holistic`, usada aqui. Migrar para a API de Tasks exigiria baixar um modelo `.task` e reescrever `extract()`. Essa versão exige `numpy<2`, por isso `data/` usa um venv separado do de `model/`.

## Validação feita

- Testes automatizados (extrator falso, normalização, recorte, detector falso, `extract()` em vídeo sintético preto) passam.
- A extração foi exercitada antes do YOLOv8 em um vídeo gerado a partir de uma foto de pessoa (corpo 100% e mãos detectadas).
- **YOLOv8 com pesos reais (2026-10-19):** `yolov8n.pt` rodou de ponta a ponta no Python 3.12. Teste em 150 quadros de um vídeo de webcam (1280×720, uma pessoa), com e sem recorte:

  | Cenário | Recorte | Corpo | Mão esq. | Mão dir. |
  | --- | --- | --- | --- | --- |
  | Webcam, pessoa ocupa o quadro | quase o quadro todo | 100% → 100% | 20% → 20% | 34% → 35% |
  | Simulado: pessoa a 50% num quadro 1920×1080 | caixa em volta da pessoa | 99% → 99% | 39% → 37% | 44% → 45% |
  | Simulado: pessoa a 35% num quadro 1920×1080 | caixa em volta da pessoa | 97% → 99% | 25% → 33% | 40% → 46% |

  (sem YOLO → com YOLO). Leitura: o detector localiza a pessoa corretamente e o fluxo funciona; o ganho em mãos é **pequeno e só aparece quando a pessoa é pequena no quadro** (35%). Um único clipe, uma pessoa, sem repetição: **é indício, não conclusão**. A simulação reduz o quadro da webcam e o põe num fundo verde; não é o MINDS-Libras.
- **Ainda não rodado:** nenhum vídeo do MINDS-Libras (o download dos ZIPs não terminou e o trecho baixado não traz o `moov` do MP4, que fica no fim do arquivo). O A/B no dataset real é a medida que decide se o YOLOv8 compensa.

## Limitações conhecidas

- Os cabeçalhos dos ZIP foram lidos nos arquivos **parcialmente baixados**. Uma pasta de câmera além de `Canon` pode existir mais adiante nos ZIP; nesse caso o lote a ignora (padrão `--camera Canon`).
- O recorte fixo pressupõe câmera parada (é o caso no MINDS-Libras, com fundo chroma key). Se a pessoa sair da caixa durante o vídeo, parte do corpo fica fora do recorte.
- O YOLOv8 só localiza a pessoa; não melhora a detecção de mão por si só. O ganho vem de dar mais pixels ao MediaPipe.
- O rosto não é extraído (fora do layout atual).
