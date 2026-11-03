# Página "Sprints" do Google Sites: texto pronto

Para as duas pessoas do Google Sites. Criem uma página nova chamada **Sprints** e colem as quatro seções abaixo, **a mais recente em cima**. Reconstruído em 2026-11-02 a partir do histórico do repositório; as **datas são aproximadas** e os campos "Quem" precisam ser completados pelo grupo.

Antes das sprints, na mesma página, colem o resumo da jornada.

---

## Resumo da jornada

O Sinaliza começou como um tradutor que tocava gravações reais de sinalizantes num avatar 3D nosso. Em quatro semanas aprendemos, com pesquisa e testes, que esse caminho tinha dois problemas: o avatar não ficava preciso e converter palavra por palavra na ordem do português produz **português sinalizado**, e não Libras. Mudamos para um caminho com mais evidência: **aprender com machine learning, a partir de frases glosadas por intérpretes, quais palavras viram sinal**, usando o avatar do VLibras. O orientador aprovou a mudança.

---

## Sprint 4 · semana até 02/11/2026 (mais recente)

**Objetivo.** Executar o novo caminho: obter a base de dados, treinar e escolher o modelo de machine learning e preparar o web.

**Entregue**
- Base **VLibrasBD** (127 mil frases em português com a glosa feita por intérpretes) baixada, conferida e guardada em banco de dados, com os créditos devidos.
- Análise exploratória e preparação dos dados, com as decisões justificadas.
- **Cinco abordagens comparadas** com registro dos experimentos no MLflow: lista fixa (como era antes), Regressão Logística, Árvore de Decisão, Random Forest e KNN.
- Otimização do modelo com Optuna, validação cruzada, curva de aprendizado, teste fora do domínio e teste final.
- Definição do contrato entre a API de ML e o web, com um protótipo (mock) para o time web começar a **trilha de aprendizado gamificada**.
- Divisão do grupo: ML e API, web e Google Sites.

**Resultados.** O modelo escolhido (Random Forest otimizado) tem F1-macro **0,885** no teste final contra **0,823** da lista fixa usada antes (+6 pontos). A validação cruzada é estável (0,879 ± 0,001).

**Dificuldades e limites.** O ganho é de poucos pontos; os rótulos têm ruído que ainda vamos medir; o modelo decide *quais* sinais entram, não a *ordem*; o desempenho cai de 2 a 4 pontos em outro tipo de texto; não houve validação por pessoas surdas.

**Próximos passos.** Orquestrar o pipeline com Airflow, integrar o modelo à API, Docker Compose completo, painel de acompanhamento, desenvolver a trilha de aprendizado no web, conferência manual dos rótulos e apresentação final.

**Quem.** Equipe: Amanda, Bruno, Caio, Carlos, Felipe e Fabiana. *(Completar quem fez o quê.)* Machine learning e API: Carlos.

---

## Sprint 3 · semana de 26/10 a 28/10/2026 (aproximada): a virada do projeto

**Objetivo.** Responder à pergunta do orientador: *"quebrar o texto em palavras-chave é a melhor forma de converter para Libras?"*

**Entregue**
- **Relatório de pesquisa** sobre como converter português em Libras.
- Conclusão: o que fazíamos (descartar palavras de uma lista e tocar um sinal por palavra, na ordem do português) é **português sinalizado**, rejeitado pela literatura e pela comunidade surda, porque Libras tem gramática própria.
- O caminho com mais evidência, que é o do VLibras: **aprender a glosa a partir de um corpus feito por intérpretes** (VLibrasBD).
- **Plano de machine learning:** classificar, palavra por palavra, se ela vira sinal ou é descartada; comparar modelos; otimizar; validar; registrar tudo no MLflow.
- O gerador de movimento deixou de ser a entrega principal de ML.

**Aprendizado.** Um sistema que só mostra um sinal por palavra não representa a língua. Declaramos essa limitação e passamos a chamar o resultado de **"sequência de sinais"**, não de "tradução de Libras".

**Apresentação ao orientador.** Ele gostou do estudo, concordou em seguir a base do VLibras e pediu que o projeto deixe claro **onde aplicamos machine learning** e que a pipeline seja bem documentada.

**Próximos passos.** Baixar o corpus, preparar os dados e treinar os modelos.

**Quem.** *(Completar.)*

---

## Sprint 2 · semana de 19/10 a 25/10/2026 (aproximada): o caminho antigo, avatar 3D e movimento

**Objetivo.** Gerar o movimento dos sinais a partir de gravações reais e mostrá-lo num avatar 3D.

**Entregue**
- Dados reais: base **V-LIBRASIL** baixada e **629 gravações** processadas (210 sinais × 3 sinalizantes), extraindo a posição de corpo e mãos com MediaPipe, com recorte da pessoa por YOLOv8 (sugestão do orientador).
- Vocabulário de **210 sinais** curado pela equipe, com reconhecimento de formas (plural, conjugação).
- Palavras fora do vocabulário **aproximadas por similaridade**, sempre sinalizadas como aproximação; 30 frases de exemplo em 6 categorias; a interface mostra como cada palavra virou sinal.
- Primeiro treino de um modelo de movimento (rede neural) em dados reais.
- A API passou a tocar as gravações reais, sinal por sinal, com transições.
- **Avatar 3D realista (Microsoft Rocketbox)** animado pelos pontos extraídos, com tradução própria dos pontos para os ossos do personagem e 42 testes.

**Resultado do modelo de movimento.** Não superou a simples média das gravações de cada sinal (acerto do sinal em 1º lugar: 6,7% contra 7,6%). Pela nossa própria regra, o modelo não se justificou.

**Dificuldades.** Os dedos do avatar 3D seguiam imprecisos: os pontos do MediaPipe são medidos em 2D e a profundidade é estimada, as mãos se sobrepõem, e o rosto, que carrega parte da gramática, não era capturado. Gastamos vários dias ajustando (limites anatômicos dos dedos, suavização, profundidade das mãos) e o resultado continuava pouco confiável.

**Decisão (25/10).** Trocar o avatar pelo **player do VLibras** (Ícaro, Hosana e Guga), que roda localmente e toca os nossos sinais com qualidade muito maior. O trabalho do avatar Rocketbox ficou guardado em `historico/`.

**Próximos passos.** Revisar o rumo do machine learning, já que o movimento mostrado deixou de vir dos nossos dados.

**Quem.** *(Completar.)*

---

## Sprint 1 · semana de 12/10 a 18/10/2026 (aproximada): a base do projeto

**Objetivo.** Definir o escopo e montar a base técnica.

**Entregue**
- Documentos da fase 1: pesquisa, personas, requisitos e ideação.
- **Escopo reduzido** (por volta desta fase), depois de conversa com o professor: o projeto deixou de reconhecer o sinal feito pelo usuário na câmera e passou a **mostrar sinais a partir de texto**.
- Estrutura do projeto: API (FastAPI), interface web (React) e Docker, subindo tudo com um comando.
- Fonte de dados definida (MINDS-Libras), vocabulário inicial de 20 sinais e formato dos pontos do corpo e das mãos (75 pontos).
- Primeira versão do texto → sinais, por **tabela de palavras**.
- Esqueleto de treino com linhas de base e métrica de comparação de movimentos.
- Extração em lote dos pontos do corpo e das mãos.

**Aprendizado.** Dados de vídeo são pesados (só o subconjunto inicial passa de 16 GB) e a qualidade da extração dos pontos limita tudo o que vem depois.

**Próximos passos.** Obter dados reais e treinar o primeiro modelo.

**Quem.** *(Completar.)*
