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

## Fontes candidatas (a validar)

- **MINDS-Libras**: 20 sinais, 12 sinalizantes, cerca de 1.200 vídeos. Citada na pesquisa da fase 1. Serve para um vocabulário inicial pequeno, não para frases.
- Dicionário/banco de sinais do VLibras (licença e formato a verificar).
- Corpus de Libras de universidades brasileiras (disponibilidade e licença a verificar).

Definir a fonte, a licença e o vocabulário do MVP é o primeiro passo desta pasta. Os vídeos de sinalizantes são dados pessoais: conferir a licença de uso e não versionar o conteúdo bruto.

## Limitações conhecidas

- O script não foi executado contra vídeos reais ainda.
- O rosto não é extraído (fora do layout atual).
