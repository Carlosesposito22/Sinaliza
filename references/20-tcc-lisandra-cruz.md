# TCC de Lisandra Sousa da Cruz (UFRPE, 2019)

**Comparação de algoritmos de reconhecimento de gestos aplicados à sinais estáticos de Libras.** Monografia de Bacharelado em Sistemas de Informação, UFRPE, Recife, 12/07/2019, 53 páginas. Orientador: Filipe Cordeiro; coorientador: Valmir Macario Filho. Arquivo: `Documentos/tcc_lisandrasousadacruz.pdf`.

Indicado pelo orientador do Sinaliza como leitura útil. Lido por inteiro em 2026-10-19. O que segue é o resumo do TCC e, separado, **o que se aproveita no Sinaliza**. Onde há inferência nossa, está marcado.

## O que o TCC faz

- **Tarefa:** classificar **imagens de mãos** em sinais **estáticos** de Libras (reconhecimento, o sentido inverso do nosso escopo atual). Fora do escopo dela: gestos dinâmicos, sinais com corpo ou rosto, vídeo e tempo real.
- **Dados:** dataset de **Bastos (2016)**, 40 sinais estáticos: numerais de um dígito (sem 0, 3, 6, 9), o alfabeto **sem K, H, J e Z** (movimento) e 12 palavras (adulto, américa, avião, casa, gasolina, identidade, juntos, lei, palavra, pedra, pequeno, verbo). 9.600 imagens, **metade delas são máscaras binárias de pele**, ou seja, cerca de **4.800 fotos** de **5 pessoas** (3 mulheres adultas, 1 homem adulto, 1 adolescente), feitas com 3 especialistas e 2 alunos surdos fluentes em Libras.
- **Modelos comparados:** VGG13 e VGG16 (CNNs profundas), FFCNN (CNN pequena com filtro de Gabor e momentos de Zernike, de Chevtchenko et al. 2018, que a autora esperava que vencesse) e a MLP com descritores HOG + Zernike do próprio Bastos (resultado copiado da dissertação, não reexecutado).
- **Protocolo:** 10 repetições, a cada uma 75% das imagens para treino e 25% para teste, sorteadas ao acaso; 100 épocas; três taxas de aprendizagem (0,01, 0,001, 0,0001); média e desvio padrão; teste F de variâncias e **teste t** (95%, 18 graus de liberdade) para ver se as diferenças são significativas; precisão, revocação e F1 **por sinal**.
- **Resultado:** a hipótese **não se confirmou**. VGG16 teve a maior acurácia (**99,45%**, α = 0,01), depois VGG13 (99,09%), FFCNN (98,2%, α = 0,001) e a MLP de Bastos (96,77%). Com α = 0,01 a FFCNN **divergiu** (3,2%); com α = 0,0001 as VGG ficaram em ~25% (não convergiram em 100 épocas). As diferenças entre as redes foram significativas no teste t. Erros se concentraram em sinais de mão parecida: "s" confundido com "a" (16%), "l" com "i" (10%), "pedra" com "junto" (4,5%).
- **Dificuldade relatada (seção 6.2):** a primeira versão do dataset da própria autora (60 imagens de 38 gestos, **2 pessoas**) fez as VGG falharem em classificar os gestos de uma pessoa quando treinadas com os da outra; ela abandonou esse dataset por falta de tempo.

## Como ler os números (cautelas)

- Os 99% **não dizem** que o modelo generaliza para uma pessoa nova. O TCC sorteia imagens ao acaso, e a **própria autora relata** (6.2) que treinar numa pessoa e testar na outra falhou. O texto não afirma que o sorteio separe pessoas, então **[inferido]** as imagens da mesma pessoa caem em treino e teste, e a acurácia mede memorização do estilo daquelas 5 pessoas, em boa parte.
- As 10 repetições sorteiam do **mesmo conjunto**, então as amostras do teste t **[inferido]** não são independentes e o `p` fica otimista.
- As redes usam otimizadores e tamanhos de lote diferentes (SGD e 32 nas VGG; Adam e 100 na FFCNN), então comparar "qual rede é melhor por taxa de aprendizagem" mistura efeitos. A explicação de "overshooting" para a FFCNN em 0,01 é plausível, mas não foi testada isoladamente.
- Tudo é sobre **imagem estática de mão, em ambiente controlado**. Nada disso vale como evidência sobre gerar movimento de sinais dinâmicos.
- Dados de contexto (IBGE, leis, formação de professores) são de 2012–2019. Há uma frase sobre a origem da Libras "por volta de 1951" no mesmo parágrafo em que o INES é fundado em 1857; **não reutilizar** essa data sem conferir.

## O que dá para aproveitar no Sinaliza

### 1. Alto valor, aplicável já

