"""Painel do Sinaliza: monitoramento do classificador T1 em execução.

ETAPA: visualização (sem ML novo). Lê o Postgres (`inferencias`, `indicadores_horarios`), a API, o MLflow e o Airflow.
O que o modelo faz: decide, palavra por palavra, se ela vira sinal (MANTER) ou não (DESCARTAR). A saída da API é uma
sequência de sinais, não uma tradução de Libras.

Rodar: streamlit run app.py (ou o serviço `dashboard` do compose, http://localhost:8501).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

import charts
import data

st.set_page_config(page_title="Sinaliza · Painel do modelo", page_icon="📊", layout="wide")

WINDOWS = {"Últimas 6 horas": 6, "Últimas 24 horas": 24, "Últimos 3 dias": 72, "Últimos 7 dias": 168}
REFRESH_SECONDS = 10


@st.cache_resource
def get_config() -> data.Config:
    return data.Config.from_env()


@st.cache_resource
def get_engine(url: str):
    return create_engine(url, pool_pre_ping=True)


def pct(value: float | None, digits: int = 1) -> str:
    return "—" if value is None or pd.isna(value) else f"{value * 100:.{digits}f}%".replace(".", ",")


def num(value: float | None, digits: int = 3) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:.{digits}f}".replace(".", ",")


def ago(moment: datetime | None) -> str:
    if moment is None:
        return "nunca"
    seconds = max(0, int((datetime.now(timezone.utc) - moment).total_seconds()))
    if seconds < 90:
        return f"há {seconds} s"
    if seconds < 5400:
        return f"há {seconds // 60} min"
    if seconds < 172800:
        return f"há {seconds // 3600} h"
    return f"há {seconds // 86400} dias"


def theme_mode() -> str | None:
    try:
        return st.context.theme.type
    except Exception:  # versões sem st.context.theme
        return None


@st.cache_data(ttl=8, show_spinner=False)
def cached_services(config: data.Config, _engine) -> list[data.ServiceStatus]:
    """O painel se atualiza a cada 10 s; sem isto, um serviço parado atrasaria cada atualização."""
    return data.check_services(config, _engine)


def show(chart) -> None:
    st.altair_chart(chart, width="stretch", theme=None)


# --- seções --------------------------------------------------------------------------------------------------------


def overview(config: data.Config, hourly: pd.DataFrame, totals: dict, since: datetime, tokens: dict) -> None:
    overall = data.hourly_overall(hourly, since)
    in_use = data.api_model(config.api_url)

    if in_use is None:
        st.error("✖ A API não responde. As inferências novas não estão sendo geradas.")
    elif in_use.startswith("lista-fixa"):
        st.warning(f"⚠ A API está atendendo **sem o modelo** ({in_use}). A decisão de cada palavra vem da lista fixa, não de ML.")
    else:
        st.success(f"✔ Modelo em uso: **{in_use}**")

    if overall.empty:
        st.info(
            "Ainda não há indicadores consolidados nesta janela. O DAG `monitoramento` roda a cada hora; "
            f"há {totals['pendentes']} inferências aguardando. Envie frases pela API ou pelo simulador "
            "(`python -m textgloss.simulador`) e dispare o DAG no Airflow."
        )
        return

    words = int(overall["palavras"].sum())
    weights = overall["palavras"].clip(lower=1)

    def weighted(column: str) -> float:
        return float((overall[column].fillna(0) * weights).sum() / weights.sum()) if words else float("nan")

    # Rótulos curtos (o texto longo vai no tooltip): em tela estreita rótulo e valor longos são cortados.
    cols = st.columns(5)
    cols[0].metric("Frases", f"{int(overall['frases'].sum()):,}".replace(",", "."), help="Frases atendidas pela API na janela (já consolidadas).")
    cols[1].metric("Mantidas", pct(weighted("taxa_manter")), help="Parte das palavras que o modelo decidiu manter (MANTER).")
    cols[2].metric("Sem sinal", pct(weighted("taxa_sem_sinal")), help="Palavras que o modelo manteve mas que não têm sinal no vocabulário.")
    cols[3].metric("Incertas", pct(weighted("taxa_incerta")), help="Palavras com probabilidade de MANTER entre 0,4 e 0,6.")
    cols[4].metric("Latência p95 (ms)", f"{overall['latencia_p95_ms'].max():.0f}", help="Maior p95 por hora na janela (aproximação conservadora).")
    if totals["pendentes"]:
        st.caption(f"{totals['pendentes']} inferências ainda não consolidadas pelo DAG `monitoramento` (não entram nos números acima).")

    left, right = st.columns(2)
    with left:
        st.subheader("Frases por hora")
        show(charts.frases_por_hora(data.fill_hours(overall, since), tokens))
    with right:
        st.subheader("Latência da API")
        show(charts.latencia(overall, tokens))
    st.subheader("Palavras sem sinal e decisões incertas, por hora")
    show(charts.taxas(overall, tokens))
    with st.expander("Ver os números por hora (tabela)"):
        table = overall.assign(hora=overall["hora"].dt.strftime("%d/%m %H:00"))
        st.dataframe(table, hide_index=True, width="stretch")


def inferences(recent: pd.DataFrame, since: datetime, tokens: dict) -> None:
    window = recent[recent["em"] >= pd.Timestamp(since)]
    if window.empty:
        st.info("Nenhuma inferência nesta janela.")
        return
    origins = sorted(window["origem"].fillna("—").unique())
    chosen = st.multiselect("Origem", origins, default=origins, help="Quem enviou a frase: `simulador`, `web`, ...")
    window = window[window["origem"].fillna("—").isin(chosen)]
    words = data.explode_words(window)

    st.subheader("Últimas inferências")
    st.dataframe(data.recent_table(window), hide_index=True, width="stretch")
    st.caption(
        "A API só grava o **texto** das frases do simulador ou quando `SINALIZA_LOG_TEXT=true`; nas demais, aparece "
        "“(texto não gravado)” e só a decisão e a probabilidade de cada palavra. O texto é apagado depois da retenção."
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Probabilidade de MANTER")
        hist = data.probability_histogram(words)
        if hist["palavras"].sum() == 0:
            st.info("Sem decisões do modelo na janela (só da lista fixa, que não é ML).")
        else:
            show(charts.histograma_probabilidades(hist, tokens))
            st.caption("Quanto mais perto de 0 ou de 1, mais certeza. O modelo mantém a palavra quando a probabilidade chega a 0,5.")
            with st.expander("Ver como tabela"):
                st.dataframe(hist[["faixa", "palavras"]], hide_index=True, width="stretch")
    with right:
        st.subheader("Decisões de baixa confiança")
        low = data.low_confidence(words)
        if low.empty:
            st.info("Nenhuma decisão entre 0,4 e 0,6 na janela.")
        else:
            shown = low.assign(
                em=low["em"].dt.strftime("%d/%m %H:%M"),
                palavra=low["palavra"].fillna("(texto não gravado)"),
                probabilidade=low["probabilidade"].map(lambda v: num(v, 2)),
            ).rename(columns={"em": "quando (UTC)", "decisao": "decisão", "tipo": "resultado"})
            st.dataframe(shown, hide_index=True, width="stretch")

    st.subheader("Palavras sem sinal no vocabulário")
    unknown = data.unknown_words(words)
    if unknown.empty:
        st.info("Nenhuma palavra sem sinal com texto gravado nesta janela.")
    else:
        show(charts.barras_ordenadas(unknown, "palavra", "ocorrencias", tokens, "ocorrências"))
        st.caption("Só entram frases com o texto gravado. São candidatas a entrar no vocabulário (sempre a validar com quem sabe Libras).")


def model_tab(config: data.Config, tokens: dict) -> None:
    in_use = data.api_model(config.api_url)
    registry = data.registered_model(config.mlflow_url)
    st.subheader("Versão em uso")
    left, right = st.columns(2)
    left.metric("Na API agora", in_use or "API fora do ar")
    if registry:
        right.metric("Registrada no MLflow", f"{registry['nome']}/{registry['versao']}", help=f"Registrada em {registry['registrado_em']:%d/%m/%Y %H:%M} UTC")
    else:
        right.metric("Registrada no MLflow", "nenhuma", help="Ainda não existe `sinaliza-t1`: rode o DAG `treino_t1`.")

    if registry:
        m = registry["metricas"]
        st.subheader("Teste final do modelo registrado")
        st.caption(
            f"Run `{registry['run_name']}`, registrada em {registry['registrado_em']:%d/%m/%Y %H:%M} UTC. "
            "O teste final usa 10% das frases separadas desde o início e roda uma única vez por MLflow."
        )
        base = m.get("teste_lista_fixa_f1_macro")
        cols = st.columns(5)
        cols[0].metric("F1-macro", num(m.get("teste_f1_macro")),
                       delta=None if base is None else f"{(m['teste_f1_macro'] - base):+.3f} vs lista fixa".replace(".", ","),
                       help="Métrica principal: média do F1 de MANTER e de DESCARTAR.")
        cols[1].metric("Acurácia", num(m.get("teste_accuracy")))
        cols[2].metric("Precisão (MANTER)", num(m.get("teste_precision_manter")))
        cols[3].metric("Revocação (MANTER)", num(m.get("teste_recall_manter")))
        cols[4].metric("Tempo de treino", "—" if "tempo_treino_s" not in m else f"{m['tempo_treino_s'] / 60:.0f} min")
        st.markdown(f"[Abrir a run no MLflow]({config.mlflow_public_url}/#/experiments)")

    st.subheader("Comparação dos modelos treinados (validação)")
    comparison = data.training_comparison(config.mlflow_url, config.experiment)
    if comparison.empty:
        st.info("Sem runs de treino no MLflow para o experimento configurado.")
    else:
        show(charts.comparacao_modelos(comparison, tokens))
        st.caption("A lista fixa é a referência sem ML (o que a API fazia antes do modelo). O modelo escolhido está em azul.")
        with st.expander("Ver como tabela"):
            st.dataframe(comparison.assign(f1_macro=comparison["f1_macro"].map(num)), hide_index=True, width="stretch")


def services_tab(config: data.Config, engine, totals: dict) -> None:
    st.subheader("Estado dos serviços")
    statuses = cached_services(config, engine)
    table = pd.DataFrame([{"serviço": s.name, "estado": s.label, "detalhe": s.detail, "resposta (ms)": s.ms} for s in statuses])
    st.dataframe(table, hide_index=True, width="stretch")
    if any(s.ok is False for s in statuses):
        st.error("Há serviço fora do ar. Veja a coluna “detalhe”.")

    st.subheader("Frescor dos dados")
    cols = st.columns(4)
    cols[0].metric("Frases gravadas", f"{totals['frases']:,}".replace(",", "."))
    cols[1].metric("Última inferência", ago(totals["ultima"]))
    cols[2].metric("Última hora consolidada", ago(totals["consolidado_ate"]), help="Início da última hora com indicadores gravados pelo DAG `monitoramento` (não é quando o DAG rodou).")
    cols[3].metric("Aguardando consolidação", totals["pendentes"])
    st.caption("O painel só mostra o que a API gravou em `inferencias`. Se a “última inferência” for antiga, ninguém está usando a API.")


# --- montagem ------------------------------------------------------------------------------------------------------


def main() -> None:
    config = get_config()
    engine = get_engine(config.database_url)

    with st.sidebar:
        st.header("Painel")
        window_label = st.selectbox("Janela de tempo", list(WINDOWS), index=1)
        auto = st.toggle(f"Atualizar a cada {REFRESH_SECONDS} s", value=True)
        st.caption("Horários em UTC. Fontes: Postgres, API, MLflow e Airflow.")

    st.title("Sinaliza · painel do modelo")
    st.caption(
        "Monitoramento do classificador T1 (ML nosso), que decide palavra por palavra se ela vira sinal. "
        "A saída é uma **sequência de sinais**, não uma tradução de Libras."
    )

    @st.fragment(run_every=f"{REFRESH_SECONDS}s" if auto else None)
    def body() -> None:
        tokens = charts.tokens(theme_mode())
        since = datetime.now(timezone.utc) - timedelta(hours=WINDOWS[window_label])
        try:
            recent = data.load_recent(engine)
            hourly = data.load_hourly(engine)
            totals = data.totals(engine)
        except Exception as error:  # banco fora do ar: o resto do painel ainda mostra o estado dos serviços
            st.error(f"Não foi possível ler o banco ({type(error).__name__}). Veja a aba Serviços.")
            recent, hourly, totals = (pd.DataFrame(columns=data.RECENT_COLUMNS), pd.DataFrame(columns=data.HOURLY_COLUMNS),
                                      {"frases": 0, "pendentes": 0, "ultima": None, "primeira": None, "consolidado_ate": None})
        tab_overview, tab_inferences, tab_model, tab_services = st.tabs(["Visão geral", "Inferências", "Modelo", "Serviços"])
        with tab_overview:
            overview(config, hourly, totals, since, tokens)
        with tab_inferences:
            inferences(recent, since, tokens)
        with tab_model:
            model_tab(config, tokens)
        with tab_services:
            services_tab(config, engine, totals)

    body()


main()
