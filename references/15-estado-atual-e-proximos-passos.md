# Estado atual e próximos passos

## Retomada (atualizada em 2026-11-07, após a Fase 10)

**Resumo.** Fases 1 a 10 do [plano de ML](22-plano-ml-texto-glosa.md) concluídas (a 9 ficou completa com o `web` compilando de novo), ~90% dos entregáveis que dão a nota ([checklist](23-checklist-requisitos-ml.md)). O modelo do T1 (manter ou descartar cada palavra) é o **Random Forest otimizado**, F1-macro 0,885 no teste final contra 0,823 da lista fixa, registrado no MLflow como `sinaliza-t1` v1. O Airflow orquestra o pipeline (4 DAGs) e a **API já usa o `sinaliza-t1`** no `/translate` (com plano B), grava as frases e há um simulador de uso. Faltam o painel, o Compose completo testado em máquina limpa e a apresentação. **Verificado em 2026-11-05:** a pilha postgres + mlflow + api (com o modelo) + airflow roda junto em ~2,7 GB dos 3,8 GB do Docker atual, subindo a API antes do Airflow; simulador → API → DAG `monitoramento` funcionou nela.

### O que está feito (e onde)

| Entregável | Feito | Documento |
| --- | --- | --- |
| 1 Bootstrap dataset | VLibrasBD (127.349 pares, hash conferido) no Postgres | [`24`](24-pipeline-de-dados-ponta-a-ponta.md) |
| 2 EDA e preparação | Notebooks 01 e 02, rótulos T1, divisão por frase | [`24`](24-pipeline-de-dados-ponta-a-ponta.md) |
| 3 Baseline | Regressão Logística 0,876 × lista fixa 0,822 | [`25`](25-baseline-t1.md) |
| 4 Comparação | Árvore 0,870, Random Forest 0,852, KNN 0,846 | [`26`](26-comparacao-de-modelos-t1.md) |
| 5 Optuna | Random Forest 0,852 → 0,884 (25 tentativas) | [`27`](27-otimizacao-random-forest.md) |
| 6 Validação | CV k=5, curva de aprendizado, fora do domínio, teste final | [`28`](28-validacao-e-generalizacao-t1.md) |

Decisões fechadas: abordagem por **glosa** aprovada pelo orientador; **embarcado e MQTT fora do escopo** (o embarcado não é do grupo); licença CC BY-SA do VLibrasBD resolvida só com **créditos**; modelo escolhido: **Random Forest otimizado**. Requisito R0 do orientador: deixar claro onde está o ML e documentar a pipeline ponta a ponta.

### O que falta (ordem sugerida)

