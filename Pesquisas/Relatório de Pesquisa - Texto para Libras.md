# Relatório de Pesquisa: Como Converter Texto em Português para Libras

(Grupo 10)

## 1. Contexto e Pergunta de Pesquisa

O Sinaliza recebe um texto em português e o mostra como uma sequência de sinais de Libras, executada pelo avatar do VLibras. Na apresentação do andamento do projeto, o orientador questionou a etapa que transforma o texto em sinais. Hoje ela funciona por palavras-chave:

1. O texto é dividido em palavras e expressões de até três palavras (ex.: "dor de cabeça", "por favor").
2. São descartados artigos, preposições, conjunções e os verbos ser e estar.
3. Cada palavra restante é reduzida à forma de dicionário (lematização: "comprando" → "comprar").
4. Cada forma é associada a uma glosa (o nome do sinal), e os sinais são tocados **na ordem do texto em português**.

● **Pergunta do orientador:** quebrar o texto em palavras-chave é de fato a melhor forma de fazer essa conversão, ou existe uma forma melhor? Como grupo, temos a responsabilidade de não ensinar Libras de forma errada.

● **Objetivo desta pesquisa:** levantar, com base em estudos publicados, (a) o que a linguística da Libras diz sobre a conversão palavra por palavra, (b) como os sistemas existentes fazem essa conversão, (c) como as pessoas surdas avaliam esses sistemas e (d) qual método o Sinaliza deve adotar.

## 2. Metodologia da Pesquisa

● **Frentes investigadas:** a pesquisa foi dividida em cinco frentes independentes:

1. Linguística da Libras e notação por glosas;
2. Sistemas brasileiros de conversão português → Libras (VLibras, Hand Talk e trabalhos acadêmicos);
3. Estado da arte internacional em tradução de texto para línguas de sinais;
4. Avaliação desses sistemas por pessoas surdas e posicionamentos éticos da comunidade;
5. Caminhos práticos de implementação (ferramentas, dados, licenças e métodos de avaliação).

● **Fontes consultadas:** artigos científicos (SBC OpenLib, ACL Anthology, arXiv, SciELO e periódicos de linguística), dissertações e teses, legislação brasileira (Planalto), declarações de entidades internacionais de surdos, o código-fonte aberto do VLibras e as fichas técnicas de bases de dados públicas.

● **Critério de confiabilidade:** cada afirmação foi associada à sua fonte. Quando a obra original não pôde ser lida e a informação veio de um autor que a cita, a referência aparece com *apud*. As obras que ainda precisam ser conferidas no original estão listadas na seção 8.

● **Período:** outubro de 2026.

## 3. Fundamentação: a Libras como Língua

### 3.1. A Libras tem gramática própria

A Lei nº 10.436/2002 reconhece a Libras como sistema linguístico de natureza visual-motora, "com estrutura gramatical própria" (BRASIL, 2002). A literatura descreve essa gramática em quatro dimensões que a conversão palavra por palavra não alcança:

● **Ordem das palavras.** A ordem básica proposta para a Libras é Sujeito-Verbo-Objeto (SVO), mas ela é flexível. Topicalização, foco, perguntas e verbos com concordância alteram essa ordem, e essas construções vêm acompanhadas de marcas não manuais; sem elas, "as construções são consideradas agramaticais" (QUADROS; KARNOPP, 2004, p. 142 *apud* SALLES, 2006). Exemplos glosados pelas autoras mostram o que a ordem do português não reproduz: "CERCA GATO SENTAR DORMIR-NA-CERCA", com o local antes da figura, e "JOÃO TELA PINTAR-PINCEL", com o instrumento incorporado ao verbo e sem sinal para "com" (QUADROS; KARNOPP, 2004, p. 208-209 *apud* BENASSI et al., 2013).

● **Uso do espaço.** Os referentes são posicionados em pontos do espaço à frente de quem sinaliza, e os pronomes e verbos com concordância se movem entre esses pontos; para as autoras, o estabelecimento nominal e o sistema pronominal "são fundamentais para as relações sintáticas" (QUADROS; KARNOPP, 2004, p. 127 *apud* SALLES, 2006). Classificadores e descrições imagéticas descrevem forma, local e movimento, e tiveram "alta produtividade" em todas as narrativas analisadas do Corpus de Libras (LUCHI; QUADROS, 2024).

● **Expressões não manuais.** Expressões faciais e movimentos de cabeça e corpo marcam o tipo de frase (pergunta, afirmação), tópico, foco, negação, grau e aspecto (QUADROS; KARNOPP, 2004 *apud* SALLES, 2006). Paiva et al. (2018) mostram que "O professor teve paciência com o aluno" é glosado como PROFESSOR TER PACIÊNCIA ALUN@, enquanto "O professor teve muita paciência com o aluno" se torna PROFESSOR PACIÊNCIA-MUIT@ TER ALUN@: a intensidade vira um sinal modificado com expressão facial, e a posição do verbo muda.

● **Tempo e palavras funcionais.** A Libras é descrita como língua sem flexão de tempo no verbo: o tempo é expresso por advérbios e expressões temporais (FIGUEIREDO, 2020). Ela também não tem artigos, preposições nem verbos de ligação como sinais independentes (BENASSI et al., 2013). Isso não significa uma gramática simplificada: "esses mecanismos são discursivos e espaciais, estando incorporados ao movimento ou em referentes espaciais" (FERNANDES, 2012 *apud* STREIECHEN; KRAUSE-LEMKE, 2014).

A tabela abaixo resume o que o método atual faz com cada fenômeno:

| Fenômeno | O que acontece em Libras (fonte) | O que o método por palavras-chave faz |
|---|---|---|
| Artigos, preposições, ser/estar | Não são sinais; a função passa para o espaço e o movimento (Benassi et al., 2013; Fernandes, 2012 *apud* Streiechen; Krause-Lemke, 2014) | Remove as palavras, mas não transfere a função delas |
| Ordem da frase | SVO flexível, alterada por tópico, foco e perguntas (Quadros; Karnopp, 2004 *apud* Salles, 2006) | Mantém sempre a ordem do português |
| Verbos com concordância | O verbo se move entre os pontos de quem age e de quem recebe (Quadros; Karnopp, 2004 *apud* Salles, 2006) | Toca a forma de dicionário do verbo |
| Pergunta e negação | Marcadas por expressão facial e, na negação, por incorporação ao verbo (Quadros; Karnopp, 2004 *apud* Salles, 2006) | Não marca; a pergunta pode parecer uma afirmação |
| Intensidade | Sinal modificado com expressão facial (Paiva et al., 2018) | Toca "muito" como sinal separado, na ordem do português |
| Tempo verbal | Sem flexão; marcado por advérbios (Figueiredo, 2020) | A lematização já usa o infinitivo, o que é coerente |

### 3.2. Português sinalizado não é Libras

A literatura brasileira tem um nome para a prática de usar sinais da Libras na estrutura do português: **português sinalizado**, característico da Comunicação Total. A primeira regra que Rabelo (1992) descreve para ele é que "a ordem das palavras nas frases mantém a mesma estrutura das do Português", e Goldfeld (1997) o define como "o léxico da língua de sinais submetido à gramática da língua oral", registrando que a educação de surdos nesse modelo "continuou resultando em fracassos" (RABELO, 1992; GOLDFELD, 1997 *apud* OLIVEIRA; FIGUEIREDO, 2017). Ao avaliar tradutores automáticos com crianças surdas, Colling e Boscarioli (2014) atribuem a baixa compreensão ao formato "mais associado ao português sinalizado que a Libras efetivamente" e lembram que esse modelo é "há tempos, bastante refutado pela comunidade surda".

Pelas definições dessas fontes, a saída atual do Sinaliza é um **português sinalizado telegráfico**: usa o vocabulário da Libras, mantém a ordem do português, remove os conectivos e não reproduz a gramática espacial nem as expressões não manuais.

### 3.3. Glosas: uma notação útil, mas incompleta

Glosa é a palavra do português, escrita em maiúsculas, usada para nomear um sinal (ex.: CASA, PROFESSOR). As convenções brasileiras incluem maiúsculas, hífen para sinais compostos de várias palavras, verbos no infinitivo e @ no lugar da marca de gênero (FERREIRA-BRITO, 1995 *apud* PAIVA et al., 2018). Mas a glosa é "nada mais do que nomes convencionalmente associados aos sinais" (McCLEARY; VIOTTI, 2007 *apud* LEITE et al., 2022). Leite et al. (2022) falam numa "tirania das glosas": a glosagem enviesa a semântica, dirige a atenção para palavras isoladas do português e só registra expressões não manuais com marcas adicionais.

No plano internacional, Müller et al. (2023) mostram que "uma sequência linear de glosas não é uma representação adequada de um enunciado sinalizado", porque perde de forma irrecuperável as expressões não manuais, o uso do espaço e as referências do discurso. Ainda assim, como o avatar do VLibras recebe glosas, a glosa continua sendo a interface do Sinaliza. A pergunta passa a ser **quão rica** é a glosa enviada ao avatar.

### 3.4. Marco legal

● **Lei nº 10.436/2002:** reconhece a Libras como língua com gramática própria e estabelece que ela não substitui a modalidade escrita do português (BRASIL, 2002).

● **Decreto nº 5.626/2005:** dá às pessoas surdas prioridade na formação para o ensino de Libras e define o português como segunda língua para surdos (BRASIL, 2005).

● **Lei nº 14.191/2021:** insere na LDB a educação bilíngue de surdos, com a Libras como primeira língua (BRASIL, 2021).

● **Lei Brasileira de Inclusão (Lei nº 13.146/2015):** garante a oferta de educação bilíngue e de tradutores e intérpretes de Libras (BRASIL, 2015).

Essas normas não regulam software, mas tratam Libras e português como línguas distintas. Apresentar a estrutura do português como se fosse Libras vai contra esse entendimento.

## 4. Como os Sistemas Brasileiros Fazem a Conversão

### 4.1. VLibras: três gerações de método

O VLibras, desenvolvido pelo LAViD/UFPB, é o único tradutor português → Libras em produção cujo método pode ser conferido, porque seu código é aberto (licença LGPL-3.0). A pesquisa identificou três gerações:

| Geração | Período | Método | Evidência |
|---|---|---|---|
| 1. Regras | 2012-2017 | Classificação gramatical das palavras, dicionário de 295.451 entradas, verbos no infinitivo, datilologia para nomes próprios e regras de transferência escritas por especialistas (11 regras no artigo; 104 regras morfológicas e 46 sintáticas no código) | BLEU-4 de 12% e WER de 75,3% contra glosas de intérpretes. Com 20 surdos, 79,38% de acerto em questões de compreensão com a trilha em Libras, contra 25,63% com legendas (ARAÚJO et al., 2014) |
| 2. Regras + rede neural | 2019 em diante | Uma etapa de regras gera a "glosa-regra" (remove artigos e algumas preposições, lematiza, troca sinônimos e expressões compostas). Uma rede neural (fairseq LightConv), treinada com pares glosa-regra → glosa de intérprete, corrige ordem, negação, intensidade, verbos direcionais e homônimos | Código dos pacotes `vlibras-translate` e `vlibras-deeplearning` (PyPI) |
| 3. + Refinamento por LLM | 2026 | Refinamento opcional da glosa por modelo de linguagem (gpt-4o por padrão, desligado por padrão), acionado só quando a glosa tem verbo direcional ou palavra desambiguada | Código do repositório oficial `vlibras-translator-text-core` |

