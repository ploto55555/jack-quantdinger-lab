from flask import Flask

from app.routes.jack_os_api import jack_os_api


AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _app():
    app = Flask(__name__)
    app.register_blueprint(jack_os_api)
    return app


def _allow_auth(monkeypatch):
    monkeypatch.setattr(
        "app.utils.auth.verify_token",
        lambda token: {"sub": "test", "user_id": 1, "role": "admin"},
    )


def test_tools_requires_login():
    client = _app().test_client()
    response = client.get("/api/jack-os/tools")
    assert response.status_code == 401


def test_tools_returns_disabled_registry(monkeypatch):
    _allow_auth(monkeypatch)
    client = _app().test_client()

    response = client.get("/api/jack-os/tools", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 1
    assert body["data"]["enabled"] is False
    assert body["data"]["tools"]
    assert all(tool["enabled"] is False for tool in body["data"]["tools"])


def test_grade_setup_accepts_bad_payload_safely(monkeypatch):
    _allow_auth(monkeypatch)
    client = _app().test_client()

    response = client.post("/api/jack-os/grade-setup", json={"score": "bad"}, headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["score"] == 0
    assert body["data"]["grade"] == "no_trade"


def test_risk_decision_accepts_bad_payload_safely(monkeypatch):
    _allow_auth(monkeypatch)
    client = _app().test_client()

    response = client.post(
        "/api/jack-os/risk-decision",
        json={"equity": "bad", "drawdown_percent": "bad", "setup_score": "bad"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["allowed"] is False
    assert body["data"]["mode"] == "pause"
    assert body["data"]["risk_percent"] == 0.0


def test_risk_decision_s_setup_is_manual_planning_only(monkeypatch):
    _allow_auth(monkeypatch)
    client = _app().test_client()

    response = client.post(
        "/api/jack-os/risk-decision",
        json={"equity": 1000, "drawdown_percent": 0, "setup_score": 20, "losing_streak": 0},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["allowed"] is True
    assert body["data"]["mode"] == "attack"
    assert body["data"]["risk_percent"] == 3.0
