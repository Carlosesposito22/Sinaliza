# Guia para quem vai fazer o web: a trilha de Libras gamificada

Leia este arquivo primeiro. Ele junta o contexto que vocês precisam para andar sem esperar o ML. O detalhe técnico da API está em [`contrato-api-web.md`](contrato-api-web.md); aqui está o **porquê**, o **o quê** e o **como começar**.

## 1. A missão em poucas linhas

Construir, no `web/`, uma **trilha de aprendizado de sinais de Libras**, gamificada e **inspirada no Duolingo**: a pessoa avança por unidades e lições, faz exercícios curtos com um avatar que sinaliza, ganha XP, estrelas e sequência de dias. O **tradutor de texto** que já existe continua como uma tela à parte.

- **Quem usa:** gente que quer aprender os primeiros sinais (familiares, colegas, profissionais de escola e saúde). Pensem em celular primeiro.
- **O que existe hoje:** só o tradutor (`App.tsx`) e o avatar. A trilha é toda nova.
- **O ML** fica com o Carlos. Vocês conversam com ele só pelo contrato; o **mock** responde no lugar do ML até ele terminar.

## 2. Em 15 minutos: rodando

Precisa de Node 20+, Docker (ou Python 3.12) e internet na primeira vez.

```bash
docker compose --profile mock up --build mock-api
```

Em outro terminal, na pasta `web/`:

```bash
npm install
npm run signs
npm run dev
```

- `npm run signs` baixa, **uma vez**, os 209 sinais do dicionário do VLibras para `web/public/vlibras/signs/` (fora do git). Sem isso o avatar **soletra** em vez de sinalizar.
- O front abre em http://localhost:5173 e fala com o mock em http://localhost:8000. Teste a API no navegador em http://localhost:8000/docs.
- Sem Docker: veja [`mock-api/README.md`](../mock-api/README.md).
- A porta 8000 é a da API real também: **suba o mock ou a API real, não os dois**.
- `npm run build` (tipos + build) e `npm test` precisam continuar passando.

## 3. O que já está pronto para vocês usarem

| Arquivo | Para quê |
| --- | --- |
| [`src/contract.ts`](../web/src/contract.ts) | Tipos de **tudo** que a API devolve (trilha, exercícios, progresso, tradutor). Usem em vez de escrever tipos novos |
| [`src/learnApi.ts`](../web/src/learnApi.ts) | `fetchPath`, `fetchLesson`, `fetchProgress`, `completeLesson`, `resetProgress`; já gera e guarda o `X-Learner-Id` |
| [`src/VLibrasAvatar.tsx`](../web/src/VLibrasAvatar.tsx) | O avatar: recebe `glosses` e toca (Ícaro, Hosana ou Guga) |
| [`src/vlibras.ts`](../web/src/vlibras.ts) | Ponte com o player (`vlibrasPlayer().play(...)`, `toVlibrasGloss`) |
| [`src/App.tsx`](../web/src/App.tsx), [`src/api.ts`](../web/src/api.ts) | O tradutor atual (exemplo de como consumir a API) |
| [`../mock-api`](../mock-api/README.md) | O servidor de mentira, com a trilha de verdade (24 lições, 96 sinais) |

O que **não existe** e é de vocês: rotas, telas da trilha, componentes de exercício, estado global, design, testes de interface.

## 4. Regras que não se negociam

1. **Nenhum sinal é inventado.** Só existem os sinais que a API manda (do vocabulário curado, que vêm do dicionário do VLibras). Se faltar conteúdo, peçam ao Carlos ou ampliem o vocabulário, nunca escrevam um sinal à mão.
2. **Ninguém do grupo fala Libras.** Mostrem sempre o `disclaimer` que vem de `GET /learn/path` (os rótulos não foram validados por falante de Libras). Nada de "aprenda Libras fluente".
3. **Dizer "sequência de sinais"**, não "tradução de Libras". Libras tem gramática própria que o MVP não cobre.
4. **Não afirmar nada sobre a ordem dos sinais numa frase.** Por isso não há exercício de "montar a frase" na v1.
5. **Não versionar** vídeos, `web/public/vlibras/signs/`, nem dados. O `.gitignore` já cuida dos sinais.
6. **Não copiar o Duolingo.** Inspiração sim; mascote, nome, cores exatas, fontes, sons e textos deles, não (marca registrada e direito autoral). Criem a identidade do **Sinaliza**.
7. **Mudou o formato da API?** Fale com o Carlos e mude `schemas.py`, o contrato, `contract.ts` e `openapi-mock.json` no mesmo pull request.

## 5. A inspiração: o que aprender com o Duolingo