O ponto central para o Sinaliza: **a etapa de regras da geração 2 do VLibras faz praticamente o mesmo que o Sinaliza faz hoje.** No VLibras, porém, ela é só o ponto de partida; quem transforma o resultado em glosa de Libras é a rede neural treinada com glosas de intérpretes. Há também uma diferença: o VLibras não remove ser e estar de forma incondicional, enquanto o Sinaliza remove sempre.

### 4.2. O corpus de glosas de intérpretes (VLibrasBD)

O recurso mais aproveitável encontrado é o corpus **pt-br2libras-gloss**, ou VLibrasBD (LIMA et al., 2025a; 2025b):

● **Tamanho:** 127.349 pares de frase em português e glosa em Libras (72.312 de domínio geral e 55.037 de textos do gov.br).

● **Produção:** glosado à mão por intérpretes certificados (dez intérpretes por 12 meses e quatro por cerca de 20 meses), a partir de frases do CETENFolha, da Wikipédia e do gov.br. Segundo os autores, "nenhuma ferramenta automática foi usada para alinhamento".

● **Licença:** CC BY-SA 4.0 (uso permitido com atribuição e compartilhamento pela mesma licença).

● **Notação:** definida em relatório técnico próprio (LIMA et al., 2025c) e feita para que o player do VLibras, o mesmo avatar usado pelo Sinaliza, decodifique as glosas. Ela marca homônimos (BANCO&DINHEIRO), tipo de frase ([PONTO], [INTERROGAÇÃO], [EXCLAMAÇÃO]), compostos (BOM_DIA), verbos direcionais (1S_PEDIR_2S), negação incorporada (NÃO_) e intensidade ((+) e (-)).

● **Exemplos do corpus:** "Tenho mais um favor para pedir." → TER FAVOR 1S_PEDIR_2S [PONTO]; "O banco é longe daqui?" → BANCO&DINHEIRO LONGE [INTERROGAÇÃO]. As frases em português têm, em média, 12,83 palavras, e as glosas, 7,61 sinais.

● **Limitações declaradas pelos autores:** o corpus cobre apenas sinais manuais lexicais, não trata expressões não manuais nem tempo, e tem viés de textos governamentais.

### 4.3. Hand Talk e outros sistemas comerciais

A Hand Talk não publica documentação técnica do seu método. A única descrição pública é a da loja de aplicativos, que menciona inteligência artificial e "mais de 38 mil palavras validadas por especialistas" (HAND TALK, 2026). A empresa adquiriu a ProDeaf em 2018. Para Rybená, Falibras e outros, também não foi encontrada documentação técnica.

### 4.4. Pesquisa acadêmica brasileira recente

● De Martino e Christinele (2024) ajustaram modelos de tradução pré-treinados (OPUS-MT) com 4.553 pares de português e glosa. O melhor resultado foi 24,06 BLEU; os mesmos modelos treinados do zero ficaram abaixo de 1,85 BLEU. Cerca de 10% das glosas geradas não existiam no vocabulário de treino, o que é um problema direto para avatares que dependem de um dicionário de sinais.

● A equipe do VLibras na UFPB também estuda técnicas de aumento de dados para a tradução português-Libras (SILVA et al., 2024).

● **Não foi encontrado estudo publicado que use modelos de linguagem (LLMs) para gerar glosa de Libras a partir de texto com avaliação por métricas.**

## 5. Estado da Arte Internacional

### 5.1. Famílias de abordagem

A literatura internacional pode ser organizada pelo que fica entre o texto e o sinal. A tabela resume as famílias de abordagem encontradas:

| Abordagem | Como funciona | Exemplos | O que a evidência mostra |
|---|---|---|---|
| Palavra → sinal (dicionário) | Cada palavra vira um sinal, na ordem da língua oral | Primeiras versões do ViSiCAST (Reino Unido) | Abandonada cedo: "não é a forma preferida em que os surdos pré-linguais desejam ver a língua de sinais" (BANGHAM et al., 2000) |
| Regras de transferência | Análise sintática do texto e regras escritas por especialistas | ViSiCAST, TESSA, VLibras geração 1 | Funciona em domínios fechados; o TESSA só funcionou porque se limitou a frases fixas de atendimento (COX et al., 2000) |
| Tradução estatística texto → glosa | Modelo probabilístico treinado em pares texto-glosa | San-Segundo et al. (2008) para língua de sinais espanhola | Superada por regras de domínio e por redes neurais |
| Tradução neural texto → glosa | Rede neural sequência-para-sequência treinada em pares texto-glosa | Camgöz et al. (2018); Spoken2Sign (ZUO et al., 2024); VLibras geração 2 | Abordagem dominante quando há corpus; exige milhares de pares |
| Regras + neural | Regras geram dados ou uma glosa inicial, e a rede neural refina | Chiruzzo et al. (2022); VLibras geração 2 | Melhor resultado em cenários com poucos dados (seção 5) |
| Texto → movimento sem glosa | Gera a pose do corpo direto a partir do texto | Progressive Transformers (SAUNDERS et al., 2020); SignLLM (FANG et al., 2024) | Exige grandes corpora de vídeo; não serve para avatares baseados em dicionário de sinais |
| LLMs gerando glosas | Modelo de linguagem com instruções e exemplos | Protótipo para ASL com GPT-4o (2024); K-RSL (KOZHIRBAYEV; IMASHEV, 2026) | Promissor para reduzir anotação, mas limitado pela gramática própria e pela falta de dados |

Os sistemas que animam avatares a partir de um dicionário de sinais, como o Spoken2Sign (ZUO et al., 2024) e o modelo aberto de Moryossef et al. (2023), continuam usando o caminho texto → glosa → dicionário → avatar. Para o Sinaliza, que usa o player do VLibras, o ganho está na etapa texto → glosa.

### 5.2. A evidência mais próxima do caso do Sinaliza

