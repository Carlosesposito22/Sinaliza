# Ideação, priorização e decisões

Fonte: `Documentos/Ideação, Proposição e Planejamento G10.docx` (e o PDF equivalente), mais as decisões posteriores registradas no repositório. A proposta abaixo é a **original** (escopo antigo); o fim do arquivo registra o que mudou.

## Metodologia de ideação

- **Brainstorming reverso:** "como faríamos um app de reconhecimento de Libras ser inútil?" → respostas viraram requisitos positivos.
- **Mapas mentais** a partir de "reconhecimento de sinal em tempo real": Interface, Backend/ML, Gamificação, Privacidade de dados biométricos.
- **Round robin** para equilibrar o lado técnico e o de interação.
- Grupo 100% Ciência da Computação, sem Design. Produção estimada: 15–20 ideias, 6–8 levadas à prototipação; quatro eixos (reconhecimento/feedback em tempo real, gamificação, interface/UX, dados/privacidade/performance).

## Critérios de seleção (tripé da inovação)

- **Desejabilidade:** interação bidirecional; engajamento e contexto; tolerância ao erro (feedback intermediário "quase lá").
- **Viabilidade:** hardware simples (webcam), tecnologias maduras e abertas (MediaPipe, MINDS-Libras), robustez a iluminação, privacidade por design.
- **Viabilidade econômica:** dataset gratuito; alinhamento com inovação pública (lacuna nos programas da Prefeitura do Recife).

## MoSCoW original

| Prioridade | Itens |
| --- | --- |
| Must | Reconhecimento bidirecional em tempo real (MediaPipe + LSTM/CNN); feedback de similaridade (acerto/erro/quase lá); tela de consentimento e adequação à LGPD |
| Should | Gamificação e progressão por níveis (estrutura desacoplada do motor de IA) |
| Could | Dicionário consultável integrado (reaproveitando os vídeos do treino) |
| Won't | Tradução unidirecional via avatar 3D (já coberta por Hand Talk/ProDeaf/VLibras); sensores vestíveis |

> **Ironia a registrar:** o escopo atual implementa justamente o item que a fase 1 classificou como *Won't have*. A justificativa da mudança é a restrição de validação (ninguém sabe Libras), não uma reavaliação de mercado.

## Funcionalidades selecionadas (escopo antigo)

1. Reconhecimento do sinal via câmera com feedback em tempo real (hipótese: reduzir a insegurança ao praticar sozinho).
2. Feedback acerto / erro / "quase lá" por limiar de similaridade.
3. Gamificação com progressão por níveis (alfabeto → frases de escola/saúde/trabalho).
4. Dicionário consultável de sinais.

## Backlog original

| ID | Item | Prioridade | Trilha |
| --- | --- | --- | --- |
| 01 | Extração de pontos-chave (MediaPipe Holistic) | Must | ML |
| 02 | Classificador de sinais (LSTM/CNN no MINDS-Libras) | Must | ML |
| 03 | Feedback em tempo real com limiar de similaridade | Must | Backend + Frontend |
| 04 | Estrutura de níveis desacoplada do motor | Should | Backend |

Trilhas de desenvolvimento: **Machine Learning, Backend, Frontend, Testes**.

## Cronograma original (8 semanas)

| Semanas | Atividades | Resultado |
| --- | --- | --- |
| 1–2 | Setup, extração com MediaPipe, primeiros testes com MINDS-Libras | Protótipo capturando/visualizando pontos da mão em tempo real |
| 3–4 | Treino inicial do classificador, limiar de similaridade | Modelo reconhecendo conjunto reduzido de sinais com acerto mensurável |
| 5–6 | Integração backend–frontend, captura e feedback visual | Protótipo jogável com feedback em pelo menos um nível |
| 7–8 | Testes de usabilidade e ajuste em condições variadas | Versão testável com usuários reais e relatório |

O cronograma **não foi reescrito** para o escopo atual. **[a confirmar]** prazos reais restantes.

## Enquadramento nas trilhas da disciplina (apresentação)

