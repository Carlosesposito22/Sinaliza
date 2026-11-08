"""Gráficos do painel (Altair), com a paleta de referência validada (`dataviz`: azul e laranja dos slots 1 e 2,
verificados nos dois modos; o slot 3 não é usado porque o verde-água fica abaixo de 3:1 no tema claro).

Regras seguidas: uma só escala por gráfico (nada de eixo duplo); texto em tinta neutra, nunca na cor da série;
marcas finas, grade discreta; barras partem do zero (o que não parte do zero é ponto); legenda quando há 2 séries,
com o valor mais recente rotulado direto; destaque em uma cor e o resto em cinza. Todos têm tooltip.
"""
from __future__ import annotations

import math

import altair as alt
import pandas as pd

LIGHT = {
    "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
    "series1": "#2a78d6", "series2": "#eb6834", "gray": "#a6a49c",
}
DARK = {
    "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835",
    "series1": "#3987e5", "series2": "#d95926", "gray": "#6b6a64",
}
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
HEIGHT = 260


def tokens(mode: str | None) -> dict:
    return DARK if mode == "dark" else LIGHT


def _style(chart, t: dict):
    return (
        chart.configure(background="rgba(0,0,0,0)", font=FONT)
        .configure_view(stroke=None)
        .configure_axis(
            labelColor=t["muted"], titleColor=t["ink2"], gridColor=t["grid"], domainColor=t["axis"],
            tickColor=t["axis"], labelFontSize=12, titleFontSize=12, titleFontWeight="normal",
        )
        .configure_legend(labelColor=t["ink2"], titleColor=t["ink2"], orient="top", labelFontSize=12, symbolType="stroke")
    )


def _hour_axis(title: str = "hora (UTC)"):
    return alt.X("hora:T", title=title, axis=alt.Axis(format="%d/%m %Hh", labelOverlap=True, grid=False))


def frases_por_hora(hourly: pd.DataFrame, t: dict):
    """Colunas de uma cor: quantas frases a API atendeu em cada hora."""
    # Eixo ordinal com todas as horas da janela (ver data.fill_hours): a largura da coluna se ajusta ao espaço e há
    # folga entre colunas vizinhas.
    bars = alt.Chart(hourly).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=t["series1"]).encode(
        x=alt.X("hora:O", timeUnit="yearmonthdatehours", title="hora (UTC)", scale=alt.Scale(paddingInner=0.3),
                axis=alt.Axis(format="%d/%m %Hh", labelOverlap=True, labelAngle=-45, grid=False)),
        y=alt.Y("frases:Q", title="frases", axis=alt.Axis(tickMinStep=1)),
        tooltip=[alt.Tooltip("hora:T", title="hora", format="%d/%m %H:00"), alt.Tooltip("frases:Q", title="frases"),
                 alt.Tooltip("palavras:Q", title="palavras")],
    )
    return _style(bars.properties(height=HEIGHT), t)


def _two_lines(frame: pd.DataFrame, columns: dict[str, str], t: dict, y_title: str, y_format: str, value_label: str):
    """Duas linhas (azul e laranja) com legenda, marcadores, tooltip e o último valor rotulado."""
    long = frame.melt(id_vars="hora", value_vars=list(columns), var_name="coluna", value_name="valor")
    long["serie"] = long["coluna"].map(columns)
    names = list(columns.values())
    color = alt.Color("serie:N", title=None, sort=names, scale=alt.Scale(domain=names, range=[t["series1"], t["series2"]]))
    base = alt.Chart(long).encode(
        x=_hour_axis(), y=alt.Y("valor:Q", title=y_title, axis=alt.Axis(format=y_format), scale=alt.Scale(zero=True)), color=color,
    )
    lines = base.mark_line(strokeWidth=2, interpolate="linear")
    points = base.mark_point(filled=True, size=70).encode(
        tooltip=[alt.Tooltip("hora:T", title="hora", format="%d/%m %H:00"), alt.Tooltip("serie:N", title="série"),
                 alt.Tooltip("valor:Q", title=value_label, format=y_format)],
    )
    last = long.sort_values("hora").groupby("serie", sort=False).tail(1)
    labels = alt.Chart(last).mark_text(align="left", dx=8, fontSize=12, color=t["ink"]).encode(
        x="hora:T", y="valor:Q", text=alt.Text("valor:Q", format=y_format),
    )
    return _style((lines + points + labels).properties(height=HEIGHT), t)


def latencia(hourly: pd.DataFrame, t: dict):
    return _two_lines(hourly, {"latencia_p50_ms": "mediana (p50)", "latencia_p95_ms": "p95"}, t, "latência (ms)", ".0f", "latência (ms)")


