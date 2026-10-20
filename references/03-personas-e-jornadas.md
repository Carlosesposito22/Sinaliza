# Personas e jornadas

Fonte: `Documentos/Personas.pdf`, `Documentos/Proto Jornada do Usuário Atual .pdf`. São **protopersonas**: hipóteses da equipe, "a serem validadas com pesquisa/entrevistas com usuários reais". Foram desenhadas para o escopo antigo (jogo de prática com câmera).

## Persona 1 — Júlia, 32, executiva (ouvinte; usuária principal no escopo antigo)

- **Perfil:** pouco conhecimento de Libras, quer aprender para se comunicar melhor com pessoas surdas. Alta familiaridade com tecnologia.
- **Objetivo:** aprender e praticar Libras de forma simples e interativa.
- **Necessidades:** feedback imediato, exercícios práticos, evolução por níveis, forma interativa de aprender.
- **Dores:** não sabe se faz os sinais corretamente; dificuldade de praticar sozinha; nem sempre há quem corrija; insegurança.
- **Oportunidade (escopo antigo):** ferramenta que usa a câmera para identificar os movimentos e informar se o sinal foi correto.

## Persona 2 — Matheus, 25, jornalista (surdo; beneficiário indireto)

- **Perfil:** surdo, usuário de Libras, impactado indiretamente quando mais ouvintes aprendem a se comunicar com ele.
- **Objetivo:** comunicar-se com ouvintes com mais facilidade e autonomia, sem depender só do próprio esforço.
- **Necessidades:** mais autonomia; mais pessoas preparadas para usar Libras; mais acessibilidade e ferramentas.
- **Dores:** ouvintes não sabem Libras; dependência de intérpretes/familiares; dificuldade em escola, saúde e trabalho.

## Persona 3 — Helena, 50, professora (ouvinte; usuária direta no escopo antigo)

- **Perfil:** professora de turma regular com aluno surdo. **Baixa familiaridade com tecnologia — precisa de interface simples e guiada.**
- **Objetivo:** comunicar-se melhor com alunos surdos e tornar a aula mais inclusiva.
- **Necessidades:** aprender e praticar Libras de forma prática; verificar/corrigir sinais; usar recursos de Libras na escola.
- **Dores:** pouco domínio de Libras; dificuldade de comunicação direta; dependência do intérprete; dificuldade de adaptar atividades; falta de recursos para praticar no dia a dia.

## Jornadas atuais (5 etapas cada)

Estrutura: Necessidade → Dificuldade → Busca/Tentativa → Prática/Intermediação → Problema atual. Cada etapa traz situação, ação, pensamento, dor, ponto de contato e sentimento.

| Persona | Fio condutor | Sentimentos ao longo da jornada | Oportunidade identificada |
| --- | --- | --- | --- |
| Júlia | Conhece uma pessoa surda → percebe que não se comunica → decide aprender → pratica sozinha → fica sem saber se está certo ("Será que estou fazendo esse sinal certo?") | Insegurança, frustração, motivação, dúvida, insegurança | Forma prática e interativa de praticar Libras com feedback sobre a execução |
| Matheus | Precisa falar com ouvinte → percebe que ele não entende Libras → recorre a gestos/escrita → precisa de intérprete/familiar → segue encontrando barreiras ("Seria mais fácil se mais pessoas soubessem Libras") | Motivação, frustração, insegurança, dependência, frustração | Comunicação mais acessível, ajudando ouvintes a aprender e praticar |
| Helena | Recebe aluno surdo → percebe pouco conhecimento → busca cursos/vídeos → tenta praticar → continua dependente do intérprete | Interesse, insegurança, motivação, dúvida, frustração | Ferramenta prática e interativa para professores aprenderem e receberem feedback |

Pontos de contato recorrentes: interação presencial, internet/apps/cursos online, vídeos, intérprete/familiar, sala de aula, saúde, trabalho.

## Como isto se encaixa no escopo atual

As três jornadas convergem na dor "**não sei se estou fazendo o sinal certo**", que pede *avaliação da execução do usuário*. Isso é do escopo antigo. O escopo atual (texto → Libras) atende outra parte das jornadas:

- **"Demonstração"** — a pesquisa com usuários citou "prática + correção + demonstração" como necessidades; um avatar que mostra o sinal cobre a demonstração.
- **Helena** — pode usar a ferramenta para saber *como se sinaliza* uma palavra/frase que quer dizer ao aluno (com a ressalva do vocabulário de 20 sinais).
- **Matheus** — continua como beneficiário indireto.
- **Júlia** — o fluxo de aprendizado ("vejo o sinal") existe; o de correção ("recebo feedback") não.

**[a confirmar com a equipe]** se as personas serão refeitas/ajustadas para o escopo novo. Até lá, tratar a ficha de cada persona como contexto de usuário, não como especificação de funcionalidade.

Requisito transversal que vale para qualquer escopo: **interface simples e guiada** (Helena) e linguagem acessível — o público inclui pessoas com pouca familiaridade tecnológica e, potencialmente, pessoas surdas com português escrito como segunda língua (ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md)).