Requisitos de ML: reconhecimento por câmera, classificação, treino e comparação de modelos, validação, tempo real, integração com o jogo. Requisito complementar: privacidade (LGPD). Planejamento em cinco frentes: **Dados → Modelo → Validação → Integração → Testes**. Validação prevista: métricas de desempenho, matriz de confusão, validação cruzada, ajuste de hiperparâmetros.

No escopo atual essas frentes continuam, com troca de objeto: o modelo é **gerador de movimento**, a validação usa **DTW** (e a validação cruzada **por sinalizante**), e "matriz de confusão" deixa de fazer sentido (não é classificação) — a menos que se treine um classificador auxiliar para avaliar os movimentos gerados [ideia, não implementada].

## Decisões posteriores (código e docs)

| Data | Decisão | Onde |
| --- | --- | --- |
| 2026-10-14 | Escopo: ML gera movimento a partir do texto; não reconhece o sinal do usuário | `README.md` |
| 2026-10-14 | Dados de movimento: MINDS-Libras, 20 sinais como vocabulário fechado | `docs/dados-e-vocabulario.md` |
| 2026-10-14 | Subconjunto inicial: sinalizantes 01, 02, 07, 10 (~16,3 GB) | idem |
| 2026-10-14 | Texto → glosa por tabela (`vocabulary.json`) no MVP | idem |
| 2026-10-14 | Formato de pose: 75 keypoints (pose 33 + mãos 21+21), sem rosto | `docs/pose-format.md` |
| 2026-10-14 | Modelo só se justifica se superar a recuperação (medoide) em DTW em sinalizante não visto | `model/README.md` |
| 2026-10-14 | MediaPipe fixado em `0.10.21` (API `mp.solutions.holistic`); venvs separados para `data/` e `model/` | `data/README.md` |
| 2026-10-14 | Docker: nginx serve o front e repassa `/api/*` à API (sem CORS) | `docker-compose.yml`, `web/nginx.conf` |
| 2026-10-14 | Avatar inicial é esqueleto (three.js); avatar com rig/GLB e retargeting vem depois | `web/src/Avatar.tsx` |
| 2026-10-19 | YOLOv8 entra como ferramenta de extração (recorte da pessoa), ligado por padrão; só detecta pessoa, não mãos | `data/person_crop.py` |
| 2026-10-19 | Texto → glosa: tabela + aproximação por embedding de palavras (`char-ngram` padrão, `sentence-transformers` opcional), sempre sinalizada; palavra sem sinal é ignorada com aviso | `api/app/text_to_gloss.py` |
| 2026-10-19 | Frases de exemplo por categoria geradas por modelos de frase e validadas contra o vocabulário (sem LLM) | `api/app/phrases.py`, `data/phrases.json` |
| 2026-10-19 | Normalização passa a ser em pixels do quadro original; mãos sem corpo no quadro usam a última referência válida | `data/extract_keypoints.py` |
| 2026-10-19 | Treino com **dois datasets**: MINDS-Libras e V-LIBRASIL (a pedido do avaliador, que recomendou vários datasets). Apoema-Libras560 descartado; Libras-UFPel fica como reserva. V-LIBRASIL só local, fora do repositório | `references/21-datasets-de-treino.md` |

## Rascunho de hipótese para o escopo atual

> **[proposta, não validada pela equipe]** Acreditamos que, ao gerar o movimento de sinais de Libras a partir de gravações reais de sinalizantes e exibi-lo em um avatar a partir de texto em português, conseguimos demonstrar uma sequência de sinais para um vocabulário fechado de forma objetivamente próxima da gravação (DTW menor que as linhas de base em sinalizante não visto) — sem pretender substituir tradução linguística nem intérprete.

## O que a fase 1 deixou em aberto (e ainda importa)

- O limiar de similaridade — **deixa de importar** (era do feedback acerto/quase lá).
- Conjunto inicial de sinais — **resolvido**: 20 sinais do MINDS-Libras.
- Acurácia em ambientes não controlados — **deixa de importar** (não há captura ao vivo).
- Validação com usuários reais, surdos e ouvintes — **continua importando**, e é o ponto mais frágil (ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md)).
