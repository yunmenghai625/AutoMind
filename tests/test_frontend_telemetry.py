from fastapi.testclient import TestClient


def test_frontend_error_report_accepts_only_non_content_metadata(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telemetry/frontend-errors",
        json={"source": "window.error", "name": "TypeError", "route": "/cockpit"},
    )

    assert response.status_code == 202
    assert response.content == b""


def test_frontend_web_vital_report_validates_rating(client: TestClient) -> None:
    accepted = client.post(
        "/api/v1/telemetry/web-vitals",
        json={"name": "LCP", "value": 1234.5, "rating": "good", "route": "/"},
    )
    rejected = client.post(
        "/api/v1/telemetry/web-vitals",
        json={"name": "LCP", "value": 1234.5, "rating": "unknown", "route": "/"},
    )

    assert accepted.status_code == 202
    assert rejected.status_code == 422


def test_frontend_web_vital_rejects_unknown_metric_names(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telemetry/web-vitals",
        json={"name": "attacker-controlled", "value": 1, "rating": "good", "route": "/"},
    )

    assert response.status_code == 422
