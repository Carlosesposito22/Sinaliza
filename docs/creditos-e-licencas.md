# Créditos e licenças

## Avatar 3D

- **Modelo:** **Male_Adult_08** (arquivos `m014_*`) da coleção **Microsoft Rocketbox** (Gonzalez-Franco et al., 2020), obtido em 2026-10-20 do repositório [microsoft/Microsoft-Rocketbox](https://github.com/microsoft/Microsoft-Rocketbox). Em `web/public/avatar/`: `avatar.fbx` (o FBX original, sem alterações) e as texturas `body.jpg`, `head.jpg` e `opacity.webp`, **convertidas** dos TGA originais (2048 × 2048) para JPEG/WebP, só para reduzir o tamanho.
- **Licença:** **MIT**, Copyright (c) 2020 Microsoft. O texto está em `web/public/avatar/LICENSE-rocketbox.md` e vai junto com o modelo, como a licença pede.
- Para trocar de personagem, troque os arquivos de `web/public/avatar/` (e a tabela `TEXTURES` em `web/src/RocketboxAvatar.tsx`) e confira a licença do novo modelo.

## Bibliotecas do front (todas MIT)

- [`three`](https://github.com/mrdoob/three.js) 0.169: renderização 3D e carga do FBX.
- `react`, `vite`, `typescript`, `vitest`: interface, build e testes.

## Dados de treino

Ver [`references/21-datasets-de-treino.md`](../references/21-datasets-de-treino.md): o V-LIBRASIL só vale para pesquisa e ensino, sem redistribuição, e fica fora do repositório. Os movimentos que a API toca (`motions.npz`) são derivados dele e também ficam fora.
