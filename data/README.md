# data

Preparação dos dados de treino: vídeos de sinais → sequências de keypoints no [formato de pose](../docs/pose-format.md).

## Estrutura

```
data/
  raw/                    ZIPs e vídeos originais (não versionado)
  processed/              arrays .npy gerados (não versionado)
  vocabulary.json         vocabulário do MVP: 210 sinais curados do V-LIBRASIL (gerado por build_vocabulary.py)
  vocabulary-minds.json   vocabulário antigo, os 20 sinais do MINDS-Libras (usado pelo comando `zip` e pelos testes)
  phrases.json            frases de demonstração por categoria (gerado por api/app/phrases.py)
  build_vocabulary.py     gera vocabulary.json a partir das classes do V-LIBRASIL (tabela de curadoria)
  extract_keypoints.py    extração: MediaPipe Holistic, YOLOv8 opcional (um vídeo, ZIP do MINDS ou pasta do V-LIBRASIL)
  vlibrasil.py            lote do V-LIBRASIL: seleção pelo vocabulário, paralelismo, aparar repouso
  person_crop.py          detector de pessoa com YOLOv8 e cálculo do recorte
  minds_libras.py         leitura dos ZIPs do MINDS-Libras e layout de saída
  tests/
```

## Fonte e vocabulário

Decididos em [`docs/dados-e-vocabulario.md`](../docs/dados-e-vocabulario.md): o treino usa o **V-LIBRASIL** (só pesquisa e ensino, sem redistribuição; os vídeos ficam fora do repositório, em `C:\Users\Carlos\Desktop\Projetos 6\Datasets`) com os 210 sinais curados de [`vocabulary.json`](vocabulary.json). O MINDS-Libras (CC BY 4.0, 20 sinais) não foi baixado; as seções sobre ele abaixo valem se for usado.

### V-LIBRASIL: extração em lote

```powershell
py -3.12 -m venv .venv ; .venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
python extract_keypoints.py vlibrasil "<pasta>/videos UFPE (V-LIBRASIL)/data" "<pasta>/processed/v-librasil" --workers 6
```

Extrai só os sinais de `vocabulary.json` (629 vídeos), **sem YOLOv8**, com `--upper-body` e `--target-fps 30`, e **apara o repouso** do começo e do fim. Saída: `<saída>/<NN>/<GLOSA>_1.npy` (NN = 01 a 03) e `extraction_log.csv`; retomável. Guarde a saída **fora do repositório** (`Projetos 6\Datasets\processed\v-librasil`). Para mudar o vocabulário, edite a tabela `CURATED` de `build_vocabulary.py` e rode `python build_vocabulary.py "<pasta>/annotations.csv"`.

## MINDS-Libras: download do subconjunto inicial (opcional)

Sinalizantes 01, 02, 07 e 10, cerca de 16,3 GB no total, de [zenodo.org/records/2667329](https://zenodo.org/records/2667329):

```powershell
New-Item -ItemType Directory -Force raw/minds-libras
foreach ($i in 1, 2, 7, 10) {
  $nome = "Sinalizador{0:00}.zip" -f $i
  curl.exe -L -C - --retry 20 --retry-all-errors -o "raw/minds-libras/$nome" "https://zenodo.org/records/2667329/files/${nome}?download=1"
}
```

`-C -` retoma downloads interrompidos. MD5 dos quatro arquivos (do Zenodo): 01 `0259b309d2d5472f20d9842547d94a8c`, 02 `e2b8673264ba7fca4cfc071654a099e8`, 07 `8e885f5cb6823744a583f206e4d2051c`, 10 `d6012f3e49e95d0cef7f6ec888743baa`; conferir com `Get-FileHash raw/minds-libras/Sinalizador07.zip -Algorithm MD5`. O outro dataset de treino, o V-LIBRASIL, e a situação de acesso estão em [`references/21-datasets-de-treino.md`](../references/21-datasets-de-treino.md); ele fica só na máquina do Carlos, em `C:\Users\Carlos\Desktop\Projetos 6\Datasets\v-librasil`, fora do repositório.

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
- **V-LIBRASIL (2026-10-19), 9 vídeos reais** (Banheiro, Filho e Barulho × 3 articuladores, 1080p, da cintura para cima): sem YOLOv8, corpo 100%, mão esquerda 97% e direita 96%; com YOLOv8, 100%, 97% e 94% (+1,3 s por vídeo). **Aqui o YOLOv8 não ajuda** (a pessoa já ocupa o quadro): use `--no-yolo`. O A/B no MINDS-Libras, onde a pessoa é pequena no quadro, não foi feito (o MINDS não foi baixado).
- **Ainda não rodado:** nenhum vídeo do MINDS-Libras e a extração em lote dos 4.086 vídeos do V-LIBRASIL (o lote atual lê ZIPs do MINDS; o V-LIBRASIL é uma pasta de `.mp4` nomeados `<Sinal>_Articulador<N>.mp4`).

## Limitações conhecidas

- Os cabeçalhos dos ZIP foram lidos nos arquivos **parcialmente baixados**. Uma pasta de câmera além de `Canon` pode existir mais adiante nos ZIP; nesse caso o lote a ignora (padrão `--camera Canon`).
- O recorte fixo pressupõe câmera parada (é o caso no MINDS-Libras, com fundo chroma key). Se a pessoa sair da caixa durante o vídeo, parte do corpo fica fora do recorte.
- O YOLOv8 só localiza a pessoa; não melhora a detecção de mão por si só. O ganho vem de dar mais pixels ao MediaPipe.
- O rosto não é extraído (fora do layout atual).
