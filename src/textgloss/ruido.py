"""Ruído dos rótulos T1, medido na conferência manual de 200 palavras.

ETAPA: avaliação da qualidade dos dados (sem ML). O rótulo `MANTER` / `DESCARTAR` de cada palavra vem de um
alinhamento automático de lemas (`align.py`) e erra quando o intérprete usou outro sinal para a mesma ideia.
A equipe conferiu `amostra_conferencia_200.csv` (100 MANTER e 100 DESCARTAR, sorteadas) preenchendo a coluna
`rotulo_correto` com 1 ou 0. Este módulo transforma a planilha em taxas de erro com intervalo de confiança.

Cuidado estatístico: a amostra é 100/100, mas o corpus não é metade MANTER. A taxa geral é a média das taxas por
classe PONDERADA pela proporção real de cada classe no corpus (`relatorio_preparacao.json`), e não a média simples.

Uso: python -m textgloss.ruido [caminho_da_planilha.csv]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

from . import config

Z95 = 1.96
CLASSES = {1: "MANTER", 0: "DESCARTAR"}


def wilson(errors: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Intervalo de Wilson para uma proporção (bom com amostra pequena e proporção perto de 0)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = errors / n
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def load(path: Path | str | None = None) -> pd.DataFrame:
    """Planilha com só as linhas conferidas (`rotulo_correto` igual a 0 ou 1), com a coluna `errado`."""
    path = Path(path) if path else config.PROCESSED_DIR / "amostra_conferencia_200.csv"
    sheet = pd.read_csv(path, dtype={"rotulo_correto": "string"}, encoding="utf-8-sig")
    done = sheet[sheet["rotulo_correto"].str.strip().isin(["0", "1"])].copy()
    done["rotulo_correto"] = done["rotulo_correto"].str.strip().astype(int)
    done["errado"] = done["rotulo"].astype(int) != done["rotulo_correto"]
    return done


def manter_share(report_path: Path | None = None) -> float:
    """Proporção de MANTER no corpus preparado (do `relatorio_preparacao.json`)."""
    report_path = report_path or config.PROCESSED_DIR / "relatorio_preparacao.json"
    return float(json.loads(report_path.read_text(encoding="utf-8"))["proporcao_manter"])


def summarize(done: pd.DataFrame, share_manter: float) -> dict:
    """Taxa de rótulo errado por classe e geral (ponderada), cada uma com intervalo de 95%."""
    if done.empty:
        return {"conferidas": 0}
    by_class = {}
    for label, name in CLASSES.items():
        part = done[done["rotulo"].astype(int) == label]
        errors, n = int(part["errado"].sum()), len(part)
        low, high = wilson(errors, n)
        by_class[name] = {"n": n, "errados": errors, "taxa": errors / n if n else float("nan"), "ic95": [low, high]}
    weights = {"MANTER": share_manter, "DESCARTAR": 1 - share_manter}
    overall = sum(weights[name] * by_class[name]["taxa"] for name in weights if by_class[name]["n"])
    variance = sum(
        weights[name] ** 2 * by_class[name]["taxa"] * (1 - by_class[name]["taxa"]) / by_class[name]["n"]
        for name in weights if by_class[name]["n"]
    )
    half = Z95 * math.sqrt(variance)
    return {
        "conferidas": len(done),
        "por_classe": by_class,
        "proporcao_manter_corpus": share_manter,
        "taxa_geral_ponderada": overall,
        "ic95_geral": [max(0.0, overall - half), min(1.0, overall + half)],
        "taxa_simples_amostra": float(done["errado"].mean()),
    }


def report(summary: dict) -> str:
    if not summary["conferidas"]:
        return "Nenhuma linha conferida ainda."
    lines = [f"{summary['conferidas']} palavras conferidas."]
    for name, data in summary["por_classe"].items():
        low, high = data["ic95"]
        lines.append(f"  rótulo {name}: {data['errados']} errados em {data['n']} ({data['taxa']:.1%}; IC 95% {low:.1%} a {high:.1%})")
    low, high = summary["ic95_geral"]
    lines.append(
        f"Taxa geral de rótulo errado, ponderada pela proporção real de MANTER no corpus ({summary['proporcao_manter_corpus']:.1%}): "
        f"{summary['taxa_geral_ponderada']:.1%} (IC 95% {low:.1%} a {high:.1%}); a média simples da amostra seria {summary['taxa_simples_amostra']:.1%}."
    )
    return "\n".join(lines)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    done = load(path)
    summary = summarize(done, manter_share()) if not done.empty else {"conferidas": 0}
    print(report(summary))
    if summary["conferidas"]:
        out = config.PROCESSED_DIR / "ruido_rotulos.json"
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"salvo em {out}")


if __name__ == "__main__":
    main()
