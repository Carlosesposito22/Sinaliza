# Front (`web/`)

React 18 + Vite 5 + TypeScript 5.6. Pacote `sinaliza-web` 0.1.0. O avatar é o player Unity WebGL do VLibras, servido localmente.

## Arquivos (`web/src/`)

| Arquivo | Papel |
| --- | --- |
| `main.tsx` | Entrada React |
| `App.tsx` | Frases de exemplo por categoria, formulário, palavras → sinais (`MatchWord`) e o avatar |
| `api.ts` | `translate`, `fetchCategories`; tipos `PoseSequence`, `WordMatch`, `MatchKind`, `TranslateResponse`, `Category`, `Phrase`; leitura do `detail` dos erros da API |
| `vlibras.ts`, `VLibrasAvatar.tsx`, `vlibras-glosses.json` | Avatar do VLibras (ver abaixo) |
| `vlibras.test.ts` | 3 testes (vitest) do mapeamento das glosas |
| `styles.css` | Estilos (tema claro/escuro por `prefers-color-scheme`) |
| `index.html`, `vite.config.ts`, `tsconfig.json`, `nginx.conf`, `Dockerfile` | Build e serviço |
| `scripts/fetch-vlibras-signs.mjs` | `npm run signs`: baixa os sinais do vocabulário para `public/vlibras/signs/BR/` |

## Comportamento

- **Frases de exemplo por categoria:** ao carregar, busca `GET /categories`. Se falhar ou vier vazio, a seção não aparece. Os botões de categoria (`aria-pressed`) abrem a lista de frases; clicar numa frase preenche o texto **e traduz**.
- **Formulário:** textarea (até 500 caracteres) e botão "Traduzir". Texto inicial: "O filho está com dor de cabeça.". O subtítulo mostra a **quantidade real de sinais** (busca `GET /vocabulary`; sem resposta, diz "poucos").
- **Resultado, palavra por palavra** (`matches`, na ordem do texto):
  - `exact`: caixinha com a palavra e a glosa;
  - `approx`: caixinha **tracejada**, glosa precedida de "~" e `title` com a similaridade; nota "Palavras com ~ foram aproximadas… confira se o sinal serve";
  - `ignored`: palavra **riscada**, nota "Palavras riscadas não têm sinal no vocabulário e foram ignoradas";
  - `function` (artigo, preposição): texto cinza, sem alarde.
  Abaixo, as glosas na ordem.
- **Aviso sobre a animação:** "Movimento: sinais do dicionário do VLibras, tocados na ordem das glosas. Não é tradução para Libras." A sequência de keypoints (`pose`) que a API devolve não é usada pelo front desde 2026-10-25.
- **Aviso fixo no subtítulo:** o vocabulário é pequeno e isto não é tradução para Libras.
- **Erros:** o `detail` da API é mostrado (ex.: "nenhuma palavra do texto tem sinal no vocabulário (210 sinais)"); se não houver `detail`, mostra `A API respondeu <status>`. Erro limpa o resultado anterior.
- `API_URL`: `import.meta.env.VITE_API_URL ?? "http://localhost:8000"`. No Docker, `VITE_API_URL=/api` e o nginx repassa à API.

## Avatar do VLibras (desde 2026-10-25)

Avatar único do front, com três personagens à escolha: **Ícaro** (padrão), **Hosana** e **Guga**. Substituiu o avatar Rocketbox animado pelos keypoints das gravações, cujos dedos seguiam imprecisos; o Rocketbox e o trabalho de retargeting estão em [`historico/avatar-rocketbox/`](../historico/avatar-rocketbox/README.md). Decisão em [`06-ideacao-e-decisoes.md`](06-ideacao-e-decisoes.md).

