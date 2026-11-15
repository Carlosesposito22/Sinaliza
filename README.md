# Sinaliza

Projeto de Projetos 6 (Grupo 10). Recebe **texto em português** e mostra a **sequência de sinais de Libras** correspondente, tocada por um avatar (o player do VLibras). A saída é uma sequência de sinais, **não uma tradução de Libras**: sem gramática nem expressão facial, e nada aqui foi validado por falante de Libras.

> **O machine learning** do projeto é um classificador, treinado por nós, que decide **palavra por palavra** se ela vira sinal (`MANTER` ou `DESCARTAR`). Ele supera a lista fixa que a API usava antes: F1-macro **0,885** contra **0,823** no teste final. O restante (tabela do vocabulário, lema, aproximação, player do VLibras) é regra ou externo.

**Site do projeto (Google Sites):** https://sites.google.com/cesar.school/sinaliza/in%C3%ADcio

## Equipe (Grupo 10, CESAR School)

<table>
  <tr>
    <td align="center"><img src="docs/equipe/amanda-montarroyos.jpg" width="110" alt="Amanda Montarroyos"><br><b>Amanda Montarroyos</b><br><a href="https://github.com/amanda-montarroios">@amanda-montarroios</a></td>
    <td align="center"><img src="docs/equipe/bruno-assuncao.jpg" width="110" alt="Bruno Assunção"><br><b>Bruno Assunção</b><br><a href="https://github.com/brunooassuncao">@brunooassuncao</a></td>
    <td align="center"><img src="docs/equipe/caio-ferreira.jpg" width="110" alt="Caio Ferreira"><br><b>Caio Ferreira</b><br><a href="https://github.com/CaioLira18">@CaioLira18</a></td>
    <td align="center"><img src="docs/equipe/carlos-eduardo.jpg" width="110" alt="Carlos Eduardo"><br><b>Carlos Eduardo</b><br><a href="https://github.com/Carlosesposito22">@Carlosesposito22</a></td>
    <td align="center"><img src="docs/equipe/fabiana-coelho.jpg" width="110" alt="Fabiana Coelho"><br><b>Fabiana Coelho</b><br><a href="https://github.com/fabianacoelhoo">@fabianacoelhoo</a></td>
    <td align="center"><img src="docs/equipe/felipe-marques.jpg" width="110" alt="Felipe Marques"><br><b>Felipe Marques</b><br><a href="https://github.com/Felipemmdo">@Felipemmdo</a></td>
  </tr>
</table>

## Leia primeiro (documentação do ML)

| Para quê | Documento |
| --- | --- |
| **Onde está o ML e a pipeline ponta a ponta** (diagrama, entrada e saída de cada etapa, como reproduzir) | [`references/24-pipeline-de-dados-ponta-a-ponta.md`](references/24-pipeline-de-dados-ponta-a-ponta.md) |
| **Roteiro da demonstração** (apresentação e demonstração automática) | [`references/30-roteiro-da-demonstracao.md`](references/30-roteiro-da-demonstracao.md) |
| **Checklist dos 10 entregáveis de ML** e o que está feito | [`references/23-checklist-requisitos-ml.md`](references/23-checklist-requisitos-ml.md) |
| Plano de ML, baseline, comparação, Optuna e validação | [`22`](references/22-plano-ml-texto-glosa.md), [`25`](references/25-baseline-t1.md), [`26`](references/26-comparacao-de-modelos-t1.md), [`27`](references/27-otimizacao-random-forest.md), [`28`](references/28-validacao-e-generalizacao-t1.md) |
| Como rodar, testar e quanta memória precisa | [`references/14-como-rodar-e-testar.md`](references/14-como-rodar-e-testar.md) |
| Estado atual e pendências | [`references/15-estado-atual-e-proximos-passos.md`](references/15-estado-atual-e-proximos-passos.md) |

O contexto da fase 1 (problema, personas, similares, requisitos) está em `Documentos/`; o índice de tudo está em [`references/README.md`](references/README.md).

## Arquitetura

```
VLibrasBD ─► Airflow (ingestão, preparação) ─► Postgres ─► Airflow (treino) ─► MLflow (experimentos e Model Registry)
                                                                                         │ sinaliza-t1
totens simulados ─MQTT─► mosquitto ─► receptor ─► Postgres: mensagens_mqtt
                                         │
                                         ▼
texto ─► web ─────────────────────► api (FastAPI) ─► spaCy ─► CLASSIFICADOR T1 (ML nosso) ─► tabela/lema ─► sequência de sinais ─► avatar do VLibras
                                         │
                                         └─► Postgres: inferencias ─► Airflow (monitoramento) ─► painel (Streamlit)
```

