# Sugestões do orientador

Em conversa com o orientador, o Carlos anotou três termos: **YOLOv8**, **embeddings** e **geração de textos a partir de categorias**. Não temos a explicação completa do orientador para cada um; o que está aqui é a **interpretação** adotada em 2026-10-19 e o que foi implementado. **[a confirmar com o orientador]** se as interpretações batem.

## Resumo

| Termo | Interpretação adotada | Onde entra | Estado |
| --- | --- | --- | --- |
| **YOLOv8** | Ferramenta de visão computacional na **preparação dos dados**: detecta a pessoa e recorta o vídeo antes do MediaPipe | `data/person_crop.py`, `data/extract_keypoints.py` | Implementado; rodou com pesos reais em um vídeo de teste (ganho pequeno, só com a pessoa pequena no quadro). **Ganho no MINDS-Libras não medido** |
| **Embeddings** | (a) o embedding de sinal que o modelo já usa; (b) embeddings de **palavras** para aproximar palavras fora do vocabulário | (a) `model/`, (b) `api/app/embeddings.py`, `text_to_gloss.py` | (a) documentado e com ferramenta de inspeção; (b) implementado (`char-ngram` calibrado à mão; `sentence-transformers` opcional e **não testado com o modelo real**) |
| **Geração de textos a partir de categorias** | **Frases de exemplo em português por categoria** (contexto: escola, saúde, serviços, trabalho, família, geral), geradas por modelos de frase e validadas contra o vocabulário | `api/app/phrases.py`, `data/phrases.json`, `GET /categories`, front | Implementado (30 frases) |

## YOLOv8

- **O que faz aqui:** localiza a pessoa (classe `person` do COCO, `yolov8n.pt`). O vídeo é recortado em volta dela e o MediaPipe Holistic roda no recorte, com mais pixels nas mãos. Os keypoints continuam sendo do MediaPipe.
- **Por que assim:** o MINDS-Libras é 1920×1080 com a pessoa ocupando parte do quadro; reduzir o quadro inteiro encolhe as mãos. O YOLOv8-pose padrão tem 17 pontos de corpo e **não tem dedos**, então não substitui o MediaPipe; a Ultralytics tem um dataset de *hand keypoints*, mas com rótulos do próprio MediaPipe e licença CC BY-NC-SA 4.0, sem modelo oficial pré-treinado.
- **Por padrão ligado** (`--no-yolo` desliga).
- **Licença:** Ultralytics é **AGPL-3.0** (ou Enterprise). Uso offline na extração; a API não o usa.
- **Testado (2026-10-19) com pesos reais:** funciona de ponta a ponta. Em um clipe de webcam e em uma simulação de quadro 1080p, o ganho na detecção de mãos foi **pequeno e só com a pessoa pequena no quadro** (35%): mãos 25/40% → 33/46%; sem ganho a 50% ou com a pessoa ocupando o quadro. Um clipe, sem repetição: indício, não conclusão.
- **Falta:** medir **no MINDS-Libras** se a taxa de mãos detectadas melhora. Se não melhorar, o custo (PyTorch no ambiente de `data/`) não se justifica e `--no-yolo` basta.
- Detalhes: [`10-pipeline-de-dados.md`](10-pipeline-de-dados.md).

## Embeddings

1. **Embedding de sinal (já existia):** o `MotionGenerator` começa com `nn.Embedding(20, 128)`; o vetor do sinal condiciona o movimento gerado. Agora há `model/sinaliza_model/embeddings.py` para inspecioná-lo (vizinhos, correlação com DTW). Detalhes em [`11-modelo-ml.md`](11-modelo-ml.md).
2. **Embedding de palavras (novo):** quando uma palavra não está na tabela, o embedding a aproxima de uma forma conhecida; se a similaridade passa do limiar, vira esse sinal, **marcada como aproximação**. Dois embedders:
   - `char-ngram` (padrão, só NumPy): pega flexões e erros de digitação; **não** pega sinônimos.
   - `sentence-transformers` (opcional): pega sentido; **não testado** com o modelo real, limiar sem calibração.
   Detalhes e limiares em [`12-api.md`](12-api.md).
- **Ressalva central:** proximidade de escrita ou de sentido **não é** equivalência em Libras. Sem falante de Libras para validar, a aproximação é proposta.

## Geração de textos a partir de categorias

A interpretação mais provável e mais fácil de defender é: gerar **frases em português** para cada categoria, usando o vocabulário de 20 sinais, para demonstração e teste. Foi o que se fez, por modelos de frase com lacunas (sem LLM), com validação automática (só palavras com sinal exato, pelo menos 2 sinais, pelo menos um sinal da categoria).

Outras leituras possíveis, **não implementadas**:
- **Gerar dados de texto** para treinar um texto → glosa (aumento de dados), com o corpus `pt-br2libras-gloss`.
- **Geração condicionada à categoria** em geral: o `MotionGenerator` já gera movimento condicionado ao sinal (a "categoria" seria o sinal).
- Usar um LLM para propor frases por categoria, restrito ao vocabulário e passando pela mesma validação. Nunca para inventar conteúdo de Libras.

## Perguntas para o orientador

1. A leitura de "geração de textos a partir de categorias" como frases de exemplo por categoria é a que ele tinha em mente?
2. O YOLOv8 era para o recorte na extração, ou ele pensou em outro uso (por exemplo, reconhecimento ao vivo, que saiu do escopo)?
3. Para embeddings, ele esperava a aproximação de palavras, a análise do embedding de sinal, ou outra coisa?
4. Algum LLM/modelo de linguagem é bem-vindo na geração de frases, ou prefere-se o método por modelos de frase?