Chiruzzo et al. (2022) testaram, para espanhol → língua de sinais espanhola (LSE), um conjunto de regras quase idêntico ao do Sinaliza: remover determinantes e algumas preposições e escrever as demais palavras como lema em maiúsculas.

● Com um corpus de 416 pares, essas regras obtiveram 29,73 BLEU, contra 29,94 de uma rede neural treinada só nesses pares: **com poucos dados, as palavras-chave empatam com a rede neural.**

● Regras escritas para o domínio (153 regras) chegaram a 57,8 BLEU, contra 49,4 de um modelo estatístico (SAN-SEGUNDO et al., 2008 *apud* CHIRUZZO et al., 2022).

● O melhor resultado veio da combinação: as regras geraram cerca de 400 mil glosas sintéticas, a rede neural foi pré-treinada nelas e depois ajustada nos pares reais. O ganho foi de cerca de 15 pontos, chegando a **58,98 BLEU**.

● Os próprios autores alertam que a regra "palavra vira lema em maiúsculas" fabrica glosas que não existem na língua de sinais: menos de 50% das glosas do corpus estavam no léxico disponível.

Ou seja, a literatura trata a abordagem por palavras-chave como **ponto de partida** para línguas com poucos recursos, e não como resultado final.

### 5.3. Como avaliar sem enganar

Müller et al. (2023) mostram que a avaliação por BLEU é reportada de forma inconsistente: só a forma de dividir o texto em unidades pode fazer o mesmo resultado variar de 25,61 para 10,18. Os autores recomendam usar o SacreBLEU com a tokenização desligada para glosas, informar a configuração usada e discutir as limitações. Eles também lembram que glosas de corpora diferentes não são comparáveis entre si.

## 6. Avaliação por Pessoas Surdas e Posicionamentos da Comunidade

### 6.1. Estudos empíricos no Brasil

Os estudos brasileiros encontrados que avaliaram tradutores automáticos com pessoas surdas ou intérpretes estão resumidos abaixo:

| Estudo | Participantes | Principal achado |
|---|---|---|
| Colling e Boscarioli (2014) | 6 intérpretes e 2 crianças surdas; Rybená, Hand Talk e ProDeaf | Compreensão das frases entre 2,5% e 30%, atribuída ao formato de português sinalizado |
| Melquíades Macêdo et al. (2025) | 5 surdos, 5 ouvintes leigos e 5 especialistas; VLibrasWidget | Nota de usabilidade (SUS) dos surdos foi 54, abaixo do limiar de 68, contra 84 e 91 dos ouvintes; só os surdos detectaram sinais incorretos |
| Moraes et al. (2018) | 5 surdos, com rastreamento ocular | Queixas de excesso de datilologia, sinais fora de contexto e avatar sem expressão |
| Rocha e Melgaço (2018) | 87 respondentes (24,1% surdos) | Sinais na mesma ordem do português escrito, o que distorce o sentido; falta de expressão facial |
| Corrêa, Gomes e Ribeiro (2017) | Análise de 38 palavras homônimas | Tradução errada pode levar o aprendiz a internalizar parâmetros linguísticos de forma equivocada |
| Bedana et al. (2019) | Edital do Enem 2018 | O avatar não tem maturidade para contextos críticos |

As amostras são pequenas, mas os estudos apontam na mesma direção: os erros mais citados são a **ordem do português**, a **falta de expressão facial**, os **homônimos** e os **verbos direcionais**. Melquíades Macêdo et al. (2025) também mostram que apenas usuários fluentes percebem os erros de sinalização, o que significa que um grupo sem fluência em Libras não consegue avaliar a própria saída sozinho.

Os estudos também registram o valor dessas ferramentas: pessoas surdas as usam sobretudo como dicionário e apoio de vocabulário, e uma pesquisadora surda recomenda o avatar como ferramenta auxiliar quando não há intérprete (DIAS, 2018 *apud* JORNAL DA UNICAMP, 2018).

### 6.2. Posição da Federação Mundial dos Surdos (WFD) e da WASLI

A declaração conjunta da WFD e da Associação Mundial de Intérpretes de Língua de Sinais (WASLI) é a posição internacional de referência sobre avatares (WFD; WASLI, 2018):

● Afirma que uma tradução exata palavra a sinal "não é possível" (*"a word-to-sign exact translation is not possible"*).

● Desaconselha avatares para conteúdo ao vivo, complexo ou de grande importância, e aceita seu uso para informação estática e pré-gravada, desde que pessoas surdas tenham participado da avaliação das frases sinalizadas.

● Desaconselha escolher um único sinal para cada palavra, porque as variantes devem ser registradas.

### 6.3. Ética no desenvolvimento de tecnologia para línguas de sinais

● De Meulder (2021) recomenda que essas tecnologias sejam criadas junto com pessoas surdas, com pesquisadores surdos na liderança ou coliderança, e considera justificável começar por domínios restritos e previsíveis. A autora alerta que pessoas surdas tendem a dar respostas socialmente desejáveis ao avaliar tecnologias feitas "para" elas.

● Desai et al. (2024), uma equipe inteiramente surda, revisaram 101 artigos e encontraram 51 que usam glosas, muitas vezes tratadas como se fossem tradução. Os autores pedem transparência sobre a equipe, os sinalizantes e as convenções de glosa usadas.

## 7. Comparação das Abordagens para o Sinaliza

A tabela compara as opções viáveis para o projeto. O esforço e o risco são estimativas do grupo.

