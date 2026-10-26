# Riscos e questões abertas

Classificação: **Alto / Médio / Baixo** é julgamento nosso **[inferido]**.

## Riscos

| # | Risco | Nível | Mitigação / próximo passo |
| --- | --- | --- | --- |
| 1 | **Ninguém valida Libras.** A métrica DTW diz que o movimento se parece com a gravação, não que seja Libras correta nem compreensível. O pivô deslocou o problema, não o eliminou | Alto | Identificar um validador (professor, intérprete, pessoa surda) antes de qualquer avaliação com usuários; nas demos, falar "sequência de sinais" e nunca "tradução" |
| 2 | **Dados não baixados/validados.** ZIPs incompletos; extração nunca rodou em vídeo do MINDS-Libras; estrutura dos ZIPs inferida de cabeçalhos | Alto | Concluir download; rodar `--limit` pequeno; inspecionar `extraction_log.csv` |
| 3 | **Qualidade da detecção de mãos.** Sinais dependem da configuração de mão; MediaPipe pode perder mãos (motion blur, sobreposição). Mão não detectada vira zero | Alto | Ler taxas de detecção; `fill_missing_hands` repete a última mão; avaliar sinais com baixa detecção |
| 4 | **Modelo pode não superar o medoide.** MSE tende a média borrada; poucos sinalizantes | Médio | Já previsto: ficar com o medoide se for o caso |
| 5 | **Concatenação de sinais ≠ Libras.** Sem gramática, sem expressão facial, sem transições naturais (coarticulação) | Médio | Documentar o limite; suavizar transições; deixar claro na interface |
| 6 | **Vocabulário minúsculo (20 sinais)** frente aos concorrentes (38 mil). Muitas palavras caem fora; a demo pode parecer pobre | Médio | Escolher frases de demo dentro do vocabulário; política clara para palavra desconhecida; V-LIBRASIL como expansão (com restrição de licença) |
| 7 | **Polissemia** (banco, bala): um sinal gravado para duas palavras | Baixo | Notas já no `vocabulary.json`; mostrar a glosa junto do avatar |
| 8 | **Licenças.** V-LIBRASIL não redistribui; pt-br2libras-gloss é CC BY-SA 4.0 (share-alike pode afetar modelos treinados nele); vídeos de sinalizantes são dados pessoais | Médio | Seguir `docs/dados-e-vocabulario.md`; confirmar com o professor; atribuição do MINDS-Libras na UI/README |
| 9 | **Coerência com a disciplina.** Entregas anteriores descrevem outro escopo; avaliadores podem esperar o jogo com câmera | Médio | Registrar a decisão com o professor (data, o que foi combinado); reescrever hipótese/requisitos; **[a confirmar]** critérios da próxima entrega |
| 10 | **Compatibilidade de ambiente:** Python 3.13 local vs `mediapipe==0.10.21`; `numpy<2` vs torch | Baixo/Médio | Venvs separados; usar Python 3.10–3.12 para `data/` se não houver wheel **[a verificar]** |
| 11 | **Desempenho da resposta:** JSON com todos os frames | Baixo | Arredondar casas decimais; limite de 500 caracteres já existe |
| 12 | ~~Borda na normalização~~ **resolvido em 2026-10-19:** sem corpo no quadro, as mãos usam a última referência válida (ver [`08-formato-de-pose.md`](08-formato-de-pose.md)) | — | `.npy` antigos não são comparáveis; reextrair |
| 13 | **Licença do Ultralytics (AGPL-3.0)** | Médio | Uso só offline, na extração; a API não o usa. Se algum dia o YOLOv8 for servido ou distribuído, reavaliar com o professor (ou licença Enterprise). Ver [`09-dados-e-vocabulario.md`](09-dados-e-vocabulario.md) |
| 17 | **Só um dataset, com 3 sinalizantes.** O V-LIBRASIL tem uma gravação por pessoa por sinal; serve para recuperação e vocabulário, e a validação em pessoa nova usa só 3 pessoas. O MINDS não foi baixado | Alto | Decidir o segundo dataset (MINDS sinalizante 07, 2,53 GB, ou nenhum); ver `21-datasets-de-treino.md` |
| 18 | ~~Quadris fora do quadro no V-LIBRASIL~~ **tratado em 2026-10-20:** a origem da normalização passou para o meio dos ombros e os índices 23–32 são zerados (ver `08-formato-de-pose.md`). `.npy` extraídos antes dessa data não servem | — | Reextrair se houver arquivos antigos |
| 19 | ~~Vocabulário do MVP não casa com o V-LIBRASIL~~ **tratado em 2026-10-20:** `vocabulary.json` agora são 210 sinais curados do V-LIBRASIL; o casamento é com acento primeiro ("avó" e "avô" não se juntam), com lematizador e formas de várias palavras. **Os rótulos continuam sem validação de falante de Libras** | Alto | Achar quem valide |
| 20 | **O modelo não supera a média por sinal** e o sinal certo só é o mais parecido em ~8% dos casos (acaso 0,5%): com 2 gravações por sinal e 3 pessoas, a variação entre sinalizantes domina | Alto | Aceitar a média por sinal como gerador; mais sinalizantes ou mais gravações por sinal (segundo dataset) são o que mudaria o resultado |
| 21 | **Mãos não detectadas:** 70 gravações com a mão esquerda abaixo de 80% (49 na direita); não se sabe quantas são sinais de uma mão só | Médio | Olhar os casos com taxa baixa |
| 14 | **Ganho do YOLOv8 não medido no dataset real.** Em teste com um clipe de webcam e uma simulação 1080p o ganho em mãos foi pequeno e só com a pessoa pequena no quadro; recorte fixo assume câmera parada | Médio | A/B com `--limit` pequeno e `--no-yolo` nos vídeos do MINDS-Libras; olhar `extraction_log.csv` |
| 15 | **Aproximação por embedding pode errar:** o usuário vê um sinal que não corresponde à palavra (ex.: parecido na escrita, ou "perto" no sentido com o embedder semântico) | Médio | Sempre marcada com "~" e aviso; limiar conservador (0,65 no `char-ngram`); embedder semântico precisa de calibração antes de uso; validar com falante de Libras |
| 16 | **Frases de exemplo dão falsa impressão de cobertura:** os modelos de frase foram escritos para caber nos 20 sinais | Baixo | Mostram palavras ignoradas (`ignored`); aviso "não é tradução para Libras" no subtítulo |

