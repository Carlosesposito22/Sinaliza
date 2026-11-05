# API (`api/`)

FastAPI 0.115+, pydantic v2, Python 3.12 (no Docker). Título "Sinaliza API", versão `0.3.0`.

**Onde está o ML na API (fase 8):** o classificador T1, treinado por nós e registrado no MLflow como `sinaliza-t1`, decide para cada palavra do texto se ela vira sinal (MANTER) ou não (DESCARTAR). Ele substitui a lista fixa `FUNCTION_WORDS`, que sobrou só como plano B (`model_version: "lista-fixa"`). O restante (tabela do vocabulário, lema, aproximação por embedding, gerador) é regra ou externo. Código do modelo: `textgloss/infer.py`.

## Arquivos (`api/app/`)

| Arquivo | Papel |
| --- | --- |
| `main.py` | App, CORS, endpoints; monta `vocabulary`, `text_to_gloss`, `generator`, o provedor do modelo e o registro de inferências |
| `model_provider.py` | **ML:** carrega o `sinaliza-t1` do MLflow numa thread, repete até conseguir, devolve `None` enquanto não há modelo (plano B: lista fixa); devolve ao sistema a memória do pico de carga |
| `inference_log.py` | Grava cada frase atendida em `inferencias` (Postgres) em segundo plano; nunca afeta a resposta; texto só do simulador ou com `SINALIZA_LOG_TEXT=true` |
| `vocabulary.py` | Lê `data/vocabulary.json` (`Vocabulary`, `Sign`); `lookup()` casa com acento primeiro; caminho por `SINALIZA_VOCABULARY` |
| `embeddings.py` | `Embedder` (Protocol), `CharNgramEmbedder`, `SentenceTransformerEmbedder`, `build_embedder` |
| `text_to_gloss.py` | `TextToGloss`: palavra → glosa por tabela, **lematizador** (simplemma) e, na falta, por embedding; formas de várias palavras; `Match` |
| `phrases.py` | Gerador das frases de exemplo por categoria; CLI `python -m app.phrases [--check]` |
| `generator.py` | `PoseGenerator` (Protocol: `name` e `generate`) e `StubGenerator` (aceno de teste) |
| `motion_generator.py` | `MotionPlayback`: toca gravações reais por sinal, com transições; `transition()` |
| `pose_format.py` | `POSE_COUNT=33`, `HAND_COUNT=21`, `NUM_KEYPOINTS=75`, `LOWER_BODY_START=23`, `LAYOUT` |
| `schemas.py` | `PoseSequence`, `TranslateRequest`, `WordMatch`, `TranslateResponse`, `VocabularyResponse`, `CategoriesResponse` |

Testes em `api/tests/` (`test_api.py`, `test_api_model.py`, `test_text_to_gloss.py`, `test_text_to_gloss_model.py`, `test_model_provider.py`, `test_inference_log.py`, `test_phrases.py`, `test_motion_generator.py`): **63, passam** (2026-11-05; usam um classificador falso, não precisam do MLflow nem do spaCy; `pytest.ini` põe a raiz do repositório no path para achar `textgloss`). Requisitos: `requirements.txt` (inclui `numpy` e `simplemma`); `requirements-ml.txt` (modelo T1 e gravação: scikit-learn, skops, mlflow-skinny, spaCy, pandas, SQLAlchemy, psycopg; é o que o Docker instala); opcional `requirements-semantic.txt` (`sentence-transformers`).

## Vocabulário

`data/vocabulary.json` (versão 2, gerado por `data/build_vocabulary.py`): **210 sinais curados do V-LIBRASIL** (escola 37, saúde 37, serviços 36, trabalho 24, família 30, geral 72; um sinal pode estar em mais de um contexto). Cada sinal tem `gloss`, `video_class` (nome da classe no V-LIBRASIL, usado para achar os vídeos), `pt` (formas em português, minúsculas, com acento), `contexts` e, às vezes, `note`. O vocabulário antigo do MINDS-Libras (20 sinais) ficou em `data/vocabulary-minds.json`.

## Fluxo do `POST /translate`

```
texto ──► classificador T1 (ML) ──► decisões por palavra ──► TextToGloss.resolve ──► matches ──► glosas ──► generator ──► pose
                 │                                                                                                     
                 └─ sem modelo (ainda carregando, MLflow fora, falha): lista fixa FUNCTION_WORDS, model_version "lista-fixa"
```