| Abordagem | Fidelidade à Libras | Esforço | Dados necessários | Principal risco |
|---|---|---|---|---|
| Palavras-chave (atual) | Baixa: produz português sinalizado | Já implementada | Tabela de sinais | Apresentar português sinalizado como Libras |
| Regras escritas pelo grupo | Média em frases simples | Médio | Regras com fonte | Ninguém no grupo sabe Libras para escrever ou conferir as regras |
| Usar o tradutor do VLibras como está | Média: a do VLibras | Baixo | Nenhum | Herdar os erros documentados do VLibras sem contribuição própria |
| **Regras + modelo neural treinado no corpus de intérpretes** | **A maior entre as viáveis: aprende com glosas humanas** | Alto | VLibrasBD (127 mil pares, aberto) | Glosas inexistentes no dicionário (mitigável por filtro) e falta de validação por surdos |
| LLM com exemplos | Desconhecida para Libras | Baixo para protótipo | Exemplos do corpus | Saída plausível e errada, sem estudo de erro publicado |
| Texto → movimento sem glosa | Potencialmente alta | Muito alto | Grandes corpora de vídeo | Inviável com os dados disponíveis |

## 8. Limitações desta Pesquisa

● **Obras de base lidas por citação.** As obras de Quadros e Karnopp (2004), Ferreira-Brito (1995), Felipe (*Libras em Contexto*) e Gesser (2009) não foram lidas no original; o conteúdo veio de resenhas e artigos que as citam com página. Antes do relatório final, o grupo deve conferir em biblioteca as páginas citadas.

● **Divergência entre fontes.** Streiechen e Krause-Lemke (2014) afirmam que os verbos em Libras não mudam com tempo e pessoa, enquanto Quadros e Karnopp (2004) descrevem verbos com concordância de pessoa. Este relatório adota a leitura de que a primeira afirmação vale para tempo e para verbos sem concordância, o que é coerente com a notação 1S_PEDIR_2S do corpus de intérpretes.

● **Evidência empírica pequena.** O dado de compreensão de 2,5% a 30% vem de duas crianças. Não foi encontrado estudo com surdos adultos que compare, no mesmo avatar, saída por palavras-chave, por regras e por modelo neural.

● **Sistemas fechados.** A Hand Talk não publica seu método, e a arquitetura e as métricas do modelo neural do VLibras em produção não são públicas.

● **Player do VLibras.** Não foi encontrada documentação de quais marcações da notação (como [INTERROGAÇÃO], NÃO_ e (+)) o player interpreta; isso precisa ser testado.

● **Pequena divergência no corpus.** O artigo do VLibrasBD informa 55.037 pares de textos do governo no texto e 55.047 na Tabela 5.

## 9. Conclusão: o Caminho Escolhido pelo Sinaliza

● **Resposta à pergunta do orientador.**

Quebrar o texto em palavras-chave não é a melhor forma de converter português em Libras. Pelas definições da literatura, o resultado é português sinalizado: sinais da Libras na estrutura do português, sem o uso do espaço e sem as expressões não manuais, um modelo refutado pela comunidade surda e associado a baixa compreensão. A pesquisa também mostra, porém, que a análise por palavras é um **ponto de partida legítimo**: é exatamente a primeira etapa do VLibras e o baseline usado na literatura para línguas com poucos recursos. O problema está em parar nela.

● **Método escolhido: conversão em duas etapas, com regras seguidas de um modelo neural treinado em glosas de intérpretes.**

É o mesmo método da geração 2 do VLibras, e o que obteve os melhores resultados nos estudos encontrados:

1. **Análise do texto e regras:** com uma biblioteca de processamento de português (spaCy), o texto é dividido em frases, as palavras são lematizadas, e são identificados expressões compostas, nomes próprios, negações e perguntas. O resultado é uma "glosa-regra", próxima do que o Sinaliza já produz hoje.

2. **Modelo neural treinado no corpus de intérpretes:** um modelo sequência-para-sequência pré-treinado em português (PTT5 ou ByT5) é ajustado com os 127 mil pares do VLibrasBD. Ele transforma o texto na glosa da Libras, aprendendo com os intérpretes a ordem, a negação, a intensidade, os verbos direcionais e a desambiguação de homônimos.

3. **Filtro pelo dicionário do avatar:** a saída é restrita às glosas que existem no dicionário do player do VLibras. Nomes próprios e palavras sem sinal são soletrados em datilologia, evitando glosas inventadas pelo modelo (cerca de 10% em De Martino e Christinele, 2024).

4. **Avatar:** a glosa final é enviada ao player do VLibras, que já interpreta a notação do corpus.

● **Por que esse método.**

○ O VLibras, sistema brasileiro em produção, partiu do mesmo ponto em que o Sinaliza está e evoluiu para esse método (ARAÚJO et al., 2014; código dos pacotes `vlibras-translate` e `vlibras-deeplearning`).

○ Em cenários com poucos dados, combinar regras e rede neural superou tanto as regras sozinhas quanto a rede neural sozinha, com ganho de cerca de 15 pontos de BLEU (CHIRUZZO et al., 2022).

○ Ajustar um modelo pré-treinado funciona com poucos pares de português e glosa de Libras, enquanto treinar do zero não funciona (DE MARTINO; CHRISTINELE, 2024).

○ O corpus VLibrasBD é aberto, foi glosado à mão por intérpretes e usa a notação do mesmo avatar usado pelo Sinaliza (LIMA et al., 2025a; 2025c).

○ O método dá ao Sinaliza um componente de Machine Learning com avaliação objetiva, em uma etapa que define a qualidade linguística da saída.

● **Como o método será avaliado.**

○ Avaliação automática: em um conjunto de frases do corpus separado do treino, usando SacreBLEU com a tokenização desligada, chrF e WER, como recomendam Müller et al. (2023), e comparando três sistemas: o método atual por palavras-chave, o tradutor do VLibras e o modelo do Sinaliza. Esses números medem a proximidade às glosas dos intérpretes, não a aprovação por pessoas surdas.

○ Testes por fenômeno: frases com pergunta, negação, intensidade, verbos direcionais e homônimos, os erros mais citados nos estudos com surdos (seção 6).

○ Validação humana: avaliação de uma amostra das saídas por pelo menos uma pessoa surda fluente e um intérprete, seguindo a recomendação da WFD/WASLI (2018) e de De Meulder (2021).

