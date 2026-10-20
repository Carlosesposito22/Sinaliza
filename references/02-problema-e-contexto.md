# Problema e contexto

Fonte: `Documentos/Entrega 1.docx` e `Documentos/Matriz de Pesquisa Grupo 10.xlsx`. Os números abaixo são os **da pesquisa documental do grupo**; não foram reverificados nesta pasta. A Matriz de Pesquisa classifica cada achado como CERTEZA, SUPOSIÇÃO ou DÚVIDA — mantenha esse rigor ao citar.

## Problema (formulação da fase 1)

> Como apoiar, de forma acessível e contínua, a comunicação e o aprendizado de Libras entre pessoas surdas e ouvintes nos diferentes espaços sociais em que essa comunicação é necessária, considerando a escassez de intérpretes e profissionais fluentes em Libras e a ausência de ferramentas capazes de avaliar, em tempo real, se um sinal está sendo corretamente reproduzido — e não apenas traduzido de forma unidirecional?

A segunda metade ("avaliar se um sinal está sendo reproduzido") pertence ao escopo antigo. Ver [`01-escopo-atual.md`](01-escopo-atual.md).

Contextos citados na apresentação: escola e faculdade, saúde, trabalho, atendimento em estabelecimentos, transporte e dia a dia.

## Dados de contexto

| Dado | Fonte citada | Confiança (Matriz) |
| --- | --- | --- |
| Mais de 10 milhões de pessoas surdas no Brasil (~5%); ~2,3 milhões se declaram surdas ou com grande dificuldade para ouvir | Censo 2022 (IBGE) | Alta / CERTEZA |
| Apenas **2,6%** das pessoas com dificuldade para ouvir declaram saber Libras | PNS 2019 (IBGE) | Alta / CERTEZA |
| 1,5 milhão de alunos da educação básica com deficiência em turmas de educação especial | Censo Escolar 2022 (Inep) | Alta / CERTEZA |
| Matrículas de alunos com necessidades especiais na rede pública: 382.215 (2000) → 636.451 (2012), +66,51% | Artigo SciELO | citado na Entrega 1 |
| Receio de evasão escolar: 28% das famílias de alunos com deficiência vs 19% dos demais (dez/2021) | CNN Brasil | Média / **SUPOSIÇÃO** (percepção, não taxa de evasão) |
| Evasão de surdos no ensino superior (uma instituição privada): 42% no 1º semestre, 58% no 2º | Redalyc | Média / **SUPOSIÇÃO** (uma instituição; não generalizar) |
| 100% dos idosos surdos entrevistados apontam a saúde como maior problema de comunicação | Pesquisa nacional (citada na Entrega 1) | — |
| Autônomos: 26% dos ouvintes vs 37% dos surdos | Instituto Locomotiva | citado na Entrega 1 |
| 182 mil pessoas com deficiência no Recife | Câmara Municipal do Recife (Censo 2022) | Alta / CERTEZA |

## Causas e consequências (resumo da Entrega 1)

- **Causas:** formação superficial de professores em Libras; modelo pedagógico dependente do intérprete; ensino pensado em português com Libras como tradução secundária.
- **Consequências:** evasão e defasagem escolar; letramento em português escrito comprometido; na saúde, dependência de familiar/intérprete, risco ao diagnóstico e violação de privacidade; no trabalho, barreiras de comunicação com colegas e gestores.

## Soluções existentes e lacunas (fase 1)

- **Tradutores português → Libras com avatar 3D:** Hand Talk, ProDeaf, VLibras. Limitações apontadas: sinais ausentes na base (ProDeaf), maior uso de datilologia (ProDeaf vs Hand Talk). Detalhes em [`04-analise-de-similares.md`](04-analise-de-similares.md).
- **Acadêmicas, reconhecimento por câmera:** IFES (alfabeto + gamificação), UNESP (MediaPipe Holistic + LSTM, sinais isolados), MINDS-Libras (dataset; CNNs com até 93,3% de acurácia média).
- **Lacunas na fase 1:** nenhum app avaliava a execução do usuário; projetos acadêmicos ficavam em alfabeto/sinais isolados; nada de apoio à comunicação cotidiana em tempo real; formação docente em Libras segue insuficiente.
- **Lacuna institucional:** o tema não aparece nos desafios do E.I.T.A! Recife (2º ciclo) nem no Summer Job 2026 (Prefeitura do Recife/CESAR). Pode servir de argumento para propor o projeto como desafio institucional no futuro (SECTI, Secretaria de Educação) — **[ideia da fase 1, não é prioridade atual]**.

## Dúvidas abertas da Matriz de Pesquisa

| Tópico | Dúvida | Ação registrada |
| --- | --- | --- |
| LGPD e captura de gestos | Não está claro se vídeo de corpo/mãos para reconhecimento de sinais é dado biométrico sensível | Verificar com o professor/orientador; desenhar consentimento e retenção antes de captar dados de usuários |
| Robustez por câmera | Sistemas só com câmera são sensíveis a variação de iluminação | Testar em condições reais antes de validar o MediaPipe |
| Limites pedagógicos do Hand Talk | O artigo foi citado, mas os limites específicos não foram extraídos | Ler o artigo na íntegra |
| Libras Aventura | Sem dados públicos de acurácia, usuários ou validação pedagógica | Tratar como SUPOSIÇÃO |

## Pesquisa com usuários (apresentação do grupo)

40+ respostas a um formulário (link na apresentação, não disponível localmente). Síntese do próprio grupo:

- **Dificuldades:** comunicação e conhecimento de Libras.
- **Necessidades:** prática, correção e demonstração.
- **Interesse:** câmera, gamificação e evolução.

> Essa pesquisa foi desenhada em torno do jogo com câmera. A necessidade de "demonstração" é a que mais se conecta ao escopo atual (ver um sinal demonstrado por avatar).