1. ~~Fase 7, Airflow (entregável 2)~~ **feita em 2026-11-05**: DAGs `vlibrasbd_ingestao`, `preparacao_t1`, `treino_t1` e `monitoramento` e o serviço `airflow`. Como rodar e recursos em [`14`](14-como-rodar-e-testar.md); descrição dos DAGs em [`24`](24-pipeline-de-dados-ponta-a-ponta.md). Validação: ingestão e preparação (`limite` 3.000) e treino até a validação cruzada rodaram no Airflow, numa amostra e num experimento descartável (apagado); o gate do teste final (`--se-pendente`) foi conferido no MLflow real; o monitoramento foi testado com frases sintéticas. **Não foi feita** a execução completa dentro do Docker (preparação de 127 mil frases, Optuna de 25 tentativas): num Docker com 2 CPUs o primeiro trial já levou 12 min.
2. ~~Fase 8, integração (entregável 7)~~ **feita em 2026-11-05**: `textgloss/infer.py`, `api/app/model_provider.py`, `inference_log.py`, campos novos do contrato no `/translate`, `textgloss/simulador.py`, expurgo de texto no `monitoramento`. Ver [`12-api.md`](12-api.md) e [`24`](24-pipeline-de-dados-ponta-a-ponta.md). **Pendências:** (a) a equipe confirmar finalidade e retenção do texto e o **aviso de privacidade no web** antes de ligar `SINALIZA_LOG_TEXT` para usuários reais ([`16`](16-riscos-e-questoes-abertas.md)); (b) decidir se o modelo pode descartar palavra do vocabulário curado (hoje pode; `SINALIZA_MODEL_DISCARDS_KNOWN=false` inverte), porque ele erra palavras como "preciso"; (c) a API precisa de ~2,8 GB na carga e ~1,26 GB depois (a ordem de subida importa; ver [`14`](14-como-rodar-e-testar.md)).
3. ~~Fase 9, Docker Compose completo (entregável 8)~~ **feita em 2026-11-07, sem `web` e `dashboard`**: healthchecks e ordem de subida, `GET /ready`, `airflow/bootstrap.sh` (primeira subida automática, perfis `demo` e `completo`), `.env.example`, teste numa cópia limpa. Ver [`14`](14-como-rodar-e-testar.md). **Pendências:** (a) **o build do `web` falhava na `main`** depois do merge do PR #1 (`b07e48f`); **corrigido em 2026-11-08, ainda sem commit**: imports corrigidos em 2026-11-08 (sem mover nem renomear arquivos): `App.tsx` apontava `about`, `lesson` e `translator` para `src/features/...`, `Translatorpage.tsx` importava `../../api` e `Trail.test.ts`/`TrailPage.tsx` importavam `./Trail` (o arquivo é `trail.ts`). Verificado no Linux do Docker: `tsc` + `vite build` passam, os 6 testes do vitest passam, `docker compose up --build web` sobe (postgres → mlflow → api → web) e o Tradutor devolveu "FILHO · DOR DE CABEÇA" pela API real. **Segue pendente, e não é de import:** a aba **Trilha** mostra "Not Found" com a API real, porque `/learn/*` só existe no `mock-api` (no contrato é a parte do time do web). O arquivo `Translatorpage.tsx` (com `p` minúsculo) continua com esse nome e é importado assim; renomear para `TranslatorPage.tsx` é limpeza opcional do time do web (no Windows, renomear só a caixa de letras não aparece no git); (b) o `dashboard` foi feito na fase 10; (c) o perfil `completo` não foi executado inteiro no Docker.
4. ~~Fase 10, painel (entregável 9)~~ **feita em 2026-11-07**: `dashboard/` (Streamlit; abas Visão geral, Inferências, Modelo e Serviços; atualiza a cada 10 s; tema claro e escuro) e o serviço `dashboard` no compose. Verificado no navegador com 62 inferências reais do `sinaliza-t1` (banco descartável, já removido), o MLflow real e o Airflow real; 24 testes. A verificação achou dois erros que os testes não pegavam (o `/health` do MLflow responde texto puro e o painel o marcava fora do ar; o histograma saía como fatias finas), já corrigidos. Ver [`14`](14-como-rodar-e-testar.md). **Pendências:** o painel mostra o que o DAG `monitoramento` consolidou (a cada hora), então logo depois de usar a API os indicadores ainda não aparecem; o texto das frases só aparece para o simulador ou com `SINALIZA_LOG_TEXT=true`; o painel foi adicionado ao compose depois do teste em máquina limpa e não foi reexecutado nela.
5. **Fase 11, apresentação (entregável 10).** Demonstração ponta a ponta, decisões técnicas e limitações (ordem dos sinais, sem validação por pessoas surdas, ruído de rótulo, escopo sem embarcado).

### Pendências menores

- **Conferência manual das 200 palavras** (`data/processed/vlibrasbd/amostra_conferencia_200.csv`, coluna `rotulo_correto`, depois a última célula do notebook 02). Depende da equipe; dá a taxa de ruído dos rótulos.
- **R0 (orientador):** completar o documento de ponta a ponta [`24`](24-pipeline-de-dados-ponta-a-ponta.md) com treino, API e painel; atualizar os diagramas conforme as fases avançam.
- Avaliação ponta a ponta contra o `vlibras-translate` (BLEU/chrF/WER): opcional, não é da rubrica.
- Os valores de CV e fora do domínio usaram amostras; ver os limites em [`28`](28-validacao-e-generalizacao-t1.md).

### Como retomar o ambiente

```bash
docker compose up -d postgres mlflow
```