● **O que o método não resolve.**

A glosa não carrega todo o uso do espaço nem todas as expressões não manuais; essa parte depende do player do VLibras. Enquanto a saída não for validada por pessoas surdas, a interface do Sinaliza informará que se trata de uma sequência de sinais gerada automaticamente e ainda não revisada por surdos.

● **Próximos passos.**

1. Baixar o VLibrasBD e medir quantas de suas glosas existem no dicionário do player do VLibras.
2. Testar no player quais marcações da notação ele interpreta.
3. Trocar a análise do texto pelo spaCy e montar a etapa de regras.
4. Ajustar o modelo no corpus e avaliá-lo contra os dois baselines.
5. Buscar uma pessoa surda fluente e um intérprete para a validação.

## Referências

As obras citadas por meio de outra (*apud*), como Quadros e Karnopp (2004), Ferreira-Brito (1995), Rabelo (1992), Goldfeld (1997), Fernandes (2012), McCleary e Viotti (2007), San-Segundo et al. (2008) e Dias (2018), aparecem no texto com a indicação da obra consultada; a lista abaixo traz apenas as obras consultadas diretamente.

ARAÚJO, Tiago Maritan U. de et al. An approach to generate and embed sign language video tracks into multimedia contents. *Information Sciences*, v. 281, p. 762-780, 2014. DOI: 10.1016/j.ins.2014.04.008. Disponível em: https://transforma.fbb.org.br/storage/socialtecnologies/482/files/Ins_publicado.pdf. Acesso em: 26 out. 2026.

BANGHAM, J. Andrew et al. *Virtual signing: capture, animation, storage and transmission – an overview of the ViSiCAST project*. Norwich: University of East Anglia, 2000. Disponível em: https://www.visicast.cmp.uea.ac.uk/Papers/iee2000-04PaperBFinal.pdf. Acesso em: 26 out. 2026.

BEDANA, Priscila R. F.; FREITAS, Fernando A.; PERES, Sarajane M.; BARBOSA, Felipe V. Análise de tradução automática português-Libras no contexto do edital do Enem 2018. In: SIMPÓSIO BRASILEIRO DE INFORMÁTICA NA EDUCAÇÃO (SBIE), 30., 2019, Brasília. *Anais* [...]. Porto Alegre: SBC, 2019. p. 1151-1160. Disponível em: https://sol.sbc.org.br/index.php/sbie/article/view/40144. Acesso em: 26 out. 2026.

BENASSI, Claudio Alves et al. Relendo Quadros e Karnopp 2004. *Revista de Letras Norte@mentos*, v. 6, n. 12, p. 133-146, 2013. Disponível em: https://periodicos.unemat.br/index.php/norteamentos/article/download/6881/5413/27807. Acesso em: 26 out. 2026.

BRASIL. Lei nº 10.436, de 24 de abril de 2002. Dispõe sobre a Língua Brasileira de Sinais - Libras e dá outras providências. Brasília, 2002. Disponível em: https://www.planalto.gov.br/ccivil_03/leis/2002/l10436.htm. Acesso em: 26 out. 2026.

BRASIL. Decreto nº 5.626, de 22 de dezembro de 2005. Regulamenta a Lei nº 10.436, de 24 de abril de 2002. Brasília, 2005. Disponível em: https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2005/decreto/d5626.htm. Acesso em: 26 out. 2026.

BRASIL. Lei nº 13.146, de 6 de julho de 2015. Institui a Lei Brasileira de Inclusão da Pessoa com Deficiência. Brasília, 2015. Disponível em: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm. Acesso em: 26 out. 2026.

BRASIL. Lei nº 14.191, de 3 de agosto de 2021. Altera a Lei nº 9.394, de 20 de dezembro de 1996, para dispor sobre a modalidade de educação bilíngue de surdos. Brasília, 2021. Disponível em: https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14191.htm. Acesso em: 26 out. 2026.

CAMGÖZ, Necati Cihan et al. Neural sign language translation. In: IEEE CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION (CVPR), 2018. Disponível em: https://openaccess.thecvf.com/content_cvpr_2018/html/Camgoz_Neural_Sign_Language_CVPR_2018_paper.html. Acesso em: 26 out. 2026.

CHIRUZZO, Luis; McGILL, Euan; EGEA-GÓMEZ, Santiago; SAGGION, Horacio. Translating Spanish into Spanish Sign Language: combining rules and data-driven approaches. In: WORKSHOP ON TECHNOLOGIES FOR MACHINE TRANSLATION OF LOW-RESOURCE LANGUAGES (LoResMT), 5., 2022, Gyeongju. *Proceedings* [...]. ACL, 2022. p. 75-83. Disponível em: https://aclanthology.org/2022.loresmt-1.10/. Acesso em: 26 out. 2026.

COLLING, Juliane; BOSCARIOLI, Clodis. Avaliação de tecnologias de tradução Português-Libras visando o uso no ensino de crianças surdas. *RENOTE – Revista Novas Tecnologias na Educação*, v. 12, n. 2, 2014. Disponível em: https://seer.ufrgs.br/renote/article/download/53550/33053. Acesso em: 26 out. 2026.

CORRÊA, Ygor; GOMES, Rafael Peduzzi; RIBEIRO, Vinicius Gadis. Aplicativos de tradução Português-Libras na educação bilíngue: desafios frente à desambiguação. *RENOTE – Revista Novas Tecnologias na Educação*, v. 15, n. 2, 2017. Disponível em: https://seer.ufrgs.br/index.php/renote/article/view/79277. Acesso em: 26 out. 2026.

COX, Stephen et al. TESSA, a system to aid communication with deaf people. In: ACM CONFERENCE ON ASSISTIVE TECHNOLOGIES (ASSETS), 2000. Disponível em: https://www.visicast.cmp.uea.ac.uk/Papers/Cox-Assets-2000.pdf. Acesso em: 26 out. 2026.

