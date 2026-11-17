# Contrato da API para o web (versão 2)

> **Versão 2 (2026-11-17):** a trilha passou a ser feita de **temas** (escola, família, saúde). Cada tema tem aulas de sinais, uma aula de frases e termina numa **prova**: o avatar sinaliza sem legenda e a pessoa escreve o que entendeu. Nota ≥ 70% libera o próximo tema; abaixo disso, ela refaz as aulas do tema antes de tentar de novo. Mudou: `units` → `themes`, `unit_id` → `theme_id`, `progress.themes`, `needs_redo`, `exam_unlocked`, os exercícios `learn_phrase` e `phrase_to_text` e os endpoints da prova. O conteúdo saiu do código e foi para `data/trilha.json`. Tudo isso é **regra, não ML**.
>
> **Só o nosso dicionário:** a trilha, os exercícios, a revisão, o desafio e o dicionário usam **apenas os 210 sinais do vocabulário curado** (`data/vocabulary.json`, classes do V-LIBRASIL). O avatar do VLibras só toca esses sinais. O mock recusa subir se `data/trilha.json` citar uma glosa fora dele, e `POST /learn/check` recusa glosa de fora (`422`).
>
> **Acrescentado depois (só acrescenta, ainda v2):** conquistas (3.8), exercício de escrever `sign_to_text` (3.3), `POST /learn/check` (3.9), revisão dos erros e desafio do dia (3.10), dicionário (3.11) e os campos `review_signs`, `challenge_available` e `challenge_done_today` no progresso.

Combinado entre quem faz o **ML/API** e quem faz o **web** (trilha de aprendizado gamificada). **Quem vai fazer o web começa por [`guia-web-trilha.md`](guia-web-trilha.md).** Vale para o **mock** (`mock-api/`) e para a **API real** (`api/`): o web é escrito uma vez e só troca a URL.

| Fonte de verdade | Onde |
| --- | --- |
| Formatos (Pydantic) | [`mock-api/sinaliza_mock/schemas.py`](../mock-api/sinaliza_mock/schemas.py) |
| Tipos do front (TypeScript) | [`web/src/contract.ts`](../web/src/contract.ts) |
| Cliente da trilha | [`web/src/learnApi.ts`](../web/src/learnApi.ts) |
| Esquema OpenAPI do mock | [`docs/openapi-mock.json`](openapi-mock.json) (e `/docs` com o mock no ar) |
| Este texto | explica o porquê, as regras e os exemplos |

## 1. Como usar o mock agora

O mock responde na **porta 8000, a mesma da API real**, com o conteúdo da trilha de verdade (lido de `data/trilha.json`) e o tradutor com respostas falsas no formato final.

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
- **Erros:** status HTTP certo e corpo `{"detail": "mensagem em português"}`. `422` para entrada inválida ou texto sem sinais, `404` para aula ou tema inexistente, `400` sem `X-Learner-Id`, `409` para aula bloqueada ou prova fechada. O front mostra o `detail` ao usuário.
- **Identidade (sem login por enquanto):** o front gera um UUID uma vez, guarda em `localStorage` e envia em **todas** as chamadas de progresso no cabeçalho `X-Learner-Id`. Não há dado pessoal. Trocar de navegador cria um perfil novo.
- **Compatibilidade:** dentro de uma versão, mudanças só **acrescentam** campos. Remover ou renomear campo exige nova versão (`contract_version`), aviso ao outro lado e atualização dos quatro arquivos da tabela acima.
- **Avatar:** o front toca as glosas com o player local do VLibras (`VLibrasAvatar`, que recebe `glosses`). A API **não envia vídeo nem pose**; só nomes de sinais.

## 3. Endpoints