- **Player, local:** o Unity WebGL do widget oficial [`vlibras-web-browsers`](https://github.com/spbgovbr-vlibras/vlibras-web-browsers) (LGPL-3.0; versão do commit `d292d36`, 2026-09-29), copiado sem alterações para `web/public/vlibras/` (20 MB: `unity-loader.js`, `playerweb.json` e os três `playerweb.*.unityweb`). Roda a partir do nosso servidor (Vite ou nginx); não usamos o widget hospedado do VLibras.
- **Ponte (`vlibras.ts`):** singleton, porque o Unity só se instancia uma vez por página. `UnityLoader.instantiate`, `SendMessage("PlayerManager", ...)` com `playNow` (glosa), `setBaseUrl` (pasta dos sinais), `Change` (personagem) e `setSlider` (velocidade), e os retornos globais que o Unity chama (`onLoadPlayer`, `onPlayingStateChange` etc.). `VLibrasAvatar.tsx` mostra o player, a escolha do personagem e o botão "Repetir".
- **Sinais, locais:** as **nossas glosas** (`result.glosses`) vão para o player; o tradutor de texto do VLibras **não** é usado (exige autorização, e o texto → glosa é parte do nosso trabalho). O player lê cada sinal de `web/public/vlibras/signs/BR/<GLOSA>`, arquivos baixados uma vez do dicionário do VLibras (bundles da versão `2018.3.1`) por `npm run signs` (209 arquivos, 5,2 MB). **Ficam fora do git** (o dicionário não traz licença de redistribuição): num clone novo, rode `npm run signs` antes do `npm run dev` ou do build do Docker. Durante o uso nada é buscado nos servidores do VLibras. Sinal sem arquivo é **soletrado** pelo avatar.
- **Cobertura (conferida em 2026-10-25):** 202 dos 210 sinais existem no dicionário com o mesmo nome; sinais de várias palavras usam `_` (`CADEIRA_DE_RODAS`). Os 8 restantes (`DOR DE CABEÇA`, `DOR DE GARGANTA`, `DOR DE OUVIDO`, `DEVER DE CASA`, `COM SEDE`, `COM MEDO`, `SE CASAR`, `MELHOR AMIGO`) viram sinais que existem (`DOR CABEÇA`, `SEDE` etc.), pela tabela `vlibras-glosses.json`, que o script e o front usam. **Proposta não validada:** não sabemos se é assim que se sinaliza em Libras, nem se o sinal do VLibras corresponde ao do V-LIBRASIL.
- **Personalização:** o player tem uma função de personalização (`CustomizationBridge.setURL`, que recebe o endereço de uma configuração) cujo formato não achamos documentado; não foi usada. Mudar a aparência dos personagens exigiria o projeto Unity, que não é público; o repositório `libraske-player`, que tem modelos do Guga e da Hosana, não tem licença. Criar um avatar próprio fica para depois do MVP.
- **Limites:** estilo cartum; o movimento **não vem dos nossos dados** (nem das gravações, nem do modelo); sem expressão facial controlada por nós. Não é tradução para Libras.

## Verificado

- `npm run build` (`tsc --noEmit` + Vite) e `npm test` (3 testes) passam.
- **Player local (2026-10-25):** no navegador (Vite), com o cache do navegador limpo, "O filho está com dor de cabeça." toca FILHO → DOR → CABEÇA com legenda, e os sinais vêm de `localhost/vlibras/signs/BR/` (nenhum pedido aos servidores do VLibras). A troca para Hosana funciona no front; Guga foi conferido numa página de teste. No Docker, o nginx serve o player e os sinais (incluindo nomes com acento, como `CABEÇA`); a imagem do front tem 143 MB.
- Conferido no navegador (servidores locais): categorias carregam, clicar numa frase traduz, palavra aproximada aparece tracejada com "~", palavra sem sinal aparece riscada e as duas notas aparecem. Não foram testados celular, teclado/leitor de tela nem o tema claro.

## Lacunas conhecidas **[observadas]**

- Controles de reprodução: só "Repetir" (o player aceita pausa e velocidade, ainda não expostas) — importante para quem aprende um sinal.
- Sem destaque de **qual glosa está sendo sinalizada** no momento.
- Sem testes de front.
- Acessibilidade: o player não tem alternativa textual além das glosas e da legenda; revisar contraste e navegação por teclado (persona Helena: interface simples e guiada).
- Sem Design no grupo: a UI é funcional e simples.
