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


def test_run_candles_sample_get_computes_from_candles():
    client = _app().test_client()

    response = client.get("/api/jack-backtest/run-candles-sample?symbol=GBPJPY&timeframe=H4&limit=10&initial_capital=10000")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["summary"]["strategy_name"] == "Buy & Hold Candle Chain Test"
    assert data["summary"]["symbol"] == "GBPJPY"
    assert data["summary"]["timeframe"] == "H4"
    assert data["summary"]["status"] == "computed_from_sample_candles"
    assert data["summary"]["number_of_candles"] == 10
    assert data["summary"]["number_of_trades"] == 1
    assert data["equity_curve"]
    assert data["trades"][0]["side"] == "long"


def test_run_candles_sample_post_accepts_payload():
    client = _app().test_client()

    response = client.post(
        "/api/jack-backtest/run-candles-sample",
        json={"symbol": "XAUUSD", "timeframe": "H1", "limit": 5, "initial_capital": 500},
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["summary"]["symbol"] == "XAUUSD"
    assert data["summary"]["timeframe"] == "H1"
    assert data["summary"]["initial_capital"] == 500
    assert len(data["equity_curve"]) == 5
