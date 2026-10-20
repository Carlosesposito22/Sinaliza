# Front (`web/`)

React 18 + Vite 5 + TypeScript 5.6 + three.js 0.169. Pacote `sinaliza-web` 0.1.0.

## Arquivos (`web/src/`)

| Arquivo | Papel |
| --- | --- |
| `main.tsx` | Entrada React |
| `App.tsx` | Frases de exemplo por categoria, formulário, palavras → sinais (`MatchWord`) e o avatar |
| `api.ts` | `translate`, `fetchCategories`; tipos `PoseSequence`, `WordMatch`, `MatchKind`, `TranslateResponse`, `Category`, `Phrase`; leitura do `detail` dos erros da API |
| `Avatar.tsx` | Canvas three.js que anima os keypoints |
| `skeleton.ts` | `NUM_KEYPOINTS=75` e a lista de ossos (`BONES`) |
| `styles.css` | Estilos (tema claro/escuro por `prefers-color-scheme`) |
| `index.html`, `vite.config.ts`, `tsconfig.json`, `nginx.conf`, `Dockerfile` | Build e serviço |

## Comportamento

- **Frases de exemplo por categoria:** ao carregar, busca `GET /categories`. Se falhar ou vier vazio, a seção não aparece. Os botões de categoria (`aria-pressed`) abrem a lista de frases; clicar numa frase preenche o texto **e traduz**.
- **Formulário:** textarea (até 500 caracteres) e botão "Traduzir". Texto inicial: "O filho está com dor de cabeça.". O subtítulo mostra a **quantidade real de sinais** (busca `GET /vocabulary`; sem resposta, diz "poucos").
- **Resultado, palavra por palavra** (`matches`, na ordem do texto):
  - `exact`: caixinha com a palavra e a glosa;
  - `approx`: caixinha **tracejada**, glosa precedida de "~" e `title` com a similaridade; nota "Palavras com ~ foram aproximadas… confira se o sinal serve";
  - `ignored`: palavra **riscada**, nota "Palavras riscadas não têm sinal no vocabulário e foram ignoradas";
  - `function` (artigo, preposição): texto cinza, sem alarde.
  Abaixo, as glosas na ordem.
- **Aviso fixo no subtítulo:** o vocabulário é pequeno e isto não é tradução para Libras.
- **Erros:** o `detail` da API é mostrado (ex.: "nenhuma palavra do texto tem sinal no vocabulário (210 sinais)"); se não houver `detail`, mostra `A API respondeu <status>`. Erro limpa o resultado anterior.
- `API_URL`: `import.meta.env.VITE_API_URL ?? "http://localhost:8000"`. No Docker, `VITE_API_URL=/api` e o nginx repassa à API.

## Avatar (esqueleto)

Desenha só a **parte de cima do corpo** (cabeça, ombros, braços e mãos): os dados vêm da cintura para cima e os pontos 23–32 são zerados. Pontos `[0, 0, 0]` (ausentes) e ossos com uma ponta ausente saem de cena, em vez de aparecer na origem. A câmera foi reenquadrada para a origem nos ombros.

`Avatar` recebe `pose: PoseSequence | null`: cena, câmera perspectiva (FOV 40, posição `(0, -0.1, 6.5)`) e renderer transparente; **75 pontos** (`THREE.Points`, azul) e **ossos** (`LineSegments`, cinza): corpo (14 ossos) + 21 por mão; a cada quadro escolhe `index = floor(elapsed * fps) % frames.length` — a animação **repete em laço**; `ResizeObserver` ajusta o tamanho.

Substituir por um avatar com rig (GLB) mantém a entrada `PoseSequence`; exige **retargeting** dos keypoints para os ossos do rig.

## Verificado

- `npm run build` (`tsc --noEmit` + Vite) passa.
- Conferido no navegador (servidores locais): categorias carregam, clicar numa frase traduz, palavra aproximada aparece tracejada com "~", palavra sem sinal aparece riscada e as duas notas aparecem. Não foram testados celular, teclado/leitor de tela nem o tema claro.

## Lacunas conhecidas **[observadas]**

- Sem **controles de reprodução** (pausar, repetir, velocidade) — importante para quem aprende um sinal.
- Sem destaque de **qual glosa está sendo sinalizada** no momento.
- O avatar é o `StubGenerator` (aceno): a animação **não corresponde** às glosas mostradas.
- Sem testes de front.
- Acessibilidade: o canvas não tem alternativa textual além das glosas; revisar contraste e navegação por teclado (persona Helena: interface simples e guiada).
- Sem rosto/expressão (limite do formato de pose).
- Sem Design no grupo: a UI é funcional e simples.
