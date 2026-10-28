# Caminhos práticos para melhorar a etapa texto → glosa do Sinaliza (além de palavras-chave)

Notas de pesquisa (outubro de 2026). Contexto: o pipeline atual tokeniza com regex, junta expressões de até 3 palavras, remove palavras funcionais, lematiza com simplemma, mapeia para ~210 glosas (vocabulário do V-LIBRASIL), aproxima palavras fora do vocabulário por embedding (sempre sinalizado) e mantém a ordem do português. Ninguém da equipe sabe Libras. Nada aqui é regra de Libras validada pela equipe: as afirmações linguísticas são reproduzidas das fontes citadas, e várias só foram vistas em resumo (indicado em cada item).

## 1. Ferramentas de PLN em português para uma etapa de transferência por regras

### Takeaway
Dá para trocar regex + simplemma por um analisador de dependências do português (spaCy `pt_core_news_*` ou Stanza) que já entrega, numa só passada, segmentação de frases, lemas, traços morfológicos (incluindo `Polarity=Neg` e `PronType=Int` do treebank Bosque) e entidades nomeadas (PER/LOC/ORG/MISC) para disparar datilologia. Isso melhora a *análise* do português, mas não diz nada sobre a gramática da Libras: as regras de transferência continuam precisando de fonte linguística.