Abram o Duolingo e observem. O que importa não é a aparência, são estes **padrões de produto**:

| Padrão | Como o Duolingo faz | Como fica no Sinaliza |
| --- | --- | --- |
| **Trilha** | Caminho vertical em curva, com círculos de lição e unidades separadas por faixas coloridas | Tela inicial: `units` coloridas (`color`, `icon`) com as lições em caminho. Estados: concluída (com estrelas), disponível (destacada, "COMEÇAR"), bloqueada (cinza, cadeado) |
| **Lição curta e focada** | Barra de progresso no topo, um exercício por tela, botão "Continuar" | 13 exercícios por lição, barra de progresso, um por tela |
| **Feedback imediato** | Ao responder: verde ou vermelho, mostra a resposta certa, botão para seguir | Mesmo fluxo: "Verificar" → resultado → "Continuar". Ao errar, mostrar o sinal certo tocando |
| **Apresentar antes de testar** | Ensina a palavra, depois pratica | O `learn_sign` apresenta os 4 sinais antes dos exercícios |
| **Recompensa** | XP, estrelas/coroas, nível | `xp_gained`, `stars`, `level`, `bonus_perfect` na tela de resultado |
| **Hábito** | Sequência (streak), meta diária | `streak_days`, `daily_goal_xp`, `xp_today` no topo e no perfil |
| **Celebração** | Tela de fim de lição com animação e resumo | Tela de resultado: estrelas, XP, "meta cumprida!", próxima lição liberada (`unlocked_lesson_ids`) |
| **Recomeço sem culpa** | Pode refazer; erros viram prática | Refazer é permitido; reprovar (< 60%) não dá XP mas não pune |
| **Tom** | Encorajador, frases curtas, humor leve | Microcopy acolhedor; sem humilhar quem erra |

**Diferenças importantes do nosso caso:**

- **O público pode ser surdo.** Nada pode depender de **som**: sem "ding" obrigatório, sem exercício de ouvir. Feedback é visual (cor, ícone, movimento) e, se tiver som, opcional e desligável.
- **O protagonista é o avatar**, não o texto. A pessoa aprende **vendo** o sinal; o avatar precisa ser grande, repetível e sem pressa (botão "ver de novo"; velocidade lenta é um bônus, o player aceita).
- **Sem gramática de Libras.** Só sinais isolados e o par sinal ↔ palavra.

## 6. Telas sugeridas

Rascunhos para discutirem; o design final é de vocês (não há designer no grupo).

```
1. TRILHA (home)                 2. LIÇÃO                          3. RESULTADO
┌───────────────────────┐       ┌───────────────────────┐         ┌───────────────────────┐
│ 🔥 3   ⚡ 45 XP  Nív.1 │       │ ✕  ▓▓▓▓▓░░░░░░░  5/13 │         │        ⭐⭐⭐          │
│ Meta de hoje ▓▓▓░ 20  │       │                       │         │  Lição concluída!     │
├───────────────────────┤       │   [ AVATAR  ▶ ↻ ]     │         │  +25 XP  (perfeita +5)│
│ ▌👪 Família           │       │                       │         │  🔥 sequência: 4 dias  │
│     (✓⭐⭐⭐)           │       │ O que este sinal      │         │  Meta de hoje ✔        │
│        (●) Família 2  │       │ significa?            │         │  Nova lição liberada  │
│     (🔒) Família 3     │       │  ( ) menina           │         │                       │
│ ▌☀️ Dia a dia          │       │  ( ) família          │         │  [   CONTINUAR   ]    │
│     (🔒) ...           │       │  ( ) natal            │         └───────────────────────┘
├───────────────────────┤       │       [ VERIFICAR ]   │
│ Trilha│Tradutor│Perfil│       └───────────────────────┘
└───────────────────────┘
```

| Tela | O que mostra | Endpoints |
| --- | --- | --- |
| **Trilha** | Unidades e lições com estado, estrelas, XP, nível, sequência e meta do dia | `GET /learn/path` + `GET /learn/progress` |
| **Lição** | Um exercício por tela, barra de progresso, avatar, verificação e feedback | `GET /learn/lessons/{id}` |
| **Resultado** | Estrelas, XP, bônus, nível, meta, lições liberadas | `POST /learn/lessons/{id}/complete` |
| **Perfil / estatísticas** | XP total, nível, sequência atual e melhor, lições concluídas | `GET /learn/progress` |
| **Tradutor** | O que já existe hoje, evoluído: mostrar `decision`/`probability` por palavra e `model_version` | `POST /translate` |
| **Sobre / aviso** | O `disclaimer` e os créditos (VLibras, V-LIBRASIL, VLibrasBD) | `GET /learn/path` |