| Pasta | Papel | Estado |
| --- | --- | --- |
| `src/textgloss/` | **ML**: ingestão, preparação, treino, Optuna, validação, inferência do modelo, simulador de uso, consolidação e demonstração (`python -m textgloss.<módulo>`) | Pronto, com testes |
| `dags/`, `Dockerfile` e `airflow/` | Os quatro DAGs do Airflow (ingestão, preparação, treino, monitoramento), a imagem (Dockerfile da raiz) e os scripts de partida; na primeira subida de uma máquina limpa rodam sozinhos | Pronto |
| `api/` | Serviço HTTP. Texto → decisão do modelo por palavra → glosas. Grava as inferências | Funcional, com o modelo `sinaliza-t1` (ou a lista fixa, se ele não estiver disponível) |
| `app/` | Painel de monitoramento (Streamlit): indicadores, inferências, modelo e estado dos serviços | Pronto, com testes |
| `embedded/` | **Sistema embarcado simulado**: totens de atendimento que publicam frases via MQTT (`totem.py`) | Pronto, com testes |
| `receptor/` | Assina o broker MQTT, grava cada mensagem no Postgres e pede a inferência ao modelo pela API | Pronto, com testes |
| `mosquitto/` | Configuração do broker MQTT (Eclipse Mosquitto) | Pronto |
| `web/` | Front (React + Vite): tradutor e trilha de aprendizado. Toca os sinais no avatar do VLibras | Tradutor funcional; a trilha depende dos endpoints `/learn/*` (hoje só no `mock-api/`) |
| `mock-api/` | Mock da API para o time do web trabalhar sem o ML | Pronto |
| `notebooks/` | EDA, preparação, comparação de modelos, otimização e validação, com texto explicando cada decisão | Pronto |
| `model/` | Experimento anterior (gerador de movimento, DTW); não é a entrega de ML | Mantido, não entra no compose |
| `data/` | Vocabulário curado (210 sinais do V-LIBRASIL) e extração de keypoints (experimento anterior) | O V-LIBRASIL fica só local, fora do repositório (ver `references/21-datasets-de-treino.md`) |
| `docs/` | Contrato da API com o web, créditos e licenças | — |

### Estrutura do repositório (a sugerida pela cadeira de AM)

O repositório segue a estrutura da especificação de Aprendizado de Máquina:

```
/
├── data/                # Dados (brutos e processados fora do Git; conferência dos rótulos em data/conferencia/)
├── notebooks/           # EDA e experimentos (01 EDA, 02 preparação, 03 comparação, 04 otimização, 05 validação)
├── src/                 # Código de treinamento: o pacote textgloss (python -m textgloss.<módulo>)
├── embedded/            # Simulador do sistema embarcado: totens que publicam frases via MQTT
├── dags/                # DAGs do Apache Airflow (ingestão, preparação, treino, monitoramento)
├── api/                 # API de inferência (FastAPI, modelo sinaliza-t1)
├── app/                 # Dashboard (Streamlit)
├── mlruns/              # MLflow: artefatos das runs (conteúdo fora do Git; ver mlruns/README.md)
├── Dockerfile           # Imagem do pipeline de treino (Airflow + src/)
├── docker-compose.yml   # Execução completa da solução (um único comando)
├── reports/             # Relatório em PDF (formato SBC), fonte LaTeX e figuras
├── requirements.txt     # Dependências da solução num ambiente único (inclui `-e .` para o src/)
└── README.md
```

Pastas e arquivos a mais, que a solução também usa: `receptor/` (recebe o MQTT e grava no banco), `mosquitto/`
(configuração do broker), `airflow/` (scripts de partida da imagem do `Dockerfile`), `mlflow/` e `postgres/`
(imagem e inicialização dos serviços), `web/` (front com o avatar, entrega de Projetos 6), `mock-api/`,
`pyproject.toml` (só para o `pip install -e .` achar o `src/`), `references/` e `docs/` (documentação) e
`model/` e `historico/` (experimentos anteriores, fora da solução). Os serviços além do pipeline de treino têm o
próprio `Dockerfile` na pasta de cada um.

