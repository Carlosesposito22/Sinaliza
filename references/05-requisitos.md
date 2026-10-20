# Requisitos

Fonte: `Documentos/Requisitos Preliminares.docx`. Foram escritos como **diretrizes de necessidade do usuário**, sem foco em implementação, no escopo antigo (jogo com câmera). A coluna "No escopo atual" é uma avaliação nossa **[inferido]**; confirmar com a equipe.

| ID | Requisito original | Evidência que o gerou | No escopo atual |
| --- | --- | --- | --- |
| **R01** | Interação e validação bidirecional em tempo real: receber gestos do usuário e dar feedback imediato sobre a correção do sinal | Hand Talk/VLibras/ProDeaf são unidirecionais e não avaliam o usuário | **Não se aplica** (escopo muda para texto → Libras). Sobra o espírito de "resposta rápida" |
| **R02** | Curva de aprendizado com progressão de dificuldade | Projetos acadêmicos ficam no alfabeto/sinais soltos | **Fora do escopo** (sem gamificação/níveis) |
| **R03** | Foco em comunicação prática e contextos do cotidiano (sala de aula, consulta, escritório) | Só 2,6% dos que têm dificuldade auditiva sabem Libras; barreiras em escola, saúde, trabalho | **Parcial.** O vocabulário já traz `contexts` (escola, saúde, serviços, geral, trabalho, família) em `data/vocabulary.json`; frases de demo usam contextos reais |
| **R04** | Autonomia e privacidade de comunicação (menos dependência de intermediários) | Saúde: 100% dos idosos surdos apontam atendimento como gargalo; dependência de familiar viola privacidade | **Motivação mantida.** A ferramenta não substitui intérprete; pode ajudar a comunicar frases simples |
| **R05** | Conformidade com LGPD no tratamento de dados capturados por câmera | LGPD trata biometria/gestos como dado sensível | **Mudou de forma.** Não há captura do usuário. Ainda há: (a) vídeos de sinalizantes do dataset são dados pessoais (não versionar `raw/`); (b) texto digitado — definir se é registrado. Ver [`16-riscos-e-questoes-abertas.md`](16-riscos-e-questoes-abertas.md) |
| **R06** | Engajamento ativo para mitigar evasão | 28% vs 19% de receio de evasão; 42%/58% no ensino superior | **Fora do escopo** |

## Requisitos implícitos do escopo atual

Não estão nos documentos da fase 1; derivam do código e das decisões de 2026-10-14. **[inferido]**

| ID provisório | Requisito | Onde está |
| --- | --- | --- |
| RN01 | O sistema recebe texto em português (até 500 caracteres) e devolve sequência de glosas e de poses | `api/app/schemas.py`, `POST /translate` |
| RN02 | O movimento é descrito no formato de pose único (75 keypoints, normalizado) | [`08-formato-de-pose.md`](08-formato-de-pose.md) |
| RN03 | O gerador de movimento é trocável (interface `PoseGenerator`) | `api/app/generator.py` |
| RN04 | O modelo só entra no produto se superar as linhas de base em métrica objetiva (DTW) em sinalizante não visto | [`11-modelo-ml.md`](11-modelo-ml.md) |
| RN05 | O sistema nunca se apresenta como tradução linguisticamente correta de Libras; nas demos, "sequência de sinais" | `docs/dados-e-vocabulario.md` |
| RN06 | Comportamento para palavra fora do vocabulário deve estar definido antes de expor ao público (aviso ou soletração) | **Em aberto** |
| RN07 | Subir tudo com um comando (`docker compose up --build`) | `docker-compose.yml` |
| RN08 | Interface simples e guiada (persona Helena) | Parcial; ver [`13-web.md`](13-web.md) |
| RN09 | Dados brutos e derivados respeitam licenças (CC BY 4.0 com atribuição; V-LIBRASIL não redistribuir) | `docs/dados-e-vocabulario.md` |
