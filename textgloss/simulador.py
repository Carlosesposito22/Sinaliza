"""Simulador de uso: envia frases à API, como se fossem usuários, para gerar dados novos.

ETAPA: fonte de dados novos (sem ML). Faz o papel que a rubrica dá ao sistema embarcado: alimenta a API
com frases novas; a API classifica cada palavra com o modelo T1 e grava em `inferencias`; o DAG
`monitoramento` consolida e o painel mostra. Cada requisição leva `X-Origem: simulador`, o que autoriza a API
a gravar o texto (as frases são públicas: `data/phrases.json` ou o conjunto de teste do VLibrasBD).

Uso: python -m textgloss.simulador --n 30 --intervalo 1 [--url http://localhost:8000] [--fonte frases|corpus]
"""
import argparse
import json
import random
import time
import urllib.error
import urllib.request

from . import config


def load_phrases(source: str) -> list[str]:
    if source == "frases":
        data = json.loads((config.ROOT / "data" / "phrases.json").read_text(encoding="utf-8"))
        return [p["text"] for category in data["categories"] for p in category["phrases"]]
    import pandas as pd

    frases = pd.read_parquet(config.PROCESSED_DIR / "frases.parquet", columns=["texto", "split"])
    texts = frases.loc[frases["split"] == "teste", "texto"]
    return [t for t in texts if 8 <= len(t) <= 200]


def send(url: str, text: str, timeout: float = 30.0) -> dict:
    request = urllib.request.Request(
        f"{url.rstrip('/')}/translate",
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Origem": "simulador"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def run(url: str, phrases: list[str], n: int, interval: float, seed: int, out=print) -> dict:
    rng = random.Random(seed)
    stats = {"enviadas": 0, "ok": 0, "rejeitadas": 0, "erros": 0, "modelos": {}}
    for i in range(n):
        text = rng.choice(phrases)
        stats["enviadas"] += 1
        try:
            body = send(url, text)
            stats["ok"] += 1
            version = body["model_version"]
            stats["modelos"][version] = stats["modelos"].get(version, 0) + 1
            out(f"[{i + 1}/{n}] {version} {body['latency_ms']} ms | {text[:60]} -> {' '.join(body['glosses'])}")
        except urllib.error.HTTPError as error:
            # 422: a frase não tem nenhuma palavra com sinal; é resposta válida da API, não falha.
            stats["rejeitadas" if error.code == 422 else "erros"] += 1
            out(f"[{i + 1}/{n}] HTTP {error.code} | {text[:60]}")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            stats["erros"] += 1
            out(f"[{i + 1}/{n}] erro de rede: {error} | {text[:60]}")
        if interval and i < n - 1:
            time.sleep(interval)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--n", type=int, default=30, help="quantas frases enviar")
    parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre frases")
    parser.add_argument("--fonte", choices=["frases", "corpus"], default="frases")
    parser.add_argument("--semente", type=int, default=config.SEED)
    args = parser.parse_args()
    stats = run(args.url, load_phrases(args.fonte), args.n, args.intervalo, args.semente)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
