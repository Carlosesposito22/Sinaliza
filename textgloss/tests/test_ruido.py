import json

import pandas as pd
import pytest

from textgloss import ruido


def sheet(tmp_path, rows):
    path = tmp_path / "amostra.csv"
    pd.DataFrame(rows, columns=["frase_id", "texto", "glosa", "palavra", "lema", "rotulo", "rotulo_correto"]).to_csv(
        path, index=False, encoding="utf-8-sig")
    return path


def rows(manter_wrong, manter_ok, descartar_wrong, descartar_ok, blank=0):
    out = []
    for i in range(manter_ok):
        out.append([i, "t", "g", "p", "l", 1, "1"])
    for i in range(manter_wrong):
        out.append([i, "t", "g", "p", "l", 1, "0"])
    for i in range(descartar_ok):
        out.append([i, "t", "g", "p", "l", 0, "0"])
    for i in range(descartar_wrong):
        out.append([i, "t", "g", "p", "l", 0, "1"])
    out += [[i, "t", "g", "p", "l", 0, None] for i in range(blank)]
    return out


def test_wilson_interval_matches_known_values():
    low, high = ruido.wilson(10, 100)
    assert low == pytest.approx(0.0552, abs=0.001) and high == pytest.approx(0.1744, abs=0.001)
    low, high = ruido.wilson(0, 100)
    assert low == 0.0 and high == pytest.approx(0.0370, abs=0.001)  # zero erros não vira "certeza de zero"
    assert all(pd.isna(v) for v in ruido.wilson(0, 0))


def test_load_keeps_only_checked_rows_and_flags_errors(tmp_path):
    done = ruido.load(sheet(tmp_path, rows(5, 95, 20, 80, blank=7)))
    assert len(done) == 200 and int(done["errado"].sum()) == 25


def test_load_of_an_empty_sheet_is_empty(tmp_path):
    assert ruido.load(sheet(tmp_path, [[0, "t", "g", "p", "l", 1, None]])).empty
    assert ruido.report(ruido.summarize(ruido.load(sheet(tmp_path, [[0, "t", "g", "p", "l", 1, None]])), 0.55)) == "Nenhuma linha conferida ainda."


def test_overall_rate_is_weighted_by_the_real_class_share(tmp_path):
    done = ruido.load(sheet(tmp_path, rows(5, 95, 20, 80)))  # MANTER 5% errado, DESCARTAR 20% errado
    summary = ruido.summarize(done, share_manter=0.55)
    assert summary["por_classe"]["MANTER"]["taxa"] == pytest.approx(0.05)
    assert summary["por_classe"]["DESCARTAR"]["taxa"] == pytest.approx(0.20)
    assert summary["taxa_geral_ponderada"] == pytest.approx(0.55 * 0.05 + 0.45 * 0.20)
    assert summary["taxa_simples_amostra"] == pytest.approx(0.125)  # a média simples é outra coisa
    low, high = summary["ic95_geral"]
    assert low < summary["taxa_geral_ponderada"] < high


def test_report_text_mentions_both_classes_and_the_weighting(tmp_path):
    summary = ruido.summarize(ruido.load(sheet(tmp_path, rows(5, 95, 20, 80))), 0.55)
    text = ruido.report(summary)
    assert "MANTER: 5 errados em 100" in text and "DESCARTAR: 20 errados em 100" in text
    assert "ponderada" in text and "55,0%".replace(",", ".") in text


def test_manter_share_reads_the_preparation_report(tmp_path):
    path = tmp_path / "relatorio.json"
    path.write_text(json.dumps({"proporcao_manter": 0.5512}), encoding="utf-8")
    assert ruido.manter_share(path) == pytest.approx(0.5512)
