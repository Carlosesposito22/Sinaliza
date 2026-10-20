# API (`api/`)

FastAPI 0.115+, pydantic v2, Python 3.11 (no Docker). Título "Sinaliza API", versão `0.3.0`.

## Arquivos (`api/app/`)

| Arquivo | Papel |
| --- | --- |
| `main.py` | App, CORS, endpoints; monta `vocabulary`, `text_to_gloss` e `generator` |
| `vocabulary.py` | Lê `data/vocabulary.json` (`Vocabulary`, `Sign`); `lookup()` casa com acento primeiro; caminho por `SINALIZA_VOCABULARY` |
| `embeddings.py` | `Embedder` (Protocol), `CharNgramEmbedder`, `SentenceTransformerEmbedder`, `build_embedder` |
| `text_to_gloss.py` | `TextToGloss`: palavra → glosa por tabela, **lematizador** (simplemma) e, na falta, por embedding; formas de várias palavras; `Match` |
| `phrases.py` | Gerador das frases de exemplo por categoria; CLI `python -m app.phrases [--check]` |
| `generator.py` | `PoseGenerator` (Protocol: `name` e `generate`) e `StubGenerator` (aceno de teste) |
| `motion_generator.py` | `MotionPlayback`: toca gravações reais por sinal, com transições; `transition()` |
| `pose_format.py` | `POSE_COUNT=33`, `HAND_COUNT=21`, `NUM_KEYPOINTS=75`, `LOWER_BODY_START=23`, `LAYOUT` |
| `schemas.py` | `PoseSequence`, `TranslateRequest`, `WordMatch`, `TranslateResponse`, `VocabularyResponse`, `CategoriesResponse` |

Testes em `api/tests/` (`test_api.py`, `test_text_to_gloss.py`, `test_phrases.py`, `test_motion_generator.py`): **40, passam**. Requisitos: `requirements.txt` (inclui `numpy` e `simplemma`); opcional `requirements-semantic.txt` (`sentence-transformers`).

## Vocabulário

`data/vocabulary.json` (versão 2, gerado por `data/build_vocabulary.py`): **210 sinais curados do V-LIBRASIL** (escola 37, saúde 37, serviços 36, trabalho 24, família 30, geral 72; um sinal pode estar em mais de um contexto). Cada sinal tem `gloss`, `video_class` (nome da classe no V-LIBRASIL, usado para achar os vídeos), `pt` (formas em português, minúsculas, com acento), `contexts` e, às vezes, `note`. O vocabulário antigo do MINDS-Libras (20 sinais) ficou em `data/vocabulary-minds.json`.

## Fluxo do `POST /translate`

```
texto ──► TextToGloss.resolve ──► matches (por palavra) ──► glosas ──► generator.generate ──► pose
```

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

### `GET /health` → `{"status": "ok"}`

### `POST /translate`
Request: `{"text": "..."}` (até 500 caracteres; `strip()` e não pode ficar vazio → 422).

```json
{
  "text": "O filho está com dor de cabeça.",
  "glosses": ["FILHO", "DOR DE CABEÇA"],
  "matches": [
    {"word": "O", "gloss": null, "kind": "function", "score": 0.0},
    {"word": "filho", "gloss": "FILHO", "kind": "exact", "score": 1.0},
    {"word": "está", "gloss": null, "kind": "function", "score": 0.0},
    {"word": "com", "gloss": null, "kind": "function", "score": 0.0},
    {"word": "dor de cabeça", "gloss": "DOR DE CABEÇA", "kind": "exact", "score": 1.0}
  ],
  "pose": {"fps": 15, "layout": {"pose": [0, 33], "left_hand": [33, 54], "right_hand": [54, 75]}, "frames": []}
}
```
(`frames` abreviado.) Em `ignored`, o `score` é a melhor similaridade encontrada, abaixo do limiar.

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
