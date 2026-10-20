# Front (`web/`)

React 18 + Vite 5 + TypeScript 5.6 + three.js 0.169. Pacote `sinaliza-web` 0.1.0.

## Arquivos (`web/src/`)

| Arquivo | Papel |
| --- | --- |
| `main.tsx` | Entrada React |
| `App.tsx` | Frases de exemplo por categoria, formulário, palavras → sinais (`MatchWord`) e o avatar |
| `api.ts` | `translate`, `fetchCategories`; tipos `PoseSequence`, `WordMatch`, `MatchKind`, `TranslateResponse`, `Category`, `Phrase`; leitura do `detail` dos erros da API |
| `Avatar.tsx`, `RocketboxAvatar.tsx`, `SkeletonAvatar.tsx`, `retarget.ts`, `rocketbox.ts` | Avatar 3D (Rocketbox) animado pelos keypoints, com o esqueleto como reserva (ver abaixo) |
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
- **Aviso sobre a animação** (campo `generator` da resposta): com `playback`, "Movimento: gravações reais de um sinalizante do V-LIBRASIL, sinal por sinal, na ordem do texto, com transições automáticas entre eles. Não é tradução para Libras."; com `stub`, "Animação de teste (um aceno): não corresponde aos sinais mostrados."
- **Aviso fixo no subtítulo:** o vocabulário é pequeno e isto não é tradução para Libras.
- **Erros:** o `detail` da API é mostrado (ex.: "nenhuma palavra do texto tem sinal no vocabulário (210 sinais)"); se não houver `detail`, mostra `A API respondeu <status>`. Erro limpa o resultado anterior.
- `API_URL`: `import.meta.env.VITE_API_URL ?? "http://localhost:8000"`. No Docker, `VITE_API_URL=/api` e o nginx repassa à API.

## Avatar 3D (Rocketbox)