0. **Classificador T1 (ML nosso).** `infer.T1Classifier.decide` roda o spaCy no texto (os mesmos atributos do treino) e devolve, para cada palavra, a probabilidade de MANTER (`>= 0,5` é MANTER). As decisões são alinhadas às palavras do `\w+` pela **posição em caracteres** (o spaCy e a regex quebram palavras de forma diferente). Regras que decorrem disso:
   - **DESCARTAR** → `kind: "function"`, sem sinal, **mesmo que a palavra esteja no vocabulário**. É o modelo que manda; para o vocabulário curado vencer, `SINALIZA_MODEL_DISCARDS_KNOWN=false` (a palavra conhecida vira `exact` com `decision: DESCARTAR`);
   - **MANTER** → segue para tabela/lema (`exact`), aproximação (`approx`) ou `ignored`;
   - **formas de várias palavras da tabela** ("dor de cabeça") vencem o modelo (regra): a `probability` delas é a média das palavras e a `decision` sai da média;
   - palavra que o spaCy não cobriu cai na lista fixa só para ela.
   - O modelo erra: em 2026-11-05, "preciso/precisa" saiu DESCARTAR (p ≈ 0,005) de forma consistente (provável erro de classe gramatical do spaCy), e "Eu" ficou em 0,44. É o limite de um F1-macro de 0,885 e deve aparecer na apresentação.
1. `resolve` tokeniza com `\w+`. Em cada posição tenta primeiro **formas de várias palavras** (até 3, ex.: "dor de cabeça", "por favor", "com licença") e depois a palavra sozinha, e classifica:
   - **`exact`**: a forma (com acento, sem diferença de caixa) é de um sinal; ou o **lema** dela é (`aconteceram` → `acontecer`, `comprando` → `comprar`). Sem acento só vale se **uma única** glosa casar (assim "avó" e "avô" não se misturam); `score` 1.0;
   - **`function`**: artigo, preposição, conjunção, pronome, "ser/estar" etc. sem sinal próprio, ou palavra de até 2 letras. Não é falha;
   - **`approx`**: fora da tabela, mas o embedding a aproxima de uma forma conhecida com similaridade ≥ limiar → vira o sinal dessa forma. **É proposta**, não equivalência;
   - **`ignored`**: sem correspondência (ex.: "precisa", "faz"). A interface avisa.
2. As glosas são as dos `matches` que têm glosa, **na ordem do texto**.
3. Sem palavras → 422 `"o texto não contém palavras"`. Com palavras mas **nenhuma** com sinal → 422 `"nenhuma palavra do texto tem sinal no vocabulário (210 sinais)"`.

O lematizador é o **simplemma** (pacote com dicionários de ~19 MB). Erra em alguns casos (`filhas` → `filhar`, `irmãs` → `irmão`, `amigas` → `amigar`); por isso o `vocabulary.json` lista as flexões que importam e a busca tenta a forma exata **antes** do lema. Sem o pacote instalado, a API funciona sem lematizar.

Isto **não é tradução para Libras**: é a sequência de sinais isolados na ordem do texto. Ex.: "O filho tem medo do hospital" vira FILHO TER COM MEDO HOSPITAL (o verbo "ter" existe como sinal, então entra).

## Endpoints

### `GET /health` → `{"status": "ok", "contract_version": "1", "mock": false, "model": "sinaliza-t1/1"}`

`model` é quem decide as palavras agora: `"sinaliza-t1/<versão>"`, `"lista-fixa (carregando o modelo)"` ou `"lista-fixa"` (modelo desligado). O `/health` responde logo; o modelo (864 MB) leva de 10 a 20 s para chegar.

### `POST /translate`
Request: `{"text": "..."}` (até 500 caracteres; `strip()` e não pode ficar vazio → 422).

