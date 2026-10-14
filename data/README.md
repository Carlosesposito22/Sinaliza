# data

Preparação dos dados de treino: vídeos de sinais → sequências de keypoints no [formato de pose](../docs/pose-format.md).

## Estrutura

```
data/
  raw/                    ZIPs e vídeos originais (não versionado)
  processed/              arrays .npy gerados (não versionado)
  vocabulary.json         os 20 sinais do MVP
  extract_keypoints.py    extração com MediaPipe Holistic (um vídeo ou lote)
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

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

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
- Opções: `--limit N` (processa só N vídeos novos, bom para testar), `--camera ''` (todas as pastas de câmera), `--max-width` (reduz frames largos; padrão 960).

### Testes

```powershell
python -m pytest
```

Cobrem a leitura do ZIP, o layout de saída, a retomada e as taxas de detecção, com um extrator falso (não exigem MediaPipe).

## Versão do MediaPipe

O `requirements.txt` fixa `mediapipe==0.10.21`. As versões mais novas (testada: 0.10.35) removeram a API `mp.solutions.holistic`, usada aqui. Migrar para a API de Tasks exigiria baixar um modelo `.task` e reescrever `extract()`. Essa versão exige `numpy<2`, por isso `data/` usa um venv separado do de `model/`.

## Validação feita

A extração foi exercitada em um vídeo gerado a partir de uma foto de pessoa (corpo 100% e mãos detectadas), pelos comandos `video` e `zip`. Conferido: origem no meio dos quadris, largura dos ombros = 1, `y` para cima, e a saída é lida por `model/sinaliza_model/data.py`. **Ainda não foi rodada em vídeos do MINDS-Libras**: o download dos ZIPs não terminou e o trecho baixado não traz o `moov` do MP4 (fica no fim do arquivo).

## Limitações conhecidas

- Os cabeçalhos dos ZIP foram lidos nos arquivos **parcialmente baixados**. Uma pasta de câmera além de `Canon` pode existir mais adiante nos ZIP; nesse caso o lote a ignora (padrão `--camera Canon`).
- O rosto não é extraído (fora do layout atual).
