# Análise de similares

Fonte: `Documentos/Planejamento Análise de Similares.docx` e `Documentos/Matriz de Pesquisa Grupo 10.xlsx`. A análise foi feita no escopo antigo, mas os **concorrentes diretos dela são exatamente os similares do escopo atual** (tradutores texto → Libras com avatar). Esta seção é, portanto, ainda mais relevante agora.

## Ecossistema

| Tipo | Quem | Notas |
| --- | --- | --- |
| Direto | **Hand Talk** | Maior player de tradução para Libras no Brasil; prêmio ONU 2013 (World Summit Award Mobile) |
| Direto | **VLibras** | Ferramenta oficial do governo federal; traduz conteúdo digital em português para Libras |
| Direto | **ProDeaf** | Tradução automática texto/voz → Libras, avatar 3D; adquirida pela Hand Talk em 2018 |
| Indireto | Intérprete humano | Solução mais usada na prática (escola, trabalho) |
| Indireto | Cursos livres / vídeo-aulas (ex.: canal Neto Libras) | Alternativa para aprender sozinho; sem feedback de desempenho |
| Jogo | **Libras Aventura** (itch.io) | Reconhece o alfabeto com sensores de movimento em narrativa de aventura; só alfabeto, hardware específico; sem dados públicos de acurácia (SUPOSIÇÃO) |
| Analógico | Duolingo | Referência de avaliação e progressão (escopo antigo) |

## Inventário de funcionalidades

| Funcionalidade | Hand Talk | VLibras | ProDeaf |
| --- | --- | --- | --- |
| Tradução texto/voz → Libras | Sim (avançado) | Sim (avançado) | Sim (intermediário) |
| Reconhecimento do usuário fazendo o sinal | Não | Não | Não |
| Gamificação com progressão | Sim (básico/intermediário) | Não | Não |
| Dicionário consultável | Sim (avançado) | Sim (intermediário) | Não |
| Feedback imediato sobre a execução | Não | Não | Não |
| Uso offline | Sim (básico) | Não | Não |

## Engenharia reversa (como funcionam)

- **Entrada:** manual, o usuário digita texto ou grava áudio. Disparo sempre manual; fluxo unidirecional.
- **Bases próprias:** Hand Talk e VLibras têm bancos com **mais de 38 mil palavras/sinais**; não dependem de APIs de terceiros.
- **Algoritmos:**
  - Hand Talk — IA para converter conteúdo em português para Libras.
  - VLibras — regras linguísticas computacionais e NLP.
  - ProDeaf — metodologia própria com linguistas; "editor de sinais" e "gestor de sinais" internos para cadastrar/ajustar cada entrada do dicionário.
- **Estrutura de dados:** VLibras usa arquitetura híbrida — `vlibras-translator-api` com MongoDB + RabbitMQ; o WikiLibras (dicionário colaborativo) usa AdonisJS (ORM relacional). Hand Talk não divulga.
- **Interface / estados:**
  - VLibras: elemento de loading (GIF) enquanto a API traduz; elemento de erro; em falha da API **degrada para o texto original em português** (fallback); em sucesso a **glosa** vai para um player 3D (Unity/WebGL) que anima o avatar.
  - Hand Talk/ProDeaf: avatar "processando" antes de sinalizar; **palavras desconhecidas são soletradas** (datilologia) em vez de dar erro.
- **Tempo real:** VLibras usa requisição-resposta HTTP simples (sem WebSockets no cliente); RabbitMQ só entre microsserviços. Para Hand Talk/ProDeaf é razoável supor o mesmo [inferido].

## O que isso ensina ao Sinaliza (escopo atual)

Padrões que os similares já validaram e que valem ser copiados em espírito:

1. **Pipeline texto → glosa → avatar**, com a glosa como etapa intermediária explícita (é o que `api/` já faz: `to_glosses` → `generate`).
2. **Palavra desconhecida não pode quebrar:** soletrar (datilologia) ou avisar. A decisão ainda está em aberto no projeto (ver [`09-dados-e-vocabulario.md`](09-dados-e-vocabulario.md)).
3. **Estados de loading e erro explícitos**, com degradação graciosa (mostrar a glosa/texto se a animação falhar).
4. **Requisição-resposta HTTP simples** é suficiente — o que `web/` e `api/` já fazem.

## Diferencial no escopo atual

No escopo antigo o diferencial era a bidirecionalidade. No novo, os grandes concorrentes têm **dezenas de milhares de sinais** e anos de curadoria linguística; o Sinaliza tem **20 sinais** e nenhuma validação linguística. O diferencial honesto, hoje, é de **projeto acadêmico**:

- geração de movimento **aprendida de dados abertos** (MINDS-Libras, CC BY 4.0), reproduzível;
- avaliação **objetiva** contra linhas de base, com validação em sinalizante não visto;
- código aberto e formato de pose documentado.

**[a confirmar com o professor]** qual narrativa de diferencial será usada em entregas — não vender o Sinaliza como substituto de Hand Talk/VLibras.

## Bibliografia da análise (da fonte)

camarainclusao.com.br (Hand Talk, ONU); softwarepublico.gov.br/social/suite-vlibras; gov.br/governodigital (VLibras); gov.br/conecta/catalogo/apis/vlibras; github.com/spbgovbr-vlibras/vlibras-web-browsers.
