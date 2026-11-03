# Google Sites: o que atualizar (para as 2 pessoas responsáveis)

Site: https://sites.google.com/cesar.school/sinaliza/início. O orientador pediu para **manter o site sempre atualizado** e sugeriu **registrar por semana o que foi feito, como uma sprint**.

Levantamento feito em 2026-11-02 lendo o site publicado (as imagens e gráficos das páginas não puderam ser lidos; confiram no navegador).

## Como está hoje

| Página | Situação |
| --- | --- |
| Início | Preenchida, mas **desatualizada** (ver abaixo) |
| Oportunidade | Preenchida (problema, causas, pesquisa de mercado em imagens). Fala de "avaliar a execução do usuário", que saiu do escopo |
| Mercado | Preenchida. Diz que o movimento vem de ML treinado com gravações e MINDS-Libras: **já não é assim** |
| Segmentos de Clientes | Preenchida e ainda válida |
| **Nossa solução** | **Vazia: só "Em breve, nossa solução!"** |
| Estratégia | Preenchida (missão, visão, valores, dados do Recife); sem roadmap nem datas |
| Modelo de Negócios | Preenchida, com brainstorming e matrizes em imagens |
| Organização | Preenchida: sprints semanais no Trello, reunião semanal |
| Equipe | Só os nomes dos 6 membros, **sem papéis** |
| (não existe) | **Nenhuma página de sprints/andamento semanal** |

## O que mudou no projeto e o site ainda diz diferente

1. **O ML agora é texto → glosa por classificação**, treinado por nós no corpus VLibrasBD. Não é mais "movimento gerado por ML a partir de gravações de sinalizantes". O gerador de movimento ficou como experimento que não superou a média.
2. **O avatar é o player do VLibras** (rodando localmente), não um avatar 3D animado por nós. Os sinais vêm do dicionário do VLibras.
3. **Não há reconhecimento por câmera** nem avaliação da execução do usuário (escopo reduzido depois de conversa com o professor). Revisar textos de Oportunidade e Impacto que prometem "validação contínua da execução dos sinais".
4. **Novidade de produto:** o web vai ter uma **trilha de aprendizado gamificada** (estilo Duolingo). Ainda em desenvolvimento; descrevam como "em construção".
5. **Bases de dados:** MINDS-Libras e V-LIBRASIL deixaram de ser a base do ML; a base é o **VLibrasBD** (127 mil frases glosadas por intérpretes), com créditos obrigatórios.

## Tarefas (pela ordem de importância)

### 1. Criar a página "Sprints" (a sugestão do orientador)

Uma página nova, com **uma seção por semana**, mais recente em cima. Modelo:

- **Período** (ex.: 26/10 a 02/11/2026)
- **Objetivo da semana** (1 frase)
- **O que foi entregue** (lista curta, com link para o repositório ou documento)
- **Números / resultados** (métricas, gráficos)
- **Demonstração** (print ou link)
- **Problemas e riscos**
- **Próximos passos** (vira o objetivo da semana seguinte)
- **Quem fez o quê**

Alimentar toda semana, na mesma reunião em que revisam o Trello. O texto da primeira sprint está pronto abaixo.

### 2. Preencher "Nossa solução" (hoje vazia)

Explicar, em linguagem acessível, como o Sinaliza funciona de ponta a ponta. Fonte: [`references/24-pipeline-de-dados-ponta-a-ponta.md`](../references/24-pipeline-de-dados-ponta-a-ponta.md). Estrutura sugerida:

1. O que o usuário vê (digita uma frase, o avatar sinaliza, vê como cada palavra virou sinal).
2. **Onde está o machine learning** (o orientador pediu que isto fique bem claro): o modelo decide, palavra por palavra, se ela vira sinal ou é descartada, aprendendo com 127 mil frases glosadas por intérpretes.
3. O pipeline (diagrama): dados → preparação → treino → modelo → API → avatar.
4. Resultados (tabela e gráficos, abaixo).
5. Limitações, ditas com franqueza.
6. A trilha de aprendizado (em construção).
7. Tecnologias: Postgres, MLflow, Optuna, scikit-learn, spaCy, FastAPI, React, Docker.

### 3. Atualizar "Início", "Mercado" e "Oportunidade"

Corrigir os pontos da seção anterior (itens 1 a 5). Em Mercado, trocar MINDS-Libras e "movimento gerado por ML" por VLibrasBD e "decisão de quais palavras viram sinal por ML". Manter os concorrentes citados (Hand Talk, VLibras, ProDeaf) e dizer como o Sinaliza se diferencia (código aberto, mostra como cada palavra virou sinal, trilha de aprendizado).

### 4. Página ou seção de resultados de ML

