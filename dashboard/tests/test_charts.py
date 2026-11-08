import pandas as pd
import pytest

import charts
import data

HOURLY = pd.DataFrame({
    "hora": pd.to_datetime(["2026-11-05 09:00", "2026-11-05 10:00", "2026-11-05 11:00"], utc=True),
    "frases": [5, 8, 3], "palavras": [27, 44, 16],
    "taxa_manter": [0.6, 0.62, 0.55], "taxa_sem_sinal": [0.05, 0.04, 0.08], "taxa_incerta": [0.07, 0.09, 0.05],
    "latencia_p50_ms": [150.0, 160.0, 140.0], "latencia_p95_ms": [210.0, 250.0, 190.0],
})
COMPARISON = pd.DataFrame({
    "modelo": ["random-forest-otimizado", "regressao-logistica", "lista-fixa"],
    "etapa": ["otimizacao", "baseline", "baseline"], "f1_macro": [0.884, 0.876, 0.822], "ml": [True, True, False]})
HISTOGRAM = pd.DataFrame({
    "inicio": [i / 10 for i in range(10)], "fim": [(i + 1) / 10 for i in range(10)],
    "faixa": [f"{i / 10:.1f}–{(i + 1) / 10:.1f}" for i in range(10)], "palavras": [9, 1, 0, 0, 2, 3, 0, 1, 2, 20]})
UNKNOWN = pd.DataFrame({"palavra": ["precisa", "faz", "ontem"], "ocorrencias": [7, 3, 1]})


@pytest.mark.parametrize("mode", ["light", "dark", None])
def test_every_chart_builds_a_valid_spec_in_both_themes(mode):
    t = charts.tokens(mode)
    specs = [
        charts.frases_por_hora(HOURLY, t), charts.latencia(HOURLY, t), charts.taxas(HOURLY, t),
        charts.histograma_probabilidades(HISTOGRAM, t), charts.barras_ordenadas(UNKNOWN, "palavra", "ocorrencias", t, "ocorrências"),
        charts.comparacao_modelos(COMPARISON, t),
    ]
    for chart in specs:
        spec = chart.to_dict()  # valida o esquema Vega-Lite
        assert "$schema" in spec


def test_chart_colors_come_from_the_validated_palette():
    for mode, (c1, c2) in {"light": ("#2a78d6", "#eb6834"), "dark": ("#3987e5", "#d95926")}.items():
        t = charts.tokens(mode)
        assert (t["series1"], t["series2"]) == (c1, c2)
        spec = charts.latencia(HOURLY, t).to_dict()
        assert [c1, c2] == spec["layer"][0]["encoding"]["color"]["scale"]["range"]


def test_comparison_axis_uses_distinct_two_decimal_ticks():
    spec = charts.comparacao_modelos(COMPARISON, charts.tokens("light")).to_dict()
    values = spec["layer"][0]["encoding"]["x"]["axis"]["values"]
    assert values == sorted(set(values)) and all(round(v, 2) == v for v in values)
    assert values[0] <= 0.822 and values[-1] >= 0.884


def test_histogram_bars_start_at_zero():
    spec = charts.histograma_probabilidades(HISTOGRAM, charts.tokens("light")).to_dict()
    bars = spec["layer"][0]
    assert bars["mark"]["type"] == "bar" and bars["encoding"]["y2"] == {"datum": 0}


def test_the_chosen_model_is_the_only_highlighted_one():
    t = charts.tokens("light")
    dots = charts.comparacao_modelos(COMPARISON, t).to_dict()["layer"][0]
    assert dots["encoding"]["color"]["condition"]["value"] == t["series1"] and dots["encoding"]["color"]["value"] == t["gray"]
    assert dots["mark"]["type"] == "circle"  # eixo sem zero: pontos, nunca barras


def test_charts_with_a_single_hour_still_build():
    one = HOURLY.head(1)
    t = charts.tokens("light")
    for chart in (charts.frases_por_hora(one, t), charts.latencia(one, t), charts.taxas(one, t)):
        chart.to_dict()


def test_data_helpers_feed_the_charts_without_errors():
    words = data.explode_words(pd.DataFrame(columns=data.RECENT_COLUMNS))
    assert data.probability_histogram(words)["palavras"].sum() == 0
    assert data.unknown_words(words).empty and data.low_confidence(words).empty