```json
{
  "text": "O filho está com dor de cabeça.",
  "glosses": ["FILHO", "DOR DE CABEÇA"],
  "matches": [
    {"word": "O", "gloss": null, "kind": "function", "score": 0.0, "decision": "DESCARTAR", "probability": 0.0},
    {"word": "filho", "gloss": "FILHO", "kind": "exact", "score": 1.0, "decision": "MANTER", "probability": 0.92},
    {"word": "está", "gloss": null, "kind": "function", "score": 0.0, "decision": "DESCARTAR", "probability": 0.0},
    {"word": "com", "gloss": null, "kind": "function", "score": 0.0, "decision": "DESCARTAR", "probability": 0.01},
    {"word": "dor de cabeça", "gloss": "DOR DE CABEÇA", "kind": "exact", "score": 1.0, "decision": "MANTER", "probability": 0.6}
  ],
  "pose": {"fps": 15, "layout": {"pose": [0, 33], "left_hand": [33, 54], "right_hand": [54, 75]}, "frames": []},
  "model_version": "sinaliza-t1/1",
  "latency_ms": 180
}
```
(`frames` abreviado; probabilidades ilustrativas.) Em `ignored`, o `score` é a melhor similaridade encontrada, abaixo do limiar. Campos novos (contrato v1, `docs/contrato-api-web.md`): `matches[].decision` (o que o **modelo** decidiu) e `probability` (de MANTER), `model_version` e `latency_ms`. `decision` e `kind` são coisas diferentes: uma palavra pode ser MANTER e ainda assim `ignored` por não ter sinal. **Sem modelo** (`model_version: "lista-fixa"`), `probability` é só 0 ou 1 (regra da lista, não ML).

**Gravação:** depois de responder, a API grava a frase em `inferencias` (se `SINALIZA_LOG_DATABASE_URL` estiver definida): contagens, probabilidade média, decisões, latência, versão do modelo, origem (cabeçalho opcional `X-Origem`, só `[a-z0-9_-]` até 32 caracteres; o simulador envia `simulador`). **Texto e palavras só são gravados** para `X-Origem: simulador` (frases públicas) ou com `SINALIZA_LOG_TEXT=true`. Erro de gravação só vai para o log.

### `GET /vocabulary`
`{"signs": [{"gloss", "forms", "contexts", "note"}]}`.

### `GET /categories`
`{"categories": [{"id", "label", "phrases": [{"text", "glosses", "ignored"}]}]}` — lê `data/phrases.json`. Ordem: escola, saúde, serviços, trabalho, família, geral.

CORS só para `http://localhost:5173` e `http://127.0.0.1:5173`. No Docker, o nginx do front repassa `/api/`.

## Embeddings para palavras fora do vocabulário

Escolha por `SINALIZA_EMBEDDER`:

| Embedder | Captura | Não captura | Custo |
| --- | --- | --- | --- |
| `char-ngram` (padrão) | **forma**: erros de digitação ("escolla" → ESCOLA) | **sentido** | só NumPy, sem download |
| `sentence-transformers` | **sentido** (sinônimos) | também erra por proximidade semântica | PyTorch + modelo multilíngue baixado na primeira vez |

- **Limiar:** `SINALIZA_APPROX_THRESHOLD` (padrão do embedder). Para `char-ngram` é **0,7**, calibrado à mão no vocabulário de 210 sinais (281 formas): pega "escolla" (0,78) e **não** pega "banco" (0,64, → BRANCO) nem "irmao" (0,67, → IRMÃ, que é outra palavra). Com o vocabulário antigo (20 sinais) o limiar bom era 0,65: **sobe com o tamanho do vocabulário**; recalibrar se ele mudar.
- Com o lematizador, as flexões (plural, tempo verbal) já casam por lema; a aproximação ficou para erros de digitação.
- **`sentence-transformers` não foi testado com o modelo real**; o limiar 0,7 dele não está calibrado.
- A aproximação **nunca é silenciosa**: o front marca com "~" e avisa.

## Frases de exemplo por categoria (`phrases.py`)

"Geração de textos a partir de categorias", por **modelos de frase com lacunas**, escritos à mão em português (categoria = contexto do vocabulário). Cada frase só entra se toda palavra com sinal casar por tabela ou lema (nenhuma `approx`), tiver **pelo menos dois sinais** e **pelo menos um sinal do contexto** (`geral` é livre). Se um modelo gerar frase inválida, a geração **falha**. `python -m app.phrases` grava `data/phrases.json` (**57 frases**); `--check` confere se está atualizado, e um teste faz isso. É texto em português, **não** Libras; palavras sem sinal (verbos, por exemplo) aparecem em `ignored`.

## Geradores de pose

```python
class PoseGenerator(Protocol):
    name: str
    def generate(self, glosses: list[str]) -> PoseSequence: ...
```

A resposta de `POST /translate` traz `generator`: `"playback"` ou `"stub"`. O front usa isso para avisar o que a animação é.

### `MotionPlayback` (reprodução de gravações)

