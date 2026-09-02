from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rejects_short_question():
    response = client.post("/api/research", json={"question": "short"})
    assert response.status_code == 422