### Cited Findings
- **spaCy `pt_core_news_sm` 3.7.0**: licença **CC BY-SA 4.0**; treinado em **UD Portuguese Bosque v2.8** + **WikiNER**; componentes `tok2vec, morphologizer, parser, lemmatizer, senter, attribute_ruler, ner` (o `senter` vem desligado por padrão); rótulos de NER `LOC, MISC, ORG, PER`; acurácias publicadas: UPOS 96,24; morfologia 94,71; lema 96,76; UAS/LAS 88,91/84,44; F de entidades 87,98 — [Hugging Face: spacy/pt_core_news_sm](https://huggingface.co/spacy/pt_core_news_sm)
- O spaCy oferece para português apenas `pt_core_news_sm`, `md` e `lg` (os dois últimos com vetores); não há modelo `trf` para português listado — [spaCy Models: Portuguese](https://spacy.io/models/pt)
- **Stanza** (v1.5.1 sobre UD 2.12) tem três pacotes de português com estas pontuações: Bosque (UPOS 97,45; UFeats 96,44; Lemas 98,04; LAS 87,75), CINTIL (97,19; 95,48; 98,56; 80,09) e PetroGold (98,59; 98,51; 99,02; 93,28) — [Stanza Performance](https://stanfordnlp.github.io/stanza/performance.html). Observação: PetroGold é de domínio de petróleo e gás e CINTIL é português europeu, então as notas altas não se transferem automaticamente para frases do dia a dia (inferência, ver abaixo).
- **UD Portuguese Bosque**: licença **CC BY-SA 4.0**; 9.357 frases, 210.958 tokens; gênero notícia; mistura **português europeu (CETEMPúblico) e brasileiro (CETENFolha)**; anota `Polarity=Neg` em *não* e *nada* e `PronType=Int` em *que, quem, qual, quais, quanto(s), quê* — [UD Portuguese Bosque](https://universaldependencies.org/treebanks/pt_bosque/index.html)
- **Porttinari** (NILC/USP): treebank multigênero de português brasileiro em UD; no UD desde a v2.13 com licença **CC BY 4.0**; a parte jornalística revisada tem 8.418 frases; o subcorpus Porttinari-base, revisado manualmente, tem 168.080 tokens, com concordância entre anotadores de 97,8% (POS) e 96,2% (dependências); um artigo do UDW 2026 descreve a inclusão de informação morfológica de negação no Porttinari — [UD Portuguese Porttinari](https://universaldependencies.org/treebanks/pt_porttinari); [STIL 2021: Porttinari](https://sol.sbc.org.br/index.php/stil/article/view/17778); [STIL 2023: The Dawn of the Porttinari](https://sol.sbc.org.br/index.php/stil/article/view/25443) (números via resumo de busca)
- O próprio tradutor do VLibras usa, no pré-processamento, etiquetação morfossintática com **Aelius**, lematização com **cogroo4py**, reconhecimento de nomes próprios e de erros de ortografia (hunspell) — [TestPyPI: vlibras-translate](https://test.pypi.org/pypi/vlibras-translate/json)

### Inferences
- Com `Polarity=Neg` e `PronType=Int` (e o `?` final) o pipeline consegue **detectar** negação e pergunta de forma confiável, mesmo sem saber ainda o que fazer com elas em Libras. Já é útil para a UX: avisar "esta frase é negativa/pergunta; a sequência de sinais não mostra a expressão facial correspondente".
- Entidades `PER`/`LOC`/`ORG` são o gatilho natural para datilologia de nomes próprios, mas o player só toca o que existe no dicionário; datilologia exige que os sinais de letras estejam no pacote local (ver seção 2).
- Para um projeto em Windows, spaCy é a escolha de menor atrito (pip, sem Java). Stanza é mais pesado (PyTorch) mas tem Bosque com UFeats ligeiramente melhor. Trocar simplemma pelo lematizador do spaCy reduz erros em formas verbais irregulares, porque usa o contexto (POS).
- Os tempos verbais do português (`Tense=Past/Fut` no UD) podem ser extraídos, mas a seção 6 mostra que a fonte encontrada descreve a Libras como língua "sem-tense": converter tempo verbal em sinal exige regra com fonte, não inventada.

### Gaps
- **UDPipe** e ferramentas do NILC além do Porttinari (ex.: analisadores treinados nele) não foram verificados nesta rodada.
- Licença do Stanza e disponibilidade de NER em português no Stanza não foram confirmadas (a página de desempenho não informa).
- **Desambiguação de sentido (WSD)** para palavras polissêmicas em português: nenhuma ferramenta pronta foi encontrada nesta pesquisa. A metodologia de Reis (2020) aponta homônimos como ponto fraco de tradutores automáticos para Libras (seção 4), então o problema é real, mas a solução não foi pesquisada.

## 2. Reaproveitar o tradutor do VLibras (código, API, convenções de glosa)

### Takeaway
O tradutor de texto do VLibras é software livre (**LGPL-3.0**) e instalável via pip (`vlibras-translate`, função `rule_translation`), mas depende de Java 17 e hunspell (marcado como "Linux only"), o que no Windows significa WSL/Docker. Não encontrei documentação nem termos de uso de um endpoint público de tradução. A vantagem estrutural é que a saída do VLibras usa as mesmas convenções do dicionário que o player do Sinaliza já toca.

### Cited Findings
- Organização **spbgovbr-vlibras** no GitHub: `vlibras-translator-text-core`, `vlibras-translator-api`, `vlibras-player-webjs`, `vlibras-web-browsers`, `vlibras-dictionary-api`, `vlibras-portal` etc., todos com licença **LGPL-3.0** (alguns repositórios de dicionário/libraske sem licença declarada) — [GitHub API: repos spbgovbr-vlibras](https://api.github.com/orgs/spbgovbr-vlibras/repos?per_page=100)
- **`vlibras-translate`** (pacote Python do LAViD-UFPB, autor Caio Moraes): resumo "VLibras (LAViD-UFPB) translation module for translating brazilian portuguese to LIBRAS"; campo de licença vazio, mas o classificador e o README declaram **LGPLv3**; versão estável 1.3.3 (pré-release 1.3.4rc2); dependências `nltk, unidecode, pygtrie, psutil, interruptingcow, loguru, cogroo4py==0.5.1, hunspell (Linux only)` e extra opcional `vlibras-deeplearning>=1.4.0`; pré-requisitos Java 17, Hunspell (`libhunspell-dev`), Cython, Python 3.8+ — [TestPyPI: vlibras-translate](https://test.pypi.org/pypi/vlibras-translate/json)
- Exemplo do README: `Translation().rule_translation('Maria comprou por três parcelas de 35,50 reais naquela loja.')` → `MARIA COMPRAR POR 3 PARCELA 35 VÍRGULA 50 REAL AQUELE LOJA [PONTO]` (verbo lematizado, plural removido, número em dígitos, vírgula decimal como `VÍRGULA`, pontuação final como `[PONTO]`, preposição "por" mantida) — [TestPyPI: vlibras-translate](https://test.pypi.org/pypi/vlibras-translate/json)
- **`vlibras-translator-text-core`** (v2.5.0, selo "VLibras suite 2026", LGPL-3.0): worker Python que consome a fila RabbitMQ `translate.to_text`; usa `vlibras-translate 1.3.4rc1` e `vlibras-deeplearning 1.4.1rc1`; tem etapas opcionais desligadas por padrão `ENABLE_DL_TRANSLATION` e `ENABLE_REFINEMENT`, esta última um **refinador por LLM** configurado por `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o` — [GitHub: vlibras-translator-text-core](https://github.com/spbgovbr-vlibras/vlibras-translator-text-core)
- **`vlibras-translator-api`** (v2.4.0, LGPL-3.0): API Node.js que exige MongoDB, RabbitMQ, Redis e o text core implantado antes; documentação só em `localhost:3000/docs`; o README não cita nenhum endpoint público — [GitHub: vlibras-translator-api](https://github.com/spbgovbr-vlibras/vlibras-translator-api)
- Arquitetura histórica: o VLibras faz tradução **por interlíngua, sendo a glosa a interlíngua**, aplicando primeiro regras de transferência morfossintática — [ACM WebMedia 2019: Analysis of Rule-Based Machine Translation and Neural Machine Translation](https://dl.acm.org/doi/10.1145/3323503.3360305) (via trecho de busca; PDF bloqueado); código de 2015 mostra o módulo Python **PortGlosa** chamado de C++ e carregando Aelius — [softwarepublico.gov.br: py_tradutor.cpp](https://softwarepublico.gov.br/gitlab/vlibras/vlibras-desktop/raw/548a87f822435d58055aa009b4d9a6fe1f7ba4ea/src/py_tradutor.cpp)
- Plano de trabalho do MDH descreve o **VLibras Tradutor** como baseado em aprendizado profundo, treinado com corpus bilíngue Português–Glosa, com meta de expansão de 50.000 frases com apoio de linguistas e intérpretes de Libras — [gov.br/MDH: Plano de Trabalho SEI 3061631](https://www.gov.br/mdh/pt-br/acesso-a-informacao/convenios-e-transferencias/SEI_MDH3061631PlanodeTrabalho.pdf) (via resumo de busca)
- O widget (`vlibras-web-browsers`, LGPL-3.0) tem modos de build com links de "dth – homologação", "ovh" e produção, sem nomes de host no README — [GitHub: vlibras-web-browsers](https://github.com/spbgovbr-vlibras/vlibras-web-browsers)
- No Sinaliza, o player recebe a glosa pela mensagem Unity `PlayerManager.playNow(gloss)`; sinais de várias palavras usam `_` (ex.: `CADEIRA_DE_RODAS`); o comentário do código registra que "o tradutor de texto do VLibras não é usado" — `Sinaliza/web/src/vlibras.ts` (código local); os sinais vêm do dicionário público `dicionario2-dth.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/` e não têm licença de redistribuição — `Sinaliza/docs/creditos-e-licencas.md` (local)
- Avaliação de 2025 do VLibrasWidget (especialistas + usuários surdos e ouvintes) encontrou 28 problemas de interface/interação (1 alto, 8 médios, 10 baixos, 9 cosméticos) — [SBQS 2025: Hand-Speaking Technology](https://sol.sbc.org.br/index.php/sbqs/article/view/39021)

### Inferences
- **Licença**: LGPL-3.0 permite usar `vlibras-translate` como biblioteca num backend FastAPI sem abrir o código do Sinaliza, desde que se preserve o aviso de licença e a possibilidade de substituir a biblioteca (é o mesmo regime do player já usado). Isso não cobre o *dicionário de sinais*, que segue sem licença de redistribuição.
- **Ganho real**: a glosa do VLibras sai nos nomes do dicionário VLibras, o mesmo que o player toca; isso resolve parte do mapeamento que hoje é manual (210 glosas). Porém o VLibras gera glosas para todo o dicionário dele, não só para as 210 baixadas; seria preciso baixar os sinais extras ou filtrar/marcar o que ficar fora.
- **Risco de "lavagem" de qualidade**: adotar o VLibras troca "nossas regras sem fonte" por "regras de terceiros com fragilidades documentadas" (seção 4: negação, interrogativas, homônimos, verbos direcionais). Continua sendo preciso rotular a saída como não validada.
- **Custo de engenharia**: Java 17 + hunspell (Linux) + cogroo4py num projeto Windows → rodar em contêiner Docker/WSL como microserviço. Esforço estimado: médio (1–3 dias para subir e integrar), sem treinar nada.
- Não usar endpoint público não documentado: sem termos de uso localizados, chamar servidores do governo a partir do Sinaliza é risco de disponibilidade e de conformidade; a versão local via pip evita isso.

### Gaps
- **Endpoint público** (`traducao2.vlibras.gov.br` ou similar) e **termos de uso** de API: nenhuma página oficial encontrada; não confirmado se existe, se é aberto ou sob quais condições.
- **Convenções de glosa do player** além de `_`, `[PONTO]`, `VÍRGULA` e números (ex.: marcadores de interrogação, exclamação, intensidade, datilologia com `&` ou similar): não documentadas nos READMEs consultados. Seria preciso ler o código-fonte de `vlibras-translate` (pacote LGPL, pode ser inspecionado) ou testar o player localmente.
- Se o pacote `vlibras-deeplearning` traz pesos de modelo e sob qual licença: não verificado.

## 3. Opções orientadas a dados: corpus pt-br2libras-gloss, ajuste fino de seq2seq e LLMs

### Takeaway
Existe um corpus paralelo grande e aberto — **pt-br2libras-gloss** (UFPB, 127.349 pares, **CC BY-SA 4.0**) — produzido pelo mesmo grupo do VLibras; um seq2seq pequeno (PTT5, MIT) ajustado nele tende a reproduzir as convenções e escolhas do VLibras, o que é coerente com o player mas não é validação independente. Não encontrei modelo text→gloss de Libras pronto no Hugging Face nem estudo que meça alucinação de LLMs em glosa de Libras.

### Cited Findings
- **pt-br2libras-gloss v2** (28/05/2025, DOI 10.17632/ryj88ckjww.2): 127.349 pares alinhados; CSV UTF-8 com colunas `pt-br`, `libras-gloss`, `is_government_source` (55.047 pares vêm de sites do governo federal) e `english_translation` (gerada automaticamente, só metadado); licença **CC BY-SA 4.0**; autores Manuella Lima, Daniel França, Diego Silva, Dilainne Albuquerque, Daniel Lacerda, Rostand Costa, Guido Souza Filho, Tiago Araújo (UFPB); financiadores SNDPD e Secretaria de Governo Digital; **a página não informa como as glosas foram produzidas** — [Mendeley Data: pt-br2libras-gloss v2](https://data.mendeley.com/datasets/ryj88ckjww/2); v1 (23/04/2025) tinha 3 colunas — [Mendeley Data v1](https://data.mendeley.com/datasets/ryj88ckjww/1)
- Dissertação de Dilainne Albuquerque (UFPB, coautora do dataset) descreve um corpus bilíngue de **57.206** pares português–glosa construído com **10 intérpretes de Libras**, usado para treinar um novo modelo do tradutor VLibras e avaliado com usuários surdos, que relataram entender melhor as frases — [Repositório UFPB 123456789/31303](https://repositorio.ufpb.br/jspui/handle/123456789/31303) (via resumo de busca; PDF retornou erro 502)
- Um artigo de 2026 chama o conjunto de ~127 mil pares de **VLibras-DB (Lima et al., 2025)** e observa que ele cobre sinais lexicais manuais, **não marcadores não manuais nem tempo** — [arXiv 2607.11341: In-Car Sign Language Corpus](https://arxiv.org/pdf/2607.11341) (via resumo de busca)
- Aumento de dados para tradução neural PB→Libras (UFPB, WebMedia 2024, mesmo grupo): back-translation e sua combinação com substituição de sinônimos guiada por POS foram as técnicas mais eficazes (BLEU); corpus e arquitetura não aparecem no resumo — [SBC WebMedia 2024](https://sol.sbc.org.br/index.php/webmedia/article/view/30327)
- **PTT5** (unicamp-dl): licença **MIT**; tamanhos small (60M), base (220M), large (740M); pré-treinado no BrWaC; vocabulário português recomendado — [Hugging Face: unicamp-dl/ptt5-base-portuguese-vocab](https://huggingface.co/unicamp-dl/ptt5-base-portuguese-vocab)
- Busca "libras" no Hugging Face (12 modelos): nenhum é claramente tradutor texto→glosa; há reconhecimento de sinais, YOLO e geração de imagens; `GabrielRodris/tradutor-libras` não tem tags que permitam confirmar — [Hugging Face API: models?search=libras](https://huggingface.co/api/models?search=libras&limit=50)
- Trabalho em língua gestual portuguesa (Glossifica, IPVC): abordagem por regras teve BLEU 0,722 / METEOR 0,796 contra BLEU 0,698 / METEOR 0,752 da abordagem neural — [Repositório IPVC: Glossifica](http://repositorio.ipvc.pt/handle/20.500.11960/3232) (via resumo; é LGP, não Libras)
- Arquitetura híbrida PB→glosa Libras (Seq2Seq LSTM + dicionário de mapeamentos + embeddings) é proposta em artigo da REASE, com expansão do corpus e Transformers como trabalhos futuros — [REASE](https://periodicorease.pro.br/rease/article/download/25311/16061/77259) (via resumo de busca)
- "Uso de Glosas para Tradução Automática em Libras" (Santos e França, UECE, Latinoware 2025): propõe converter texto em glosa e depois "suavizar" com LLM; relata BLEU-1 71,23 contra 34,01 de modelo direto. A métrica avalia o **texto final**, e os trabalhos relacionados citados são de vídeo→texto; ou seja, não mede a qualidade da glosa para sinalização — [SBC Latinoware 2025](https://sol.sbc.org.br/index.php/latinoware/article/view/40998)
- LLMs: o próprio VLibras prevê um refinador por LLM (gpt-4o por padrão), **desligado por padrão** — [GitHub: vlibras-translator-text-core](https://github.com/spbgovbr-vlibras/vlibras-translator-text-core); um projeto de doutorado na UFSC pesquisa ChatGPT para tradução em Libras, sem resultados publicados na notícia — [Uninter](https://www.uninter.com/noticias/?p=68362); edital do MPRS (2026) para tradutor de Libras exige fidelidade semântica — [MPRS: Desafio 40](https://www.mprs.mp.br/media/areas/licitacao/arquivos/2026/2_01_26_cp_desafio40_tradutor_libras.pdf)

### Inferences
- **O corpus resolve o "de onde vem a regra"?** Só em parte. Se as glosas vieram de intérpretes (dissertação: 10 intérpretes, 57 mil pares) há conhecimento humano embutido; mas a página do dataset não diz se os intérpretes traduziram do zero ou **corrigiram saídas do VLibras**, e um modelo treinado nele aprende as convenções do VLibras. Para o Sinaliza isso é vantagem prática (mesmo dicionário do player) e limitação metodológica (não é validação independente). CC BY-SA 4.0 exige atribuição e que derivados do *dataset* (ex.: subconjunto filtrado publicado) saiam sob a mesma licença.
- **Uso barato do corpus sem treinar nada**: (a) extrair de forma empírica como o corpus trata negação, interrogativas, tempo e plural, e usar isso como *fonte citável* de padrões; (b) medir cobertura do vocabulário de 210 glosas (quantas frases são 100% cobertas); (c) montar um conjunto de teste de frases cobertas para BLEU/chrF.
- **Ajuste fino de PTT5-small/base** em 127 mil pares é factível numa GPU modesta ou Colab, mas o modelo vai gerar glosas fora das 210 disponíveis; exige pós-filtro (decodificação restrita ou mapeamento) e continua sem validação por surdos. Esforço: médio-alto; benefício linguístico: incerto.
- **LLM com prompt**: sem estudo de erro em glosa de Libras, sem corpus de referência no prompt e sem quem valide, é a opção de maior risco de saída plausível e errada. Se usado, só com few-shot tirado do corpus citado, vocabulário fechado nas 210 glosas e rótulo explícito de não validado.

### Gaps
- Procedência exata das glosas do pt-br2libras-gloss (tradução humana do zero, pós-edição de VLibras, ou geração automática) — não declarada na página; PDF da dissertação inacessível (erro 502).
- Resultados (BLEU/chrF) de modelos PTT5/mT5/BART-pt para PB→glosa Libras: nenhum artigo encontrado com números.
- Corpus **Libras-UFPel** (PROPOR 2026), paralelo Libras–português: só o título foi encontrado — [CNLSE: Libras-UFPel Corpus](https://cnlse.es/es/recursos/biblioteca/libras-ufpel-corpus-a-parallel-dataset-of-brazilian-sign-language-and-portuguese-for-multimodal-research-and-processing); tamanho, glosas e licença não verificados.
- Sabiá, Llama, Claude e GPT aplicados a glosa de Libras: nenhuma avaliação publicada encontrada.

## 4. Avaliação viável sem sinalizantes na equipe, e como envolver surdos e TILS

### Takeaway
Sem sinalizantes, o máximo honesto é avaliação automática contra um corpus de referência (BLEU/chrF/WER sobre glosas) e uma suíte de frases de teste por fenômeno, guiada pela lista de pontos fracos já documentada para o VLibras (homônimos, advérbios de negação, verbos direcionais, interrogativas e exclamativas). A validação de verdade precisa de surdos e intérpretes, e existe metodologia publicada para isso.

### Cited Findings
- **Metodologia multinível** (Luana Silva Reis, mestrado UFPB, 2020): métodos para avaliar tradutores automáticos PB→Libras com intérpretes, com surdos e também sem usuários; aplicada em três estudos de caso com o VLibras; aponta fragilidades em **homônimos, advérbios de negação, verbos direcionais e frases interrogativas e exclamativas** — [BDTD/IBICT: Reis 2020](https://bdtd.ibict.br/vufind/Record/UFPB-2_2bebf04c92d80763b4699251897e44c4)
- Tese UFPB de 2018 propõe arquitetura flexível para tradutores texto→glosa por regras baseada no tradutor do VLibras e avalia com **BLEU e WER** (prova de conceito inglês→glosa ASL) — [Repositório UFPB 123456789/15628](https://repositorio.ufpb.br/jspui/handle/123456789/15628) (via resumo de busca; PDF retornou erro 502)
- O modelo treinado no corpus de 57 mil pares foi avaliado com **usuários surdos**, que relataram compreender melhor as frases — [Repositório UFPB 123456789/31303](https://repositorio.ufpb.br/jspui/handle/123456789/31303) (via resumo)
- Avaliação do VLibrasWidget combinou revisão heurística por especialistas com testes com usuários surdos e ouvintes (observação + satisfação subjetiva) — [SBQS 2025](https://sol.sbc.org.br/index.php/sbqs/article/view/39021)
- O G'Libras, sistema especialista para criação de glosas, parte da premissa de que as regras devem ser customizadas por profissionais de Libras — [SBC DESAFIE: G'Libras](https://sol.sbc.org.br/index.php/desafie/article/view/10045) (via resumo de busca)
- Bragg et al. (ASSETS 2019) defendem que processamento de línguas de sinais precisa ser interdisciplinar, incluindo estudos e cultura surda — [Microsoft Research: Bragg et al. 2019](https://www.microsoft.com/en-us/research/?p=599343); [PDF NSF PAR](https://par.nsf.gov/servlets/purl/10170029)

### Inferences
- **Suíte de fenômenos (sem sinalizantes)**: montar ~30–60 frases por categoria de Reis (2020) — negação, interrogativa (com e sem pronome interrogativo), exclamativa, homônimos (ex.: palavras com dois sentidos no vocabulário), verbos direcionais, expressões de tempo, nomes próprios — e registrar, para cada uma, a saída atual e a saída de referência do pt-br2libras-gloss quando houver frase equivalente. Isso não prova correção em Libras; prova consistência com uma referência citada e expõe regressões.
- **Métricas**: BLEU/chrF/WER sobre glosas são viáveis com o pt-br2libras-gloss como referência, restringindo às frases cujo vocabulário cabe nas 210 glosas. A referência é do ecossistema VLibras (seção 3), então o número mede proximidade ao VLibras, não qualidade em Libras.
- **Recrutamento** (sugestões da equipe, não verificadas): cursos de Letras-Libras e intérpretes/TILS da própria universidade, núcleos de acessibilidade, associações de surdos locais; usar o formato de Reis (2020) — mostrar a sequência de sinais no avatar e pedir compreensão/naturalidade — em sessões curtas, remuneradas ou com crédito, e com consentimento.

### Gaps
- Detalhes dos níveis e instrumentos da metodologia de Reis (2020): só o resumo foi lido.
- Fontes sobre recrutamento ético de surdos/TILS no Brasil (cursos Letras-Libras, NAPNE, FENEIS/associações) não foram pesquisadas nesta rodada.
- Uso de chrF especificamente em glosa de Libras: nenhum trabalho encontrado.

## 5. Transparência e UX: como rotular os limites da saída

### Takeaway
A posição internacional das entidades de surdos e intérpretes é que tradução palavra-a-sinal exata não é possível e que avatares não substituem intérpretes, sobretudo em conteúdo complexo ou importante. Isso sustenta: mostrar a glosa, chamar a saída de "sequência de sinais", oferecer um modo "palavra por palavra" assumido como apoio de vocabulário, e não oferecer um modo "frase" como se fosse tradução.

### Cited Findings
- Declaração **WFD + WASLI** sobre avatares (2018): a diferença de qualidade linguística entre humanos e avatares é o motivo para desaconselhar avatares como substitutos de sinalizantes humanos; tradução exata palavra-a-sinal não é possível porque toda tradução considera contexto e normas culturais; preocupação especial com conteúdo ao vivo, complexo ou importante — [WFD/WASLI Statement on Avatar (PDF)](https://wfdeaf.org/wp-content/uploads/WFD-and-WASLI-Statement-on-Avatar-FINAL-14032018-Updated-14042018.pdf); [WFD: notícia](https://wfdeaf.org/?p=7496)
- Wolfe et al. (2021) apontam como nicho prático de avatares a comunicação **unidirecional** de texto **roteirizado e previsível** (ex.: avisos de estação ou hotel) — [R. Wolfe: Statement re Avatars (PDF)](https://www.oeglb.at/wp-content/uploads/2021/05/20_R.Wolfe_StatementReAvatars_EN.pdf) (via resumo de busca)
- A glosa não é língua natural nem escrita da Libras: é notação que usa palavras do português para representar sinais de forma aproximada, não capta tridimensionalidade e simultaneidade, e não há padrão único de notação — [SBC Latinoware 2025](https://sol.sbc.org.br/index.php/latinoware/article/view/40998)
- O corpus VLibras-DB não cobre marcadores não manuais nem tempo — [arXiv 2607.11341](https://arxiv.org/pdf/2607.11341) (via resumo)

### Inferences
- Rótulos concretos derivados das fontes: "Sequência de sinais (não é tradução para Libras)"; exibir a glosa em MAIÚSCULAS ao lado do avatar; marcar com "~" sinais aproximados (já feito); quando o analisador detectar pergunta/negação, mostrar "A expressão facial que marca pergunta/negação em Libras não é reproduzida".
- **Modo "palavra por palavra"** (vocabulário): cada sinal isolado com a palavra correspondente — honesto e coerente com o nicho de vocabulário fechado. **Modo "frase"**: só faz sentido se as regras tiverem fonte; caso contrário, é melhor não existir do que sugerir gramática que a equipe não domina.
- O nicho de Wolfe (texto previsível, unidirecional) combina com um vocabulário de 210 sinais: frases-modelo curtas validadas uma a uma por um surdo/TILS são mais defensáveis que um gerador aberto.

### Gaps
- Não foram encontrados estudos ou guias brasileiros sobre como apps de Libras (VLibras, Hand Talk) rotulam limitações na interface.

## 6. Matriz de recomendação (palavras-chave × regras × VLibras × treino × LLM)

### Takeaway
Para um projeto estudantil com 210 sinais e sem sinalizantes, a combinação de melhor custo-benefício é: **(A) manter palavras-chave com rótulos honestos + (B) trocar a análise para spaCy (negação, pergunta, NER, segmentação) + (C) usar o pt-br2libras-gloss e/ou o `vlibras-translate` local como referência citável**, deixando reordenação só para fenômenos com fonte. As regras sugeridas pelo orientador ("tempo primeiro, negação no fim, interrogativo no fim") só têm sustentação parcial nas fontes encontradas.

### Cited Findings (base linguística disponível para regras de reordenação)
- **Ordem básica SVO**: em sentenças menos marcadas com argumentos expressos, a ordem básica da Libras é SVO, confirmando Quadros (1999) e Ferreira-Brito (1995), com dados do Corpus de Libras da Grande Florianópolis — [Royer e Quadros, Revista da ABRALIN 2019/2020](https://revista.abralin.org/index.php/abralin/article/view/1375). OSV e SOV são descritas como derivadas da SVO (Quadros e Karnopp, 2004) — [Quadros e Karnopp: Gramática da língua de sinais brasileira (ResearchGate)](https://www.researchgate.net/publication/289938060_Gramatica_da_lingua_de_sinais_brasileira) (via resumo de busca)
- **Interrogativas**: o elemento interrogativo (WH) pode aparecer **in situ, na periferia esquerda ou duplicado** (Quadros 2004; Nunes e Quadros 2006) — [UFAL: A posição do elemento interrogativo "que" nas sentenças em Libras](https://www.repositorio.ufal.br/handle/123456789/15120) (via resumo de busca; texto completo não lido). Interrogação e negação são associadas a **marcas não manuais** (Quadros e Karnopp) — mesma busca, fonte secundária.
- **Tempo**: Figueiredo e Lourenço (UFMG) analisam a Libras como língua **sem-tense**, sem marcação temporal no verbo e com advérbio/expressão de tempo opcional — [Repositório UFMG](https://repositorio.ufmg.br/items/835c3b33-23c3-4056-a077-19acf62fbe90/full); [Scripta 2020 (DOAJ)](https://doaj.org/article/07b31f4fcba34696ba586adf64041a64). Em orações temporais, a **anteposição** da oração temporal é a ordem não marcada (Crescêncio Neto e Rodrigues, 2022, Corpus de Libras UFSC) — [Estudos Linguísticos (GEL)](https://revistadogel.emnuvens.com.br/estudos-linguisticos/article/download/3267/2123) (via resumo de busca)
- **Negação**: o movimento lateral de cabeça tem valor de negação (Arrotéia, 2005, citado por Mendes, UFJF 2024) — [UFJF: dissertação de Lucas Mendes](https://www2.ufjf.br/ppglinguistica/wp-content/uploads/sites/119/2025/03/Lucas.pdf) (via resumo de busca)

### Inferences — matriz
| Opção | Esforço | Dados | Licença | Fidelidade linguística | Risco | Encaixe com 210 sinais |
|---|---|---|---|---|---|---|
| **A. Palavras-chave + rótulos de limitação** (atual, melhorado) | Baixo (horas) | Nenhum novo | — | Baixa, mas assumida | Baixo se rotulado; alto se chamado de tradução (WFD/WASLI) | Total |
| **B. A + análise com spaCy** (frases, lemas contextuais, `Polarity=Neg`, `PronType=Int`, NER→datilologia, avisos de ENM ausente) | Baixo–médio (1–2 dias) | Nenhum | CC BY-SA 4.0 (modelo) | Igual a A na ordem; melhor lematização e avisos | Baixo | Total; datilologia exige sinais de letras no pacote local |
| **C. B + reordenação mínima com fonte**: (i) expressão/oração de tempo no início (anteposição não marcada, GEL 2022); (ii) não flexionar tempo verbal (sem-tense, UFMG); (iii) manter SVO (ABRALIN) | Médio (2–4 dias + testes) | Suíte de frases | — | Média-baixa; cada regra citada | Médio: "negação no fim" e "interrogativo no fim" **não** têm fonte encontrada (WH pode ser in situ, inicial ou duplicado) | Bom |
| **D. Reusar `vlibras-translate` (regras do VLibras) local** | Médio (Docker/WSL, Java 17, hunspell) | Nenhum | LGPL-3.0 | Média; fragilidades documentadas (Reis 2020) | Médio: dependência pesada; saída fora das 210 glosas | Precisa filtrar ou baixar mais sinais do dicionário |
| **E. Ajuste fino de seq2seq (PTT5) no pt-br2libras-gloss** | Alto (semanas) | 127 mil pares, CC BY-SA 4.0 | MIT (PTT5) + CC BY-SA (dados) | Imita o VLibras; sem validação independente | Alto: frases fluentes erradas, vocabulário aberto | Fraco sem decodificação restrita |
| **F. LLM com prompt** (GPT/Claude/Sabiá/Llama) | Baixo para protótipo, alto para tornar confiável | Few-shot do corpus | Termos do provedor | Desconhecida (sem estudos) | Muito alto: plausível e não validado; dados a terceiros | Exige restringir às 210 glosas |

- **Recomendação sequencial**: A + B agora; usar o pt-br2libras-gloss como **referência citável** (cobertura e suíte de testes); C apenas com as regras (i)–(iii) e marcadas como "proposta não validada"; D como comparação lado a lado (mostrar "o que o VLibras gera") em vez de substituir; E e F só depois de haver alguém surdo/TILS para validar.
- Um caminho intermediário de baixo custo para "frase" é **frases-modelo**: um conjunto pequeno de frases curtas do domínio do projeto, revisadas por um surdo/TILS, servidas como sequências fixas — alinhado ao nicho "texto previsível" de Wolfe (2021).

### Gaps
- Posição do sinal de negação (ex.: NÃO pós-verbal) e de expressões interrogativas no fim da frase: **nenhuma fonte encontrada**; não implementar sem fonte.
- Topicalização como regra de transferência: só a menção de OSV/SOV derivadas; sem condições de uso que permitam automatizar.
- Leitura integral de Quadros e Karnopp (2004) e de Felipe (manuais de Libras) não foi feita; as afirmações acima vêm de resumos e citações secundárias.