Escolhido quando `SINALIZA_MOTIONS` aponta para um arquivo `.npz` de movimentos (montado por `python -m sinaliza_model.motions`, em `model/`). Cada glosa vira a **gravação real de um sinalizante do V-LIBRASIL** (por padrão, o com mais mão detectada, o `01`: uma pessoa só para o avatar não "trocar de pessoa" entre sinais). Entre dois sinais, uma **transição de 8 quadros** (~0,27 s) interpola, com `smoothstep`, do último quadro de um ao primeiro do outro. Ponto ausente (`[0, 0, 0]`) em uma das pontas não é interpolado (não "corre" até a origem). Sinal sem movimento no arquivo é pulado; se nenhum tem, a API responde 422. A saída tem 30 fps e os valores são arredondados a 3 casas (em float64, para o JSON não carregar `0.12300000339`).

- Medido no arquivo real (210 sinais, 20 MB): "O filho está com dor de cabeça" → 2 sinais, 318 quadros, **489 KB de JSON**, 59 ms. Frases de ~12 sinais passam de 1 MB.
- **Por que reprodução e não rede:** no teste em dado real (3 folds) o modelo não superou a média por sinal, e uma gravação real é mais nítida que uma média (que borra as mãos). Ver `11-modelo-ml.md`.
- **Limites:** sinais isolados na ordem do texto, sem gramática, sem expressão facial, sem coarticulação aprendida (a transição é só interpolação); o movimento é de **uma** pessoa; os sinais não foram validados por falante de Libras. **Não é tradução para Libras.**
- Arquivo ausente ou inválido **não derruba a API**: cai no stub e avisa no log.
- O `.npz` é derivado do V-LIBRASIL (sem redistribuição): **fica fora do repositório**.

### `StubGenerator` (sem `SINALIZA_MOTIONS`)

`fps=15`, 1 s por glosa; cada quadro é um **aceno** de braço direito. **Não representa Libras** e não corresponde às glosas. Segue o contrato do formato de pose (origem nos ombros, 23–32 zerados).

`test_api.py` força o stub (mesmo que `SINALIZA_MOTIONS` esteja definida na máquina) e assume 1 s por glosa.

## Docker

**Fase 8 (2026-11-05):** a imagem agora é Python 3.12 com `requirements-ml.txt` e o modelo `pt_core_news_md` do spaCy (**1,43 GB**), e copia só `config.py`, `features.py`, `infer.py` e `monitor.py` do `textgloss`. O serviço `api` do compose define `MLFLOW_TRACKING_URI`, `SINALIZA_MODEL_CACHE` (volume `modelcache`, para não baixar o modelo a cada subida), `SINALIZA_LOG_DATABASE_URL` e `SINALIZA_LOG_TEXT`, e depende de `postgres` e `mlflow`. **Memória (medida):** o modelo chega a ~2,2 a 2,8 GB na carga e fica em ~1,26 GB (carregou em ~13 s no compose normal, em 2026-11-05; suba a API antes do Airflow); ver [`14-como-rodar-e-testar.md`](14-como-rodar-e-testar.md). Variáveis: `SINALIZA_USE_MODEL=false` (só lista fixa), `SINALIZA_MODEL_VERSION` (fixa a versão; padrão é a mais alta), `SINALIZA_MODEL_DISCARDS_KNOWN=false`. Para rodar fora do Docker, com o `textgloss` na raiz: `$env:PYTHONPATH=".."`.

O build da API usa a **raiz do repositório** como contexto para copiar `data/vocabulary.json` e `data/phrases.json` para `/srv/data/`. O `docker-compose.yml` monta a pasta de movimentos do host em `/srv/motions` (somente leitura) e aponta `SINALIZA_MOTIONS` para `/srv/motions/motions.npz`:

```powershell
$env:SINALIZA_MOTIONS_DIR = "C:\Users\Carlos\Desktop\Projetos 6\Datasets\motions"
docker compose up --build
```

Sem `SINALIZA_MOTIONS_DIR` a pasta padrão é `./data/motions` (vazia, git-ignorada) e a API usa o stub, com aviso no log. **Verificado em 2026-10-20** com e sem a variável (`generator` `playback` e `stub`; a imagem da API tem 397 MB com `simplemma`).

## Pontos de atenção

- Sem autenticação, rate limit nem log do texto.
- A resposta carrega **todos os frames** em JSON.
- Para o sinal cobrir mais palavras, acrescente formas em `data/build_vocabulary.py` (tabela `CURATED`) e rode `python build_vocabulary.py <annotations.csv>`; depois `python -m app.phrases`.