Para mostrar ao orientador e a quem visitar o site. Números verificados (de [`references/25`](../references/25-baseline-t1.md) a [`28`](../references/28-validacao-e-generalizacao-t1.md)):

| Modelo | F1-macro (validação) |
| --- | --- |
| Lista fixa (sem ML, como era antes) | 0,822 |
| Regressão Logística (baseline) | 0,876 |
| Árvore de Decisão | 0,870 |
| Random Forest (padrão) | 0,852 |
| KNN | 0,846 |
| **Random Forest otimizado com Optuna** | **0,884** |

**Teste final** (dados separados, usados uma vez): **0,885** contra 0,823 da lista fixa. Validação cruzada de 5 dobras: 0,879 ± 0,001. Gráficos prontos nos notebooks `notebooks/03` a `05` e no MLflow (matrizes de confusão, curvas ROC, curva de aprendizado, fora do domínio). Prints do MLflow (http://localhost:5000 com `docker compose up -d postgres mlflow`) também servem.

### 5. Equipe

Colocar o **papel de cada pessoa** (hoje só nomes). Sugestão de papéis: ML e API; Web (trilha gamificada, 2 pessoas); Documentação e Google Sites (2 pessoas). Ajustem com o que o grupo combinou.

### 6. Estratégia: roadmap

Acrescentar um roadmap curto com as próximas etapas (abaixo) e a validação por pessoas fluentes em Libras como passo necessário.

### 7. Créditos e licenças (obrigatório)

Uma seção (rodapé ou página "Créditos") com: **VLibrasBD** (Lima et al., 2025, *Data in Brief*; CC BY-SA 4.0, obrigatório dar créditos), **VLibras** (player e dicionário de sinais, LGPL-3.0), e demais ferramentas. Texto base em [`docs/creditos-e-licencas.md`](creditos-e-licencas.md).

### 8. Links

Manter os links do repositório, dos slides do SR1 e acrescentar a documentação do projeto (`references/`).

## Regras de redação (valem para o site inteiro)

- Dizer **"sequência de sinais"**, nunca "tradução de Libras". O MVP concatena sinais isolados, sem gramática de Libras nem expressão facial.
- Ninguém do grupo fala Libras: **não afirmar que os sinais foram validados**. A validação por pessoas fluentes continua sendo o próximo passo.
- Não prometer o que não existe (reconhecimento por câmera, feedback de execução).
- Todo número vem dos documentos do repositório; se mudar, atualizar no site.
- Cuidado com imagens: não publicar vídeos de sinalizantes das bases (licença).

## Texto pronto da primeira sprint (ajustem as datas ao calendário de vocês)

**Sprint: semana até 02/11/2026**

**Objetivo.** Fechar a parte de machine learning do projeto e deixar claro onde ela atua.

**Entregue**
- Escopo do ML definido com o orientador: aprender, com frases glosadas por intérpretes, **quais palavras de uma frase viram sinal** (abordagem por glosa aprovada por ele).
- Base de dados: **VLibrasBD**, 127 mil pares português → glosa, carregada em banco Postgres com conferência de integridade.
- Análise exploratória e preparação dos dados em notebooks (limpeza, atributos de linguagem, rótulos, divisão treino/teste por frase).
- **Cinco modelos treinados e comparados** e registrados no MLflow; otimização de hiperparâmetros com Optuna; validação cruzada, curva de aprendizado e teste fora do domínio.
- Modelo final registrado: Random Forest otimizado.
- Contrato de API e protótipo (mock) para o time web começar a trilha de aprendizado gamificada.

**Resultados.** Teste final F1-macro **0,885** contra **0,823** da lista fixa que usávamos antes (+6 pontos); validação cruzada estável (0,879 ± 0,001).

**Limitações.** O ganho é de poucos pontos; os rótulos têm ruído que ainda vamos medir; o modelo decide *quais* sinais entram, não a *ordem*; o desempenho cai de 2 a 4 pontos em outro tipo de texto; não houve validação por pessoas surdas.

**Próximos passos.** Orquestrar o pipeline com Airflow; integrar o modelo à API e registrar as frases recebidas; Docker Compose com todos os serviços; painel de acompanhamento; trilha de aprendizado no web; conferência manual dos rótulos; apresentação final.

**Quem fez o quê.** ML e API: Carlos. Web: definição do contrato e protótipo feitos; desenvolvimento da trilha começa na próxima semana.

## Pronto quando

- Existe a página **Sprints** com a primeira sprint.
- "Nossa solução" deixou de estar vazia e mostra onde está o ML.
- Início, Mercado e Oportunidade não afirmam nada que o projeto já não faz.
- Equipe tem papéis; há seção de créditos.
- O orientador consegue ver, só pelo site, o que foi feito na semana.