| # | O que | Como entra no Sinaliza |
| --- | --- | --- |
| 1 | **Generalização entre pessoas é o ponto fraco** (seção 6.2) | É a prova mais próxima de que o nosso plano está certo: validar **em sinalizante que não apareceu no treino**. Citar este TCC como evidência para a escolha. Com 4 sinalizantes no subconjunto inicial, a forma natural é **leave-one-signer-out** (4 dobras), não um sorteio de gravações |
| 2 | **Os cinco parâmetros dos sinais**: configuração de mão, ponto de articulação, orientação, movimento, expressão facial e/ou corporal (seção 2.1) | Mapeia o que o formato de pose captura e o que não (tabela abaixo) e vira **roteiro para o validador de Libras** avaliar parâmetro por parâmetro, em vez de "está certo ou errado?" |
| 3 | **Terminologia** (seção 2.1): a comunidade surda prefere **"surdo"**; "deficiente auditivo" é visto como pejorativo e **"surdo-mudo" causa desconforto**, porque a maioria dos surdos tem o aparelho fonador íntegro e não fala por não ouvir (Espote et al. 2013; Gesser 2008) | Regra de redação para UI, documentos e apresentação: **surdo / pessoa surda**. "Deficiência auditiva" só ao citar categoria do IBGE. Conferido: o código e a interface atuais **não** usam os termos problemáticos; só o glossário foi ajustado (ver abaixo). **[a confirmar com uma pessoa surda]** |
| 4 | **Metodologia de avaliação**: repetições com média ± desvio, teste de hipótese, métricas **por sinal**, curvas de treino, varredura de taxa de aprendizagem | Adaptações concretas em `model/` (seção "Evolução proposta da avaliação") |
| 5 | **Resultado negativo reportado com honestidade** | A hipótese da autora foi refutada e ela publicou assim. Mesmo critério para nós: se o modelo não superar o medoide, reportar isso (já é a regra do projeto) |
| 6 | **Precedentes de validação com especialistas** | Bastos fez o dataset com **3 especialistas e 2 alunos surdos** fluentes; Teodoro (2015) fez um especialista em Libras escolher as 30 palavras. Reforça a pendência nº 1 do projeto: **alguém que saiba Libras** precisa validar sinais, mapeamentos aproximados e frases |

#### Parâmetros dos sinais × formato de pose do Sinaliza **[análise nossa]**

| Parâmetro (TCC, 2.1) | O que o formato de pose tem | Risco |
| --- | --- | --- |
| Configuração de mão | 21 keypoints por mão (MediaPipe) | A detecção de mão é o gargalo (taxas ainda não medidas no MINDS-Libras); mão não detectada vira zero. O recorte com YOLOv8 existe por isso |
| Ponto de articulação | Corpo (33 pontos) e mãos no mesmo espaço normalizado pelos ombros | Contato com a cabeça ou o peito exige posição relativa precisa; `z` do MediaPipe é aproximado e **não há rosto** |
| Orientação das mãos | Derivável da posição dos 21 pontos | `z` aproximado afeta a orientação da palma |
| Movimento | Sequência temporal de frames | Reamostragem para 32 frames apaga a **duração** e o ritmo; transições entre sinais ainda não existem |
| Expressão facial e/ou corporal | Corpo sim; **rosto não** | Fora do formato por decisão; limita marcações gramaticais (pergunta, negação, intensidade) |

Um achado que reforça a decisão de ter corpo e mãos no formato: Bastos **excluiu** do dataset de mão apenas sinais estáticos que envolvem outras partes do corpo, citando **"conhecer" (cabeça), "amigo" (peito) e "aluno" (braço)**. **CONHECER e ALUNO estão no nosso vocabulário de 20 sinais**, o que confirma que dependem de posição relativa ao corpo e que não bastaria modelar só as mãos.

### 2. Valor médio, vale verificar

| # | O que | Como entra | Pendência |
| --- | --- | --- | --- |
| 7 | **Dataset de Bastos (2016)** como fonte de **mãos estáticas do alfabeto e números** | O MINDS-Libras **não tem alfabeto manual**, e por isso o projeto não tem como soletrar palavra sem sinal (limite registrado em `09-dados-e-vocabulario.md`). Rodar o MediaPipe Hands nas imagens daria 21 keypoints por letra | **Não sabemos se está disponível nem a licença.** O TCC diz que o autor quis "deixá-lo disponível para a comunidade", mas não traz link. Faltam **H, K, J, Z** (e J e Z têm movimento): o alfabeto ficaria incompleto. São **imagens**, não vídeo, de 5 pessoas; misturar com o estilo do MINDS-Libras exige cuidado. Pedir ao orientador o contato de Bastos ou da autora |
| 8 | **Classificador auxiliar sobre keypoints** para medir **reconhecibilidade** do movimento gerado | Complementa o DTW: treinar um classificador dos 20 sinais em keypoints reais (modelo pequeno) e ver se o movimento **gerado** é classificado como o sinal certo, com precisão, revocação, F1 e **pares confundidos** por sinal, como na Tabela 6 do TCC | **Ideia, não implementada.** O classificador também precisa de validação em sinalizante não visto, e acertar o classificador não é acertar Libras |
| 9 | **Tabela de trabalhos relacionados** | Serve para o relatório e a apresentação: Koroishi e Silva 2015 (Kinect, 12 sinais, ~65%), Bastos 2016 (MLP, 40 sinais, 96,77%), Teodoro 2015 (vídeo, 30 palavras, Random Forest), Neto e Menezes 2018 (CNN 3D em língua de sinais argentina, 64 gestos, 94,22%), Chevtchenko et al. 2018 (FFCNN, ASL, 92,53%) | Todos são **reconhecimento**; nenhum **gera** movimento. Isso é, honestamente, a lacuna que o Sinaliza ocupa, mas também diz que **não temos baseline na literatura de geração** |
| 10 | **Contexto local** | O TCC cita os totens digitais em Libras da Hand Talk no **shopping RioMar, em Recife** | Ponto de contexto para a apresentação (o tema na cidade); não é requisito |