(Para o Airflow: `docker compose up -d airflow`, interface em http://localhost:8080; ver [`14`](14-como-rodar-e-testar.md).)

- MLflow: http://localhost:5000 (experimento `t1-manter-descartar`). Postgres: `localhost:5432`, usuário/senha/banco `sinaliza`.
- Ambiente Python do ML: `textgloss/.venv` (Python 3.12). Testes: `cd textgloss && .venv/Scripts/python -m pytest` (25 passam).
- Dados em `data/raw/vlibrasbd/` e `data/processed/vlibrasbd/` não são versionados. Se sumirem: `python -m textgloss.ingest`, depois `python -m textgloss.prepare --processos 4`.
- Os modelos e as runs vivem no volume `mlartifacts` e no Postgres do compose. Se o volume for apagado, refazer: `train baseline`, `train modelos`, `tune` (~40 min), `validate cv|curva|dominio` (~1 h) e **não** repetir o teste final (o código se recusa; ver abaixo).

### Cuidados

- **O teste final já foi usado.** Não ajustar modelo olhando para ele. Para mudar de modelo, seria preciso uma nova divisão de teste.
- O volume do Postgres já existente não roda `postgres/init-mlflow.sql`; em volume novo o banco `mlflow` é criado sozinho.
- O MLflow exige `skops_trusted_types=["sklearn.tree._tree.Tree"]` ao salvar árvores (já está no código).
- Treinos do Random Forest ocupam todos os núcleos e a memória; as consultas ao MLflow ficam lentas enquanto rodam.
- Não chamar a saída de "tradução de Libras": é "sequência de sinais" (regras do `CLAUDE.md`).

---

> **Situação dos requisitos de ML (atualizada em 2026-11-02).** A entrega de ML é o **texto → glosa por classificação** ([`22-plano-ml-texto-glosa.md`](22-plano-ml-texto-glosa.md)). Situação frente aos requisitos de ML da disciplina:
>
> | Requisito | Situação |
> | --- | --- |
> | Bootstrap dataset (VLibrasBD) + persistência no banco | **Feito em 2026-11-02** (`textgloss/ingest.py`, Postgres) |
> | Airflow + notebook de EDA + preparação | Notebooks e preparação **feitos em 2026-11-02**; DAGs do Airflow **feitos em 2026-11-05**; falta a conferência manual de 200 rótulos |
> | Baseline no MLflow | **Feito em 2026-11-02** (F1-macro 0,876 contra 0,822 da lista fixa) |
> | Três modelos comparados com gráficos | **Feito em 2026-11-02** (melhor: Regressão Logística, F1-macro 0,876) |
> | Optuna | **Feito em 2026-11-02** (Random Forest 0,852 → 0,884) |
> | Validação cruzada e generalização | **Feito em 2026-11-02**; teste final: Random Forest otimizado, F1-macro 0,885 |
> | Modelo integrado à API, consumindo frases novas | **Feito em 2026-11-05** (API com `sinaliza-t1`, simulador, `inferencias`, monitoramento) |
> | Docker Compose com Postgres, MLflow, Airflow, API, web e painel | Parcial (`api`, `web`, `postgres`, `mlflow` e `airflow`; faltam `dashboard` e o teste em máquina limpa) |
> | Painel | **Feito em 2026-11-07** (`dashboard/`, Streamlit) |
> | Embarcado + MQTT | Fora do escopo (decisão do Carlos; ver `23-checklist-requisitos-ml.md`) |
>
> **Próximos passos:** ver a seção "Retomada" abaixo.

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
6. ~~Avatar com rig~~ **feito em 2026-10-20:** rapaz realista (Microsoft Rocketbox, FBX, MIT) animado pelos keypoints, com retargeting próprio (braços, mãos e dedos). **2026-10-21:** movimento refeito (z do braço pelo comprimento do osso, suavização, cotovelo como dobradiça, pronação no antebraço, giro de cabeça e rolagem do peito, pausa entre repetições). **2026-10-25:** substituído pelo player do VLibras e guardado em `historico/avatar-rocketbox/` (ver 6b).
6b. **Avatar do VLibras (2026-10-25):** é o avatar do MVP (Ícaro, Hosana ou Guga), rodando localmente com os sinais do vocabulário; o Rocketbox foi para `historico/avatar-rocketbox/`. Em aberto: como apresentar a parte de ML, que não aparece mais no avatar; avatar próprio fica para depois do MVP. Ver `13-web.md`.
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
9. ~~Avatar com rig e retargeting~~ **feito** e depois substituído pelo VLibras (ver itens 6 e 6b).
10. **Validar com alguém que saiba Libras** (sinais, aproximações, frases) e registrar em `docs/`.
11. **Atualizar a documentação da disciplina** para o escopo atual.

## Pergunta que o projeto precisa responder para ser defensável

"O modelo gera movimento **melhor que simplesmente recuperar a gravação mais representativa** do sinal, em um sinalizante que o modelo nunca viu?" — medida em DTW. Se a resposta for "não", a conclusão honesta é **ficar com recuperação (medoide)** e dedicar o tempo restante a transições, avatar, interface e validação. Esse resultado também é um achado válido para a disciplina.

## Divergências encontradas entre documentos e código

- As entregas da fase 1 descrevem o escopo antigo (ver [`01-escopo-atual.md`](01-escopo-atual.md)).
- `Documentos/` (fase 1) fala em reconhecimento por câmera, MediaPipe ao vivo e LGPD de captura; nada disso existe mais no código.
