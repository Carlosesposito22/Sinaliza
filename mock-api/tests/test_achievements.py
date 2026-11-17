import pytest
from fastapi.testclient import TestClient

from sinaliza_mock.achievements import Stats, catalog
from sinaliza_mock.server import app, content, store

client = TestClient(app)
HEADERS = {"X-Learner-Id": "conquistas-1"}


@pytest.fixture(autouse=True)
def clean():
    store.learners.clear()
    yield
    store.learners.clear()


def complete(lesson_id, correct=10, total=10, day=None):
    headers = {**HEADERS, **({"X-Mock-Today": day} if day else {})}
    return client.post(f"/learn/lessons/{lesson_id}/complete", headers=headers, json={"correct": correct, "total": total}).json()


def finish(theme_id, correct=10):
    return [complete(lid, correct) for lid in content.theme_lessons[theme_id]][-1]


def exam(theme_id, wrong=0):
    items = content.exams[theme_id]
    answers = [{"question_id": i.id, "text": "" if n < wrong else i.expected_text} for n, i in enumerate(items)]
    return client.post(f"/learn/themes/{theme_id}/exam", headers=HEADERS, json={"answers": answers}).json()


def ids(result):
    return {a["id"] for a in result["new_achievements"]}


def test_catalogo_tem_ids_unicos_e_um_trofeu_por_tema():
    items = catalog([(t.id, t.title) for t in content.themes])
    assert len({i.id for i in items}) == len(items)
    assert {f"tema-{t.id}" for t in content.themes} <= {i.id for i in items}


def test_contagem_respeita_o_alvo():
    persistente = next(i for i in catalog([]) if i.id == "persistente")
    assert persistente.check(Stats(exams_taken=2)) == (False, 2)
    assert persistente.check(Stats(exams_taken=9)) == (True, 5)


def test_lista_comeca_toda_bloqueada_com_progresso_zerado():
    body = client.get("/learn/achievements", headers=HEADERS).json()
    assert body["unlocked_count"] == 0 and body["total"] == len(body["achievements"]) >= 10
    assert all(not a["unlocked"] and a["unlocked_at"] is None for a in body["achievements"])
    # todo mundo começa no nível 1; o resto começa do zero
    assert all(a["current"] == (1 if a["id"] == "nivel-3" else 0) for a in body["achievements"])
    assert client.get("/learn/achievements").status_code == 400


def test_primeira_aula_perfeita_da_duas_medalhas_uma_vez_so():
    first = content.theme_lessons["escola"][0]
    assert ids(complete(first, 13, 13)) == {"primeira-aula", "aula-perfeita"}
    assert ids(complete(first, 13, 13)) == set()  # não ganha de novo


def test_aula_reprovada_nao_da_conquista():
    assert complete(content.theme_lessons["escola"][0], 2, 13)["new_achievements"] == []


def test_nota_maxima_de_primeira():
    finish("escola")
    result = exam("escola")
    assert {"primeira-prova", "aprovado", "nota-maxima", "de-primeira", "tema-escola"} <= ids(result)
    assert "volta-por-cima" not in ids(result)
    body = client.get("/learn/achievements", headers=HEADERS).json()
    trilha = next(a for a in body["achievements"] if a["id"] == "trilha-completa")
    assert not trilha["unlocked"] and (trilha["current"], trilha["target"]) == (1, 3)


def test_volta_por_cima_depois_de_reprovar():
    finish("escola")
    failed = exam("escola", wrong=16)
    assert ids(failed) == {"primeira-prova"}
    finish("escola")
    passed = exam("escola", wrong=4)
    assert {"aprovado", "volta-por-cima", "tema-escola"} <= ids(passed)
    assert "de-primeira" not in ids(passed) and "nota-maxima" not in ids(passed)


def test_sequencia_de_tres_dias():
    lessons = content.theme_lessons["escola"]
    assert "sequencia-3" not in ids(complete(lessons[0], day="2026-11-01"))
    complete(lessons[1], day="2026-11-02")
    assert "sequencia-3" in ids(complete(lessons[2], day="2026-11-03"))
    body = client.get("/learn/achievements", headers={**HEADERS, "X-Mock-Today": "2026-11-03"}).json()
    seq = next(a for a in body["achievements"] if a["id"] == "sequencia-3")
    assert seq["unlocked_at"] == "2026-11-03"


def test_trilha_completa():
    for theme in content.theme_order:
        finish(theme)
        last = exam(theme)
    assert "trilha-completa" in ids(last)
