# Template SBC do relatório de Aprendizado de Máquina

O relatório da cadeira de AM **tem que** ser feito no template da SBC (Sociedade Brasileira de Computação) enviado pelo professor, **sem alterar margens, fontes, espaçamento ou número de colunas**. Fora do formato, a nota do bloco **Comunicação (20%) é zero**. Ver [`31-requisitos-cadeira-am.md`](31-requisitos-cadeira-am.md), seção 5.

## Onde está o template

- PDF original: [`../Documentos/Aprendizado de Maquina/sbc_template.pdf`](../Documentos/Aprendizado%20de%20Maquina/) (4 páginas, "Instructions for Authors of SBC Conferences Papers and Abstracts").
- Cópia editável no Google Docs do Carlos: https://docs.google.com/document/d/13uScUtFwatxbg6OF_Q9Xm47eLfPOm-RJKcf8LWFGisQ/edit
- **Cuidado:** a especificação diz que relatório "em formato livre (Word, Google Docs etc.)" é considerado fora do formato. Escrever **dentro** do template (o arquivo do professor, mesmo aberto no Google Docs) é usar o template; o que não vale é um documento próprio. Ao exportar o PDF, conferir que margens, fontes e espaçamentos continuam os do modelo (o Google Docs costuma trocar Times por Times New Roman e mexer em espaçamento). **[a confirmar com o professor]** se ele prefere a versão LaTeX oficial da SBC.

## Regras de formatação (do próprio template)

| Elemento | Regra |
| --- | --- |
| Papel e colunas | A4, **uma coluna** |
| Margens | superior **3,5 cm**, inferior **2,5 cm**, laterais **3,0 cm** |
| Cabeçalho, rodapé, números de página | **nenhum** (números de página suprimidos) |
| Fonte do corpo | **Times, 12 pt**, **6 pt antes** de cada parágrafo |
| Parágrafos | o 1º parágrafo de cada seção **sem recuo**; os seguintes com recuo de **1,27 cm** na 1ª linha |
| Título | centralizado, **16 pt, negrito**, 12 pt de espaço antes |
| Autores | centralizados, **12 pt, negrito**, todos na mesma linha, separados por vírgula, 12 pt depois do título |
| Endereços (instituição) | centralizados, 12 pt, 12 pt depois dos nomes |
| E-mails | **Courier New 10 pt**, 6 pt antes e depois |
| Abstract e Resumo | Times 12 pt, recuo de **0,8 cm** dos dois lados; as palavras **Abstract** e **Resumo** em negrito antes do texto; **no máximo 10 linhas cada**; os dois **na primeira página**. Artigo em português exige **os dois** (Abstract em inglês + Resumo) |
| Títulos de seção | **13 pt, negrito**, alinhados à esquerda, 12 pt extra antes; numeração opcional |
| Títulos de subseção | **12 pt, negrito**, alinhados à esquerda |
| Legendas de figura e tabela | **Helvetica 10 pt, negrito**, 6 pt antes e depois; centralizada se couber em uma linha, senão justificada com recuo de 0,8 cm dos dois lados |
| Posição das legendas | figura: legenda **abaixo**; tabela: legenda **acima** |
| Tabelas | evitar fundo colorido ou sombreado e linhas grossas, duplas ou desnecessárias; não usar mais casas decimais do que a precisão justifica |
| Imagens | preto e branco ou cinza, exceto em artigos publicados eletronicamente (o nosso é PDF, então cor é aceitável **[inferido]**); 600 dpi (P&B) ou 150–300 dpi (cinza); evitar resolução excessiva |
| Citações | autor e ano entre colchetes, ex.: [Knuth 1984], [Boulic and Renault 1991]; ou ano entre parênteses, ex.: Knuth (1984) |
| Lista de referências | 12 pt, 6 pt antes de cada referência; 1ª linha sem recuo, as seguintes com recuo de **0,5 cm** |

## Primeira página (ordem obrigatória)

1. Título
2. Nomes dos autores
3. Instituição e endereço (CESAR School, Recife – PE – Brasil)
4. E-mails
5. **Abstract** (inglês, ≤ 10 linhas)
6. **Resumo** (português, ≤ 10 linhas)
7. Início da seção 1

## Esqueleto sugerido para o relatório do Sinaliza **[proposta]**

Segue a ordem dos blocos de nota da especificação, para o professor achar cada critério:

1. **Introdução** — problema (acessibilidade em Libras), o que o Sinaliza faz e o que **não** faz (sequência de sinais, não tradução), onde está o ML (tarefa T1). Fonte: `00`, `01`, `24`.
2. **Dados e Análise Exploratória** (bloco Análise de Dados, 15%) — VLibrasBD (bootstrap), estatísticas descritivas, tratamento e justificativas, ≥ 5 figuras interpretadas. Fonte: notebooks 01 e 02, `21`, `22`.
3. **Metodologia de Validação** — holdout agrupado por frase, StratifiedGroupKFold, por que LOO não se aplica, Optuna. Fonte: `27`, `28`.
4. **Modelagem e Resultados** (bloco Modelagem e Validação, 30%) — baseline, comparação de ≥ 3 modelos, matriz de confusão, ROC/PR, análise crítica, otimização, teste final. Fonte: `25`, `26`, `27`, `28`, notebooks 03–05.
5. **Arquitetura e MLOps** (bloco MLOps, 25%) — aquisição (embarcado simulado + MQTT), Airflow, MLflow, API, dashboard, Docker Compose. Fonte: `24`, `14`, `30`.
6. **Limitações e Trabalhos Futuros** — ordem dos sinais, sem validação por surdos, ruído dos rótulos, privacidade.
7. **Conclusão**
8. **Referências** — VLibras/VLibrasBD, spaCy, scikit-learn, Optuna, MLflow, Airflow, TCC indicado pelo orientador, etc. (ver `docs/creditos-e-licencas.md`).

Ao final, salvar o PDF em `reports/` (estrutura sugerida pela especificação).
