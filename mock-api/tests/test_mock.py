import json

import pytest
from fastapi.testclient import TestClient

from sinaliza_mock import content as content_module
from sinaliza_mock.server import app, content, store

client = TestClient(app)
HEADERS = {"X-Learner-Id": "teste-1"}


@pytest.fixture(autouse=True)
def clean():
    store.learners.clear()
    yield
    store.learners.clear()


def vocabulary_glosses():
    return {s["gloss"] for s in content_module.load_signs()}


def test_health_informa_contrato_e_mock():
    body = client.get("/health").json()
    assert body == {"status": "ok", "contract_version": "1", "mock": True}


def test_translate_tem_os_campos_novos_do_contrato():
    response = client.post("/translate", json={"text": "A criança vai à escola"})
    assert response.status_code == 200
    assert response.headers["X-Sinaliza-Mock"] == "1"
    body = response.json()
    assert body["model_version"] == "mock" and body["pose"] is None and body["latency_ms"] >= 1
    assert body["glosses"]
    for match in body["matches"]:
        assert match["decision"] in ("MANTER", "DESCARTAR")
        assert 0 <= match["probability"] <= 1
    assert {"word", "gloss", "kind", "score"} <= set(body["matches"][0])


def test_translate_erros_seguem_o_formato_detail():
    assert client.post("/translate", json={"text": "   "}).status_code == 422
    sem_sinais = client.post("/translate", json={"text": "xyzzy plugh"})
    assert sem_sinais.status_code == 422 and isinstance(sem_sinais.json()["detail"], str)


def test_vocabulary_e_categories_existem():
    assert len(client.get("/vocabulary").json()["signs"]) == 210
    assert client.get("/categories").json()["categories"]


def test_trilha_so_usa_glosas_do_vocabulario():
    glosses = vocabulary_glosses()
    for lesson in content.lessons.values():
        for exercise in lesson.exercises:
            payload = exercise.model_dump()
            used = [payload.get("gloss")] + [o.get("gloss") for o in payload.get("options", [])] + [
                p["gloss"] for p in payload.get("pairs", [])
            ]
            assert all(g in glosses for g in used if g), (lesson.id, payload["id"])


def test_exercicios_sao_validos():
    for lesson in content.lessons.values():
        ids = [e.id for e in lesson.exercises]
        assert len(ids) == len(set(ids))
        for exercise in lesson.exercises:
            if exercise.type in ("sign_to_word", "word_to_sign"):
                option_ids = [o.id for o in exercise.options]
                assert exercise.correct_option_id in option_ids
                assert len(option_ids) == len(set(option_ids)) == 3
                labels = [getattr(o, "text", None) or o.gloss for o in exercise.options]
                assert len(set(labels)) == 3
            if exercise.type == "match_pairs":
                assert len({p.text for p in exercise.pairs}) == len(exercise.pairs) == 4


def test_path_e_lesson_batem():
    path = client.get("/learn/path").json()
    assert path["disclaimer"] and len(path["units"]) >= 4
    first = path["units"][0]["lessons"][0]
    lesson = client.get(f"/learn/lessons/{first['id']}").json()
    assert len(lesson["exercises"]) == first["n_exercises"]
    assert client.get("/learn/lessons/nao-existe").status_code == 404


def test_progresso_inicial_so_libera_a_primeira_licao():
    progress = client.get("/learn/progress", headers=HEADERS).json()
    statuses = [p["status"] for p in progress["lessons"].values()]
    assert statuses[0] == "available" and set(statuses[1:]) == {"locked"}
    assert progress["xp"] == 0 and progress["level"] == 1 and progress["streak_days"] == 0


def test_exige_learner_id():
    assert client.get("/learn/progress").status_code == 400


def test_concluir_licao_da_xp_estrelas_e_desbloqueia_a_proxima():
    first, second = content.order[:2]
    assert client.post(f"/learn/lessons/{second}/complete", headers=HEADERS, json={"correct": 5, "total": 5}).status_code == 409
    result = client.post(f"/learn/lessons/{first}/complete", headers=HEADERS, json={"correct": 13, "total": 13}).json()
    assert result["passed"] and result["stars"] == 3 and result["bonus_perfect"]
    assert result["xp_gained"] == 25 and result["unlocked_lesson_ids"] == [second]
    assert result["goal_reached_now"] and result["progress"]["streak_days"] == 1
    assert result["progress"]["lessons"][first]["status"] == "completed"


def test_reprovar_nao_da_xp_nem_desbloqueia():
    first = content.order[0]
    result = client.post(f"/learn/lessons/{first}/complete", headers=HEADERS, json={"correct": 5, "total": 13}).json()
    assert not result["passed"] and result["xp_gained"] == 0 and result["stars"] == 0
    assert result["unlocked_lesson_ids"] == [] and result["progress"]["streak_days"] == 0


def test_sequencia_de_dias():
    first, second, third = content.order[:3]
    done = {"correct": 10, "total": 10}

    def complete(lesson, day):
        return client.post(f"/learn/lessons/{lesson}/complete", headers={**HEADERS, "X-Mock-Today": day}, json=done).json()

    assert complete(first, "2026-11-02")["progress"]["streak_days"] == 1
    assert complete(second, "2026-11-03")["progress"]["streak_days"] == 2
    lido = client.get("/learn/progress", headers={**HEADERS, "X-Mock-Today": "2026-11-06"}).json()
    assert lido["streak_days"] == 0 and lido["best_streak"] == 2
    assert complete(third, "2026-11-06")["progress"]["streak_days"] == 1


def test_nivel_sobe_a_cada_100_xp():
    xp, day = 0, 1
    for lesson in content.order[:5]:
        result = client.post(f"/learn/lessons/{lesson}/complete", headers=HEADERS, json={"correct": 10, "total": 10}).json()
        xp += result["xp_gained"]
        if xp >= 100:
            assert result["level_up"] and result["progress"]["level"] == 2
            break
    assert xp >= 100


def test_reset_zera_o_progresso():
    first = content.order[0]
    client.post(f"/learn/lessons/{first}/complete", headers=HEADERS, json={"correct": 10, "total": 10})
    assert client.delete("/learn/progress", headers=HEADERS).status_code == 204
    assert client.get("/learn/progress", headers=HEADERS).json()["xp"] == 0


def test_openapi_exportado_esta_em_dia():
    from pathlib import Path

    exported = Path(__file__).resolve().parents[2] / "docs" / "openapi-mock.json"
    if exported.exists():
        assert json.loads(exported.read_text(encoding="utf-8")) == app.openapi(), (
            "docs/openapi-mock.json desatualizado: rode `python -m sinaliza_mock.export_openapi`"
        )