**Modelo:** **Male_Adult_08** do [Microsoft Rocketbox](https://github.com/microsoft/Microsoft-Rocketbox) (licença **MIT**, Copyright 2020 Microsoft): um rapaz realista, de camisa azul, expressão simpática. Escolhido pelo usuário entre os modelos do Rocketbox em 2026-10-20, no lugar do personagem de estilo anime (VRoid) que a primeira versão usava. Arquivos em `web/public/avatar/` (2,4 MB no total): `avatar.fbx` (508 KB, esqueleto Bip01 com 81 ossos e dedos), `body.jpg`, `head.jpg` e `opacity.webp` (texturas de 2048 × 2048 convertidas dos TGA originais, que pesavam 42 MB; `opacity` traz o canal alfa de cabelo e cílios) e `LICENSE-rocketbox.md`. Créditos em `docs/creditos-e-licencas.md`.

**Carga:** `FBXLoader` do three.js. O FBX cita texturas TGA em pastas do autor (`D:\temp\...`), então os materiais são refeitos na hora (`MeshStandardMaterial` com as nossas texturas, escolhidas pelo nome do material: `m014_body`, `m014_head`, `m014_opacity`). O modelo está em centímetros (escala 0,01). Para trocar de personagem do Rocketbox, troque o FBX e as texturas e ajuste `TEXTURES` em `RocketboxAvatar.tsx`; outro rig pede outra tabela de ossos (no estilo de `rocketbox.ts`).

**Arquivos:**

| Arquivo | Papel |
| --- | --- |
| `RocketboxAvatar.tsx` | Cena three.js (luz de três pontos, câmera enquadrando da cabeça à cintura), carrega o FBX, refaz os materiais, roda o laço de animação e chama o retargeting a cada quadro |
| `rocketbox.ts` | Tabela de ossos: nome padronizado (`leftIndexProximal`) → osso Bip01 (`Bip01_L_Finger1`) |
| `retarget.ts` | `Retargeter` (independe do rig): keypoints → rotações dos ossos; `samplePose` (interpolação entre quadros); `palmFrame`, `swingOver`, `twistBetween`; `idlePoints` (braços caídos) |
| `Avatar.tsx` | Tenta o Rocketbox; se o modelo não carregar (arquivo ausente, sem WebGL), cai no esqueleto |
| `SkeletonAvatar.tsx` | O desenho antigo em pontos e linhas, agora só reserva |
| `retarget.test.ts` | 19 testes (vitest) |

**Como o retargeting funciona:** cada osso (braço, antebraço, falanges) recebe a **menor rotação** que leva a direção de repouso dele até a direção medida nos keypoints, **relativa à rotação do osso pai**; assim o giro em torno do próprio eixo acompanha o pai e o cotovelo dobra no plano certo. As direções e as rotações de **repouso são lidas de cada osso** na carga (o Rocketbox vem em pose A, com eixos próprios em cada osso), então o código não supõe pose T nem eixos alinhados. A **mão** é a exceção: o giro dela vem da **palma** (punho, base do indicador, do médio e do mindinho). Os keypoints z são reduzidos a 60% (são ruidosos). Entre quadros de 30 fps, a posição é interpolada a 60 Hz e a rotação é suavizada (`slerp` 0,6). Mão não detectada: a mão acompanha o antebraço e os dedos voltam ao repouso. Sem animação, o avatar fica com os braços caídos.

**Biblioteca:** só o `three` (MIT). A primeira versão usava o `@pixiv/three-vrm` (formato VRM), retirado quando o personagem anime saiu. Pesquisa de 2026-10-20: não achamos biblioteca pronta que leve keypoints do MediaPipe a ossos de dedos para língua de sinais; o **Kalidokit** (MIT) está parado desde 2022-02 e pede landmarks "world" que o nosso formato não guarda.

**Limites:** o **tronco, a cabeça e o rosto não mexem** (o formato de pose não tem rosto, e a cabeça/tronco ainda não são retargeted), então não há expressão facial nem marcações não manuais, embora o modelo tenha ossos de rosto (olhos, sobrancelhas, boca) que dariam para usar; os dedos dependem de keypoints de mão do MediaPipe (ruidosos em profundidade); o personagem não foi escolhido junto com pessoas surdas. **Não é tradução para Libras.**

## Verificado

- `npm run build` (`tsc --noEmit` + Vite) passa; `npm test` (vitest) passa (19 testes do retargeting, com um esqueleto de mentira, uma vez com eixos alinhados e outra com eixos de repouso diferentes em cada osso).
- **Avatar Rocketbox conferido no navegador (2026-10-20)** com gravações reais (Docker, frase "O filho está com dor de cabeça"): o rapaz carrega com pele, roupa e cabelo certos, os braços e os dedos acompanham os keypoints (mão ao peito, punho fechado, mãos abertas na altura do rosto). Conferido **à vista**, sem comparar com os sinais corretos: não sabemos se o gesto mostrado é o certo em Libras. O Docker serve `avatar/` (2,4 MB) e a imagem do front ficou com 108 MB (eram 134 MB com o VRM de 16,85 MB).
- Conferido no navegador (servidores locais): categorias carregam, clicar numa frase traduz, palavra aproximada aparece tracejada com "~", palavra sem sinal aparece riscada e as duas notas aparecem. Não foram testados celular, teclado/leitor de tela nem o tema claro.

## Lacunas conhecidas **[observadas]**

- Sem **controles de reprodução** (pausar, repetir, velocidade) — importante para quem aprende um sinal.
- Sem destaque de **qual glosa está sendo sinalizada** no momento.
- O avatar é o `StubGenerator` (aceno): a animação **não corresponde** às glosas mostradas.
- Sem testes de front.
- Acessibilidade: o canvas não tem alternativa textual além das glosas; revisar contraste e navegação por teclado (persona Helena: interface simples e guiada).
- Sem rosto/expressão (limite do formato de pose).
- Sem Design no grupo: a UI é funcional e simples.
