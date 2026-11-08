# Roteiro da demonstração ponta a ponta

Roteiro da apresentação (entregável 10) e da demonstração automática (entregável 7). Percorre o mesmo fluxo do [`24`](24-pipeline-de-dados-ponta-a-ponta.md) (R0.6): **dados → Airflow → treino no MLflow → modelo → API → dados novos → monitoramento → painel**. Dura cerca de **12 minutos** falando; a demonstração automática (`python -m textgloss.demo`) cobre os passos 5 a 7 sem ninguém clicar.

**Mensagem central (diga logo no começo):** o Sinaliza recebe texto em português e mostra a **sequência de sinais** correspondente (não é tradução de Libras). O **machine learning** está em um ponto preciso: um classificador, treinado por nós, que decide **palavra por palavra** se ela vira sinal. Ele supera por 6 pontos a lista fixa que usávamos antes (F1-macro 0,885 contra 0,823 no teste final).

## Antes de começar (5 minutos antes)

1. **Memória do Docker:** a pilha toda usa ~2,7 GB; o modelo pede ~2,8 GB só na carga. Não abra nada pesado. Detalhes em [`14`](14-como-rodar-e-testar.md).
2. Suba tudo com **um comando** (o compose sobe na ordem certa e a API passa pela carga do modelo antes do Airflow):

   ```powershell
   docker compose up -d --build
   ```

3. Confira que está tudo de pé: `python -m textgloss.demo` (passo 1 mostra o estado). Se a API mostrar `lista-fixa`, o modelo ainda está carregando (10 a 20 s) ou não está registrado; ver "Se algo falhar".
4. Deixe abertas as abas do navegador: **painel** http://localhost:8501, **MLflow** http://localhost:5000, **Airflow** http://localhost:8080, **web** http://localhost:5173 e **API** http://localhost:8000/docs.
5. Se o banco estiver vazio (nenhuma frase ainda), rode antes `python -m textgloss.simulador --n 40` e dispare o DAG `monitoramento`, para o painel não abrir vazio.

## Passo a passo

| Tempo | Passo | O que falar | O que mostrar | Onde está o ML |
| --- | --- | --- | --- | --- |
| 1 min | **0. Abertura** | Problema: pessoas surdas e ouvintes precisam de ferramentas para texto em português virar sinais. Escopo: sequência de sinais, sem gramática nem expressão facial; ninguém do grupo sabe Libras, então nada aqui foi validado por falante de Libras. | Slide de abertura | — |
| 2 min | **1. Arquitetura e onde está o ML** | O diagrama: dados, Airflow, MLflow, API, monitoramento, painel. Cada caixa é ML nosso, regra, extração ou externo. | O diagrama do [`24`](24-pipeline-de-dados-ponta-a-ponta.md) | **Só uma caixa é ML nosso na saída final**: o classificador T1 |
| 1 min | **2. Dados e rótulos** | VLibrasBD: 127 mil pares português → glosa feitos por intérpretes certificados (CC BY-SA, créditos no projeto). Cada palavra vira exemplo: `MANTER` se aparece na glosa, `DESCARTAR` se não. A divisão treino/teste é **por frase**, para não vazar. | Notebook `01-eda` e `02-preparacao`; a tabela `palavras_t1` | Aqui nasce o alvo do ML |
| 2 min | **3. Experimentos no MLflow** | Baseline (Regressão Logística) contra a lista fixa; depois Árvore, Random Forest e KNN; Optuna otimiza o Random Forest (25 tentativas); validação cruzada e teste final **uma única vez**. | MLflow, experimento `t1-manter-descartar`: comparar runs, matriz de confusão, importância de atributos | O treino e a escolha do modelo |
| 1 min | **4. Airflow** | O fluxo é automático: quatro DAGs (ingestão, preparação, treino, monitoramento). Numa máquina limpa o Airflow roda tudo sozinho na primeira subida. | Airflow: grafo do `treino_t1` e o `monitoramento` | O DAG `treino_t1` orquestra o ML |
| 2 min | **5. Inferência ao vivo** | A API usa o modelo `sinaliza-t1` do MLflow. Para cada palavra devolve a decisão e a probabilidade. Mostre uma palavra que o modelo descarta ("o", "está") e uma que mantém ("filho", "dor"). | Web (aba Tradutor) com "O filho está com dor de cabeça."; depois a API em `/docs` ou `python -m textgloss.demo` (passo 3), que mostra `MANTER`/`DESCARTAR` e a probabilidade | **O modelo decide aqui** |
| 2 min | **6. Dados novos e monitoramento** | O simulador faz o papel da fonte de dados novos (no lugar do embarcado, que não é do nosso grupo): envia frases, a API classifica e grava, o DAG `monitoramento` consolida por hora. | `python -m textgloss.simulador --n 30` e o DAG no Airflow | O modelo classifica os dados novos |
| 1 min | **7. Painel** | Monitoramento em tempo de execução: frases por hora, latência, palavras sem sinal, decisões incertas, últimas inferências, versão e métricas do modelo, estado dos serviços. | Painel, abas Visão geral, Inferências, Modelo e Serviços | Mostra a saída do modelo, sem ML novo |
| 2 min | **8. Limitações e próximos passos** | Ver abaixo. | Slide de limitações | — |