## Privacidade (LGPD) no escopo atual

A fase 1 colocou a LGPD como *Must have* por causa da captura de câmera. Sem captura do usuário, o risco mudou:

- **Não há mais vídeo/gesto do usuário** — o requisito de consentimento antes da captura **não se aplica** enquanto o produto não usar câmera. Se o escopo voltar a capturar, retomar R05.
- **Texto digitado:** a API não registra nada hoje. Se passar a gravar logs de texto, definir finalidade, retenção e aviso (pode conter dado pessoal ou sensível — saúde, por exemplo, dado o contexto de uso).
- **Dados de treino:** vídeos e keypoints de sinalizantes são dados pessoais. O dataset é CC BY 4.0, mas o conteúdo bruto não deve ser versionado (`raw/` no `.gitignore`); keypoints derivados podem ser versionados **com atribuição**.
- A dúvida da Matriz de Pesquisa (gesto como dado biométrico sensível) segue **sem resposta** e só volta a importar se houver captura.

## Questões abertas (precisam de decisão da equipe)

1. **Quem valida os sinais?** (professor, intérprete, pessoa surda — e quando)
2. ~~O que fazer com palavra fora do vocabulário?~~ **Decidido em 2026-10-19:** aproximar por embedding (sinalizado com "~") ou ignorar com aviso; soletrar não é possível (o MINDS-Libras não tem o alfabeto manual). Falta validar com falante de Libras e decidir se o embedder semântico entra.
3. ~~Qual a unidade de demonstração?~~ **Encaminhado:** frases de exemplo por categoria (`data/phrases.json`). Falta o professor confirmar se é isso que ele quis dizer com "geração de textos a partir de categorias".
4. **Qual o critério de sucesso do projeto?** Proposta: DTW do gerador < medoide e < média da classe em sinalizante não visto + demonstração funcional + validação qualitativa por pelo menos uma pessoa que saiba Libras.
5. ~~Avatar com rig ou esqueleto?~~ **Resolvido em 2026-10-25:** player do VLibras, local (ver `13-web.md`). Avatar próprio fica para depois do MVP.
6. **Prazo e entregas restantes da disciplina** (o cronograma de 8 semanas era do escopo antigo).
7. **Personas e hipótese:** refazer para o escopo atual ou manter como contexto.
8. **Atribuição e licença do próprio repositório** (não há `LICENSE`). **[a confirmar]**
9. **Disco e rede** para os ~16,3 GB (e para processar vídeo 1080p com MediaPipe, que é lento em CPU).
10. **Incluir rosto/expressão?** Cada decisão aqui muda o formato de pose e os três componentes.
11. **Texto em português como L2 para surdos:** se o usuário final é surdo, o português escrito pode ser segunda língua — a interface e as mensagens devem ser simples e curtas. **[hipótese]**
