# API (`api/`)

FastAPI 0.115+, pydantic v2, Python 3.11 (no Docker). Título "Sinaliza API", versão `0.1.0`.

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `app/main.py` | App, CORS, `GET /health`, `POST /translate`; instancia `generator = StubGenerator()` |
| `app/generator.py` | `PoseGenerator` (Protocol) e `StubGenerator` |
| `app/pose_format.py` | `POSE_COUNT=33`, `HAND_COUNT=21`, `NUM_KEYPOINTS=75`, `LAYOUT` |
| `app/schemas.py` | `PoseSequence`, `TranslateRequest`, `TranslateResponse` |
| `tests/test_api.py` | 4 testes (health, tradução, texto em branco, texto sem palavras) |
| `requirements.txt` | `fastapi>=0.115,<1`, `uvicorn[standard]>=0.30,<1`, `pydantic>=2.7,<3`, `pytest`, `httpx` |

## Endpoints

### `GET /health` → `{"status": "ok"}`
Usado no healthcheck do Docker.

### `POST /translate`
Request: `{"text": "..."}`. Validação: `max_length=500`; o texto é `strip()`ado e **não pode ficar vazio** (422).

Response (`TranslateResponse`):
```json
{ "text": "...", "glosses": ["..."], "pose": { "fps": 15, "layout": {...}, "frames": [...] } }
```
Erros: **422** se o texto for vazio/em branco ou **não contiver palavras** (`"o texto não contém palavras"`, ex.: `"?!..."`).

CORS permitido só para `http://localhost:5173` e `http://127.0.0.1:5173` (dev local). No Docker não há CORS: o nginx do front repassa `/api/`.

## Interface do gerador

```python
class PoseGenerator(Protocol):
    def to_glosses(self, text: str) -> list[str]: ...
    def generate(self, glosses: list[str]) -> PoseSequence: ...
```

### `StubGenerator` (atual)

- `to_glosses`: `re.findall(r"\w+", text)` em maiúsculas — **não consulta `vocabulary.json`**, não lematiza, não filtra. "Olá, mundo!" → `["OLÁ", "MUNDO"]`.
- `generate`: `fps=15`, 1 s por glosa (15 frames); cada frame é um **aceno** de braço direito (esquerdo parado), com frequência `2 + soma(ord(c)) % 3` por glosa. **Não representa Libras**; serve só para validar o fluxo ponta a ponta.
- O esqueleto de repouso e as mãos são desenhados à mão (geometria sintética em `_rest_pose`, `_hand`, `_frame`).

## Como plugar o modelo (próximo passo)

Criar uma classe que implemente `PoseGenerator` e trocar `generator` em `main.py`. Ela precisará:

1. **`to_glosses`**: usar `vocabulary.json` (campo `pt`, formas em minúsculas e sem acento tratadas como em `slug`) para mapear palavras → glosas; **decidir o que fazer com palavra desconhecida** (descartar? avisar na resposta? soletrar?). Considerar devolver as palavras ignoradas no payload para o front mostrar.
2. **`generate`**: obter por glosa uma sequência `(32, 75, 3)` do modelo/medoide, **reescalar no tempo** para a duração desejada e `fps`, **concatenar** com transições suaves (interpolação entre o último frame de um sinal e o primeiro do próximo) e devolver `PoseSequence`.
3. Carregar `checkpoints/model.pt` (ou os medoides) na inicialização. Hoje `api/requirements.txt` **não** inclui `torch`; se usar o medoide, basta NumPy. Decidir isso afeta o tamanho da imagem Docker.
4. Respeitar `NUM_KEYPOINTS=75` e o layout (`pose/left_hand/right_hand`).
5. Atualizar `test_api.py`: ele afirma `len(frames) == 2 * fps` para duas palavras e glosas `["OLÁ", "MUNDO"]`, que deixarão de valer.

## Pontos de atenção

- Sem autenticação, rate limit nem log do texto. Se o texto digitado passar a ser armazenado, vira dado a tratar (ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md)).
- Resposta carrega **todos os frames** em JSON (frames × 75 × 3 floats). Para frases longas, pode ficar pesada; limite de 500 caracteres ajuda. Compactar (arredondar para 3–4 casas, ou binário) se virar problema.