**Estados de toda tela:** carregando, erro (mostrar o `detail` da API), vazio, e **offline/API fora do ar** com botão "tentar de novo".

## 7. Como cada exercício deve se comportar

| `type` | Experiência |
| --- | --- |
| `learn_sign` | Cartão de apresentação: avatar toca `gloss` ao abrir, mostra `word_pt`, botão "ver de novo". Conta como acerto automático ao continuar |
| `sign_to_word` | Avatar toca `gloss` (e repete ao toque). Três opções de palavra. "Verificar" compara com `correct_option_id` |
| `word_to_sign` | Mostra `text`. As opções são **botões que tocam o sinal no avatar** ao toque e depois se escolhe uma. É o mais delicado: só há **um** avatar na página (ver seção 8) |
| `match_pairs` | Ligar 4 sinais a 4 palavras. Cada sinal toca ao toque. Cada par é acerto ou erro |
| (tipo desconhecido) | **Ignorar sem quebrar**: a API pode ganhar tipos novos |

Ao terminar, enviem `{correct, total, mistakes}` (os `mistakes` são ids de exercício errado) e usem a resposta para a tela de resultado e para atualizar o progresso **sem recarregar**: a resposta já traz o `progress` novo.

## 8. Cuidados técnicos com o avatar (leiam antes de desenhar as telas)

- **Existe uma única instância do player por página** (é um Unity WebGL, singleton em `vlibras.ts`). Não dá para mostrar 3 avatares ao mesmo tempo. Por isso `word_to_sign` toca **um sinal de cada vez** no mesmo avatar.
- **Peso:** o player tem ~20 MB e leva alguns segundos para carregar. Carreguem **uma vez** e mantenham o avatar montado entre exercícios e lições (por exemplo, no layout raiz); montar e desmontar a cada tela deixa lento e pode quebrar o player. Mostrem "Carregando o avatar…" (o `VLibrasAvatar` já faz).
- **Tocar:** `vlibrasPlayer().play(toVlibrasGloss(["MÃE"]))` ou o componente `VLibrasAvatar` com `glosses`. O botão "Repetir" já existe no componente; pausa e velocidade o player aceita, mas ainda não estão expostos (uma boa tarefa para vocês).
- **Fallback:** sinal sem arquivo local é **soletrado** pelo avatar. Avisem se virem isso: significa `npm run signs` não rodou ou o sinal não existe no dicionário.
- **Tempo de reprodução:** o avatar informa quando termina (`PlayerState.playing`). Não deixem "Verificar" liberado no meio de uma reprodução se a UX ficar confusa.
- **Personagens:** Ícaro, Hosana e Guga já estão disponíveis; deixar a pessoa escolher no perfil é fácil e dá sensação de personalização.

## 9. Arquitetura sugerida (decidam vocês)

Hoje o front é um único `App.tsx` sem rotas. Proposta de partida:

```
web/src/
  contract.ts, learnApi.ts, api.ts     (já existem)
  vlibras.ts, VLibrasAvatar.tsx         (já existem)
  app/            Layout raiz (avatar montado uma vez), rotas, navegação inferior
  features/
    trail/        tela da trilha (unidades, nós de lição)
    lesson/       fluxo da lição + um componente por tipo de exercício
    progress/     barra de XP/sequência/meta, perfil, resultado
    translator/   o tradutor atual, movido para cá
  ui/             botões, cartões, barra de progresso, ícones (design system mínimo)
```

- **Rotas:** `react-router` (ou similar): `/` trilha, `/licao/:id`, `/resultado`, `/perfil`, `/tradutor`, `/sobre`.
- **Estado:** progresso e trilha vêm da API; um contexto ou uma biblioteca de dados do servidor (como TanStack Query) simplifica cache e recarga. O estado de uma lição em andamento (índice, acertos, erros) fica local.
- **Testes:** `vitest` já está configurado. Testem a lógica (corrigir exercício, contar acertos) e, se quiserem, componentes com Testing Library.
- **Estilo:** `styles.css` atual tem tema claro/escuro; podem continuar nele ou usar CSS Modules. Definam tokens (cores, espaçamento) em um lugar só.

## 10. Divisão sugerida entre os dois

Dois fluxos que quase não se tocam, ligados por `contract.ts` e pelo layout.

| | Dev A: **fluxo da lição** | Dev B: **trilha e gamificação** |
| --- | --- | --- |
| Telas | Lição, exercícios, resultado | Trilha (home), perfil, tradutor, sobre |
| Componentes | Os 4 tipos de exercício, verificação, feedback, barra de progresso, avatar nos exercícios | Mapa da trilha, nós de lição, cabeçalho de XP/sequência/meta, estrelas, navegação inferior |
| API | `fetchLesson`, `completeLesson` | `fetchPath`, `fetchProgress`, `/translate` |
| Entrega que o outro usa | `onFinish(resultado)` | Layout raiz com o avatar montado; rotas |

