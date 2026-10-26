# Histórico: avatar Rocketbox (2026-10-20 a 2026-10-25)

Primeiro avatar 3D do Sinaliza: um rapaz realista (Microsoft Rocketbox, MIT) animado no navegador pelos keypoints das gravações do V-LIBRASIL, com retargeting próprio em three.js. **Saiu do front em 2026-10-25**, substituído pelo player do VLibras (ver `references/06-ideacao-e-decisoes.md`), porque os dedos seguiam imprecisos: eles dependem de keypoints de mão do MediaPipe, ruidosos em profundidade.

O código fica aqui só como registro do trabalho. **Não é compilado nem testado** pelo `web/` (o `three` saiu das dependências).

## O que tem aqui

| Pasta | Conteúdo |
| --- | --- |
| `src/` | `RocketboxAvatar.tsx`, `rocketbox.ts`, `retarget.ts`, `motion.ts`, `Avatar.tsx`, `SkeletonAvatar.tsx`, `skeleton.ts` e os testes (`retarget.test.ts`, `motion.test.ts`: 42 testes, passavam em 2026-10-25) |
| `public/avatar/` | O modelo `avatar.fbx`, as texturas e a licença MIT do Rocketbox (2,4 MB) |

## Como restaurar

1. Copie `src/*` para `web/src/` e `public/avatar/` para `web/public/avatar/`.
2. `npm install three@0.169 @types/three@0.169` em `web/`.
3. No `App.tsx`, mostre `<Avatar pose={result?.pose ?? null} />` (de `./Avatar`). A API continua devolvendo a sequência de keypoints (`pose`) em `/translate`.
4. Suba a API com um arquivo de movimentos (`SINALIZA_MOTIONS`); o mais recente, com as mãos reextraídas, é `Datasets/motions-world/motions.npz`.

## Como funcionava

