# Dados e vocabulário

Resumo de `docs/dados-e-vocabulario.md` (decisão de 2026-10-14; licenças e tamanhos conferidos nas páginas das fontes nessa data) e de `data/vocabulary.json`.

## Decisão

1. **Movimento (glosa → pose):** **MINDS-Libras**, com os 20 sinais como vocabulário fechado do MVP.
2. **Expansão (decidida em 2026-10-19):** acrescentar o **V-LIBRASIL** (1.364 sinais, 3 sinalizantes; só pesquisa e ensino, sem redistribuição) ao MINDS-Libras. O Apoema-Libras560 foi descartado. **O Carlos baixou só o V-LIBRASIL** (o MINDS é pesado demais), que fica **só na máquina dele, fora do repositório** (`C:\Users\Carlos\Desktop\Projetos 6\Datasets`); não se versionam vídeos nem keypoints. Detalhes em `references/21-datasets-de-treino.md`. **Atenção:** o V-LIBRASIL tem só 7 dos 20 sinais do MVP com o mesmo nome (ACONTECER, AMARELO, BANHEIRO, BARULHO, ESPELHO, FILHO, RUIM); o vocabulário do MVP (que vem do MINDS) precisa ser redefinido a partir da lista de classes do V-LIBRASIL.
3. **Texto → glosa:** no MVP, por **tabela** (`data/vocabulary.json`). O corpus `pt-br2libras-gloss` fica para uma etapa seguinte, com modelo aprendido.

## MINDS-Libras

| Item | Valor |
| --- | --- |
| Fonte | Zenodo, registro 2667329 — https://zenodo.org/records/2667329 |
| Licença | **CC BY 4.0**, acesso aberto, sem cadastro. Permite uso e redistribuição **com atribuição** |
| Conteúdo | 20 sinais, 12 sinalizantes, 5 repetições cada (~1.200 vídeos), fundo chroma key, MP4 1920×1080 a 30 fps |
| Tamanho | 12 ZIPs (um por sinalizante, 2,5–8,4 GB), 64,8 GB no total |
| Lacunas | Sinalizantes 3, 4 e 9 não gravaram todos os sinais; o 7 tem gravações extras |
| Nomes de arquivo (observado) | `SinalizadorNN/Canon/<II><Sinal>SinalizadorNN-<repetição>.mp4` (`II` = índice do sinal 01–20) — lido dos cabeçalhos de ZIPs **parcialmente baixados** |

### Subconjunto inicial

Sinalizantes **01, 02, 07 e 10** ≈ 16,3 GB (4,4 + 4,7 + 2,5 + 4,7). Dá quatro sinalizantes, o mínimo razoável para separar treino e validação por pessoa. Os demais entram se tempo de processamento e disco permitirem. Comandos de download em [`14-como-rodar-e-testar.md`](14-como-rodar-e-testar.md).

Na rede testada, o Zenodo serviu ~130–210 KB/s (cerca de um dia para os 16,3 GB); conexões em paralelo não ajudaram. **O download dos ZIPs não terminou** na máquina anterior e o trecho baixado não traz o átomo `moov` do MP4 (fica no fim do arquivo) — logo, a extração em vídeo real do MINDS-Libras ainda não foi exercitada.

## Outras fontes avaliadas (não adotadas agora)

| Fonte | Conteúdo | Motivo |
| --- | --- | --- |
| V-LIBRASIL | 1.364 termos, 3 articuladores, 4.089 vídeos | Só pesquisa/educação; **não redistribuir sem permissão**; uso comercial exige autorização. Melhor candidato para ampliar o vocabulário |
| pt-br2libras-gloss (Mendeley) | 127.349 pares português ↔ glosa | CC BY-SA 4.0. É texto, não movimento; serve para texto → glosa. Convenção de glosas não detalhada |
| Libras-UFPel Corpus | 4.800 registros (2.400 frases + 2.400 sinais), 4 sinalizantes surdos nativos | Sem link de download nem licença encontrados; vale pedir aos autores — único com **frases** |
| LIBRAS-UFOP | 56 sinais com RGB-D e esqueleto | Sem autores nem acesso encontrados |

## Os 20 sinais do MVP

`data/vocabulary.json` (versão 1; status: *proposta; formas e contextos não validados por falante de Libras*). Cada sinal tem `gloss`, `minds_label`, `pt` (formas em português que o mapeiam), `contexts` e, às vezes, `note`.

ACONTECER · ALUNO · AMARELO · AMÉRICA · APROVEITAR · BALA · BANCO · BANHEIRO · BARULHO · CINCO · CONHECER · ESPELHO · ESQUINA · FILHO · MAÇÃ · MEDO · RUIM · SAPO · VACINA · VONTADE

