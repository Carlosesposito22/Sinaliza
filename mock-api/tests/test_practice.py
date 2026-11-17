"""Treino fora da trilha: corrigir escrita, revisão dos erros, desafio do dia e dicionário. Regra, não ML."""

import pytest
from fastapi.testclient import TestClient

from sinaliza_mock.server import app, content, store

client = TestClient(app)
HEADERS = {"X-Learner-Id": "treino-1"}


@pytest.fixture(autouse=True)
def clean():
    store.learners.clear()
    store.sessions.clear()
    yield
    store.learners.clear()
    store.sessions.clear()


def complete(lesson_id, correct=10, total=10, mistakes=(), day=None):
    headers = {**HEADERS, **({"X-Mock-Today": day} if day else {})}
    body = {"correct": correct, "total": total, "mistakes": list(mistakes)}
    return client.post(f"/learn/lessons/{lesson_id}/complete", headers=headers, json=body).json()


def finish_practice(session, wrong_ids=(), day=None):
    headers = {**HEADERS, **({"X-Mock-Today": day} if day else {})}
    total = len(session["exercises"])
    body = {"correct": total - len(wrong_ids), "total": total, "mistakes": list(wrong_ids)}
    return client.post(f"/learn/practice/{session['id']}/complete", headers=headers, json=body)


def exercise_for(lesson_id, ex_type, gloss):
    lesson = content.lessons[lesson_id]
    return next(e for e in lesson.exercises if e.type == ex_type and gloss in getattr(e, "glosses", [getattr(e, "gloss", None)]))


# ---------------------------------------------------------------- escrever (sign_to_text)


def test_exercicio_de_escrever_tem_o_texto_e_e_corrigido_pela_api():
    ex = next(e for e in content.lessons["escola-1"].exercises if e.type == "sign_to_text")
    assert ex.kind == "sign" and len(ex.glosses) == 1 and ex.text == content.word(ex.glosses[0])
    ok = client.post("/learn/check", json={"glosses": ex.glosses, "text": ex.text, "answer": ex.text.upper()}).json()
    assert ok["correct"] and ok["score"] == 1 and ok["expected_text"] == ex.text
    wrong = client.post("/learn/check", json={"glosses": ex.glosses, "text": ex.text, "answer": "xícara"}).json()
    assert not wrong["correct"] and wrong["extra_words"] == ["xicara"] and not wrong["signs"][0]["correct"]


def test_escrever_frase_da_nota_parcial():
    body = {"glosses": ["CRIANÇA", "QUER", "IR", "BANHEIRO"], "text": "A criança quer ir ao banheiro.", "answer": "a criança quer"}
    result = client.post("/learn/check", json=body).json()
    assert not result["correct"] and result["score"] == 0.5


def test_check_recusa_sinal_fora_do_vocabulario():
    assert client.post("/learn/check", json={"glosses": ["PROFESSOR"], "text": "professora", "answer": "x"}).status_code == 422


# ---------------------------------------------------------------- revisão


def test_sem_erros_nao_ha_revisao():
    assert client.get("/learn/review", headers=HEADERS).status_code == 409
    assert client.get("/learn/progress", headers=HEADERS).json()["review_signs"] == 0


def test_erro_na_aula_vai_para_a_revisao_e_sai_ao_acertar():
    wrong = exercise_for("escola-1", "sign_to_word", "LIVRO")
    progress = complete("escola-1", 12, 15, [wrong.id])["progress"]
    assert progress["review_signs"] == 1

    session = client.get("/learn/review", headers=HEADERS).json()
    assert session["kind"] == "review" and session["glosses"] == ["LIVRO"]
    assert [e["type"] for e in session["exercises"]] == ["sign_to_word", "sign_to_text"]
    result = finish_practice(session).json()
    assert result["passed"] and result["cleared_glosses"] == ["LIVRO"] and result["xp_gained"] == 10
    assert result["progress"]["review_signs"] == 0
    assert "revisor" in {a["id"] for a in result["new_achievements"]}
    assert finish_practice(session).status_code == 404  # a sessão é de uso único


