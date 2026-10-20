from fastapi.testclient import TestClient

from app.main import app
from app.pose_format import LOWER_BODY_START, NUM_KEYPOINTS, POSE_COUNT

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_translate_returns_glosses_matches_and_pose_sequence():
    response = client.post("/translate", json={"text": "O filho está com dor de cabeça."})
    assert response.status_code == 200
    body = response.json()
    assert body["glosses"] == ["FILHO", "DOR DE CABEÇA"]
    assert [(m["word"], m["kind"]) for m in body["matches"]] == [
        ("O", "function"),
        ("filho", "exact"),
        ("está", "function"),
        ("com", "function"),
        ("dor de cabeça", "exact"),
    ]
    pose = body["pose"]
    assert pose["fps"] > 0
    assert len(pose["frames"]) == 2 * pose["fps"]
    for frame in pose["frames"]:
        assert len(frame) == NUM_KEYPOINTS
        assert all(len(point) == 3 for point in frame)


def test_translate_uses_lemmas_for_inflected_words():
    body = client.post("/translate", json={"text": "As crianças aconteceram."}).json()
    assert body["glosses"] == ["CRIANÇA", "ACONTECER"]
    assert {m["kind"] for m in body["matches"] if m["gloss"]} == {"exact"}


def test_translate_maps_a_typo_by_embedding_and_reports_it():
    body = client.post("/translate", json={"text": "O filho escolla"}).json()
    assert body["glosses"] == ["FILHO", "ESCOLA"]
    approx = [m for m in body["matches"] if m["kind"] == "approx"]
    assert [(m["word"], m["gloss"]) for m in approx] == [("escolla", "ESCOLA")]
    assert 0.7 <= approx[0]["score"] < 1


def test_translate_rejects_blank_text():
    assert client.post("/translate", json={"text": "   "}).status_code == 422


def test_translate_rejects_text_without_words():
    response = client.post("/translate", json={"text": "?!..."})
    assert response.status_code == 422
    assert response.json()["detail"] == "o texto não contém palavras"


def test_translate_rejects_text_without_any_known_sign():
    response = client.post("/translate", json={"text": "Olá, mundo!"})
    assert response.status_code == 422
    assert "vocabulário" in response.json()["detail"]


def test_stub_pose_has_shoulder_origin_and_no_lower_body():
    frames = client.post("/translate", json={"text": "casa"}).json()["pose"]["frames"]
    for frame in frames:
        left, right = frame[11], frame[12]
        assert abs((left[1] + right[1]) / 2) < 1e-3  # meio dos ombros em y = 0
        assert abs((left[0] + right[0]) / 2) < 1e-3
        assert all(point == [0.0, 0.0, 0.0] for point in frame[LOWER_BODY_START:POSE_COUNT])
        assert frame[0][1] > 0  # nariz acima dos ombros


def test_vocabulary_lists_signs_with_forms_notes_and_video_class():
    signs = {s["gloss"]: s for s in client.get("/vocabulary").json()["signs"]}
    assert len(signs) >= 100
    assert "dor de cabeça" in signs["DOR DE CABEÇA"]["forms"]
    assert {"rã", "sapo"} <= set(signs["RÃ"]["forms"])
    assert signs["RÃ"]["note"]
    assert "escola" in signs["BANHEIRO"]["contexts"]


def test_categories_follow_vocabulary_contexts_and_every_phrase_translates():
    categories = client.get("/categories").json()["categories"]
    assert [c["id"] for c in categories] == ["escola", "saude", "servicos", "trabalho", "familia", "geral"]
    for category in categories:
        assert category["phrases"]
        for phrase in category["phrases"][:3]:
            body = client.post("/translate", json={"text": phrase["text"]}).json()
            assert body["glosses"] == phrase["glosses"]