| Contexto (proposta) | Sinais |
| --- | --- |
| Escola | ALUNO, BANHEIRO, FILHO |
| Saúde | VACINA, MEDO, RUIM, VONTADE, BANHEIRO, FILHO |
| Serviços | BANCO |
| Trabalho | BANHEIRO (marcado no JSON; não consta na tabela do doc) |
| Família | FILHO (marcado no JSON; idem) |
| Geral | ACONTECER, AMARELO, AMÉRICA, APROVEITAR, BALA, BARULHO, CINCO, CONHECER, ESPELHO, ESQUINA, MAÇÃ, SAPO (+ RUIM, VONTADE) |

Notas no JSON: **BALA** = doce (não projétil); **BANCO** = financeiro (não de sentar).

### Frases de demonstração (só com o vocabulário)

- "O filho tem medo da vacina" → FILHO MEDO VACINA
- "O aluno quer ir ao banheiro" → ALUNO BANHEIRO
- "Eu quero conhecer a América" → CONHECER AMÉRICA

Perceba que as demos **descartam** a maior parte das palavras ("o", "tem", "quer", "ir"…), e que a saída não é a gramática de Libras.

`data/phrases.json` guarda **30 frases por categoria** (escola, saúde, serviços, trabalho, família, geral), geradas por modelos de frase em `api/app/phrases.py` e validadas contra o vocabulário (ver [`12-api.md`](12-api.md)). É texto em português, não Libras.

## Comportamento para palavra fora do vocabulário (decidido em 2026-10-19)

Cada palavra do texto recebe uma classe, e a API devolve isso em `matches`:

| Classe | O que é | Na interface |
| --- | --- | --- |
| `exact` | Está na tabela (`pt` do `vocabulary.json`) | Caixinha com palavra e glosa |
| `approx` | Fora da tabela, mas o **embedding** a aproxima de uma forma conhecida (similaridade ≥ limiar) | Caixinha tracejada com "~" e aviso para conferir |
| `function` | Artigo, preposição, conjunção, palavra ≤ 2 letras | Cinza, sem alarde |
| `ignored` | Sem correspondência (ex.: verbos) | Riscada, com aviso |

Não há **soletração**: o MINDS-Libras não tem o alfabeto manual. A aproximação é **proposta** (escrita parecida, ou sentido parecido com o embedder semântico): proximidade não garante que o sinal sirva em Libras.

## Limites que precisam ficar explícitos

- **Não é tradução para Libras.** Libras tem gramática própria (ordem, uso do espaço, expressão facial). O MVP converte palavras em **sequência de sinais isolados na ordem do texto**. Nas demonstrações, chamar de "sequência de sinais".
- **Palavras fora do vocabulário:** comportamento definido (ver seção acima): aproximação por embedding, sinalizada, ou ignoradas com aviso.
- **Polissemia:** "banco" e "bala" têm um único sinal gravado.
- **Validação linguística:** ninguém do grupo fala Libras. Contextos e formas em `vocabulary.json` são **propostas**. É preciso identificar quem valida (professor, intérprete, pessoa surda) antes da avaliação com usuários.
- **Licença dos derivados:**
  - MINDS-Libras (CC BY 4.0): keypoints extraídos podem ser versionados **com atribuição**.
  - V-LIBRASIL: não versionar vídeos nem keypoints derivados sem permissão.
  - pt-br2libras-gloss (CC BY-SA 4.0): confirmar com o professor o efeito do share-alike em modelos treinados nele.
- **Dados pessoais:** vídeos de sinalizantes são dados pessoais; citar o dataset conforme o Zenodo e **não versionar `raw/`**.
- **Ferramentas:** o **Ultralytics (YOLOv8) é AGPL-3.0** (ou licença Enterprise) — conferido em 2026-10-19. Aqui roda **só offline**, no recorte dos vídeos; a API não o usa. Se o projeto passar a servir ou distribuir o Ultralytics, reavaliar com o professor. O dataset de *hand keypoints* da Ultralytics é CC BY-NC-SA 4.0 e os rótulos são do próprio MediaPipe; **não é usado**. Detalhes em `docs/dados-e-vocabulario.md`.

## Como isso vira ML

Com 20 classes e ~60 gravações por classe, treina-se um **gerador de movimento condicionado ao sinal**, validado em sinalizante não visto no treino. Linha de base: **recuperação** — a gravação mais representativa de cada sinal, concatenada. O modelo só se justifica se superar a linha de base numa métrica objetiva (DTW para gravações de sinalizante não visto). A métrica mede **fidelidade ao movimento gravado, não correção linguística**. Ver [`11-modelo-ml.md`](11-modelo-ml.md).
