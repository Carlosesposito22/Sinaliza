# Créditos e licenças

## Avatar (VLibras)

- **Player:** o Unity WebGL do widget [spbgovbr-vlibras/vlibras-web-browsers](https://github.com/spbgovbr-vlibras/vlibras-web-browsers) (commit `d292d36`, 2026-09-29), da Suíte VLibras (Ministério da Gestão e da Inovação em Serviços Públicos, LAVID/UFPB), com os personagens Ícaro, Hosana e Guga. Em `web/public/vlibras/`: `unity-loader.js`, `playerweb.json` e os três `playerweb.*.unityweb` (20 MB), **sem alterações**. A ponte em JS foi escrita por nós em `web/src/vlibras.ts`.
- **Licença:** **LGPL-3.0**. O texto está em `web/public/vlibras/LICENSE-vlibras.txt` e vai junto com os arquivos. Se o player for modificado, o código modificado tem de ficar disponível sob a mesma licença; o nosso código que só o usa não precisa.
- **Sinais:** baixados do dicionário público do VLibras (`dicionario2-dth.vlibras.gov.br`) por `npm run signs` e servidos localmente de `web/public/vlibras/signs/`. **Não são versionados:** o dicionário não traz licença de redistribuição.
- O nome VLibras e os personagens são do projeto VLibras; não apresentamos o Sinaliza como produto do VLibras.

## Avatar anterior (histórico)

O avatar Rocketbox (Microsoft, MIT) usado de 2026-10-20 a 2026-10-25 está em `historico/avatar-rocketbox/`, com a licença em `public/avatar/LICENSE-rocketbox.md`.

## Bibliotecas do front (todas MIT)

- `react`, `vite`, `typescript`, `vitest`: interface, build e testes.

## Dados de treino

Ver [`references/21-datasets-de-treino.md`](../references/21-datasets-de-treino.md): o V-LIBRASIL só vale para pesquisa e ensino, sem redistribuição, e fica fora do repositório. Os movimentos que a API toca (`motions.npz`) são derivados dele e também ficam fora.

## VLibrasBD (corpus de texto → glosa)

Licença CC BY-SA 4.0. **Decisão (2026-11-02):** cumprimos a licença dando os devidos créditos ao VLibrasBD e a seus autores pelo uso da base, no repositório, nos notebooks e na apresentação. Não há tratamento adicional do share-alike.

- **Obra:** VLibrasBD / `pt-br2libras-gloss` (arquivo `pt_br2libras_gloss.csv`, 127.349 pares português → glosa de Libras, glosados por intérpretes certificados).
- **Autores:** Lima et al. (2025), *Data in Brief* (https://pmc.ncbi.nlm.nih.gov/articles/PMC12341731/). Conferir a lista completa de autores no artigo ao citar.
- **Fonte:** Mendeley Data, DOI 10.17632/ryj88ckjww.2 (https://data.mendeley.com/datasets/ryj88ckjww/2); relatório técnico em https://zenodo.org/records/15399589.
- **Baixado em:** 2026-11-02; SHA-256 `de0f1ddf8368b7f343b07c00e5f122ac46193d1aea2c36b642e0805c5c73fcbf` (conferido pela ingestão).
- **Uso no projeto:** rotulagem e treino do classificador texto → glosa. O CSV não é versionado.