| Método e caminho | Quem implementa a versão real | O que faz |
| --- | --- | --- |
| `GET /health` | API | `{"status":"ok","contract_version":"2","mock":false}` (a API real acrescenta `"model"`: `"sinaliza-t1/1"` ou `"lista-fixa"`) |
| `POST /translate` | **ML** | texto → glosas, com a decisão do modelo por palavra |
| `GET /vocabulary` | API (existe) | os 210 sinais |
| `GET /categories` | API (existe) | frases de exemplo por categoria |
| `GET /learn/path` | **web** | a trilha: temas, aulas e a prova de cada tema |
| `GET /learn/lessons/{id}` | **web** | uma aula com seus exercícios |
| `GET /learn/progress` | **web** | XP, nível, sequência, estado de cada tema e de cada aula |
| `POST /learn/lessons/{id}/complete` | **web** | registra o resultado da aula e devolve o que mudou |
| `GET /learn/themes/{id}/exam` | **web** | as questões da prova do tema, **sem gabarito** |
| `POST /learn/themes/{id}/exam` | **web** | corrige a prova e decide: libera o próximo tema ou manda refazer as aulas |
| `GET /learn/achievements` | **web** | a coleção de medalhas e troféus, ganhos ou não |
| `POST /learn/check` | **web** | corrige uma resposta escrita de treino (`sign_to_text`) com a regra da prova |
| `GET /learn/review` | **web** | sessão de revisão com os sinais mais errados |
| `GET /learn/challenge` | **web** | desafio do dia: sinais sorteados entre os já vistos |
| `POST /learn/practice/{id}/complete` | **web** | conclui uma sessão de revisão ou desafio |
| `GET /learn/dictionary` | **web** | os 210 sinais, com os já vistos marcados |
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
  "disclaimer": "Sinais do dicionário do VLibras escolhidos pela equipe; os rótulos e as frases não foram validados ...",
  "themes": [
    {
      "id": "escola", "title": "Escola", "description": "A escola, estudar e pedidos da sala de aula",
      "color": "#1cb0f6",
      "lessons": [
        {"id": "escola-1", "title": "A escola", "kind": "signs", "xp_reward": 20, "n_exercises": 15,
         "glosses": ["ESCOLA", "CRIANÇA", "LIVRO", "BANHEIRO"]},
        {"id": "escola-4", "title": "Frases da escola", "kind": "phrases", "xp_reward": 20, "n_exercises": 10,
         "glosses": ["CRIANÇA", "QUER", "IR", "BANHEIRO", "ESTUDO", "BIBLIOTECA", "APRENDER", "ESCREVER", "LIVRO"]}
      ],
      "exam": {"n_questions": 16, "pass_score": 0.7, "xp_reward": 50}
    }
  ]
}
```

- A ordem de `themes` e de `lessons` é a ordem da trilha. Hoje são 3 temas (Escola, Família, Saúde), com 3 ou 4 aulas cada.
- O conteúdo vem de **`data/trilha.json`**, escrito à mão pela equipe: cada sinal tem `word` (palavra de referência) e `accept` (flexões do português aceitas além das formas que o vocabulário já traz). **Toda glosa tem de estar nos 210 sinais de `data/vocabulary.json`**; o mock não sobe se não estiver. Para criar um tema, edite esse arquivo e rode os testes do mock (conferem o vocabulário e que as frases só usam sinais já ensinados).
- **Mostre o `disclaimer` na interface.** Ninguém do grupo fala Libras; não afirmar o contrário.
- `status` de tema e aula **não vem aqui**, vem de `/learn/progress`.

### 3.3 `GET /learn/lessons/{id}`

`{"id", "theme_id", "title", "kind", "xp_reward", "exercises": [...]}`. Cada exercício tem `id` e `type`; o front escolhe o componente pelo `type`. Aula de sinais (`kind: "signs"`, 15 exercícios): 4 `learn_sign`, 4 `sign_to_word`, 4 `word_to_sign`, 2 `sign_to_text` e 1 `match_pairs`. Aula de frases (`kind: "phrases"`, 10 exercícios): 1 `learn_phrase` e 1 `phrase_to_text` por frase e 2 `sign_to_text` de frase.

| `type` | O que mostrar | Campos | Como corrigir |
| --- | --- | --- | --- |
| `learn_sign` | cartão de apresentação: avatar toca `gloss`, mostra `word_pt` | `gloss`, `word_pt`, `forms` | não vale nota (conta como acerto) |
| `sign_to_word` | avatar toca `gloss`; escolher a palavra | `gloss`, `options[{id,text}]`, `correct_option_id` | comparar `id` escolhido |
| `word_to_sign` | mostra `text`; opções são botões que tocam cada sinal no avatar | `text`, `options[{id,gloss}]`, `correct_option_id` | comparar `id` escolhido |
| `match_pairs` | ligar cada sinal à sua palavra | `pairs[{id,gloss,text}]` | cada par é um acerto ou erro |
| `learn_phrase` | cartão da frase: avatar toca `glosses` em sequência, mostra `text` | `glosses`, `text` | não vale nota (conta como acerto) |
| `phrase_to_text` | avatar toca `glosses`; escolher a frase em português | `glosses`, `options[{id,text}]`, `correct_option_id` | comparar `id` escolhido |
| `sign_to_text` | avatar toca `glosses`; a pessoa **escreve** o que entendeu (treino para a prova) | `kind` (`sign`/`phrase`), `glosses`, `text` | `POST /learn/check` (3.9), mesma regra da prova; mostrar `text` só depois |

Exemplos reais:

```json
{"id":"escola-1-e1","type":"learn_sign","gloss":"ESCOLA","word_pt":"escola","forms":["escola","escolas"]}
{"id":"escola-1-e13","type":"sign_to_text","kind":"sign","glosses":["CRIANÇA"],"text":"criança"}
{"id":"escola-4-e1","type":"learn_phrase","glosses":["CRIANÇA","QUER","IR","BANHEIRO"],"text":"A criança quer ir ao banheiro."}
{"id":"escola-4-e5","type":"phrase_to_text","glosses":["CRIANÇA","QUER","IR","BANHEIRO"],"options":[{"id":"a","text":"Eu quero aprender."},{"id":"b","text":"Eu quero escrever no livro."},{"id":"c","text":"A criança quer ir ao banheiro."}],"correct_option_id":"c"}
{"id":"escola-4-e9","type":"sign_to_text","kind":"phrase","glosses":["CRIANÇA","QUER","IR","BANHEIRO"],"text":"A criança quer ir ao banheiro."}
```

- **As frases seguem a ordem do português**, sinal por sinal. Não são a gramática da Libras; a tela das frases deve dizer isso.
- **A correção das aulas é no front**: a resposta certa vem no próprio exercício; só a escrita (`sign_to_text`) pede a correção à API, para usar a mesma regra da prova. A **prova** é diferente: o gabarito fica no servidor (3.6).
- **Legenda do player desligada enquanto a pessoa responde** (a legenda escreve a glosa, que é a resposta). O front liga de novo nos cartões de apresentação e no feedback.
- Os exercícios **não são tipo-fechado**: o front deve ignorar com elegância um `type` desconhecido.

### 3.4 `GET /learn/progress` (cabeçalho `X-Learner-Id`)

```json
{
  "learner_id": "u1", "xp": 100, "level": 2, "xp_in_level": 0, "xp_to_next_level": 100,
  "streak_days": 1, "best_streak": 1, "daily_goal_xp": 20, "xp_today": 100, "goal_reached_today": true,
  "last_activity_date": "2026-11-17",
  "themes": {
    "escola": {"status": "exam_ready", "lessons_completed": 4, "lessons_total": 4, "exam_attempts": 0,
               "best_exam_score": 0.0, "last_exam_score": null, "must_redo": false},
    "familia": {"status": "locked", "...": "..."}
  },
  "lessons": {
    "escola-1": {"status": "completed", "stars": 3, "best_accuracy": 1.0, "completions": 1, "needs_redo": false}
  }
}
```

`themes[id].status`: `locked` (prova do tema anterior não aprovada), `learning` (faltam aulas), `exam_ready` (aulas feitas, prova aberta), `passed` (aprovado). `must_redo` e `lessons[id].needs_redo` ficam verdadeiros depois de uma prova reprovada, até a aula ser refeita.

### 3.5 `POST /learn/lessons/{id}/complete` (cabeçalho `X-Learner-Id`)

Pedido: `{"correct": 11, "total": 13, "mistakes": ["escola-1-e6", "escola-1-e10"]}` (`total ≥ 1`, `correct ≤ total`).
Resposta:

```json
{
  "passed": true, "accuracy": 0.8462, "stars": 2, "xp_gained": 17, "bonus_perfect": false,
  "level_up": false, "goal_reached_now": false,
  "unlocked_lesson_ids": ["escola-2"],
  "exam_unlocked": false,
  "progress": { "...": "o mesmo objeto de GET /learn/progress, já atualizado" }
}
```

Aula `locked` dá `409`. Refazer uma aula concluída é permitido. `exam_unlocked` é verdadeiro na aula que era a última pendente do tema.

### 3.6 `GET /learn/themes/{id}/exam` (cabeçalho `X-Learner-Id`)

```json
{
  "theme_id": "escola", "title": "Prova: Escola", "pass_score": 0.7,
  "questions": [
    {"id": "escola-q7", "kind": "sign", "glosses": ["BANHEIRO"]},
    {"id": "escola-q13", "kind": "phrase", "glosses": ["CRIANÇA", "QUER", "IR", "BANHEIRO"]}
  ]
}
```

- Uma questão por sinal do tema e uma por frase. A ordem é embaralhada e muda a cada tentativa.
- **Sem gabarito e sem legenda:** a resposta não vem no JSON e o front desliga a legenda do player (`vlibrasPlayer().setSubtitles(false)`) enquanto a prova corre; a legenda volta na tela de correção.
- Prova fechada (aulas pendentes ou tema bloqueado) dá `409`; tema inexistente, `404`.

### 3.7 `POST /learn/themes/{id}/exam` (cabeçalho `X-Learner-Id`)

Pedido: `{"answers": [{"question_id": "escola-q13", "text": "professor pode ir cozinha"}]}`. Questão sem resposta vale 0; `question_id` de outro tema dá `422`.

```json
{
  "passed": false, "score": 0.6, "pass_score": 0.7, "xp_gained": 0, "level_up": false, "goal_reached_now": false,
  "questions": [
    {"question_id": "escola-q13", "kind": "phrase", "glosses": ["CRIANÇA", "QUER", "IR", "BANHEIRO"],
     "expected_text": "A criança quer ir ao banheiro.", "answer": "crianças querem ir cozinha", "score": 0.6,
     "signs": [{"gloss": "CRIANÇA", "word": "criança", "correct": true}, {"gloss": "QUER", "word": "querer", "correct": true},
               {"gloss": "IR", "word": "ir", "correct": true}, {"gloss": "BANHEIRO", "word": "banheiro", "correct": false}],
     "extra_words": ["cozinha"]}
  ],
  "unlocked_theme_ids": [],
  "must_redo_lesson_ids": ["escola-1", "escola-2", "escola-3", "escola-4"],
  "progress": { "...": "o mesmo objeto de GET /learn/progress, já atualizado" }
}
```

(Exemplo com uma questão só; a nota da prova é a média de todas.)

**Correção (regra, não ML; código em `mock-api/sinaliza_mock/grading.py`):**

1. A resposta é normalizada: minúsculas, sem acento, sem pontuação.
2. Cada glosa da questão procura na resposta uma das formas de `accept` (ex.: `IR` aceita "vou", "vai"; `QUER` aceita "quero"). Cada palavra vale para um sinal só. **A ordem não importa**: não afirmamos nada sobre a ordem dos sinais em Libras.
3. Palavras que sobram contam como erro (para não valer escrever todas as palavras do tema). Não contam as palavras funcionais (artigos, preposições, pronomes) nem as da frase esperada que não viraram sinal ("precisa" em "O doente precisa dormir").
4. Nota da questão = sinais certos ÷ (sinais da questão + palavras que sobraram). Nota da prova = média das questões.

### 3.8 `GET /learn/achievements` (cabeçalho `X-Learner-Id`)

A coleção de conquistas (medalhas e troféus), ganhas ou não. Acrescentado em 2026-11-17, dentro da v2 (só acrescenta).

```json
{
  "unlocked_count": 7, "total": 17,
  "achievements": [
    {"id": "nota-maxima", "title": "Nota máxima", "description": "Tire 100% numa prova de tema.",
     "kind": "trophy", "tier": "gold", "category": "provas", "icon": "star",
     "unlocked": true, "unlocked_at": "2026-11-17", "current": 1, "target": 1},
    {"id": "persistente", "title": "Persistente", "description": "Entregue 5 provas.",
     "kind": "medal", "tier": "silver", "category": "provas", "icon": "exam",
     "unlocked": false, "unlocked_at": null, "current": 1, "target": 5}
  ]
}
```

- `kind`: `medal` ou `trophy`; `tier`: `bronze`, `silver` ou `gold`; `category`: `temas`, `provas`, `aulas` ou `habito`. `icon` é um nome curto; o front desenha um padrão se não conhecer.
- `current`/`target` servem para a barra de progresso das conquistas de contagem ("2/5").
- `LessonResult` e `ExamResult` ganharam `new_achievements` (mesmo formato): as conquistas ganhas **naquela** aula ou prova, para o front comemorar na hora.
- O catálogo e as regras ficam em `mock-api/sinaliza_mock/achievements.py`: 6 de provas (primeira prova, aprovado, nota máxima, de primeira, volta por cima, 5 provas), 4 de aulas, 3 de hábito (3 e 7 dias seguidos, nível 3), 1 troféu por tema e "Trilha completa". Conquista ganha nunca é perdida; a data é a da primeira vez.

### 3.9 `POST /learn/check`

Corrige uma resposta escrita de treino (`sign_to_text`) com a regra da prova (3.7). Não grava nada.
Pedido: `{"glosses": ["CRIANÇA", "QUER", "IR", "BANHEIRO"], "text": "A criança quer ir ao banheiro.", "answer": "criança quer ir"}`.

```json
{"correct": false, "score": 0.75, "expected_text": "A criança quer ir ao banheiro.",
 "signs": [{"gloss": "CRIANÇA", "word": "criança", "correct": true}, {"gloss": "QUER", "word": "querer", "correct": true},
           {"gloss": "IR", "word": "ir", "correct": true}, {"gloss": "BANHEIRO", "word": "banheiro", "correct": false}],
 "extra_words": []}
