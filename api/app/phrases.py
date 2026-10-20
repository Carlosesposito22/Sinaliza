"""Frases de demonstração por categoria (contexto), geradas por modelos de frase.

Cada categoria é um contexto do vocabulário (escola, saúde, serviços, trabalho,
família, geral). As frases saem de modelos com lacunas, escritos à mão em
português, e **só entram se passarem na validação**:

- toda palavra com sinal casa por tabela (`exact`), sem aproximação;
- ao menos dois sinais;
- ao menos um sinal do contexto da categoria (a categoria "geral" é livre).

Isto gera **texto em português**, não Libras: ninguém aqui inventa sinal ou
gramática. As palavras do modelo sem sinal (verbos, por exemplo) aparecem em
`ignored` e a interface deve mostrá-las.

Gerar o arquivo:  python -m app.phrases
Conferir (CI/teste):  python -m app.phrases --check
"""

import argparse
import itertools
import json
import os
import sys
from pathlib import Path

from .embeddings import CharNgramEmbedder
from .text_to_gloss import TextToGloss
from .vocabulary import Vocabulary, slug

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "phrases.json"

ORDER = ["escola", "saúde", "serviços", "trabalho", "família", "geral"]

TEMPLATES: dict[str, list[tuple[str, dict[str, list[str]]]]] = {
    "escola": [
        ("{a} precisa ir ao banheiro.", {"a": ["A criança", "O garoto", "A menina"]}),
        ("{a} aprende matemática.", {"a": ["O filho", "A filha", "A criança"]}),
        ("A menina escreve no papel.", {}),
        ("O garoto estuda na biblioteca.", {}),
        ("A criança faz o dever de casa.", {}),
        ("Eu quero ensinar ciência.", {}),
        ("A escola tem um teste difícil.", {}),
        ("O filho não compreende a resposta.", {}),
    ],
    "saúde": [
        ("{a} está com dor de cabeça.", {"a": ["O filho", "A filha", "A criança"]}),
        ("{a} tem medo do hospital.", {"a": ["A criança", "O filho", "O idoso"]}),
        ("O médico explica o remédio.", {}),
        ("A enfermeira ajuda o doente.", {}),
        ("Eu tenho dor de garganta e tosse.", {}),
        ("O idoso está cansado.", {}),
        ("É uma emergência no hospital.", {}),
        ("O bebê dorme.", {}),
    ],
    "serviços": [
        ("O banheiro fica no centro.", {}),
        ("Eu quero pagar o preço.", {}),
        ("O restaurante é caro.", {}),
        ("Por favor, preciso do documento.", {}),
        ("O policial ajuda na cidade.", {}),
        ("Eu compro café no restaurante.", {}),
        ("O elevador está lento.", {}),
        ("Obrigado, com licença.", {}),
    ],
    "trabalho": [
        ("A empresa tem uma reunião.", {}),
        ("O chefe quer o relatório.", {}),
        ("Eu trabalho com o computador.", {}),
        ("A secretária imprime o arquivo.", {}),
        ("A equipe colabora no projeto.", {}),
        ("O técnico explica o cronograma.", {}),
        ("Eu preciso de um novo emprego.", {}),
    ],
    "família": [
        ("A mãe e o pai estão em casa.", {}),
        ("O filho ama a família.", {}),
        ("{a} vão à festa.", {"a": ["A tia e o tio", "O primo e a prima"]}),
        ("A irmã tem um bebê.", {}),
        ("A criança brinca com o primo.", {}),
        ("O casamento é na igreja.", {}),
        ("O aniversário é amanhã.", {}),
        ("O amigo vai para casa.", {}),
    ],
    "geral": [
        ("O sapo amarelo tem medo do barulho.", {}),
        ("A manhã é bonita.", {}),
        ("O gato come peixe.", {}),
        ("A chuva é fria.", {}),
        ("Eu quero água e café.", {}),
        ("O espelho é grande.", {}),
        ("Ontem aconteceu um barulho.", {}),
        ("Oi, tudo bem?", {}),
        ("Parabéns, a festa é bonita.", {}),
    ],
}

STATUS = (
    "frases em português geradas por modelos e validadas contra o vocabulário; "
    "não são frases de Libras e não foram validadas por falante de Libras"
)


def category_id(label: str) -> str:
    return slug(label).lower()


def expand(template: str, slots: dict[str, list[str]]) -> list[str]:
    names = list(slots)
    return [
        template.format(**dict(zip(names, values)))
        for values in itertools.product(*(slots[name] for name in names))
    ]


def generate(vocabulary: Vocabulary, resolver: TextToGloss) -> dict:
    if sorted(ORDER) != sorted(vocabulary.contexts):
        raise ValueError(f"categorias {ORDER} diferem dos contextos do vocabulário {vocabulary.contexts}")

    categories = []
    for label in ORDER:
        seen: set[str] = set()
        phrases = []
        for template, slots in TEMPLATES[label]:
            for text in expand(template, slots):
                if text in seen:
                    continue
                seen.add(text)
                matches = resolver.resolve(text)
                glosses = resolver.glosses(matches)
                problems = []
                if any(m.kind == "approx" for m in matches):
                    problems.append("palavra aproximada por embedding")
                if len(glosses) < 2:
                    problems.append("menos de dois sinais")
                if label != "geral" and not any(label in vocabulary.by_gloss[g].contexts for g in glosses):
                    problems.append(f"nenhum sinal do contexto {label!r}")
                if problems:
                    raise ValueError(f"frase inválida em {label!r}: {text!r} ({'; '.join(problems)})")
                phrases.append(
                    {
                        "text": text,
                        "glosses": glosses,
                        "ignored": [m.word for m in matches if m.kind == "ignored"],
                    }
                )
        categories.append({"id": category_id(label), "label": label, "phrases": phrases})
    return {"version": 1, "status": STATUS, "categories": categories}


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def phrases_path() -> Path:
    return Path(os.environ.get("SINALIZA_PHRASES", DEFAULT_PATH))


def load(path: Path | None = None) -> list[dict]:
    path = path or phrases_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["categories"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--check", action="store_true", help="falha se o arquivo estiver desatualizado")
    parser.add_argument("--out", type=Path, default=phrases_path())
    args = parser.parse_args()

    content = dumps(generate(Vocabulary.load(), TextToGloss(Vocabulary.load(), CharNgramEmbedder())))
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        if current != content:
            print(f"{args.out} desatualizado; rode: python -m app.phrases", file=sys.stderr)
            return 1
        return 0
    args.out.write_text(content, encoding="utf-8")
    total = sum(len(c["phrases"]) for c in json.loads(content)["categories"])
    print(f"{total} frases em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