def test_errar_de_novo_na_revisao_mantem_o_sinal():
    complete("escola-1", 12, 15, [exercise_for("escola-1", "sign_to_word", "LIVRO").id])
    session = client.get("/learn/review", headers=HEADERS).json()
    result = finish_practice(session, [session["exercises"][1]["id"]]).json()
    assert result["cleared_glosses"] == [] and result["progress"]["review_signs"] == 1


def test_sinal_errado_na_prova_vai_para_a_revisao():
    for lid in content.theme_lessons["escola"]:
        complete(lid)
    items = content.exams["escola"]
    answers = [{"question_id": i.id, "text": i.expected_text} for i in items]
    answers[0]["text"] = ""  # erra a primeira questão (um sinal só)
    result = client.post("/learn/themes/escola/exam", headers=HEADERS, json={"answers": answers}).json()
    assert result["progress"]["review_signs"] == 1
    review = client.get("/learn/review", headers=HEADERS).json()
    assert review["glosses"] == items[0].glosses


# ---------------------------------------------------------------- desafio do dia


def test_desafio_precisa_de_aula_feita():
    assert client.get("/learn/challenge", headers=HEADERS).status_code == 409
    assert not client.get("/learn/progress", headers=HEADERS).json()["challenge_available"]


def test_desafio_usa_sinais_vistos_e_e_o_mesmo_no_dia():
    complete("escola-1", day="2026-11-17")
    day = {**HEADERS, "X-Mock-Today": "2026-11-17"}
    first = client.get("/learn/challenge", headers=day).json()
    again = client.get("/learn/challenge", headers=day).json()
    assert first["glosses"] == again["glosses"] and set(first["glosses"]) <= set(content.lesson_glosses["escola-1"])
    assert len(first["exercises"]) == len(first["glosses"]) == 4
    assert {e["type"] for e in first["exercises"]} <= {"sign_to_word", "sign_to_text", "word_to_sign"}


def test_desafio_da_xp_uma_vez_por_dia():
    complete("escola-1", day="2026-11-17")
    day = {**HEADERS, "X-Mock-Today": "2026-11-17"}
    result = finish_practice(client.get("/learn/challenge", headers=day).json(), day="2026-11-17").json()
    assert result["passed"] and result["xp_gained"] == 15 and result["progress"]["challenge_done_today"]
    assert "desafio-do-dia" in {a["id"] for a in result["new_achievements"]}
    session = client.get("/learn/challenge", headers=day).json()
    assert session["completed_today"]
    assert finish_practice(session, day="2026-11-17").json()["xp_gained"] == 0
    tomorrow = client.get("/learn/progress", headers={**HEADERS, "X-Mock-Today": "2026-11-18"}).json()
    assert not tomorrow["challenge_done_today"]


def test_erro_no_desafio_vai_para_a_revisao():
    complete("escola-1")
    session = client.get("/learn/challenge", headers=HEADERS).json()
    result = finish_practice(session, [session["exercises"][0]["id"]]).json()
    assert result["progress"]["review_signs"] == 1


# ---------------------------------------------------------------- dicionário


def test_dicionario_tem_os_210_sinais_e_marca_os_vistos():
    body = client.get("/learn/dictionary", headers=HEADERS).json()
    assert body["total"] == 210 and body["seen_count"] == 0
    complete("escola-1")
    body = client.get("/learn/dictionary", headers=HEADERS).json()
    seen = [s for s in body["signs"] if s["seen"]]
    assert body["seen_count"] == 4 and {s["gloss"] for s in seen} == set(content.lesson_glosses["escola-1"])
    assert body["signs"][:4] == seen  # vistos primeiro
    livro = next(s for s in body["signs"] if s["gloss"] == "LIVRO")
    assert livro["theme_ids"] == ["escola"] and "livro" in livro["forms"]
    fora = next(s for s in body["signs"] if not s["theme_ids"])
    assert not fora["seen"]  # sinal do vocabulário que nenhum tema ensina ainda


def test_erro_em_ligar_pares_nao_vai_para_a_revisao():
    # O erro num par não diz qual sinal a pessoa confundiu: não põe os 4 sinais na fila.
    match = next(e for e in content.lessons["escola-1"].exercises if e.type == "match_pairs")
    assert complete("escola-1", 14, 15, [match.id])["progress"]["review_signs"] == 0