DE MARTINO, José Mario; CHRISTINELE, Dener Stassun. Exploring pre-trained transformers for translating Portuguese text to Brazilian Sign Language. In: INTERNATIONAL CONFERENCE ON COMPUTATIONAL PROCESSING OF PORTUGUESE (PROPOR), 16., 2024, Santiago de Compostela. *Proceedings* [...]. ACL, 2024. v. 1, p. 67-75. Disponível em: https://aclanthology.org/2024.propor-1.7.pdf. Acesso em: 26 out. 2026.

DE MEULDER, Maartje. Is "good enough" good enough? Ethical and responsible development of sign language technologies. In: WORKSHOP ON AUTOMATIC TRANSLATION FOR SIGNED AND SPOKEN LANGUAGES (AT4SSL), 1., 2021. p. 12-22. Disponível em: https://aclanthology.org/2021.mtsummit-at4ssl.2.pdf. Acesso em: 26 out. 2026.

DESAI, Aashaka et al. Systemic biases in sign language AI research: a deaf-led call to reevaluate research agendas. In: LREC-COLING 2024 WORKSHOP ON SIGN LANGUAGE RESOURCES, 2024. p. 54-65. Disponível em: https://arxiv.org/html/2403.02563v1. Acesso em: 26 out. 2026.

FANG, Sen et al. SignLLM: sign language production large language models. arXiv:2405.10718, 2024. Disponível em: https://arxiv.org/abs/2405.10718. Acesso em: 26 out. 2026.

FIGUEIREDO, Lorena Mariano Borges de. *A (não) marcação de tense em língua brasileira de sinais*. Dissertação (Mestrado em Estudos Linguísticos) – Faculdade de Letras, Universidade Federal de Minas Gerais, Belo Horizonte, 2020. Disponível em: https://repositorio.ufmg.br/handle/1843/34287. Acesso em: 26 out. 2026.

HAND TALK. Página do aplicativo Hand Talk na App Store, 2026. Disponível em: https://apps.apple.com/BR/app/id659816995. Acesso em: 26 out. 2026.

JORNAL DA UNICAMP. Avatar é usado por surdos em sala de aula. Campinas, 21 dez. 2018. Disponível em: http://www2.unicamp.br/estatico-2023/ju/noticias/2018/12/21/avatar-e-usado-por-surdos-em-sala-de-aula/. Acesso em: 26 out. 2026.

KOZHIRBAYEV, Zhanibek; IMASHEV, Alfarabi. Evaluating large language models for text-to-gloss translation in Kazakh-Russian Sign Language: a pilot study. In: INTERNATIONAL CONFERENCE ON LANGUAGE RESOURCES AND EVALUATION (LREC), 15., 2026, Palma. *Proceedings* [...]. 2026. p. 9964-9972. Disponível em: https://www.sign-lang.uni-hamburg.de/lrec/pub/2026.lrec-1.781.html. Acesso em: 26 out. 2026.

LEITE, Tarcísio de Arantes et al. Semântica lexical na libras: libertando-se da tirania das glosas. *Revista da ABRALIN*, v. 20, n. 2, p. 1-23, 2022. Disponível em: https://revista.abralin.org/index.php/abralin/article/view/1833. Acesso em: 26 out. 2026.

LIMA, Manuella A. C. B. et al. VLibrasBD: a Brazilian Portuguese–Brazilian Sign Language (Libras) bilingual text dataset designed to support neural machine translation. *Data in Brief*, v. 62, 111911, 2025a. DOI: 10.1016/j.dib.2025.111911. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC12341731/. Acesso em: 26 out. 2026.

LIMA, Manuella et al. *pt-br2libras-gloss*. Versão 2. Mendeley Data, 2025b. DOI: 10.17632/ryj88ckjww.2. Disponível em: https://data.mendeley.com/datasets/ryj88ckjww/2. Acesso em: 26 out. 2026.

LIMA, Manuella et al. *Technical report on description rules for Brazilian Sign Language*. Versão 1.0.0. Zenodo, 2025c. DOI: 10.5281/zenodo.15399589. Disponível em: https://zenodo.org/records/15399589. Acesso em: 26 out. 2026.

LUCHI, Marcos; QUADROS, Ronice Müller de. Descrições imagéticas presentes no Corpus da Libras. *Fórum Linguístico*, 2024. DOI: 10.5007/1984-8412.2024.e94734. Disponível em: https://periodicos.ufsc.br/index.php/forum/article/download/94734/57944/402702. Acesso em: 26 out. 2026.

MELQUÍADES MACÊDO, Thaís; GERMANO, Vinícius; COSTA, Carolina de Melo; AGUIAR, Yuska Paola Costa. Hand-speaking technology: an expert and user-based assessment of the VLibrasWidget. In: SIMPÓSIO BRASILEIRO DE QUALIDADE DE SOFTWARE (SBQS), 24., 2025, São José dos Campos. *Anais* [...]. Porto Alegre: SBC, 2025. p. 326-336. Disponível em: https://sol.sbc.org.br/index.php/sbqs/article/view/39021. Acesso em: 26 out. 2026.

MORAES et al. A usabilidade de avatares de Libras em sites: análise da interação de usuários surdos por meio do rastreador ocular (eye tracking). *Design & Tecnologia*, n. 16, p. 41-51, 2018. DOI: 10.23972/det2018iss16pp41-51. Disponível em: https://ngd.ufsc.br/wp-content/uploads/2019/09/A-usabilidade-de-avatares-de-libras-em-sites-ana%CC%81lise-da-interac%CC%A7a%CC%83o-de-usua%CC%81rios-surdos-por-meio-do-rastreador-ocular-Eye-Tracking.pdf. Acesso em: 26 out. 2026.

