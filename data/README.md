# data

Preparação dos dados de treino: vídeos de sinais → sequências de keypoints no [formato de pose](../docs/pose-format.md).

## Estrutura

```
data/
  raw/         vídeos originais (não versionado)
  processed/   arrays .npy gerados (não versionado)
  extract_keypoints.py
```

## Extração

```powershell
pip install -r requirements.txt
python extract_keypoints.py raw/ProjetoX/sinal.mp4 processed/sinal.npy
```

Gera um array `float32` de formato `(frames, 75, 3)`, já normalizado (origem no meio dos quadris, unidade = largura dos ombros, `y` para cima).

## Fonte e vocabulário

Decididos em [`docs/dados-e-vocabulario.md`](../docs/dados-e-vocabulario.md): MINDS-Libras (CC BY 4.0) com os 20 sinais listados em [`vocabulary.json`](vocabulary.json).

## Download do subconjunto inicial

Sinalizantes 01, 02, 07 e 10, cerca de 16,3 GB no total, de [zenodo.org/records/2667329](https://zenodo.org/records/2667329):

```powershell
New-Item -ItemType Directory -Force raw/minds-libras
foreach ($i in 1, 2, 7, 10) {
  $nome = "Sinalizador{0:00}.zip" -f $i
  curl.exe -L -o "raw/minds-libras/$nome" "https://zenodo.org/records/2667329/files/${nome}?download=1"
}
```

A estrutura interna dos ZIP (nomes de pastas e arquivos por sinal) ainda não foi conferida; descompactar e ajustar a extração antes de processar em lote.

Os vídeos de sinalizantes são dados pessoais. Citar o dataset conforme a página do Zenodo e não versionar o conteúdo bruto (`raw/` está no `.gitignore`).

## Limitações conhecidas

- O script não foi executado contra vídeos reais ainda.
- O rosto não é extraído (fora do layout atual).
