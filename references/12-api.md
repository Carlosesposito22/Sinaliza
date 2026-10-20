# API (`api/`)

FastAPI 0.115+, pydantic v2, Python 3.11 (no Docker). Título "Sinaliza API", versão `0.2.0`.

## Arquivos (`api/app/`)

| Arquivo | Papel |
| --- | --- |
| `main.py` | App, CORS, endpoints; monta `vocabulary`, `text_to_gloss` e `generator` |
| `vocabulary.py` | Lê `data/vocabulary.json` (`Vocabulary`, `Sign`), `slug()`; caminho por `SINALIZA_VOCABULARY` |
| `embeddings.py` | `Embedder` (Protocol), `CharNgramEmbedder`, `SentenceTransformerEmbedder`, `build_embedder` |
| `text_to_gloss.py` | `TextToGloss`: palavra → glosa por tabela e, na falta dela, por embedding; `Match` |
| `phrases.py` | Gerador das frases de exemplo por categoria; CLI `python -m app.phrases [--check]` |
| `generator.py` | `PoseGenerator` (Protocol, só `generate`) e `StubGenerator` |
| `pose_format.py` | `POSE_COUNT=33`, `HAND_COUNT=21`, `NUM_KEYPOINTS=75`, `LAYOUT` |
| `schemas.py` | `PoseSequence`, `TranslateRequest`, `WordMatch`, `TranslateResponse`, `VocabularyResponse`, `CategoriesResponse` |

Testes em `api/tests/` (`test_api.py`, `test_text_to_gloss.py`, `test_phrases.py`): 24, passam. Requisitos: `requirements.txt`; opcional `requirements-semantic.txt` (`sentence-transformers`).

## Fluxo do `POST /translate`

```
texto ──► TextToGloss.resolve ──► matches (por palavra) ──► glosas ──► generator.generate ──► pose
```

1. `resolve` tokeniza com `\w+` e classifica **cada palavra**, nesta ordem:
   - **`exact`**: a palavra, sem acento e sem diferença de caixa, é uma das formas `pt` de um sinal (`score` 1.0);
   - **`function`**: artigo, preposição ou conjunção da lista `FUNCTION_WORDS`, ou palavra de até 2 letras. Sem sinal próprio, não é falha;
   - **`approx`**: fora da tabela, mas o embedding a aproxima de uma forma conhecida com similaridade ≥ limiar → vira o sinal dessa forma. **É proposta**, não equivalência;
   - **`ignored`**: sem correspondência (ex.: "tem", "quer", "precisa"). A interface avisa.
2. As glosas são as dos `matches` que têm glosa, **na ordem do texto** (com repetições).
3. Sem palavras → 422 `"o texto não contém palavras"`. Com palavras mas **nenhuma** com sinal → 422 `"nenhuma palavra do texto tem sinal no vocabulário (20 sinais)"`.

Isto **não é tradução para Libras**: é a sequência de sinais isolados na ordem do texto.

## Endpoints

### `GET /health` → `{"status": "ok"}`
Healthcheck do Docker.

### `POST /translate`
Request: `{"text": "..."}` (até 500 caracteres; `strip()` e não pode ficar vazio → 422).

```json
{
  "text": "O alunoss tem medo",
  "glosses": ["ALUNO", "MEDO"],
  "matches": [
    {"word": "O", "gloss": null, "kind": "function", "score": 0.0},
    {"word": "alunoss", "gloss": "ALUNO", "kind": "approx", "score": 0.823},
    {"word": "tem", "gloss": null, "kind": "ignored", "score": 0.0},
    {"word": "medo", "gloss": "MEDO", "kind": "exact", "score": 1.0}
  ],
  "pose": {"fps": 15, "layout": {"pose": [0, 33], "left_hand": [33, 54], "right_hand": [54, 75]}, "frames": []}
}
```
(`frames` abreviado.) Em `ignored`, o `score` é a melhor similaridade encontrada, abaixo do limiar.

### `GET /vocabulary`
`{"signs": [{"gloss", "forms", "contexts", "note"}]}` — os 20 sinais de `vocabulary.json`.

### `GET /categories`
`{"categories": [{"id", "label", "phrases": [{"text", "glosses", "ignored"}]}]}` — lê `data/phrases.json`. Vazio se o arquivo não existir. Ordem: escola, saúde, serviços, trabalho, família, geral.

CORS só para `http://localhost:5173` e `http://127.0.0.1:5173`. No Docker, o nginx do front repassa `/api/`.

## Embeddings para palavras fora do vocabulário

Escolha por `SINALIZA_EMBEDDER`:

| Embedder | Captura | Não captura | Custo |
| --- | --- | --- | --- |
| `char-ngram` (padrão) | **forma**: flexões, plurais, erros de digitação ("alunoss", "vacinando", "baneiro") | **sentido** ("garoto" não vira FILHO) | só NumPy, sem download |
| `sentence-transformers` | **sentido** (sinônimos, palavras relacionadas) | também erra por proximidade semântica | PyTorch + modelo multilíngue (`paraphrase-multilingual-MiniLM-L12-v2`) baixado na primeira vez |

- **Limiar:** `SINALIZA_APPROX_THRESHOLD` (padrão do embedder). Para `char-ngram` é **0,65**, calibrado à mão no vocabulário atual: pega "alunoss" 0,82, "vacinando" 0,68, "baneiro" 0,67 e **não** pega "banca" 0,60 (→BANCO) nem "maquina" 0,57 (→ESQUINA). Perde erros maiores como "vacna" 0,55. Precisão antes de cobertura: o que passa vira sinal na tela.
- **`sentence-transformers` não foi testado com o modelo real** (nem o limiar 0,7 é calibrado); o adaptador foi testado com um modelo falso. Antes de usar, calibrar o limiar com exemplos de sinônimos e de falsos positivos.
- Palavras de até 2 letras e as de `FUNCTION_WORDS` nunca vão para a aproximação.
- A aproximação **nunca é silenciosa**: o front marca com "~" e avisa.

## Frases de exemplo por categoria (`phrases.py`)

"Geração de textos a partir de categorias", por **modelos de frase com lacunas**, escritos à mão em português (categoria = contexto do vocabulário). Cada frase só entra se:
- toda palavra com sinal casa por tabela (`exact`), sem aproximação;
- tem pelo menos dois sinais;
- tem pelo menos um sinal do contexto da categoria (`geral` é livre).

Se um modelo gerar frase inválida, a geração **falha** em vez de gravar. `python -m app.phrases` grava `data/phrases.json` (30 frases); `--check` confere se o arquivo está atualizado; um teste faz essa conferência. É texto em português, **não** Libras: palavras sem sinal (verbos) aparecem em `ignored`. Nenhum LLM é usado; um LLM só poderia entrar para propor frases, que passariam pela mesma validação.

## Interface do gerador

```python
class PoseGenerator(Protocol):
    def generate(self, glosses: list[str]) -> PoseSequence: ...
```

`to_glosses` **saiu** do gerador: o texto vira glosas em `TextToGloss`.

### `StubGenerator` (atual)

`fps=15`, 1 s por glosa (15 frames); cada frame é um **aceno** de braço direito, com frequência `2 + soma(ord(c)) % 3` por glosa. **Não representa Libras**; valida o fluxo ponta a ponta.

## Como plugar o modelo (próximo passo)

Criar uma classe que implemente `PoseGenerator` e trocar `generator` em `main.py`. Ela precisará:

1. obter por glosa uma sequência `(32, 75, 3)` do modelo ou do medoide, **reescalar no tempo** para a duração desejada e o `fps`;
2. **concatenar** com transições suaves (interpolação entre o último frame de um sinal e o primeiro do próximo);
3. carregar `checkpoints/model.pt` (ou os medoides) na inicialização. `api/requirements.txt` **não** inclui `torch`; com o medoide basta NumPy. Isso afeta o tamanho da imagem Docker;
4. respeitar `NUM_KEYPOINTS=75` e o layout.

`test_api.py` já assume 1 s por glosa (`len(frames) == 3 * fps` para 3 glosas); mudar o gerador exige ajustar esse teste.

## Docker

O build da API usa a **raiz do repositório** como contexto (`docker-compose.yml`: `context: .`, `dockerfile: api/Dockerfile`) para copiar `data/vocabulary.json` e `data/phrases.json` para `/srv/data/`, apontados por `SINALIZA_VOCABULARY` e `SINALIZA_PHRASES`. O `.dockerignore` da raiz exclui `Documentos/`, `references/`, `model/` e dados. Verificado em 2026-10-19: `docker compose up --build` constrói as duas imagens (api 358 MB, web 103 MB), a API fica saudável e `/health`, `/translate`, `/vocabulary` e `/categories` respondem direto (porta 8000) e pelo proxy do nginx (`localhost:5173/api/...`); o front carrega as categorias. O primeiro build revelou que o `numpy` faltava no `api/requirements.txt` (nos testes locais ele vinha do Python do sistema); corrigido.

## Pontos de atenção

- Sem autenticação, rate limit nem log do texto. Se o texto digitado passar a ser armazenado, vira dado a tratar (ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md)).
- A resposta carrega **todos os frames** em JSON. Para frases longas pode ficar pesada; compactar (arredondar casas, ou binário) se virar problema.
- A tabela de palavras vive em `vocabulary.json` (campo `pt`): para o sinal cobrir mais palavras, acrescente formas lá. Formas que diferem só por acento (`américa`/`america`) colapsam na mesma chave.
