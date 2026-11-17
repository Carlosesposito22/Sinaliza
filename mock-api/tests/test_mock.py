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
    assert body == {"status": "ok", "contract_version": "2", "mock": True}


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


# ---------------------------------------------------------------- conteúdo da trilha


def all_glosses(payload: dict) -> list[str]:
    used = [payload.get("gloss")] + list(payload.get("glosses", []))
    used += [o.get("gloss") for o in payload.get("options", [])] + [p["gloss"] for p in payload.get("pairs", [])]
    return [g for g in used if g]


def test_trilha_so_usa_o_vocabulario_curado():
    trilha = content_module.load_trilha()
    vocabulary = vocabulary_glosses()
    assert set(trilha["signs"]) <= vocabulary, "a trilha só pode usar os 210 sinais de data/vocabulary.json"
    for lesson in content.lessons.values():
        for exercise in lesson.exercises:
            payload = exercise.model_dump()
            assert all(g in trilha["signs"] for g in all_glosses(payload)), (lesson.id, payload["id"])


def test_glosa_fora_do_vocabulario_impede_o_mock_de_subir():
    trilha = content_module.load_trilha()
    trilha["signs"]["PROFESSOR"] = {"word": "professora", "accept": []}
    with pytest.raises(ValueError, match="PROFESSOR"):
        content_module.Content(trilha, content_module.load_signs())


def test_formas_do_vocabulario_entram_nas_respostas_aceitas():
    assert "entender" in content.accept("COMPREENDER") and "compreender" in content.accept("COMPREENDER")
    assert "vou" in content.accept("IR")


def test_frases_so_usam_sinais_ensinados_ate_o_tema():
    ensinados: set[str] = set()
    for theme in content_module.load_trilha()["themes"]:
        ensinados |= {g for lesson in theme["lessons"] for g in lesson.get("signs", [])}
        for lesson in theme["lessons"]:
            for phrase in lesson.get("phrases", []):
                assert set(phrase["glosses"]) <= ensinados, (theme["id"], phrase["text"])


def test_gabarito_da_prova_tira_nota_maxima():
    for theme_id, items in content.exams.items():
        for item in items:
            grade = content_module_grade(item)
            assert grade == 1, (theme_id, item.expected_text, grade)


def content_module_grade(item) -> float:
    from sinaliza_mock.grading import grade_answer

    return grade_answer(item.expected_text, item.glosses, content.accept_table, item.expected_text).score


def test_exercicios_sao_validos():
    for lesson in content.lessons.values():
        ids = [e.id for e in lesson.exercises]
        assert len(ids) == len(set(ids))
        for exercise in lesson.exercises:
            if exercise.type in ("sign_to_word", "word_to_sign", "phrase_to_text"):
                option_ids = [o.id for o in exercise.options]
                assert exercise.correct_option_id in option_ids
                assert len(option_ids) == len(set(option_ids)) == 3
                labels = [getattr(o, "text", None) or o.gloss for o in exercise.options]
                assert len(set(labels)) == 3
            if exercise.type == "match_pairs":
                assert len({p.text for p in exercise.pairs}) == len(exercise.pairs) == 4


def test_path_tem_temas_com_aulas_e_prova():
    path = client.get("/learn/path").json()
    assert path["disclaimer"] and [t["id"] for t in path["themes"]][:3] == ["escola", "familia", "saude"]
    escola = path["themes"][0]
    assert [lesson["kind"] for lesson in escola["lessons"]] == ["signs", "signs", "signs", "phrases"]
    assert escola["exam"] == {"n_questions": 16, "pass_score": 0.7, "xp_reward": 50}
    first = escola["lessons"][0]
    lesson = client.get(f"/learn/lessons/{first['id']}").json()
    assert lesson["theme_id"] == "escola" and len(lesson["exercises"]) == first["n_exercises"] == 15
    assert [e["type"] for e in lesson["exercises"]].count("sign_to_text") == 2
    frases = client.get("/learn/lessons/escola-4").json()
    assert {e["type"] for e in frases["exercises"]} == {"learn_phrase", "phrase_to_text", "sign_to_text"}
    assert client.get("/learn/lessons/nao-existe").status_code == 404


# ---------------------------------------------------------------- progresso, aulas e prova