```

`correct` é verdadeiro só com nota 1 (todos os sinais e nenhuma palavra sobrando). Glosa fora do vocabulário dá `422`.

### 3.10 Revisão dos erros e desafio do dia (cabeçalho `X-Learner-Id`)

- `GET /learn/review` → `Practice` com até 5 sinais, os mais errados primeiro; 2 exercícios por sinal (escolher e escrever). `409` se não há nada para revisar.
- `GET /learn/challenge` → `Practice` com até 5 sinais sorteados entre os que a pessoa já viu em aulas (o mesmo sorteio o dia todo); 1 exercício por sinal, alternando escolher, escrever e palavra → sinal. `completed_today` diz se já foi feito hoje. `409` se a pessoa ainda não fez nenhuma aula.
- `POST /learn/practice/{id}/complete` com o mesmo corpo da aula (`correct`, `total`, `mistakes`) → `PracticeResult` (`passed`, `accuracy`, `xp_gained`, `level_up`, `goal_reached_now`, `cleared_glosses`, `new_achievements`, `progress`). A sessão é de uso único (`404` depois).

`Practice`: `{"id", "kind": "review"|"challenge", "title", "xp_reward", "glosses", "exercises", "completed_today"}`. O front joga os exercícios com o mesmo componente das aulas.

### 3.11 `GET /learn/dictionary` (cabeçalho `X-Learner-Id`)

Os 210 sinais do vocabulário, os já vistos primeiro: `{"total": 210, "seen_count": 4, "signs": [{"gloss": "LIVRO", "word": "livro", "forms": ["livro"], "theme_ids": ["escola"], "seen": true, "mistakes": 0}, ...]}`. `seen`: apareceu numa aula feita. `theme_ids` vazio: o sinal existe no vocabulário mas nenhum tema o ensina ainda. `mistakes`: erros ainda na fila de revisão.

## 4. Regras de gamificação (quem implementa a API real segue estas)

| Regra | Valor |
| --- | --- |
| Acurácia da aula | `correct / total` |
| Aprovação na aula | acurácia ≥ 0,6; reprovar não dá XP, não conta a aula como feita e não conta no streak |
| Estrelas | ≥ 0,9 → 3; ≥ 0,75 → 2; aprovou abaixo disso → 1; reprovou → 0 (guarda-se a melhor) |
| XP da aula | `round(xp_reward × acurácia)`, mais 5 de bônus se acertou tudo |
| Temas | só o primeiro começa aberto; o próximo abre quando a **prova** do anterior é aprovada |
| Aulas no tema | abrem em ordem; com todas feitas, a prova abre |
| Prova aprovada | nota ≥ 0,7 (`pass_score`); 50 XP só na primeira aprovação; refazer depois só melhora a melhor nota |
| Prova reprovada | num tema ainda não aprovado, **todas as aulas do tema voltam a ficar pendentes** (abertas, em qualquer ordem, com as estrelas antigas guardadas); a prova só reabre quando todas forem refeitas |
| Nível | `1 + xp ÷ 100` |
| Meta diária | 20 XP por dia; `goal_reached_now` é verdadeiro na aula ou prova que cruzou a meta |
| Sequência (streak) | dias seguidos com pelo menos uma aula ou prova aprovada; um dia inteiro sem nada zera na leitura |
| Conquistas | avaliadas depois de cada aula, prova e treino; ganha uma vez, nunca perde; regras em `achievements.py` (3.8) |
| Fila de revisão | cada exercício errado numa aula (menos `match_pairs`, que não diz qual sinal foi confundido), cada sinal errado na prova e cada erro no desafio põe o sinal na fila; acertar todos os exercícios dele numa revisão ou desafio o tira |
| Revisão | passar (≥ 60%) dá 10 XP |
| Desafio do dia | passar (≥ 60%) dá 15 XP na primeira vez do dia; refazer no mesmo dia é só treino |

O web pode propor mudanças (ex.: vidas, outra nota mínima). Mudou? Ajusta `store.py`/`content.py` do mock, esta tabela e `contract.ts` no mesmo pull request.

## 5. O que muda quando a API real entrar

1. **`/translate` (ML):** passa a devolver `decision`, `probability`, `model_version`, `latency_ms` com o modelo `sinaliza-t1`. Hoje a API real **ainda não tem esses campos nem `/learn/*`**; até lá o front desenvolvido contra o mock mostra `model_version: "mock"`.
2. **`/learn/*`:** a API real precisa implementar os 12 endpoints de `/learn` (sem o `DELETE`). Proposta: um módulo próprio `api/app/learn/` (conteúdo lido de `data/trilha.json`, correção igual a `grading.py`, conquistas iguais a `achievements.py`, progresso em Postgres) incluído em `api/app/main.py`, para quem faz web e quem faz ML não editarem os mesmos arquivos. Até lá, o mock é o servidor da trilha.
3. **Troca:** `VITE_API_URL` aponta para a API real; nenhuma mudança de código no front se o contrato for respeitado. Rodar os mesmos testes de contrato (`mock-api/tests`) contra a API real é um bom critério de pronto.

## 6. Quem é dono de quê

| Área | Dona |
| --- | --- |
| `/translate`, modelo, `matches`, `model_version` | ML (Carlos) |
| `/learn/*`, conteúdo da trilha, regras de gamificação, front | Web (as duas pessoas do web) |
| Este contrato, `schemas.py`, `contract.ts`, `openapi-mock.json` | os dois lados; mudança só com aviso e no mesmo PR |

Regenerar o OpenAPI depois de mudar `schemas.py`: `cd mock-api && .venv/Scripts/python -m sinaliza_mock.export_openapi` (o teste `test_openapi_exportado_esta_em_dia` falha se esquecer).

## 7. Perguntas em aberto

- **Login:** por enquanto é anônimo, por `X-Learner-Id`. Contas de usuário ficam para depois.
- **Mais tipos de exercício** (ex.: montar frase, ditado de sinais): precisam de decisão linguística. Ninguém do grupo sabe Libras, então só entram tipos que não afirmem gramática (ordem dos sinais, por exemplo, não).
- **Mais temas e sinais:** hoje são 3 temas e 32 dos 210 sinais do vocabulário. Ampliar é editar `data/trilha.json`, sempre dentro do vocabulário. Palavras como "professora", "aluno" e "posso" ficaram de fora porque não estão nos 210. As formas aceitas (`accept`) são português, não Libras, mas não foram revisadas por ninguém de fora.
- **Onde fica o tradutor na interface:** como tela separada ("Tradutor") ou como prática dentro da trilha. Decisão do web.