### 3. Pouco ou nenhum reuso direto

- **CNN, VGG, FFCNN, filtro de Gabor, momentos de Zernike, HOG e máscaras binárias de pele** servem para **classificar imagem**. O Sinaliza usa **landmarks do MediaPipe** como entrada e gera movimento; não há imagem de mão para classificar. Não vale importar essas técnicas só porque aparecem no TCC.
- Se o grupo quiser uma CNN em algum lugar, o ponto de contato mais natural é o **YOLOv8** já adotado (também uma CNN), e não as redes do TCC.
- Detalhes de ambiente (Python 3.6, TensorFlow 1.13, Keras) estão desatualizados.

## Evolução proposta da avaliação (`model/`) **[proposta, nada implementado]**

Inspirada na metodologia do TCC, adaptada ao nosso problema (geração, métrica DTW, poucos sinalizantes):

1. **Leave-one-signer-out:** treinar com todos menos um sinalizante, avaliar nele, repetir para cada um. Hoje `train.py` valida em um único sinalizante (`--val-signers`).
2. **Curvas de treino e validação:** registrar a perda por época (hoje `metrics.json` guarda só a primeira e a última perda de treino) para enxergar sobreajuste, como nas Figuras 15 a 22 do TCC.
3. **Varredura de taxa de aprendizagem** (por exemplo 1e-2, 1e-3, 1e-4): hoje é fixa em 1e-3. O TCC mostra que a mesma rede passa de 99% a 3% só com a taxa.
4. **Comparação com teste de hipótese:** com poucas dobras, usar teste **pareado** sobre o DTW por gravação ou por sinal (por exemplo Wilcoxon) entre modelo e medoide, e relatar o tamanho do efeito. Ressalva: gravações do mesmo sinalizante não são independentes, então tratar o `p` como indício, não como prova.
5. **Tabela por sinal** (DTW por sinal, já em `per_gloss`; e, se houver o classificador auxiliar, precisão, revocação, F1 e pares confundidos).

## Mudanças feitas na documentação por causa deste TCC

- `18-glossario.md`: verbete de terminologia ("surdo", o que evitar) e dos cinco parâmetros.
- `17-convencoes-e-regras-para-claude.md`: regra de redação com "surdo".
- `README.md` (índice de `references/`): entrada para este arquivo.

## Pontos para levar ao orientador

1. A autora (ou o orientador dela) pode **indicar pessoas surdas ou intérpretes** para validar sinais, mapeamentos e frases?
2. Como falar com **Bastos** sobre o dataset de sinais estáticos (disponibilidade e licença)? Vale incluir alfabeto manual para soletrar?
3. Para a avaliação, ele prefere o protocolo do TCC (repetições e teste t) ou leave-one-signer-out com teste pareado?
4. Um **classificador de reconhecibilidade** sobre keypoints entra como parte da validação, ou fica fora do escopo?

## Referência

CRUZ, Lisandra Sousa da. *Comparação de algoritmos de reconhecimento de gestos aplicados à sinais estáticos de Libras*. Monografia (Bacharelado em Sistemas de Informação), Universidade Federal Rural de Pernambuco, Recife, 2019.

Trabalhos citados pelo TCC que mais interessam: BASTOS, I. L. O. *Reconhecimento de sinais da Libras utilizando descritores de forma e redes neurais artificiais*, 2016; CHEVTCHENKO, S. F. et al. *A convolutional neural network with feature fusion for real-time hand posture recognition*, Applied Soft Computing, v. 73, 2018; TEODORO, B. T. *Sistema de reconhecimento automático de Língua Brasileira de Sinais*, tese, USP, 2015; KOROISHI e SILVA, *Reconhecimento de sinais da Libras por visão computacional*, Mecatrone, 2015; ESPOTE, SERRALHA e SCORSOLINI-COMIN, *Inclusão de surdos: revisão integrativa da literatura científica*, Psico-USF, 2013; GESSER, A., *Do patológico ao cultural na surdez*, Trabalhos em Linguística Aplicada, 2008. **Não lemos esses trabalhos**; as descrições vêm do que o TCC diz sobre eles.
