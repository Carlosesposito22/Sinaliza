from fastapi.testclient import TestClient

from app.main import app
from app.pose_format import NUM_KEYPOINTS

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_translate_returns_pose_sequence():
    response = client.post("/translate", json={"text": "Olá, mundo!"})
    assert response.status_code == 200
    body = response.json()
    assert body["glosses"] == ["OLÁ", "MUNDO"]
    pose = body["pose"]
    assert pose["fps"] > 0
    assert len(pose["frames"]) == 2 * pose["fps"]
    for frame in pose["frames"]:
        assert len(frame) == NUM_KEYPOINTS
        assert all(len(point) == 3 for point in frame)


def test_translate_rejects_blank_text():
    assert client.post("/translate", json={"text": "   "}).status_code == 422


def test_translate_rejects_text_without_words():
    assert client.post("/translate", json={"text": "?!..."}).status_code == 422
