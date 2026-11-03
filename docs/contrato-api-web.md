# Contrato da API para o web (versão 1)

Combinado entre quem faz o **ML/API** e quem faz o **web** (trilha de aprendizado gamificada). **Quem vai fazer o web começa por [`guia-web-trilha.md`](guia-web-trilha.md).** Vale para o **mock** (`mock-api/`) e para a **API real** (`api/`): o web é escrito uma vez e só troca a URL.

| Fonte de verdade | Onde |
| --- | --- |
| Formatos (Pydantic) | [`mock-api/sinaliza_mock/schemas.py`](../mock-api/sinaliza_mock/schemas.py) |
| Tipos do front (TypeScript) | [`web/src/contract.ts`](../web/src/contract.ts) |
| Cliente da trilha | [`web/src/learnApi.ts`](../web/src/learnApi.ts) |
| Esquema OpenAPI do mock | [`docs/openapi-mock.json`](openapi-mock.json) (e `/docs` com o mock no ar) |
| Este texto | explica o porquê, as regras e os exemplos |

## 1. Como usar o mock agora

O mock responde na **porta 8000, a mesma da API real**, com o conteúdo da trilha de verdade (feito do vocabulário curado) e o tradutor com respostas falsas no formato final.

```bash
docker compose --profile mock up --build mock-api
```

Ou sem Docker, em um terminal na pasta `mock-api/`:

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn sinaliza_mock.server:app --port 8000
```

- Documentação interativa: http://localhost:8000/docs
- O front já aponta para `http://localhost:8000` (`VITE_API_URL`). Para trocar pela API real depois, mude só essa variável.
- **A API real (`api`) usa a mesma porta:** suba uma ou outra, nunca as duas.
- O mock aceita qualquer origem (CORS); a API real aceita só `http://localhost:5173`.
- Cabeçalhos só do mock: `X-Mock-Today: AAAA-MM-DD` simula outra data (testa sequência de dias); `DELETE /learn/progress` zera o progresso.
- Testes do mock: `cd mock-api && .venv/Scripts/python -m pytest`.

## 2. Convenções gerais

- JSON em UTF-8. Nomes de campos em `snake_case`. Glosas em MAIÚSCULAS, exatamente como estão em `/vocabulary` (ex.: `"DEVER DE CASA"`).
- **Erros:** status HTTP certo e corpo `{"detail": "mensagem em português"}`. `422` para entrada inválida ou texto sem sinais, `404` para lição inexistente, `400` sem `X-Learner-Id`, `409` para lição bloqueada. O front mostra o `detail` ao usuário.
- **Identidade (sem login na v1):** o front gera um UUID uma vez, guarda em `localStorage` e envia em **todas** as chamadas de progresso no cabeçalho `X-Learner-Id`. Não há dado pessoal. Trocar de navegador cria um perfil novo.
- **Compatibilidade:** mudanças na v1 só **acrescentam** campos. Remover ou renomear campo exige nova versão (`contract_version`), aviso ao outro lado e atualização dos quatro arquivos da tabela acima.
- **Avatar:** o front toca as glosas com o player local do VLibras (`VLibrasAvatar`, que recebe `glosses`). A API **não envia vídeo nem pose**; só nomes de sinais.

## 3. Endpoints

| Método e caminho | Quem implementa a versão real | O que faz |
| --- | --- | --- |
| `GET /health` | API | `{"status":"ok","contract_version":"1","mock":false}` |
| `POST /translate` | **ML** | texto → glosas, com a decisão do modelo por palavra |
| `GET /vocabulary` | API (existe) | os 210 sinais |
| `GET /categories` | API (existe) | frases de exemplo por categoria |
| `GET /learn/path` | **web** | a trilha: unidades e lições |
| `GET /learn/lessons/{id}` | **web** | uma lição com seus exercícios |
| `GET /learn/progress` | **web** | XP, nível, sequência e estado de cada lição |
| `POST /learn/lessons/{id}/complete` | **web** | registra o resultado e devolve o que mudou |
| `DELETE /learn/progress` | só mock | zera o progresso |

### 3.1 `POST /translate` (ML)

Pedido: `{"text": "A mãe vai à escola"}` (até 500 caracteres; vazio dá `422`).

```json
{
  "text": "A mãe vai à escola",
  "glosses": ["MÃE", "ESCOLA"],
  "matches": [
    {"word": "A", "gloss": null, "kind": "function", "score": 0.0, "decision": "DESCARTAR", "probability": 0.04},
    {"word": "mãe", "gloss": "MÃE", "kind": "exact", "score": 1.0, "decision": "MANTER", "probability": 0.97},
    {"word": "vai", "gloss": null, "kind": "ignored", "score": 0.0, "decision": "MANTER", "probability": 0.62}
  ],
  "generator": "mock",
  "pose": null,
  "model_version": "mock",
  "latency_ms": 1
}
```

