# Estado atual e próximos passos

Posição em **2026-10-19**, segundo o código e o git (5 commits, todos de 2026-10-14; árvore limpa exceto `Documentos/` untracked). Nada foi executado nesta sessão: o estado abaixo vem da leitura do código e dos READMEs.

## O que está pronto

| Componente | Situação |
| --- | --- |
| Estrutura do repositório | `api/`, `web/`, `model/`, `data/`, `docs/`, Docker |
| Formato de pose | Definido e documentado (75 keypoints, normalização) |
| Decisão de dados | MINDS-Libras, 20 sinais, subconjunto inicial de 4 sinalizantes |
| Extração de keypoints | CLI (`video` e `zip`), retomável, com log de detecção; testada com extrator falso e com **um vídeo derivado de foto** |
| Treino | Pipeline completo com linhas de base e DTW; testado com dados sintéticos |
| API | `/health`, `/translate` com gerador stub |
| Front | Formulário + avatar em esqueleto animando a resposta |
| Docker | `docker compose up --build` sobe API + front (nginx com proxy) |

## O que é stub ou está faltando

1. **Dados reais:** os ZIPs do MINDS-Libras **não foram totalmente baixados**; a extração nunca rodou em vídeo real. É o gargalo de tudo que vem depois.
2. **Gerador real:** a API usa `StubGenerator` (aceno). Falta o `PoseGenerator` com modelo/medoide, concatenação e suavização de transições.
3. **Texto → glosa:** a API ainda não usa `vocabulary.json`. Falta mapear `pt` → glosa, tratar palavras desconhecidas e (se quiser) lematização simples.
4. **Modelo treinado:** nenhum resultado em dado real; não se sabe se supera o medoide.
5. **Avatar com rig:** o front desenha esqueleto; falta GLB + retargeting.
6. **Controles de reprodução e destaque da glosa atual** no front.
7. **Validação linguística:** ninguém identificado para validar sinais.
8. **Documentação para a disciplina** reescrita para o escopo novo (hipótese, personas, requisitos).
9. **Testes de front** e CI inexistentes.

## Próximos passos sugeridos (ordem de dependência)

1. **Concluir o download** dos sinalizantes 01, 02, 07, 10 (ou arranjar um espelho/disco; o Zenodo estava lento). Conferir antes a estrutura real dos ZIPs.
2. **Rodar a extração em lote** com `--limit` pequeno primeiro; ler `extraction_log.csv` (taxa de mãos detectadas). Decidir o tratamento de frames sem corpo.
3. **Rodar as linhas de base** nos dados reais (`train.py` imprime DTW das linhas de base e do modelo). Isso já responde se vale ter rede.
4. **Escolher o gerador:** medoide (simples, previsível) ou modelo, conforme o DTW.
5. **Implementar o `PoseGenerator` real** em `api/`: tabela `vocabulary.json`, política para palavras desconhecidas, concatenação com transições suaves, `fps` e duração por sinal. Atualizar `test_api.py`.
6. **Front:** destacar a glosa em execução, controles de reprodução, avisar palavras ignoradas, exibir mensagens de erro da API.
7. **Avatar com rig** e retargeting (se der tempo; o esqueleto já serve para demonstrar).
8. **Validar com alguém que saiba Libras** (professor, intérprete, pessoa surda) e registrar o resultado em `docs/`.
9. **Atualizar a documentação** (README raiz diz que o contexto da fase 1 está em `pesquisas/` — hoje está em `Documentos/`; corrigir) e reescrever hipótese/personas/requisitos para o escopo atual.
10. **Versionar `Documentos/`** (ou decidir conscientemente não versionar; contém PDFs de 16 MB).

## Pergunta que o projeto precisa responder para ser defensável

"O modelo gera movimento **melhor que simplesmente recuperar a gravação mais representativa** do sinal, em um sinalizante que o modelo nunca viu?" — medida em DTW. Se a resposta for "não", a conclusão honesta é **ficar com recuperação (medoide)** e dedicar o tempo restante a transições, avatar, interface e validação. Esse resultado também é um achado válido para a disciplina.

## Divergências encontradas entre documentos e código

- `README.md` raiz: diz que a fase 1 está em `pesquisas/` do repositório raiz da disciplina. No repositório atual a pasta é `Documentos/` (untracked).
- `README.md` raiz, "Próximos passos" 1–3: "escolher fonte", "gerar keypoints" e "definir vocabulário" — os itens 1 e 3 **já foram decididos** em `docs/dados-e-vocabulario.md`. A lista está desatualizada.
- `model/README.md`: diz que a estrutura interna dos ZIPs "ainda não foi conferida"; `data/README.md` diz que foi lida de ZIPs parcialmente baixados. Ambos concordam que **falta conferir em ZIP completo**.
- As entregas da fase 1 descrevem o escopo antigo (ver [`01-escopo-atual.md`](01-escopo-atual.md)).
