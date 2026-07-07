from flask import Flask

from app.routes.jack_os_api import jack_os_api


def _app():
    app = Flask(__name__)
    app.register_blueprint(jack_os_api)
    return app


def test_dashboard_preview_is_public():
    client = _app().test_client()

    response = client.get("/api/jack-os/dashboard")

    assert response.status_code == 200
    assert b"Jack Personal AI Capital OS" in response.data
    assert b"No broker execution in v1" in response.data


def test_tools_is_public_and_returns_disabled_registry():
    client = _app().test_client()

    response = client.get("/api/jack-os/tools")

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 1
    assert body["data"]["enabled"] is False
    assert body["data"]["auth_required"] is False
    assert body["data"]["tools"]
    assert all(tool["enabled"] is False for tool in body["data"]["tools"])


def test_grade_setup_is_public_and_accepts_bad_payload_safely():
    client = _app().test_client()

    response = client.post("/api/jack-os/grade-setup", json={"score": "bad"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["auth_required"] is False
    assert body["data"]["score"] == 0
    assert body["data"]["grade"] == "no_trade"


def test_risk_decision_is_public_and_accepts_bad_payload_safely():
    client = _app().test_client()

    response = client.post(
        "/api/jack-os/risk-decision",
        json={"equity": "bad", "drawdown_percent": "bad", "setup_score": "bad"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["auth_required"] is False
    assert body["data"]["allowed"] is False
    assert body["data"]["mode"] == "pause"
    assert body["data"]["risk_percent"] == 0.0


def test_risk_decision_s_setup_is_manual_planning_only():
    client = _app().test_client()

    response = client.post(
        "/api/jack-os/risk-decision",
        json={"equity": 1000, "drawdown_percent": 0, "setup_score": 20, "losing_streak": 0},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["allowed"] is True
    assert body["data"]["mode"] == "attack"
    assert body["data"]["risk_percent"] == 3.0