## Limitações (diga com franqueza)

- **O modelo decide quais sinais entram, não a ordem.** A saída segue a ordem do português ("português sinalizado"); a ordem da Libras exigiria outro modelo (ex.: seq2seq).
- **Nenhuma validação por pessoas surdas** ou falantes de Libras. Sinais, aproximações e frases são propostas não validadas.
- **Ruído nos rótulos:** o rótulo vem de um alinhamento automático; a equipe conferiu 200 palavras para medir isso (resultado em [`24`](24-pipeline-de-dados-ponta-a-ponta.md), quando a planilha preenchida entrar no repositório).
- **O modelo erra:** descarta "preciso" (o spaCy o trata como adjetivo) e oscila em "eu"; fora do domínio (outro tipo de texto) o desempenho cai de 2 a 4 pontos; o ganho sobre a lista fixa é de 6 pontos, não um salto.
- **Texto com várias frases** é tratado como uma frase só.
- **Escopo:** sem sistema embarcado nem MQTT (o embarcado não é do grupo); a fonte de dados novos é um simulador de uso.
- **Privacidade:** a API só grava o texto de quem pede (simulador) ou com opt-in, e o texto é apagado depois de 30 dias; falta o aviso de privacidade na interface do web.
- **Trilha de aprendizado do web:** depende de endpoints `/learn/*` que só existem no mock.
- **Infraestrutura:** o modelo (864 MB) pede ~2,8 GB na carga; o perfil `completo` do treino leva horas num Docker de 2 CPUs.

## Perguntas prováveis

| Pergunta | Resposta curta |
| --- | --- |
| Por que classificação por palavra e não um modelo de tradução? | É o caminho que o orientador aprovou, com base no VLibras/VLibrasBD; mantém o ML treinável e auditável por nós, em vez de terceirizar para um modelo pré-treinado. |
| Por que Random Forest? | Foi o que mais melhorou com o Optuna (0,852 → 0,884) e tem mais hiperparâmetros para ajustar; a Regressão Logística ficou muito perto (0,876) e é bem mais leve. |
| O teste final foi usado para escolher o modelo? | Não: a escolha usou validação e validação cruzada; o teste (10% das frases) rodou **uma única vez**, e o código se recusa a repeti-lo. |
| Como sabem que não houve vazamento? | A divisão treino/teste, a de validação e a validação cruzada são por frase (nenhuma frase está nos dois lados); há testes automáticos para as duas primeiras e a validação cruzada usa `StratifiedGroupKFold` agrupado por frase. |
| E se o modelo não estiver disponível? | A API cai na lista fixa e avisa em `model_version: "lista-fixa"`; o painel mostra o alerta. |
| Onde estão os dados dos usuários? | Só números ficam por padrão (decisão, probabilidade, latência); o texto só do simulador ou com opt-in, e some depois da retenção. |
| Por que o modelo é tão grande? | 154 árvores profundas (864 MB). Um modelo menor teria desempenho parecido, mas trocar o modelo exigiria um novo conjunto de teste, porque o atual já foi usado. |

## Demonstração automática

```powershell
python -m textgloss.demo            # percorre os 7 passos e sai com código 0 se todos passarem
python -m textgloss.demo --n 40     # com mais frases do simulador
```

O script confere os serviços, mostra o modelo registrado e a versão em uso, classifica três frases palavra por palavra, roda o simulador, aciona o DAG `monitoramento` (pela API do Airflow; se ele não responder, roda o mesmo módulo direto), lê os indicadores do banco e confere o painel. Para um stack em outras portas: `--api`, `--mlflow`, `--airflow`, `--painel` e `--banco`.

## Se algo falhar

| Sintoma | Causa provável | O que fazer |
| --- | --- | --- |
| API mostra `lista-fixa (carregando o modelo)` | o modelo (864 MB) ainda está carregando | esperar 10 a 20 s; o `/ready` só fica pronto depois |
| API mostra `lista-fixa (modelo indisponível)` | não há `sinaliza-t1` no MLflow (máquina nova) | esperar o bootstrap terminar, ou rodar o DAG `treino_t1`; na demonstração, mostrar que o plano B funciona |
| Painel sem indicadores | o DAG `monitoramento` ainda não rodou | disparar o DAG no Airflow (ou `python -m textgloss.monitor`) |
| API saiu do ar com `exit 137` | memória do Docker | subir a API antes do Airflow (o compose já faz); fechar outros programas; `SINALIZA_USE_MODEL=false` como último recurso |
| Aba Trilha do web mostra "Not Found" | `/learn/*` só existe no `mock-api` | usar o Tradutor; a trilha é da parte web |
| Tudo travado | — | `docker compose down` e `docker compose up -d --build`; o estado fica nos volumes |
