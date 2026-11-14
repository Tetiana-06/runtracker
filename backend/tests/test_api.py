"""Смоук-тести HTTP-шару."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_runtracker.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_runner_and_zones():
    response = client.post("/api/runners", json={"name": "Тестовий бігун", "age": 30})
    assert response.status_code == 201
    runner_id = response.json()["id"]

    zones = client.get(f"/api/runners/{runner_id}/zones")
    assert zones.status_code == 200
    assert len(zones.json()) == 5


def test_race_forecast_rejects_unknown_race():
    response = client.get(
        "/api/plans/race/forecast",
        params={"known_distance_km": 10, "known_time_sec": 3000, "race": "ultra"},
    )
    assert response.status_code == 400


def test_runs_intensity_breakdown():
    # Створюємо бігуна
    r_resp = client.post("/api/runners", json={"name": "Бігун для аналізу", "age": 28})
    runner_id = r_resp.json()["id"]

    # Додаємо тренування
    client.post(
        "/api/runs",
        json={
            "runner_id": runner_id,
            "distance_km": 10.0,
            "duration_sec": 3000,
            "avg_hr": 150,
            "workout_type": "tempo",
        },
    )

    response = client.get(f"/api/runs/summary/intensity?runner_id={runner_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["runner_id"] == runner_id
    assert data["total_recorded"] >= 1
    assert data["intensity_distribution"]["tempo"] >= 1