- **Campos que já existem hoje:** `text`, `glosses`, `matches[].word|gloss|kind|score`, `generator`, `pose`.
- **Campos novos (este contrato):** `matches[].decision` (`MANTER` ou `DESCARTAR`, decidido pelo modelo de ML), `matches[].probability` (probabilidade de `MANTER`, 0 a 1), `model_version` (`"sinaliza-t1/1"` na API real com o modelo; `"lista-fixa"` se cair no plano B; `"mock"`), `latency_ms`.
- **`decision` × `kind`:** `decision` é o que o modelo decidiu; `kind` é o que aconteceu depois. Uma palavra pode ser `MANTER` e ainda assim `ignored` por não ter sinal no vocabulário. O front deve mostrar essa diferença (ex.: "o modelo manteve, mas ainda não temos esse sinal").
- `pose` é legado (`null` no mock): **o web não deve depender dele**.
- Chamar o resultado de **"sequência de sinais"**, não de "tradução de Libras".

### 3.2 `GET /learn/path`

```json
{
  "title": "Trilha de Libras",
  "disclaimer": "Sinais do vocabulário curado pela equipe ... não validados por falante de Libras. Isto é uma sequência de sinais, não uma aula de Libras.",
  "units": [
    {
      "id": "familia", "title": "Família", "description": "16 sinais de família",
      "color": "#58cc02", "icon": "👪",
      "lessons": [
        {"id": "familia-1", "title": "Família 1", "xp_reward": 20, "n_exercises": 13,
         "glosses": ["FAMÍLIA", "MÃE", "PAI", "FILHO"]}
      ]
    }
  ]
}
```

- A ordem de `units` e de `lessons` é a ordem da trilha. No mock são 6 unidades, 4 lições cada (24 lições, 96 sinais), todas feitas só com sinais do vocabulário.
- **Mostre o `disclaimer` na interface** (rodapé, tela de sobre ou na primeira lição). Ninguém do grupo fala Libras; não afirmar o contrário.
- `status` (bloqueada, disponível, concluída) **não vem aqui**, vem de `/learn/progress`.

### 3.3 `GET /learn/lessons/{id}`

`{"id", "unit_id", "title", "xp_reward", "exercises": [...]}`. Cada exercício tem `id` e `type`; o front escolhe o componente pelo `type`. Uma lição do mock tem 13 exercícios: 4 `learn_sign`, 4 `sign_to_word`, 4 `word_to_sign` e 1 `match_pairs`.

| `type` | O que mostrar | Campos | Como corrigir |
| --- | --- | --- | --- |
| `learn_sign` | cartão de apresentação: avatar toca `gloss`, mostra `word_pt` | `gloss`, `word_pt`, `forms` | não vale nota (conta como acerto) |
| `sign_to_word` | avatar toca `gloss`; escolher a palavra | `gloss`, `options[{id,text}]`, `correct_option_id` | comparar `id` escolhido |
| `word_to_sign` | mostra `text`; opções são botões que tocam cada sinal no avatar | `text`, `options[{id,gloss}]`, `correct_option_id` | comparar `id` escolhido |
| `match_pairs` | ligar cada sinal à sua palavra | `pairs[{id,gloss,text}]` | cada par é um acerto ou erro |

Exemplos reais:

```json
{"id":"familia-1-e1","type":"learn_sign","gloss":"FAMÍLIA","word_pt":"família","forms":["família"]}
{"id":"familia-1-e5","type":"sign_to_word","gloss":"FAMÍLIA","options":[{"id":"a","text":"menina"},{"id":"b","text":"família"},{"id":"c","text":"natal"}],"correct_option_id":"b"}
{"id":"familia-1-e9","type":"word_to_sign","text":"família","options":[{"id":"a","gloss":"AMIGO"},{"id":"b","gloss":"MENINA"},{"id":"c","gloss":"FAMÍLIA"}],"correct_option_id":"c"}
{"id":"familia-1-e13","type":"match_pairs","pairs":[{"id":"p3","gloss":"PAI","text":"pai"},{"id":"p4","gloss":"FILHO","text":"filho"},{"id":"p2","gloss":"MÃE","text":"mãe"},{"id":"p1","gloss":"FAMÍLIA","text":"família"}]}
```

- **A correção é no front**: a resposta certa vem no próprio exercício (`correct_option_id`, `pairs`). Aceitável para o MVP, já que não há ranking nem prêmio; o servidor só registra o resultado.
- Os exercícios **não são tipo-fechado**: o front deve ignorar com elegância um `type` desconhecido (a API pode ganhar tipos novos sem quebrar a v1).
- Vidas (coração) e tempo por exercício, se quiserem, ficam só no front na v1.

