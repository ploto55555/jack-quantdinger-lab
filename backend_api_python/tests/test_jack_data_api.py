from flask import Flask

from app.routes.jack_data_api import jack_data_api


def _app():
    app = Flask(__name__)
    app.register_blueprint(jack_data_api)
    return app


def test_health_is_public():
    client = _app().test_client()

    response = client.get("/api/jack-data/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 1
    assert body["data"]["service"] == "jack-data-center"
    assert body["data"]["external_api_required"] is False


def test_symbols_returns_priority_symbols():
    client = _app().test_client()

    response = client.get("/api/jack-data/symbols")

    assert response.status_code == 200
    symbols = response.get_json()["data"]["symbols"]
    names = {item["symbol"] for item in symbols}
    assert "GBPJPY" in names
    assert "XAUUSD" in names
    assert "SPY" in names


def test_import_plan_defines_candle_schema():
    client = _app().test_client()

    response = client.get("/api/jack-data/import-plan")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["phase_1"]["timeframes"] == ["1D", "H4", "H1"]
    assert data["candle_schema"]["symbol"] == "string"
    assert data["candle_schema"]["close"] == "float"


def test_sample_candles_accepts_query_params():
    client = _app().test_client()

    response = client.get("/api/jack-data/sample-candles?symbol=XAUUSD&timeframe=H1&limit=3")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["symbol"] == "XAUUSD"
    assert data["timeframe"] == "H1"
    assert len(data["candles"]) == 3
    assert set(data["candles"][0]).issuperset({"open", "high", "low", "close", "timestamp", "source"})


def test_quality_report_returns_sample_status():
    client = _app().test_client()

    response = client.get("/api/jack-data/quality-report?symbol=GBPJPY&timeframe=H4")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["symbol"] == "GBPJPY"
    assert data["timeframe"] == "H4"
    assert data["status"] == "sample_ready"
    assert data["rows"] == 50