MORYOSSEF, Amit et al. An open-source gloss-based baseline for spoken to signed language translation. arXiv:2305.17714, 2023. Disponível em: https://arxiv.org/abs/2305.17714. Acesso em: 26 out. 2026.

MÜLLER, Mathias et al. Considerations for meaningful sign language machine translation based on glosses. In: ANNUAL MEETING OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS (ACL), 61., 2023. p. 682-693. DOI: 10.18653/v1/2023.acl-short.60. Disponível em: https://aclanthology.org/2023.acl-short.60/. Acesso em: 26 out. 2026.

OLIVEIRA, Q. M.; FIGUEIREDO, F. J. Q. Educação dos surdos no Brasil: um percurso histórico e novas perspectivas. *Revista Sinalizar*, v. 2, n. 2, p. 173-196, 2017. Disponível em: https://revistas.ufg.br/revsinal/article/download/50544/24803/211516. Acesso em: 26 out. 2026.

PAIVA, Francisco Aluisio dos Santos; BARBOSA, Plínio Almeida; DE MARTINO, José Mario; WILL, Ackley Dias; OLIVEIRA, Márcia Regina Nepomuceno dos Santos; SILVA, Ivani Rodrigues; XAVIER, André Nogueira. Análise do papel das expressões não manuais na intensificação em libras. *D.E.L.T.A.*, v. 34, n. 4, p. 1135-1158, 2018. Disponível em: https://revistas.pucsp.br/index.php/delta/article/download/40943/27628/114988. Acesso em: 26 out. 2026.

ROCHA, Cleomar; MELGAÇO, Sarah Caetano de. O uso de aplicativos para tradução de Libras. In: ROCHA, Cleomar (org.). *Anais do V Simpósio Internacional de Inovação em Mídias Interativas*. Goiânia: Media Lab/UFG, 2018. Disponível em: https://files.cercomp.ufg.br/weby/up/777/o/4_-_Sarah_Melgaco.pdf. Acesso em: 26 out. 2026.

SALLES, Heloisa Maria Moreira Lima. Resenha de *Língua de sinais brasileira: estudos linguísticos*. *Perspectiva*, Florianópolis, v. 24, n. especial, p. 203-220, 2006. Disponível em: https://periodicos.ufsc.br/index.php/perspectiva/article/download/11262/10758/34273. Acesso em: 26 out. 2026.

SAUNDERS, Ben; CAMGÖZ, Necati Cihan; BOWDEN, Richard. Progressive transformers for end-to-end sign language production. In: EUROPEAN CONFERENCE ON COMPUTER VISION (ECCV), 2020. Disponível em: https://arxiv.org/pdf/2004.14874. Acesso em: 26 out. 2026.

SILVA, Marcos André Bezerra da; LIMA, Manuella Aschoff C. B.; SILVA, Diego Ramon Bezerra da; SOUZA, Daniel Faustino L. de; COSTA, Rostand Edson O.; ARAÚJO, Tiago Maritan U. de. Uma investigação sobre técnicas de data augmentation aplicadas à tradução automática Português-LIBRAS. In: SIMPÓSIO BRASILEIRO DE SISTEMAS MULTIMÍDIA E WEB (WebMedia), 30., 2024, Juiz de Fora. *Anais* [...]. Porto Alegre: SBC, 2024. p. 318-326. DOI: 10.5753/webmedia.2024.241964. Disponível em: https://sol.sbc.org.br/index.php/webmedia/article/view/30327. Acesso em: 26 out. 2026.

STREIECHEN, Eliziane Manosso; KRAUSE-LEMKE, Cibele. Análise da produção escrita de surdos alfabetizados com proposta bilíngue. *Revista Brasileira de Linguística Aplicada*, v. 14, n. 4, p. 957-985, 2014. DOI: 10.1590/1984-639820145557. Disponível em: https://www.redalyc.org/pdf/3398/339832472009.pdf. Acesso em: 26 out. 2026.

VLIBRAS. *vlibras-translate* (versão 1.1.10) e *vlibras-deeplearning* (versão 1.0.9). LAViD/UFPB, licença LGPL-3.0. Python Package Index. Disponível em: https://pypi.org/project/vlibras-translate/ e https://pypi.org/project/vlibras-deeplearning/. Acesso em: 26 out. 2026.

VLIBRAS. *vlibras-translator-text-core*. Repositório GitHub, licença LGPL-3.0, 2026. Disponível em: https://github.com/spbgovbr-vlibras/vlibras-translator-text-core. Acesso em: 26 out. 2026.

WFD – WORLD FEDERATION OF THE DEAF; WASLI – WORLD ASSOCIATION OF SIGN LANGUAGE INTERPRETERS. *WFD and WASLI statement on use of signing avatars*. 14 mar. 2018, atualizada em 14 abr. 2018. Disponível em: https://wasli.org/wp-content/uploads/2023/07/WFD-and-WASLI-Statement-on-Avatar-FINAL-14032018-Updated-14042018-1.pdf. Acesso em: 26 out. 2026.

ZUO, Ronglai et al. A simple baseline for spoken language to sign language translation with 3D avatars. In: EUROPEAN CONFERENCE ON COMPUTER VISION (ECCV), 2024. Disponível em: https://arxiv.org/html/2401.04730v2. Acesso em: 26 out. 2026.

## Declaração de Uso de Inteligência Artificial

Declaro que utilizei a ferramenta de Inteligência Artificial Claude (Anthropic), por meio do Claude Code, neste trabalho para pesquisar fontes na internet, ler e sintetizar os estudos encontrados, redigir o texto do relatório e conferir as referências. O uso ocorreu nas etapas de levantamento bibliográfico, organização e redação do conteúdo, verificação de títulos e autores das referências e formatação deste documento no Google Docs. Não tratei dados pessoais. Revisei criticamente o conteúdo gerado e assumo a responsabilidade integral pela versão final apresentada.