def complete(lesson_id: str, correct: int = 10, total: int = 10, headers=HEADERS):
    return client.post(f"/learn/lessons/{lesson_id}/complete", headers=headers, json={"correct": correct, "total": total})


def finish_lessons(theme_id: str) -> dict:
    results = [complete(lid).json() for lid in content.theme_lessons[theme_id]]
    return results[-1]


def answers_for(theme_id: str, wrong: int = 0) -> dict:
    """Responde a prova com o gabarito; as `wrong` primeiras questões ficam em branco."""
    items = content.exams[theme_id]
    return {"answers": [{"question_id": i.id, "text": "" if n < wrong else i.expected_text} for n, i in enumerate(items)]}


def submit(theme_id: str, body: dict):
    return client.post(f"/learn/themes/{theme_id}/exam", headers=HEADERS, json=body)


def test_progresso_inicial_so_libera_a_primeira_aula_do_primeiro_tema():
    progress = client.get("/learn/progress", headers=HEADERS).json()
    statuses = [p["status"] for p in progress["lessons"].values()]
    assert statuses[0] == "available" and set(statuses[1:]) == {"locked"}
    assert [t["status"] for t in progress["themes"].values()] == ["learning", "locked", "locked"]
    assert progress["xp"] == 0 and progress["level"] == 1 and progress["streak_days"] == 0


def test_exige_learner_id():
    assert client.get("/learn/progress").status_code == 400
    assert client.get("/learn/themes/escola/exam").status_code == 400


def test_concluir_aula_da_xp_estrelas_e_desbloqueia_a_proxima():
    first, second = content.theme_lessons["escola"][:2]
    assert complete(second, 5, 5).status_code == 409
    result = complete(first, 13, 13).json()
    assert result["passed"] and result["stars"] == 3 and result["bonus_perfect"]
    assert result["xp_gained"] == 25 and result["unlocked_lesson_ids"] == [second]
    assert result["goal_reached_now"] and result["progress"]["streak_days"] == 1
    assert result["progress"]["lessons"][first]["status"] == "completed"
    assert not result["exam_unlocked"]


def test_reprovar_aula_nao_da_xp_nem_desbloqueia():
    first = content.theme_lessons["escola"][0]
    result = complete(first, 5, 13).json()
    assert not result["passed"] and result["xp_gained"] == 0 and result["stars"] == 0
    assert result["unlocked_lesson_ids"] == [] and result["progress"]["streak_days"] == 0


def test_prova_so_abre_depois_de_todas_as_aulas():
    assert client.get("/learn/themes/escola/exam", headers=HEADERS).status_code == 409
    assert submit("escola", {"answers": []}).status_code == 409
    last = finish_lessons("escola")
    assert last["exam_unlocked"] and last["progress"]["themes"]["escola"]["status"] == "exam_ready"
    exam = client.get("/learn/themes/escola/exam", headers=HEADERS).json()
    assert exam["pass_score"] == 0.7 and len(exam["questions"]) == 16
    assert {q["kind"] for q in exam["questions"]} == {"sign", "phrase"}
    dumped = json.dumps(exam, ensure_ascii=False).lower()
    assert "expected_text" not in dumped and "criança quer ir ao banheiro" not in dumped  # sem gabarito nem legenda
    assert client.get("/learn/themes/nao-existe/exam", headers=HEADERS).status_code == 404


def test_aprovar_na_prova_libera_o_proximo_tema():
    finish_lessons("escola")
    assert complete(content.theme_lessons["familia"][0]).status_code == 409
    result = submit("escola", answers_for("escola", wrong=4)).json()
    assert result["score"] == 0.75 and result["passed"] and result["xp_gained"] == 50
    assert result["unlocked_theme_ids"] == ["familia"] and result["must_redo_lesson_ids"] == []
    themes = result["progress"]["themes"]
    assert themes["escola"]["status"] == "passed" and themes["familia"]["status"] == "learning"
    assert result["progress"]["lessons"][content.theme_lessons["familia"][0]]["status"] == "available"
    again = submit("escola", answers_for("escola")).json()
    assert again["passed"] and again["xp_gained"] == 0
    assert again["progress"]["themes"]["escola"]["best_exam_score"] == 1.0