## Como rodar

### Tudo de uma vez (Docker)

```powershell
docker compose up -d --build
```

Sobe `postgres`, `mlflow`, `api`, `airflow`, `dashboard`, `web`, o broker MQTT (`mosquitto`), o `receptor` e os dois totens simulados (`totem-ubs`, `totem-inss`), **na ordem certa** (a API passa pela carga do modelo antes do Airflow). Isso basta num clone novo: o build do front baixa sozinho os sinais do VLibras (precisa de internet no primeiro build) e, **numa máquina sem dados**, o Airflow roda sozinho a ingestão, a preparação e o treino. Para uma demonstração em minutos: `$env:SINALIZA_PERFIL="demo"; docker compose up -d --build` (o padrão, `completo`, leva horas). As opções estão em [`.env.example`](.env.example).

| Serviço | Endereço |
| --- | --- |
| Front (tradutor e trilha) | http://localhost:5173 |
| API (documentação em `/docs`) | http://localhost:8000 |
| Painel | http://localhost:8501 |
| Airflow | http://localhost:8080 |
| MLflow | http://localhost:5000 |

**Memória:** o Docker precisa de pelo menos ~4 GB; a pilha toda usa ~2,7 GB em regime e o modelo pede ~2,8 GB só na carga (ver [`references/14-como-rodar-e-testar.md`](references/14-como-rodar-e-testar.md)). Depois de atualizar o repositório, use `--build`. Demonstração automática: `python -m textgloss.demo`.

Para a API tocar as gravações reais de movimento (experimento anterior), aponte `SINALIZA_MOTIONS_DIR` para a pasta com o `motions.npz` (derivado do V-LIBRASIL, fora do repositório; ver `references/12-api.md`). O front é servido pelo nginx e repassa `/api/*` para a API, então não há CORS. Para parar: `docker compose down`. O Docker Desktop precisa estar em execução.

### API

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000` (documentação em `/docs`). Testes: `python -m pytest`.

Endpoints: `POST /translate` (devolve, por palavra, `decision` e `probability` do modelo, mais `model_version`), `GET /vocabulary`, `GET /categories`, `GET /health` e `GET /ready`. Fora do Docker, o modelo só carrega com `MLFLOW_TRACKING_URI` definida e o pacote `textgloss` no `PYTHONPATH` (`$env:PYTHONPATH=".."`); sem isso a API usa a lista fixa.

Embeddings para palavras fora do vocabulário (variável `SINALIZA_EMBEDDER`):

- `char-ngram` (padrão): só NumPy; pega flexões e erros de digitação.
- `sentence-transformers` (opcional, `pip install -r requirements-semantic.txt`): pega sentido (sinônimos), baixa um modelo na primeira vez.

`SINALIZA_APPROX_THRESHOLD` muda o limiar de similaridade. Para regenerar as frases de exemplo: `python -m app.phrases`.

### Web

```powershell
cd web
npm install
npm run dev
```

Abre em `http://localhost:5173`. Para apontar para outra API, defina `VITE_API_URL`. Testes: `npm test`.

O avatar é o player do **VLibras** (Ícaro, Hosana ou Guga; `web/public/vlibras/`, LGPL-3.0), que toca as glosas. Ele e os sinais rodam localmente; os sinais ficam fora do git, então, fora do Docker, rode `npm run signs` em `web/` uma vez (só essa etapa precisa de internet); no Docker, o build já faz isso. Créditos e licenças em [`docs/creditos-e-licencas.md`](docs/creditos-e-licencas.md). O avatar anterior (Rocketbox) está em [`historico/avatar-rocketbox/`](historico/avatar-rocketbox/README.md).

## Próximos passos

1. Preencher o resultado da conferência manual dos 200 rótulos no repositório (`python -m textgloss.ruido`) e medir o ruído dos rótulos.
2. Validar os sinais com alguém que saiba Libras (hoje tudo é proposta não validada).
3. Colocar o aviso de privacidade na interface do web antes de gravar o texto de usuários reais, e implementar os endpoints `/learn/*` da trilha.
4. Decidir se o modelo pode descartar palavras do vocabulário curado (`SINALIZA_MODEL_DISCARDS_KNOWN`).
5. A ordem dos sinais segue a do português; mudá-la exigiria outro modelo.
