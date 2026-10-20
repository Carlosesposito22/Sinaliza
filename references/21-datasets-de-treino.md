# Datasets de treino: decisão e situação

O avaliador disse que usar **vários datasets** na fase de treinamento é bom. Em **2026-10-19** o Carlos escolheu o **MINDS-Libras** e o **V-LIBRASIL** (o **Apoema-Libras560 foi descartado**, sem motivo registrado). Depois, ele baixou **só o V-LIBRASIL**: o MINDS-Libras é pesado demais (64,8 GB no total). **Hoje o único dataset local é o V-LIBRASIL.** O que sobrou do MINDS é um `data/raw/minds-libras/Sinalizador01.zip` **parcial** (~446 MB de 4,43 GB, git-ignorado, pode apagar).

## Decisão e situação

| Dataset | Conteúdo | Termos | Situação |
| --- | --- | --- | --- |
| **V-LIBRASIL** | 1.364 sinais, 3 sinalizantes ("articuladores"); termos extraídos do dataset de ASL (ASLLVD) e traduzidos | Pesquisa e educação; **sem redistribuição sem permissão**; sem uso comercial; citar a dissertação de Ailton Rodrigues (UFPE, 2021); DOI do dataset 10.21227/v589-hn68 | **Baixado pelo Carlos**, só na máquina dele, fora do repositório: `C:\Users\Carlos\Desktop\Projetos 6\Datasets\videos UFPE (V-LIBRASIL)\` |
| **MINDS-Libras** | 20 sinais, 12 sinalizantes, 5 repetições, vídeo 1080p/30 fps; CC BY 4.0 | Aberto | **Não baixado** (só um zip parcial). Decisão em aberto: ver "Segundo dataset" |
| ~~Apoema-Libras560~~ | 560 sinais, 7 sinalizantes, 320×240, acesso só pelo orientador | Restrito | **Descartado** |
| Libras-UFPel Corpus | 4 surdos nativos, estúdio a 60 fps, 2.400 frases e 2.400 sinais | — | Reserva; **ainda não liberado** (contato no artigo PROPOR 2026, `aclanthology.org/2026.propor-1.112`) |

## O que há no V-LIBRASIL local (conferido em 2026-10-19)

- **Estrutura:** pasta `videos UFPE (V-LIBRASIL)\` com `data\` (**4.086** `.mp4`, 10,11 GB), `annotations.csv` (4.086 linhas: `video_id, video_name, class, user_id, width, height, fps, url_page, url_download`) e `error.csv` (3 vídeos que falharam no download: **Congelar_Articulador3, Criança_Articulador3 e Poesia_Articulador2**; o portal teria 4.089).
- **Nomes:** `<Sinal>_Articulador<N>.mp4`. **1.364 sinais**; Articulador 1 tem 1.364 vídeos, o 2 tem 1.360 e o 3 tem 1.362. **1.358 sinais têm as 3 gravações; 6 têm 2.**
- **Vídeo:** 1920×1080 em 39 de 40 vídeos amostrados (1 em 1280×720; o CSV registra 1280×720 em alguns), **30 a 60 fps**, duração de 3,4 a 9,5 s (mediana 5,2 s), 102 a 371 quadros. A coluna `fps` do CSV **não é confiável** (traz valores como 389 e 148).
- **Enquadramento:** da cintura para cima. Os **quadris ficam fora do quadro** (y da imagem entre 1,02 e 1,16; visibilidade 0,5 a 0,9), então o MediaPipe os estima.
- **Detecção (9 vídeos: Banheiro, Filho e Barulho × 3 articuladores):** MediaPipe **sem** YOLOv8: corpo 100%, mão esquerda 97%, mão direita 96%. **Com** YOLOv8: 100%, 97% e 94%, e +1,3 s por vídeo. **O YOLOv8 não ajuda neste dataset** (a pessoa já ocupa o quadro). Amostra pequena.
- **Tempo:** ~8,7 s por vídeo sem YOLO, ou **cerca de 10 horas** para os 4.086 em um processo. A máquina tem 20 processadores lógicos.
- **Repouso:** nos 3 vídeos em que medi, o movimento dos punhos ocupa só 4% a 34% dos quadros, e o primeiro e o último quadro com movimento ficam longe das pontas (ex.: quadros 5 a 259 de 354). Limiar de movimento arbitrário, então é indício, mas aponta que **é preciso aparar o repouso** antes de reamostrar.
- **Variantes:** 68 classes têm desambiguação entre parênteses (`Batida (ritmo)`, `Cinza (cor)`). **"Avó" e "Avô" colidem** no nosso `slug()` (que tira acentos), então o casamento sem acento junta duas palavras diferentes.

## Sobreposição com os 20 sinais do MVP (que vêm do MINDS)

- **Mesmo nome (7):** ACONTECER, AMARELO, BANHEIRO, BARULHO, ESPELHO, FILHO (e FILHA), RUIM.
- **Nome parecido, outro sentido ou forma (3):** "Com medo" (MEDO), "Aluno do Segundo Ano do Ensino Médio" (ALUNO), "Maçã (rosto)" (a maçã do rosto, não a fruta).
- **Ausentes (10):** AMÉRICA, APROVEITAR, BALA, BANCO, CINCO, CONHECER, ESQUINA, SAPO, VACINA, VONTADE.

Consequência: **`data/vocabulary.json` (os 20 do MINDS) não descreve o V-LIBRASIL**, e as **30 frases de demonstração** dependem de sinais que ele não tem (VACINA, MEDO, ALUNO, CONHECER, AMÉRICA...). Usar o V-LIBRASIL como base exige novo vocabulário e novas frases.

## Extração do vocabulário (2026-10-20)

`python extract_keypoints.py vlibrasil ...` extraiu **629 vídeos** (os 210 sinais do vocabulário curado × 3 sinalizantes; CRIANÇA tem 2, porque o vídeo do articulador 3 falhou no download) para `C:\Users\Carlos\Desktop\Projetos 6\Datasets\processed\v-librasil` (79 MB, **fora do repositório**): MediaPipe sem YOLOv8, origem nos ombros, parte de baixo zerada, 30 fps e repouso aparado (13% dos quadros em média). Mãos detectadas em 91,5% (esquerda) e 93,5% (direita) dos quadros. **Resultado do treino nesses dados: o modelo não supera a média por sinal** (ver `11-modelo-ml.md`).

## Segundo dataset (decisão em aberto)

Com só o V-LIBRASIL, o treino tem **3 sinalizantes e uma gravação de cada por sinal**: dá para recuperação (medoide) e para validar em um sinalizante deixado de fora (2 gravações no treino por sinal), mas é pouco para rede neural. Opções:
- **MINDS-Libras, só o sinalizante 07** (2,53 GB, o menor zip; 20 sinais × 5 repetições, MD5 `8e885f5cb6823744a583f206e4d2051c`). Dá uma checagem entre datasets nos 7 sinais em comum. Pesado, mas bem menos que os 64,8 GB.
- **Nenhum:** ficar só com o V-LIBRASIL e dizer isso na entrega (o avaliador recomendou vários).
- **Libras-UFPel**, quando for liberado.

## Regras de uso

- **V-LIBRASIL:** os vídeos ficam em `Projetos 6\Datasets`, **fora da pasta do repositório** (`Projetos 6\Sinaliza`), então o git nem os vê. **Não versionar vídeos nem keypoints derivados**; guardar os keypoints em `data/processed/` (git-ignorado) ou também em `Datasets\`. O repositório é um GitHub (`Carlosesposito22/Sinaliza`) e **não sei se é público**: versionar seria redistribuir.
- Só pesquisa e ensino, **sem uso comercial**. Se o projeto algum dia virar produto, pedir permissão aos autores. Citar o dataset nas entregas e no README.
- MINDS-Libras (se for usado): `data/raw/` já está no `.gitignore`; keypoints derivados podem ser versionados com atribuição (CC BY 4.0), mas por padrão não versionamos `.npy`.

## Vias que não usamos para o V-LIBRASIL

IEEE DataPort (exige assinatura), cópia do Kaggle (terceiro, exige conta, termos oficiais proíbem redistribuir) e Hugging Face `MALTA-Lab/MALTA_LIBRAS` (cópia de terceiro em tensores, não verificada).

## Fontes

V-LIBRASIL: `ieee-dataport.org/documents/v-librasil-new-dataset-signs-brazilian-sign-language-libras`; termos em `libras.cin.ufpe.br/pages/conditions-of-use,3` (**a página estava fora do ar; os termos vêm de resumos de busca, não da leitura direta**). MINDS-Libras: `zenodo.org/records/2667329`. Libras-UFPel: `aclanthology.org/2026.propor-1.112`. Apoema-Libras560 (descartado): `zenodo.org/records/20421823`.
