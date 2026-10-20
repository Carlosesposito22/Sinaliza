from fastapi.testclient import TestClient

from app.main import app
from app.pose_format import NUM_KEYPOINTS

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_translate_returns_glosses_matches_and_pose_sequence():
    response = client.post("/translate", json={"text": "O filho tem medo da vacina."})
    assert response.status_code == 200
    body = response.json()
    assert body["glosses"] == ["FILHO", "MEDO", "VACINA"]
    kinds = {m["word"]: m["kind"] for m in body["matches"]}
    assert kinds == {
        "O": "function",
        "filho": "exact",
        "tem": "ignored",
        "medo": "exact",
        "da": "function",
        "vacina": "exact",
    }
    pose = body["pose"]
    assert pose["fps"] > 0
    assert len(pose["frames"]) == 3 * pose["fps"]
    for frame in pose["frames"]:
        assert len(frame) == NUM_KEYPOINTS
        assert all(len(point) == 3 for point in frame)


def test_translate_maps_inflection_by_embedding_and_reports_it():
    body = client.post("/translate", json={"text": "alunoss vacinando"}).json()
    assert body["glosses"] == ["ALUNO", "VACINA"]
    assert [(m["word"], m["kind"]) for m in body["matches"]] == [("alunoss", "approx"), ("vacinando", "approx")]
    assert all(0.65 <= m["score"] < 1 for m in body["matches"])


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


def test_vocabulary_lists_the_20_signs_with_forms_and_notes():
    signs = {s["gloss"]: s for s in client.get("/vocabulary").json()["signs"]}
    assert len(signs) == 20
    assert signs["BALA"]["forms"] == ["bala", "balas"]
    assert signs["BANCO"]["note"]
    assert signs["ALUNO"]["contexts"] == ["escola"]


def test_categories_follow_vocabulary_contexts_and_every_phrase_translates():
    categories = client.get("/categories").json()["categories"]
    assert [c["id"] for c in categories] == ["escola", "saude", "servicos", "trabalho", "familia", "geral"]
    for category in categories:
        assert category["phrases"]
        for phrase in category["phrases"][:3]:
            body = client.post("/translate", json={"text": phrase["text"]}).json()
            assert body["glosses"] == phrase["glosses"]
