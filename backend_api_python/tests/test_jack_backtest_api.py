from flask import Flask

from app.routes.jack_backtest_api import jack_backtest_api


def _app():
    app = Flask(__name__)
    app.register_blueprint(jack_backtest_api)
    return app


def test_health_is_public():
    client = _app().test_client()

    response = client.get("/api/jack-backtest/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 1
    assert body["data"]["service"] == "jack-backtest"
    assert body["data"]["ai_token_required"] is False


def test_sample_result_returns_summary_equity_and_trades():
    client = _app().test_client()

    response = client.get("/api/jack-backtest/sample-result")

    assert response.status_code == 200
    body = response.get_json()
    data = body["data"]
    assert data["summary"]["strategy_name"] == "GBPJPY Trend Breakout v1"
    assert data["summary"]["symbol"] == "GBPJPY"
    assert data["summary"]["status"] == "sample_only"
    assert data["equity_curve"]
    assert data["trades"]


def test_run_sample_accepts_custom_payload():
    client = _app().test_client()

    response = client.post(
        "/api/jack-backtest/run-sample",
        json={
            "strategy_name": "XAUUSD Sample v1",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "initial_capital": 500,
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["summary"]["strategy_name"] == "XAUUSD Sample v1"
    assert data["summary"]["symbol"] == "XAUUSD"
    assert data["summary"]["timeframe"] == "H1"
    assert data["summary"]["initial_capital"] == 500
    assert data["summary"]["final_equity"] == 923
