# Datasets de treino: decisão e situação de acesso

O avaliador disse que usar **vários datasets** na fase de treinamento é bom. Em **2026-10-19** o Carlos escolheu, entre os candidatos que recomendamos, usar o **MINDS-Libras** e o **V-LIBRASIL**. O **Apoema-Libras560 foi considerado e descartado** pelo grupo (sem motivo registrado). Hoje são, portanto, **dois datasets**.

## Decisão

| Dataset | Papel | Conteúdo | Termos | Onde fica |
| --- | --- | --- | --- | --- |
| **MINDS-Libras** | Âncora | 20 sinais, 12 sinalizantes, 5 repetições, vídeo 1080p/30 fps | **CC BY 4.0**, aberto | `data/raw/minds-libras/` (dentro do repositório, git-ignorado) |
| **V-LIBRASIL** | Amplitude | 1.364 sinais, 4.089 vídeos (3 por sinal), 3 sinalizantes ("articuladores"); termos extraídos do dataset de ASL (ASLLVD) e traduzidos | Pesquisa e educação; **sem redistribuição sem permissão**; sem uso comercial; citar a dissertação de Ailton Rodrigues (UFPE, 2021); DOI do dataset 10.21227/v589-hn68 | **Só na máquina do Carlos, fora do repositório:** `C:\Users\Carlos\Desktop\Projetos 6\Datasets\v-librasil\` (pedido do Carlos por ser pesado) |

Descartado: **Apoema-Libras560** (560 sinais, 7 sinalizantes, 320×240, acesso só pelo orientador). Reserva, se o grupo quiser um terceiro: **Libras-UFPel Corpus** (ainda não liberado; contato no artigo PROPOR 2026, `aclanthology.org/2026.propor-1.112`).

## Situação em 2026-10-19

| Dataset | Situação | Próximo passo |
| --- | --- | --- |
| MINDS-Libras | **O Carlos baixa por conta própria** (sinalizantes 01, 02, 07 e 10, 16,3 GB). O download que eu tinha iniciado foi **interrompido a pedido dele** em 2026-10-19; sobrou um arquivo **parcial** `data/raw/minds-libras/Sinalizador01.zip` (~446 MB de 4,43 GB), que **não está completo** | Quando os zips estiverem em `data/raw/minds-libras/`, conferir os MD5 (abaixo) e extrair os keypoints (`data/extract_keypoints.py zip ...`). Os outros 8 sinalizantes (48,5 GB) só se o disco permitir |
| V-LIBRASIL | **Não baixado.** O portal `libras.cin.ufpe.br` responde **HTTP 502** em todas as páginas (testado várias vezes, pelo WebFetch e pelo `curl` do Windows; o servidor `150.161.2.11` responde na rede, o sistema por trás é que está fora). A pasta de destino já existe e está vazia | Tentar de novo mais tarde. Quando o portal voltar, abrir `https://libras.cin.ufpe.br/` no navegador, ir na aba **Download** e baixar por articulador (segundo o IEEE DataPort: 4,78 GB, 3,31 GB e 2,46 GB, 10,55 GB no total) para a pasta acima. Ou me passar os links que eu baixo |

Vias que **não** usamos para o V-LIBRASIL:
- **IEEE DataPort:** exige login e assinatura.
- **Cópia do Kaggle:** é de terceiro, exige conta, e os termos oficiais proíbem redistribuir.
- **Hugging Face (MALTA-Lab/MALTA_LIBRAS):** cópia de terceiro em formato de tensores; não verificamos se contém o V-LIBRASIL.
- O repositório `Malta-Lab/ISLR_LIBRAS` menciona um script de raspagem (`videos_download/download_videos.py`) para baixar os vídeos do portal; **não rodamos nem lemos esse script**, e só valeria revisá-lo antes de usar.

Disco livre antes dos downloads: **37,3 GB**. MINDS (16,3) + V-LIBRASIL (10,55) deixam cerca de 10 GB.

## Regras de uso

- **MINDS-Libras:** `data/raw/` já está no `.gitignore`. Pode versionar keypoints derivados **com atribuição** (CC BY 4.0), mas por padrão continuamos sem versionar `.npy`.
- **V-LIBRASIL:** os vídeos ficam em `Projetos 6\Datasets`, **fora da pasta do repositório** (`Projetos 6\Sinaliza`), então o git nem os enxerga. **Não versionar vídeos nem keypoints derivados**; guardar os keypoints em `data/processed/` (git-ignorado) ou também em `Datasets\`. O repositório é um GitHub (`Carlosesposito22/Sinaliza`) e **não sei se é público**: versionar seria redistribuir.
- V-LIBRASIL é só para pesquisa e ensino, **sem uso comercial**. Se o projeto algum dia virar produto, pedir permissão aos autores.
- Citar cada dataset nas entregas e no README.

## O que checar antes de misturar os dois

1. **Sobreposição de sinais.** Obter a **lista de sinais** do V-LIBRASIL (o portal tem busca por sinal) e cruzar com os 20 do MINDS. Sem sinais em comum não há validação entre datasets; o ganho fica no vocabulário.
2. **Mesmo rótulo não é, necessariamente, o mesmo sinal.** Libras tem variação regional e os termos do V-LIBRASIL vêm de tradução do ASL. Alguém que saiba Libras precisa conferir os rótulos antes de juntar.
3. **Domínios diferentes** (câmeras, fundos, pessoas): o modelo pode aprender "de qual dataset veio". Guardar o dataset de origem de cada amostra e, se possível, avaliar treinando em um e testando no outro.
4. **O V-LIBRASIL tem um sinalizante por sinal por pessoa** (3 por sinal): serve para recuperação (medoide) e vocabulário, não para treinar rede, e não permite validar em sinalizante novo com folga (só 3 pessoas). **A resolução dos vídeos é desconhecida** (não conseguimos abrir o portal).
5. Com **dois** datasets (e um deles com 3 pessoas), a validação entre datasets é mais fraca do que com três. Se isso incomodar, o Libras-UFPel é a opção mais forte quando for liberado.

## Conferir se o download do MINDS-Libras terminou

```powershell
Get-ChildItem data\raw\minds-libras | Select-Object Name, @{n='GB';e={[math]::Round($_.Length/1GB,2)}}
```

Tamanhos esperados (Zenodo): 01 = 4,43 GB, 02 = 4,67 GB, 07 = 2,53 GB, 10 = 4,68 GB. MD5 esperados: `0259b309d2d5472f20d9842547d94a8c`, `e2b8673264ba7fca4cfc071654a099e8`, `8e885f5cb6823744a583f206e4d2051c`, `d6012f3e49e95d0cef7f6ec888743baa`. Conferir um arquivo: `Get-FileHash data\raw\minds-libras\Sinalizador07.zip -Algorithm MD5`. Se parar no meio, repetir o comando de download do `data/README.md` (o `-C -` retoma). A listagem do PowerShell pode mostrar o tamanho atrasado enquanto o curl escreve.

## Fontes

V-LIBRASIL: `ieee-dataport.org/documents/v-librasil-new-dataset-signs-brazilian-sign-language-libras` e termos em `libras.cin.ufpe.br/pages/conditions-of-use,3` (**a página estava fora do ar; os termos vêm de resumos de busca, não da leitura direta**). MINDS-Libras: `zenodo.org/records/2667329`. Libras-UFPel: `aclanthology.org/2026.propor-1.112`. Apoema-Libras560 (descartado): `zenodo.org/records/20421823`.
