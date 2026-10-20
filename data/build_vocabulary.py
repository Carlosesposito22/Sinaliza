"""Gera `vocabulary.json` (vocabulário do MVP) a partir das classes do V-LIBRASIL.

O vocabulário é um **subconjunto curado**: palavras do dia a dia dos contextos que o
projeto usa (escola, saúde, serviços, trabalho, família e geral). A curadoria é só de
**palavras em português**: o rótulo de cada sinal é o nome da classe do V-LIBRASIL
(`video_class`) e **não foi validado por falante de Libras**.

A tabela abaixo é a decisão de curadoria. Cada linha é `(nome da classe, contextos,
formas extras em português)`. A forma base e a palavra entre parênteses (quando é uma
palavra só) entram em `pt` automaticamente; a API trata flexões com um lematizador.

    python build_vocabulary.py "<pasta do V-LIBRASIL>/annotations.csv"

Só lê o `annotations.csv` (nomes de classes); não toca nos vídeos.
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

from vlibrasil import file_key, slug  # noqa: E402

OUTPUT = Path(__file__).resolve().parent / "vocabulary.json"

ESCOLA, SAUDE, SERVICOS, TRABALHO, FAMILIA, GERAL = "escola", "saúde", "serviços", "trabalho", "família", "geral"

CURATED: list[tuple[str, list[str], list[str]]] = [
    # escola
    ("Escola", [ESCOLA], []),
    ("Estudo", [ESCOLA], ["estudar"]),
    ("Aprender", [ESCOLA], []),
    ("Ensinar", [ESCOLA], []),
    ("Livro", [ESCOLA], []),
    ("Escrever", [ESCOLA], []),
    ("Lápis", [ESCOLA], []),
    ("Papel", [ESCOLA], []),
    ("Giz", [ESCOLA], []),
    ("Dever de casa", [ESCOLA], []),
    ("Teste", [ESCOLA], []),
    ("Matemática", [ESCOLA], []),
    ("Ciência", [ESCOLA], []),
    ("Biblioteca", [ESCOLA], []),
    ("Leitura", [ESCOLA], []),
    ("Dicionário", [ESCOLA], []),
    ("Colégio", [ESCOLA], []),
    ("Faculdade", [ESCOLA], []),
    ("Universidade", [ESCOLA], []),
    ("Disciplina", [ESCOLA], []),
    ("Compreender", [ESCOLA], ["entender"]),
    ("Escolher", [ESCOLA], []),
    ("Resposta", [ESCOLA], []),
    ("Erro", [ESCOLA], []),
    ("Correto", [ESCOLA], []),
    ("Difícil", [ESCOLA, GERAL], []),
    ("Intervalo (pra descanso)", [ESCOLA], ["recreio"]),
    ("Pesquisar", [ESCOLA], []),
    ("Explicar", [ESCOLA], []),
    ("Memorizar", [ESCOLA], []),
    # saúde
    ("Hospital", [SAUDE], []),
    ("Médico (doutor)", [SAUDE], ["médica", "doutora"]),
    ("Enfermeira", [SAUDE], []),
    ("Doente", [SAUDE], []),
    ("Dor de cabeça", [SAUDE], []),
    ("Dor de garganta", [SAUDE], []),
    ("Dor de ouvido", [SAUDE], []),
    ("Medicamento", [SAUDE], ["remédio", "remédios"]),
    ("Medicina", [SAUDE], []),
    ("Emergência", [SAUDE], []),
    ("Tosse", [SAUDE], []),
    ("Termômetro", [SAUDE], []),
    ("Cirurgia", [SAUDE], []),
    ("Sangue", [SAUDE], []),
    ("Corpo", [SAUDE], []),
    ("Cabeça", [SAUDE], []),
    ("Garganta", [SAUDE], []),
    ("Cansado", [SAUDE, GERAL], ["cansada", "cansados", "cansadas"]),
    ("Fome", [SAUDE], []),
    ("Com sede", [SAUDE], ["sede"]),
    ("Dormir", [SAUDE], []),
    ("Respirar", [SAUDE], []),
    ("Acidente", [SAUDE], []),
    ("Machucar", [SAUDE], []),
    ("Perigo", [SAUDE], []),
    ("Urgente", [SAUDE], []),
    ("Grávida", [SAUDE], []),
    ("Surdo", [SAUDE], ["surda", "surdos", "surdas"]),
    ("Cego", [SAUDE], []),
    ("Cadeira de rodas", [SAUDE], []),
    ("Nervoso", [SAUDE], ["nervosa"]),
    ("Com medo", [SAUDE, GERAL], ["medo"]),
    # serviços
    ("Banheiro", [SERVICOS, ESCOLA, SAUDE, TRABALHO], []),
    ("Restaurante", [SERVICOS], []),
    ("Dinheiro", [SERVICOS], []),
    ("Pagar", [SERVICOS], []),
    ("Pagamento", [SERVICOS], []),
    ("Comprar", [SERVICOS], []),
    ("Vender", [SERVICOS], []),
    ("Caro", [SERVICOS], ["cara"]),
    ("Barato", [SERVICOS], ["barata"]),
    ("Preço", [SERVICOS], []),
    ("Cartão de Crédito", [SERVICOS], []),
    ("Documento", [SERVICOS], []),
    ("Formulário", [SERVICOS], []),
    ("Endereço", [SERVICOS], []),
    ("Telefone", [SERVICOS], []),
    ("Internet", [SERVICOS, TRABALHO], []),
    ("Policial", [SERVICOS], []),
    ("Governo", [SERVICOS], []),
    ("Bombeiro", [SERVICOS], []),
    ("Trem", [SERVICOS], []),
    ("Metrô", [SERVICOS], []),
    ("Carro", [SERVICOS, GERAL], []),
    ("Museu", [SERVICOS], []),
    ("Igreja", [SERVICOS], []),
    ("Cidade", [SERVICOS], []),
    ("Centro", [SERVICOS], []),
    ("Elevador", [SERVICOS], []),
    ("Escada", [SERVICOS], []),
    ("Esperar", [SERVICOS], ["espera"]),
    ("Ajudar", [SERVICOS, GERAL], []),
    ("Por favor", [SERVICOS, GERAL], []),
    ("Obrigado", [SERVICOS, GERAL], ["obrigada"]),
    ("Com licença", [SERVICOS, GERAL], []),
    ("Desculpa", [SERVICOS, GERAL], ["desculpe"]),
    ("Hora", [SERVICOS, GERAL], ["horas"]),
    # trabalho
    ("Emprego (trabalho)", [TRABALHO], ["trabalhar"]),
    ("Empresa", [TRABALHO], []),
    ("Chefe", [TRABALHO], []),
    ("Secretária", [TRABALHO], []),
    ("Secretário", [TRABALHO], []),
    ("Equipe", [TRABALHO], []),
    ("Departamento", [TRABALHO], []),
    ("Computador", [TRABALHO], []),
    ("Imprimir", [TRABALHO], ["imprime", "imprimem"]),
    ("Arquivo", [TRABALHO], []),
    ("Relatório", [TRABALHO], []),
    ("Projeto", [TRABALHO], []),
    ("Cronograma", [TRABALHO], []),
    ("Profissão", [TRABALHO], []),
    ("Serviço", [TRABALHO, SERVICOS], []),
    ("Demitir", [TRABALHO], []),
    ("Currículo", [TRABALHO], []),
    ("Colaborar", [TRABALHO], []),
    ("Entrevista", [TRABALHO], []),
    ("Reunião", [TRABALHO], []),
    ("Especialista", [TRABALHO], []),
    ("Técnico", [TRABALHO], []),
    # família
    ("Família", [FAMILIA], []),
    ("Mãe", [FAMILIA], []),
    ("Pai", [FAMILIA], ["pais"]),
    ("Filho", [FAMILIA, SAUDE, ESCOLA], ["filhos"]),
    ("Filha", [FAMILIA, SAUDE, ESCOLA], ["filhas"]),
    ("Irmã", [FAMILIA], ["irmãs"]),
    ("Tio", [FAMILIA], []),
    ("Tia", [FAMILIA], []),
    ("Primo", [FAMILIA], []),
    ("Prima", [FAMILIA], []),
    ("Sobrinho", [FAMILIA], []),
    ("Sobrinha", [FAMILIA], []),
    ("Bebê", [FAMILIA], ["bebês"]),
    ("Criança", [FAMILIA, ESCOLA], ["crianças"]),
    ("Garoto (menino)", [FAMILIA, ESCOLA], ["meninos", "garotos"]),
    ("Menina", [FAMILIA, ESCOLA], []),
    ("Homem", [FAMILIA], ["homens"]),
    ("Mulher", [FAMILIA], ["mulheres"]),
    ("Casamento", [FAMILIA], []),
    ("Se casar", [FAMILIA], []),
    ("Namorar", [FAMILIA], []),
    ("Amigo", [FAMILIA, ESCOLA], ["amiga", "amigas"]),
    ("Melhor amigo", [FAMILIA], []),
    ("Idoso", [FAMILIA, SAUDE], ["idosa", "idosos", "idosas"]),
    ("Jovem", [FAMILIA], ["jovens"]),
    ("Adulto", [FAMILIA], []),
    ("Casa", [FAMILIA, GERAL], []),
    ("Aniversário", [FAMILIA], []),
    ("Natal", [FAMILIA], []),
    ("Festa", [FAMILIA], []),
    # geral
    ("Sim", [GERAL], []),
    ("Não", [GERAL], []),
    ("Bem", [GERAL], []),
    ("Ruim", [GERAL, SAUDE], ["ruins"]),
    ("Feliz", [GERAL], ["felizes"]),
    ("Triste", [GERAL], ["tristes"]),
    ("Grande (enorme)", [GERAL], []),
    ("Pequeno", [GERAL], ["pequena", "pequenos", "pequenas"]),
    ("Novo", [GERAL], ["nova", "novos", "novas"]),
    ("Bonito", [GERAL], ["bonita", "bonitos", "bonitas"]),
    ("Feio", [GERAL], ["feia"]),
    ("Quente", [GERAL], []),
    ("Frio", [GERAL], ["fria"]),
    ("Rápido", [GERAL], ["rápida"]),
    ("Lento", [GERAL], ["lenta"]),
    ("Ontem", [GERAL], []),
    ("Amanhã", [GERAL], []),
    ("Agora", [GERAL], []),
    ("Manhã", [GERAL], []),
    ("Tarde", [GERAL], []),
    ("Noite", [GERAL], []),
    ("Dia", [GERAL], ["dias"]),
    ("Água", [GERAL], []),
    ("Café", [GERAL], []),
    ("Pão", [GERAL], []),
    ("Leite", [GERAL], []),
    ("Comer", [GERAL], []),
    ("Bebida", [GERAL], []),
    ("Fruta", [GERAL], []),
    ("Banana", [GERAL], []),
    ("Laranja", [GERAL], []),
    ("Abacaxi", [GERAL], []),
    ("Barulho", [GERAL], ["barulhos"]),
    ("Acontecer", [GERAL], []),
    ("Amarelo", [GERAL], ["amarela", "amarelos", "amarelas"]),
    ("Azul", [GERAL], []),
    ("Verde", [GERAL], []),
    ("Vermelho", [GERAL], ["vermelha"]),
    ("Branco", [GERAL], ["branca"]),
    ("Preto", [GERAL], ["preta"]),
    ("Espelho", [GERAL], ["espelhos"]),
    ("Gato", [GERAL], []),
    ("Cavalo", [GERAL], []),
    ("Peixe", [GERAL], []),
    ("Pássaro", [GERAL], []),
    ("Rã (sapo)", [GERAL], ["sapos"]),
    ("Sol", [GERAL], []),
    ("Lua", [GERAL], []),
    ("Chuva", [GERAL], []),
    ("Ir", [GERAL], []),
    ("Quer", [GERAL], ["querer"]),
    ("Gostar", [GERAL], []),
    ("Oi", [GERAL], []),
    ("Parabéns", [GERAL], []),
    ("Ver", [GERAL], []),
    ("Ouvir", [GERAL], []),
    ("Dizer", [GERAL], []),
    ("Saber", [GERAL], []),
    ("Ter", [GERAL], []),
    ("Dar", [GERAL], []),
    ("Pegar", [GERAL], []),
]


def fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def split_class(name: str) -> tuple[str, str | None]:
    match = re.match(r"^(.*?)\s*\((.*)\)\s*$", name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return name.strip(), None


def build(classes: list[str]) -> dict:
    by_slug = {slug(c): c for c in classes}
    signs = []
    seen_glosses: set[str] = set()
    seen_keys: set[str] = set()
    forms_owner: dict[str, str] = {}
    for name, contexts, extra in CURATED:
        video_class = by_slug.get(slug(name))
        if video_class is None:
            raise SystemExit(f"classe inexistente no V-LIBRASIL: {name!r}")
        base, hint = split_class(video_class)
        gloss = base.upper()
        if gloss in seen_glosses or file_key(gloss) in seen_keys:
            raise SystemExit(f"glosa repetida: {gloss}")
        seen_glosses.add(gloss)
        seen_keys.add(file_key(gloss))

        forms = [base.lower()]
        if hint and len(hint.split()) == 1:
            forms.append(hint.lower())
        forms.extend(extra)
        forms = list(dict.fromkeys(fold(f) for f in forms))
        for form in forms:
            if form in forms_owner and forms_owner[form] != gloss:
                raise SystemExit(f"forma {form!r} em {gloss} e em {forms_owner[form]}")
            forms_owner[form] = gloss

        entry = {"gloss": gloss, "video_class": video_class, "pt": forms, "contexts": contexts}
        if hint:
            entry["note"] = f"classe do V-LIBRASIL: {video_class}"
        signs.append(entry)
    return {
        "version": 2,
        "status": "subconjunto curado do V-LIBRASIL; palavras escolhidas pela equipe, rótulos não validados por falante de Libras",
        "source": "V-LIBRASIL (UFPE; uso só para pesquisa e ensino, sem redistribuição)",
        "signs": signs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("annotations", type=Path, help="annotations.csv do V-LIBRASIL")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    with args.annotations.open(encoding="utf-8", newline="") as handle:
        classes = sorted({row["class"] for row in csv.DictReader(handle)})
    data = build(classes)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for sign in data["signs"]:
        for context in sign["contexts"]:
            counts[context] = counts.get(context, 0) + 1
    print(f"{len(data['signs'])} sinais em {args.out}", file=sys.stderr)
    print(counts, file=sys.stderr)


if __name__ == "__main__":
    main()