**Pontos de ligação:** (1) o layout raiz e as rotas, que o Dev B cria no primeiro dia para o Dev A encaixar a lição; (2) a tela de resultado, que mostra o `progress` novo e leva de volta à trilha. Combinem esses dois no primeiro dia e o resto anda em paralelo. Um branch por pessoa, pull requests pequenos, e não mexam no mesmo arquivo ao mesmo tempo sem avisar.

## 11. Marcos e "pronto quando"

| Marco | Entrega | Pronto quando |
| --- | --- | --- |
| **M1** Esqueleto | Rotas, layout, avatar montado uma vez, trilha listando unidades/lições do mock com estados | Navega Trilha → Lição → Trilha; bloqueada não abre |
| **M2** Uma lição completa | Os 4 exercícios, verificação, feedback, barra de progresso, resultado | Joga a lição `familia-1` do início ao fim e o resultado bate com o `POST /complete` |
| **M3** Gamificação | XP, estrelas, nível, sequência, meta, desbloqueio refletidos na trilha | Completar uma lição desbloqueia a próxima na tela, sem recarregar; `X-Mock-Today` mostra a sequência subindo |
| **M4** Polimento | Estados de carregando/erro, acessibilidade, celular, tema claro/escuro, perfil, tradutor com `decision`/`probability` | Passa a lista da seção 12 |
| **M5** Integração | Trocar `VITE_API_URL` para a API real | Nada quebra; as diferenças viram issue para o Carlos |

## 12. Acessibilidade e qualidade (lista de verificação)

- Funciona **sem som** e sem depender só de cor (usem também ícone e texto: "Correto", "Errado").
- Navegação por **teclado** e foco visível; botões com `aria-label`; `aria-pressed` nos selecionados; resultado anunciado (`aria-live`).
- Contraste suficiente nos dois temas; respeitar `prefers-reduced-motion` nas animações de celebração.
- Tamanho de toque adequado no celular (cerca de 44 px) e layout sem rolagem horizontal.
- Textos curtos e claros; nada de jargão (nada de "glosa" sem explicar; "sinal" é melhor).
- Todos os estados de erro mostram o `detail` da API; nenhuma tela fica em branco.
- `npm run build` e `npm test` passando.

## 13. Como trabalhar com o ML e a API real

- O mock **não é a API final**. Ele garante o formato e as regras. Quando a API real estiver pronta, só `VITE_API_URL` muda.
- A API real **ainda não tem `/learn/*`**. Proposta: vocês mesmos implementam esses 4 endpoints num módulo `api/app/learn/` (mesmas regras do `mock-api/sinaliza_mock/store.py`, progresso em banco) para não editar os arquivos do ML. Podem começar por copiar a lógica do mock. Combinem com o Carlos quando for a hora.
- O mock zera ao reiniciar; `DELETE /learn/progress` e o cabeçalho `X-Mock-Today` ajudam a testar. Códigos úteis: `400` sem `X-Learner-Id`, `409` lição bloqueada, `404` lição inexistente.
- Precisam de um campo novo (ex.: dica por exercício, vidas, ranking)? Abram a conversa com o Carlos antes: ele muda o contrato, o mock e o `contract.ts` juntos.

## 14. Ideias para depois do básico (opcional)

Vidas por lição (só no front), revisão dos sinais que a pessoa mais errou (use `mistakes`), "praticar" uma unidade já concluída, escolher o avatar, modo escuro, animação de comemoração leve, compartilhar progresso, e o tradutor mostrando a probabilidade do modelo de forma amigável ("o modelo manteve esta palavra com 97% de confiança").

## 15. Perguntas em aberto (decidam e registrem aqui)

- O tradutor é uma aba própria ou uma prática dentro da trilha?
- Login de verdade, ou perfil anônimo basta para a entrega?
- Quantas unidades e sinais a trilha final deve ter (o mock usa 96 dos 210)?
- Nome e identidade visual do app.

## Onde achar mais

[`contrato-api-web.md`](contrato-api-web.md) (API, exemplos e regras) · [`../references/13-web.md`](../references/13-web.md) (o front atual e o avatar) · [`../references/01-escopo-atual.md`](../references/01-escopo-atual.md) (escopo) · [`../references/14-como-rodar-e-testar.md`](../references/14-como-rodar-e-testar.md) (comandos) · [`creditos-e-licencas.md`](creditos-e-licencas.md) (créditos obrigatórios).