**Modelo:** **Male_Adult_08** do [Microsoft Rocketbox](https://github.com/microsoft/Microsoft-Rocketbox) (licença **MIT**, Copyright 2020 Microsoft): um rapaz realista, de camisa azul, expressão simpática. Escolhido pelo usuário entre os modelos do Rocketbox em 2026-10-20, no lugar do personagem de estilo anime (VRoid) que a primeira versão usava. Arquivos em `public/avatar/` (antes `web/public/avatar/`) (2,4 MB no total): `avatar.fbx` (508 KB, esqueleto Bip01 com 81 ossos e dedos), `body.jpg`, `head.jpg` e `opacity.webp` (texturas de 2048 × 2048 convertidas dos TGA originais, que pesavam 42 MB; `opacity` traz o canal alfa de cabelo e cílios) e `LICENSE-rocketbox.md`. Créditos em `docs/creditos-e-licencas.md`.

**Carga:** `FBXLoader` do three.js. O FBX cita texturas TGA em pastas do autor (`D:\temp\...`), então os materiais são refeitos na hora (`MeshStandardMaterial` com as nossas texturas, escolhidas pelo nome do material: `m014_body`, `m014_head`, `m014_opacity`). O modelo está em centímetros (escala 0,01). Para trocar de personagem do Rocketbox, troque o FBX e as texturas e ajuste `TEXTURES` em `RocketboxAvatar.tsx`; outro rig pede outra tabela de ossos (no estilo de `rocketbox.ts`).

**Arquivos:**

| Arquivo | Papel |
| --- | --- |
| `RocketboxAvatar.tsx` | Cena three.js (luz de três pontos, câmera enquadrando da cabeça à cintura), carrega o FBX, refaz os materiais, roda o laço de animação e chama o retargeting a cada quadro |
| `rocketbox.ts` | Tabela de ossos: nome padronizado (`leftIndexProximal`) → osso Bip01 (`Bip01_L_Finger1`) |
| `retarget.ts` | `Retargeter` (independe do rig): keypoints → rotações dos ossos (`apply`) e ângulos → cabeça e peito (`applyBody`); `samplePose` (interpolação entre quadros); `palmFrame`, `swingOver`, `twistBetween`, `twistAbout`, `alignPair`; `idlePoints` (braços caídos) |
| `motion.ts` | `prepareMotion`: prepara a sequência da API uma vez (suavização, z do braço refeito, ângulos de cabeça e tronco, entrada/saída/pausa); `sampleBody` |
| `Avatar.tsx` | Tenta o Rocketbox; se o modelo não carregar (arquivo ausente, sem WebGL), cai no esqueleto |
| `SkeletonAvatar.tsx` | O desenho antigo em pontos e linhas, agora só reserva |
| `retarget.test.ts`, `motion.test.ts` | 32 + 10 testes (vitest) |

**Preparo da sequência (`motion.ts`, 2026-10-21):** no arquivo de movimentos do V-LIBRASIL o z do corpo vindo do MediaPipe é **exagerado** (o nariz fica a 2 larguras de ombro à frente dos ombros; o antebraço, com z mediano 1,9 contra 0,7 em x e y) e **ruidoso** (variação de um quadro para o outro 15 vezes maior que a de x e y). Usado direto, jogava o antebraço para a câmera, dobrava o punho (mediana de ~55° entre antebraço e palma) e fazia o braço tremer. Agora, antes de animar: (1) cada ponto é suavizado no tempo (gaussiana centrada, σ = 1,5 quadro no corpo e 1 nas mãos, sem atraso); (2) o z do cotovelo e do punho é **refeito pelo comprimento do osso** (`z = ±√(L² − dx² − dy²)`, L = 1 largura de ombro, o 99º percentil medido em x e y; do MediaPipe só vem o lado, de forma suave), e o mesmo vale para **cada osso da mão**, do punho para a ponta (o z da mão do MediaPipe é comprimido: o mesmo osso ia de 0,34 a 0,76 da palma em 3D; os comprimentos de referência são o 99º percentil em x e y no V-LIBRASIL, em `HAND_BONES`, e o lado vem do z cru com suavidade 0,008, já que a diferença crua mediana é 0,025); com isso a dobra do punho cai para ~41° de mediana; (3) guinada, inclinação e rolagem da cabeça saem do nariz e das orelhas, e a rolagem do peito, da linha dos ombros, **relativas à postura mediana da sequência** e limitadas (30°, 20°, 15° e 6°); (4) a sequência ganha **entrada** (0,35 s, dos braços caídos ao primeiro quadro), **saída** (0,45 s) e **pausa** em repouso (0,8 s), e o laço recomeça sem salto. O formato de pose não muda: é só como o front o interpreta.

**Como o retargeting funciona:** cada osso (braço, antebraço, falanges) recebe a **menor rotação** que leva a direção de repouso dele até a direção medida nos keypoints, **relativa à rotação do osso pai**. As direções e as rotações de **repouso são lidas de cada osso** na carga (o Rocketbox vem em pose A, com eixos próprios em cada osso), então o código não supõe pose T nem eixos alinhados. Exceções: o **braço** também gira em torno de si mesmo para o **cotovelo dobrar como dobradiça** (o eixo de flexão do repouso, braço × frente, é levado até braço × antebraço medidos; entra aos poucos entre 5° e 20° de dobra, porque com o braço esticado esse plano é ruído); a **mão** tira o giro da **palma** (punho, base do indicador, do médio e do mindinho), e **metade do giro dela em torno do antebraço (pronação) passa para o antebraço**, como no braço de verdade (o rig não tem osso de torção do antebraço). Os **dedos** (2026-10-21) passam por limites anatômicos antes de mirar (`constrainFinger`): a base (MCP) flexiona de −30° a 95° e abre no máximo 20° para o lado, em relação à direção punho → base do dedo; as juntas do meio (PIP, −5° a 110°) e da ponta (DIP, −5° a 90°) são **dobradiças** que só dobram para a palma (a parte lateral da medida é descartada), e a da ponta é metade medida e metade 2/3 da do meio, como na mão de verdade. Motivo: nos dados, o eixo de dobra da junta do meio ficava a 35°–57° do eixo anatômico, e o avatar copiava isso (dedos dobrando de lado, cruzando, abertos em leque). A palma olha para +normal na mão esquerda e −normal na direita (a flexão medida vai para esse lado em 80%–88% dos quadros). O polegar só tem a dobra entre ossos vizinhos limitada a 75°. A **cabeça** gira 40% no pescoço e o resto na cabeça; o peito (`Bip01_Spine2`) só rola. Entre quadros de 30 fps, a posição é interpolada a cada quadro da tela e a rotação é suavizada com constante de tempo de 20 ms (igual em qualquer taxa de quadros do monitor). Mão não detectada: a mão acompanha o antebraço e os dedos voltam ao repouso. Sem animação, o avatar fica com os braços caídos.

**Biblioteca:** só o `three` (MIT). A primeira versão usava o `@pixiv/three-vrm` (formato VRM), retirado quando o personagem anime saiu. Pesquisa de 2026-10-20: não achamos biblioteca pronta que leve keypoints do MediaPipe a ossos de dedos para língua de sinais; o **Kalidokit** (MIT) está parado desde 2022-02, pede landmarks "world" que o nosso formato não guarda e devolve ângulos nos eixos do VRM. Em 2026-10-21, para os dedos, preferimos os limites anatômicos próprios (independem do rig) a uma biblioteca: o problema estava na profundidade dos keypoints, não no retargeting. **Melhoria na origem (feita em 2026-10-21/25):** as mãos foram reextraídas com o `HandLandmarker` do MediaPipe Tasks (*world landmarks*); o eixo de dobra dos dedos passou de 0,66 para 0,91 de alinhamento com o anatômico. Ver `references/10-pipeline-de-dados.md` (`--hand-world`). No avatar a melhora foi sutil à vista.

**Limites:** a cabeça só gira e o peito só rola, com ângulos estimados de 5 pontos do rosto em 2D (indício, não medida); o **rosto não mexe** (o formato de pose não tem rosto), então não há expressão facial nem marcações não manuais, embora o modelo tenha ossos de rosto (olhos, sobrancelhas, boca) que dariam para usar; os dedos dependem de keypoints de mão do MediaPipe (ruidosos em profundidade); o personagem não foi escolhido junto com pessoas surdas. **Não é tradução para Libras.**

## Verificado na época

- `npm run build` (`tsc --noEmit` + Vite) passa; `npm test` (vitest) passa (42 testes: retargeting com um esqueleto de mentira, uma vez com eixos alinhados e outra com eixos de repouso diferentes em cada osso, incluindo a dobradiça do cotovelo, a pronação, a cabeça e os limites dos dedos; e o preparo da sequência, incluindo o z dos dedos).
- **Dedos com limites anatômicos (2026-10-21)** conferidos no navegador com a mesma frase: mão fechada, dedos curvados para a palma e indicador apontando, sem dedo dobrando de lado nem cruzando. Conferido à vista.
- **Movimento refeito (2026-10-21)** conferido no navegador (Docker, "O filho está com dor de cabeça e precisa ir ao hospital"): cotovelos perto do corpo, antebraço sem dobrar de lado, punho sem a dobra exagerada, cabeça com pequenos giros, pausa de braços caídos entre as repetições. Conferido **à vista**, sem comparar com os sinais corretos.
- **Avatar Rocketbox conferido no navegador (2026-10-20)** com gravações reais (Docker, frase "O filho está com dor de cabeça"): o rapaz carrega com pele, roupa e cabelo certos, os braços e os dedos acompanham os keypoints (mão ao peito, punho fechado, mãos abertas na altura do rosto). Conferido **à vista**, sem comparar com os sinais corretos: não sabemos se o gesto mostrado é o certo em Libras. O Docker serve `avatar/` (2,4 MB) e a imagem do front ficou com 108 MB (eram 134 MB com o VRM de 16,85 MB).
