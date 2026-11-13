from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_salud():
    response = client.get("/api/salud")
    assert response.status_code == 200
    assert response.json() == {"estado": "ok"}
