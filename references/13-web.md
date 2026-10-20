# Front (`web/`)

React 18 + Vite 5 + TypeScript 5.6 + three.js 0.169. Pacote `sinaliza-web` 0.1.0.

## Arquivos (`web/src/`)

| Arquivo | Papel |
| --- | --- |
| `main.tsx` | Entrada React |
| `App.tsx` | Formulário (textarea, até 500 caracteres) + botão "Traduzir"; mostra glosas e o avatar |
| `api.ts` | `translate(text)` via `fetch POST {API_URL}/translate`; tipos `PoseSequence`, `TranslateResponse` |
| `Avatar.tsx` | Canvas three.js que anima os keypoints |
| `skeleton.ts` | `NUM_KEYPOINTS=75` e a lista de ossos (`BONES`) |
| `styles.css` | Estilos |
| `index.html`, `vite.config.ts`, `tsconfig.json`, `nginx.conf`, `Dockerfile` | Build e serviço |

## Comportamento

- Texto inicial: "Olá, tudo bem?".
- Ao enviar: estado `loading` ("Gerando..."), erro mostrado em `<p className="error">`, glosas em `<p className="glosses">` separadas por " · ".
- `API_URL`: `import.meta.env.VITE_API_URL ?? "http://localhost:8000"`. No Docker, `VITE_API_URL=/api` (build arg) e o nginx repassa à API.
- Erro HTTP vira `A API respondeu <status>` — a mensagem de detalhe da API (ex.: 422 "o texto não contém palavras") **não é exibida** ao usuário.

## Avatar (esqueleto)

`Avatar` recebe `pose: PoseSequence | null`:

- Cria cena, câmera perspectiva (FOV 40, posição `(0, -0.1, 6.5)`) e renderer com fundo transparente;
- Desenha **75 pontos** (`THREE.Points`, azul) e **ossos** (`LineSegments`, cinza): corpo (14 ossos: cabeça-ombros, braços, tronco, pernas) + 21 ossos por mão;
- Cada quadro do `requestAnimationFrame` escolhe `index = floor(elapsed * fps) % frames.length` — a animação **repete em laço**;
- `ResizeObserver` ajusta o tamanho; limpeza dos recursos no unmount.

Substituir por um avatar com rig (GLB) mantém a entrada `PoseSequence`. Isso exige **retargeting** dos keypoints para os ossos do rig (item "próximos passos" do README).

## Lacunas conhecidas **[observadas]**

- Sem **controles de reprodução** (pausar, repetir, velocidade) — importante para quem está aprendendo um sinal.
- Sem destaque de **qual glosa está sendo sinalizada** no momento (as glosas aparecem como texto estático).
- Sem aviso de **palavras ignoradas** ou fora do vocabulário.
- Sem estado de "nenhum resultado ainda" além do canvas vazio.
- Sem testes de front.
- Acessibilidade: o canvas não tem alternativa textual além das glosas; revisar contraste e navegação por teclado (público inclui pessoas com pouca familiaridade tecnológica — persona Helena).
- Sem rosto/expressão (limite do formato de pose).
- Sem Design no grupo: a UI é funcional e simples.