def taxas(hourly: pd.DataFrame, t: dict):
    return _two_lines(
        hourly, {"taxa_sem_sinal": "sem sinal no vocabulário", "taxa_incerta": "decisão incerta (0,4 a 0,6)"}, t,
        "% das palavras", ".1%", "% das palavras",
    )


def histograma_probabilidades(hist: pd.DataFrame, t: dict):
    """Distribuição da probabilidade de MANTER. A linha em 0,5 é o limiar de decisão do modelo."""
    bars = alt.Chart(hist).mark_bar(color=t["series1"], cornerRadiusTopLeft=4, cornerRadiusTopRight=4, stroke=None).encode(
        x=alt.X("inicio:Q", title="probabilidade de MANTER", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".1f", grid=False)),
        x2="fim:Q",
        y=alt.Y("palavras:Q", title="palavras", axis=alt.Axis(tickMinStep=1)),
        y2=alt.datum(0),  # com x2 definido, sem isto a barra vira uma fatia fina em vez de partir do zero
        tooltip=[alt.Tooltip("faixa:N", title="faixa"), alt.Tooltip("palavras:Q", title="palavras")],
    )
    rule_data = pd.DataFrame({"x": [0.5], "rotulo": ["limiar 0,5"]})
    rule = alt.Chart(rule_data).mark_rule(strokeDash=[4, 3], strokeWidth=1.5, color=t["ink2"]).encode(x="x:Q")
    label = alt.Chart(rule_data).mark_text(align="left", dx=6, baseline="top", fontSize=12, color=t["ink2"]).encode(
        x="x:Q", text="rotulo:N", y=alt.value(12),
    )
    return _style((bars + rule + label).properties(height=HEIGHT), t)


def barras_ordenadas(frame: pd.DataFrame, categoria: str, valor: str, t: dict, titulo_valor: str):
    """Barras horizontais, maior primeiro, uma cor, com o valor no fim da barra."""
    height = max(120, 28 * len(frame) + 30)
    base = alt.Chart(frame).encode(
        y=alt.Y(f"{categoria}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240, ticks=False, domain=False)),
        x=alt.X(f"{valor}:Q", title=titulo_valor, axis=alt.Axis(tickMinStep=1, grid=True)),
    )
    bars = base.mark_bar(size=16, cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=t["series1"]).encode(
        tooltip=[alt.Tooltip(f"{categoria}:N"), alt.Tooltip(f"{valor}:Q", title=titulo_valor)])
    labels = base.mark_text(align="left", dx=6, fontSize=12, color=t["ink"]).encode(text=f"{valor}:Q")
    return _style((bars + labels).properties(height=height), t)


def comparacao_modelos(frame: pd.DataFrame, t: dict, destaque: str = "random-forest-otimizado"):
    """F1-macro por modelo: pontos (não barras, porque o eixo não começa em zero), o escolhido em azul e o resto em cinza.
    A lista fixa (referência sem ML) leva o rótulo "sem ML"."""
    data = frame.copy()
    data["rotulo"] = data.apply(lambda r: r["modelo"] if r["ml"] else f"{r['modelo']} (sem ML)", axis=1)
    data["escolhido"] = data["modelo"] == destaque
    # Domínio em múltiplos de 0,02, para os rótulos do eixo não se repetirem.
    low = max(0.0, math.floor((float(data["f1_macro"].min()) - 0.01) * 50) / 50)
    high = min(1.0, math.ceil((float(data["f1_macro"].max()) + 0.01) * 50) / 50)
    ticks = [round(low + 0.02 * i, 2) for i in range(int(round((high - low) / 0.02)) + 1)]
    base = alt.Chart(data).encode(
        y=alt.Y("rotulo:N", sort=alt.EncodingSortField("f1_macro", order="descending"), title=None, axis=alt.Axis(labelLimit=240, ticks=False, domain=False)),
        x=alt.X("f1_macro:Q", title="F1-macro na validação", scale=alt.Scale(domain=[low, high]), axis=alt.Axis(format=".2f", values=ticks)),
    )
    dots = base.mark_circle(size=130).encode(
        color=alt.condition("datum.escolhido", alt.value(t["series1"]), alt.value(t["gray"])),
        tooltip=[alt.Tooltip("rotulo:N", title="modelo"), alt.Tooltip("f1_macro:Q", title="F1-macro", format=".4f")],
    )
    labels = base.mark_text(align="left", dx=12, fontSize=12, color=t["ink"]).encode(text=alt.Text("f1_macro:Q", format=".3f"))
    return _style((dots + labels).properties(height=max(120, 34 * len(data) + 30)), t)
