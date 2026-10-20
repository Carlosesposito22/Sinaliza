# Estado atual e próximos passos

Posição em **2026-10-19**, segundo o código e o git. Os 5 commits originais são de 2026-10-14; depois vieram 2 commits de documentação (`Documentos/`, `references/`, `CLAUDE.md`). As implementações das sugestões do orientador (YOLOv8, embeddings, frases por categoria) estão **no working tree, ainda sem commit**.

## O que está pronto

| Componente | Situação |
| --- | --- |
| Estrutura do repositório | `api/`, `web/`, `model/`, `data/`, `docs/`, Docker |
| Formato de pose | Definido e documentado (75 keypoints, normalização em pixels) |
| Decisão de dados | MINDS-Libras, 20 sinais, subconjunto inicial de 4 sinalizantes |
| **Extração de keypoints** | **YOLOv8 recorta a pessoa + MediaPipe Holistic**, em CLI (`video` e `zip`), retomável, com log de detecção; 20 testes passam; rodou com pesos reais num vídeo de teste |
| Treino | Pipeline completo com linhas de base e DTW; testado com dados sintéticos; **inspeção dos embeddings de sinal** |
| **Texto → glosa** | Tabela (`vocabulary.json`) + **embeddings** para palavras fora do vocabulário (`char-ngram` padrão; `sentence-transformers` opcional) com limiar; cada palavra classificada em `exact/approx/function/ignored` |
| **Frases por categoria** | 30 frases em 6 categorias (`data/phrases.json`), geradas por modelos e validadas contra o vocabulário; `GET /categories` |
| API | `/health`, `/translate` (com `matches`), `/vocabulary`, `/categories`; gerador **stub** |
| Front | Categorias e frases de exemplo; mostra como cada palavra virou sinal (aproximada "~", ignorada riscada); avatar em esqueleto |
| Docker | `docker compose up --build` verificado em 2026-10-19: imagens constroem, API saudável, endpoints respondem direto e pelo nginx, front carrega as categorias |

## O que é stub, não verificado ou está faltando

1. **Dados reais:** o **V-LIBRASIL** está baixado (só local, fora do repositório) e **629 vídeos do vocabulário foram extraídos** (210 sinais × 3 sinalizantes) para `Projetos 6\Datasets\processed\v-librasil`. O **MINDS-Libras não foi baixado**. Faltam: **validar os sinais com alguém que saiba Libras** (a curadoria é só de palavras) e **investigar as mãos não detectadas** (70 gravações abaixo de 80% na esquerda). Ver `21-datasets-de-treino.md`.
2. **YOLOv8 roda com pesos reais** (`yolov8n.pt`, 6,25 MB, em `data/yolov8n.pt`, ignorado pelo git), mas o **ganho do recorte no MINDS-Libras não foi medido**. Num clipe de webcam e numa simulação 1080p o efeito em mãos foi pequeno (só apareceu com a pessoa a 35% do quadro). Primeiro experimento real: `--limit` pequeno com e sem `--no-yolo` nos vídeos do dataset, comparando `extraction_log.csv`.
3. ~~Gerador real~~ **feito em 2026-10-20 (reprodução de gravações):** a API toca a gravação real de um sinalizante do V-LIBRASIL para cada sinal, com transições interpoladas (`MotionPlayback`). Limites: sinais isolados, uma pessoa, sem gramática nem expressão facial, sem coarticulação aprendida; sem arquivo de movimentos, cai no aceno de teste.
4. **Embedder semântico não testado:** `sentence-transformers` só foi testado com modelo falso; o limiar 0,7 não está calibrado. O `char-ngram` está calibrado à mão (0,65) em poucos exemplos.
5. **Modelo treinado:** **primeiro resultado em dado real (2026-10-20, 3 folds)**: o modelo **não supera a média por sinal** (recuperação top-1 6,7% contra 7,6%; acaso 0,5%) e a vantagem dele no DTW médio é compatível com borrão. Pela regra do projeto, o modelo não se justifica; ver `11-modelo-ml.md`.
6. **Avatar com rig:** o front desenha esqueleto; falta GLB + retargeting.
7. **Controles de reprodução e destaque da glosa atual** no front.
8. **Validação linguística:** ninguém identificado para validar sinais, mapeamentos aproximados nem frases.
9. **Testes de front** e CI inexistentes.
10. **Documentação para a disciplina** reescrita para o escopo novo (hipótese, personas, requisitos).

## Próximos passos sugeridos (ordem de dependência)

1. **Concluir o download** dos sinalizantes 01, 02, 07, 10 (ou arranjar espelho/disco). Conferir a estrutura real dos ZIPs.
2. **Rodar a extração com `--limit` pequeno**, com e sem YOLOv8, nos vídeos do MINDS-Libras; comparar as taxas de mão detectada no `extraction_log.csv`. Decidir se o recorte vale o custo (nos testes o tempo ficou parecido; o YOLOv8 roda só a cada 15 quadros).
3. **Rodar o lote completo** do subconjunto.
4. **Rodar as linhas de base e o treino** em dados reais (`train.py`); depois `sinaliza_model.embeddings` para diagnosticar.
5. **Escolher o gerador:** medoide ou modelo, conforme o DTW.
6. ~~Implementar o `PoseGenerator` real~~ **feito** (ver item 3). Falta **destacar a glosa em execução** e **controles de reprodução** no front.
7. **Calibrar o embedder semântico** (se for usá-lo): lista de sinônimos esperados e de falsos positivos; ajustar `SINALIZA_APPROX_THRESHOLD`.
8. **Front:** destacar a glosa em execução, controles de reprodução.
9. **Avatar com rig** e retargeting (se der tempo).
10. **Validar com alguém que saiba Libras** (sinais, aproximações, frases) e registrar em `docs/`.
11. **Atualizar a documentação da disciplina** para o escopo atual.

## Pergunta que o projeto precisa responder para ser defensável

"O modelo gera movimento **melhor que simplesmente recuperar a gravação mais representativa** do sinal, em um sinalizante que o modelo nunca viu?" — medida em DTW. Se a resposta for "não", a conclusão honesta é **ficar com recuperação (medoide)** e dedicar o tempo restante a transições, avatar, interface e validação. Esse resultado também é um achado válido para a disciplina.

## Divergências encontradas entre documentos e código

- As entregas da fase 1 descrevem o escopo antigo (ver [`01-escopo-atual.md`](01-escopo-atual.md)).
- `Documentos/` (fase 1) fala em reconhecimento por câmera, MediaPipe ao vivo e LGPD de captura; nada disso existe mais no código.