def test_reprovar_na_prova_obriga_a_refazer_as_aulas():
    lessons = content.theme_lessons["escola"]
    finish_lessons("escola")
    result = submit("escola", answers_for("escola", wrong=8)).json()
    assert result["score"] == 0.5 and not result["passed"] and result["xp_gained"] == 0
    assert result["must_redo_lesson_ids"] == lessons and result["unlocked_theme_ids"] == []
    progress = result["progress"]
    escola = progress["themes"]["escola"]
    assert escola["status"] == "learning" and escola["must_redo"]
    assert escola["last_exam_score"] == 0.5 and escola["exam_attempts"] == 1
    assert all(progress["lessons"][lid]["status"] == "available" for lid in lessons)
    assert all(progress["lessons"][lid]["needs_redo"] for lid in lessons)
    assert progress["lessons"][lessons[0]]["stars"] > 0  # as estrelas antigas continuam
    assert client.get("/learn/themes/escola/exam", headers=HEADERS).status_code == 409

    # na revisão as aulas ficam abertas fora de ordem; a prova volta quando todas forem refeitas
    for lid in reversed(lessons):
        last = complete(lid).json()
    assert last["exam_unlocked"] and not last["progress"]["themes"]["escola"]["must_redo"]
    approved = submit("escola", answers_for("escola")).json()
    assert approved["passed"] and approved["unlocked_theme_ids"] == ["familia"]


def test_questao_sem_resposta_vale_zero_e_questao_alheia_e_rejeitada():
    finish_lessons("escola")
    empty = submit("escola", {"answers": []}).json()
    assert empty["score"] == 0 and not empty["passed"]
    finish_lessons("escola")
    assert submit("escola", {"answers": [{"question_id": "saude-q1", "text": "x"}]}).status_code == 422


def test_correcao_mostra_o_gabarito_por_sinal():
    finish_lessons("escola")
    item = next(i for i in content.exams["escola"] if i.expected_text.startswith("A criança quer ir"))
    result = submit("escola", {"answers": [{"question_id": item.id, "text": "crianças querem ir cozinha"}]}).json()
    question = next(q for q in result["questions"] if q["question_id"] == item.id)
    assert question["expected_text"] == "A criança quer ir ao banheiro."
    assert [(s["gloss"], s["correct"]) for s in question["signs"]] == [
        ("CRIANÇA", True), ("QUER", True), ("IR", True), ("BANHEIRO", False)
    ]
    assert question["extra_words"] == ["cozinha"] and question["score"] == 0.6


def test_sequencia_de_dias():
    first, second, third = content.theme_lessons["escola"][:3]

    def on(lesson, day):
        return complete(lesson, headers={**HEADERS, "X-Mock-Today": day}).json()

    assert on(first, "2026-11-02")["progress"]["streak_days"] == 1
    assert on(second, "2026-11-03")["progress"]["streak_days"] == 2
    lido = client.get("/learn/progress", headers={**HEADERS, "X-Mock-Today": "2026-11-06"}).json()
    assert lido["streak_days"] == 0 and lido["best_streak"] == 2
    assert on(third, "2026-11-06")["progress"]["streak_days"] == 1


def test_nivel_sobe_a_cada_100_xp():
    last = finish_lessons("escola")  # 4 aulas perfeitas: 4 × 25 = 100 XP
    assert last["progress"]["xp"] == 100 and last["progress"]["level"] == 2 and last["level_up"]
    result = submit("escola", answers_for("escola")).json()
    assert result["progress"]["xp"] == 150 and not result["level_up"]


def test_reset_zera_o_progresso():
    complete(content.theme_lessons["escola"][0])
    assert client.delete("/learn/progress", headers=HEADERS).status_code == 204
    assert client.get("/learn/progress", headers=HEADERS).json()["xp"] == 0


def test_openapi_exportado_esta_em_dia():
    from pathlib import Path

    exported = Path(__file__).resolve().parents[2] / "docs" / "openapi-mock.json"
    if exported.exists():
        assert json.loads(exported.read_text(encoding="utf-8")) == app.openapi(), (
            "docs/openapi-mock.json desatualizado: rode `python -m sinaliza_mock.export_openapi`"
        )