### 3.4 `GET /learn/progress` (cabeçalho `X-Learner-Id`)

```json
{
  "learner_id": "u1", "xp": 25, "level": 1, "xp_in_level": 25, "xp_to_next_level": 75,
  "streak_days": 1, "best_streak": 1, "daily_goal_xp": 20, "xp_today": 25, "goal_reached_today": true,
  "last_activity_date": "2026-11-02",
  "lessons": {
    "familia-1": {"status": "completed", "stars": 3, "best_accuracy": 1.0, "completions": 1},
    "familia-2": {"status": "available", "stars": 0, "best_accuracy": 0.0, "completions": 0},
    "familia-3": {"status": "locked", "stars": 0, "best_accuracy": 0.0, "completions": 0}
  }
}
```

### 3.5 `POST /learn/lessons/{id}/complete` (cabeçalho `X-Learner-Id`)

Pedido: `{"correct": 11, "total": 13, "mistakes": ["familia-1-e6", "familia-1-e10"]}` (`total ≥ 1`, `correct ≤ total`).
Resposta:

```json
{
  "passed": true, "accuracy": 0.8462, "stars": 2, "xp_gained": 17, "bonus_perfect": false,
  "level_up": false, "goal_reached_now": false,
  "unlocked_lesson_ids": ["familia-2"],
  "progress": { "...": "o mesmo objeto de GET /learn/progress, já atualizado" }
}
```

Lição `locked` dá `409`. Refazer uma lição concluída é permitido.

## 4. Regras de gamificação da v1 (quem implementa a API real segue estas)

| Regra | Valor |
| --- | --- |
| Acurácia | `correct / total` |
| Aprovação | acurácia ≥ 0,6; reprovar não dá XP, não desbloqueia e não conta no streak |
| Estrelas | ≥ 0,9 → 3; ≥ 0,75 → 2; aprovou abaixo disso → 1; reprovou → 0 (guarda-se a melhor) |
| XP da lição | `round(xp_reward × acurácia)`, mais 5 de bônus se acertou tudo |
| Nível | `1 + xp ÷ 100` |
| Meta diária | 20 XP por dia; `goal_reached_now` é verdadeiro na lição que cruzou a meta |
| Sequência (streak) | dias seguidos com pelo menos uma lição aprovada; passar um dia inteiro sem lição zera na leitura |
| Desbloqueio | linear: concluir uma lição libera a próxima da trilha (entre unidades também) |

O web pode propor mudanças (ex.: vidas, XP por tipo de exercício). Mudou? Ajusta `store.py` do mock, esta tabela e `contract.ts` no mesmo pull request.

## 5. O que muda quando a API real entrar

1. **`/translate` (ML):** passa a devolver `decision`, `probability`, `model_version`, `latency_ms` com o modelo `sinaliza-t1`. Hoje a API real **ainda não tem esses campos nem `/learn/*`**; até lá o front desenvolvido contra o mock mostra `model_version: "mock"`.
2. **`/learn/*`:** a API real precisa implementar os 4 endpoints. Proposta: um módulo próprio `api/app/learn/` (conteúdo gerado pelo mesmo vocabulário, progresso em Postgres) incluído em `api/app/main.py`, para quem faz web e quem faz ML não editarem os mesmos arquivos. Até lá, o mock é o servidor da trilha.
3. **Troca:** `VITE_API_URL` aponta para a API real; nenhuma mudança de código no front se o contrato for respeitado. Rodar os mesmos testes de contrato (`mock-api/tests`) contra a API real é um bom critério de pronto.

## 6. Quem é dono de quê

| Área | Dona |
| --- | --- |
| `/translate`, modelo, `matches`, `model_version` | ML (Carlos) |
| `/learn/*`, conteúdo da trilha, regras de gamificação, front | Web (as duas pessoas do web) |
| Este contrato, `schemas.py`, `contract.ts`, `openapi-mock.json` | os dois lados; mudança só com aviso e no mesmo PR |

Regenerar o OpenAPI depois de mudar `schemas.py`: `cd mock-api && .venv/Scripts/python -m sinaliza_mock.export_openapi` (o teste `test_openapi_exportado_esta_em_dia` falha se esquecer).

## 7. Perguntas em aberto

- **Login:** a v1 é anônima por `X-Learner-Id`. Contas de usuário ficam para depois.
- **Mais tipos de exercício** (ex.: montar frase, ditado de sinais): precisam de decisão linguística. Ninguém do grupo sabe Libras, então só entram tipos que não afirmem gramática (ordem dos sinais, por exemplo, não).
- **Trilha com mais sinais:** o mock usa 96 dos 210 sinais do vocabulário; ampliar é decisão de conteúdo.
- **Onde fica o tradutor na interface:** como tela separada ("Tradutor") ou como prática dentro da trilha. Decisão do web.
