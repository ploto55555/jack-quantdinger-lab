from flask import Flask

from app.routes.jack_forex_data_api import jack_forex_data_api
from app.services.jack_forex_data_sample import csv_template


def _app():
    app = Flask(__name__)
    app.register_blueprint(jack_forex_data_api)
    return app


def test_health_is_public():
    client = _app().test_client()

    response = client.get("/api/jack-forex-data/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["code"] == 1
    assert body["data"]["service"] == "jack-forex-data-center"
    assert body["data"]["external_api_required"] is False


def test_requirements_are_forex_first():
    client = _app().test_client()

    response = client.get("/api/jack-forex-data/requirements")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["priority_symbols"][:3] == ["GBPJPY", "USDJPY", "XAUUSD"]
    assert data["phase_1_timeframes"] == ["1D", "H4", "H1"]
    assert "timestamp" in data["csv_columns"]


def test_csv_template_returns_rows():
    client = _app().test_client()

    response = client.get("/api/jack-forex-data/csv-template")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["filename"] == "jack_forex_candles_template.csv"
    assert data["columns"][0] == "symbol"
    assert data["example_rows"][0]["symbol"] == "GBPJPY"
    assert data["csv_text"].startswith("symbol,timeframe,timestamp")


def test_csv_template_csv_download():
    client = _app().test_client()

    response = client.get("/api/jack-forex-data/csv-template.csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert response.data.decode().startswith("symbol,timeframe,timestamp")


def test_sample_forex_candles_accepts_query_params():
    client = _app().test_client()

    response = client.get("/api/jack-forex-data/sample-forex-candles?symbol=XAUUSD&timeframe=H1&limit=3")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["symbol"] == "XAUUSD"
    assert data["timeframe"] == "H1"
    assert len(data["candles"]) == 3
    assert data["candles"][0]["source"] == "forex_sample"


def test_validate_csv_accepts_template():
    client = _app().test_client()

    response = client.post("/api/jack-forex-data/validate-csv", json={"csv_text": csv_template()})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["valid"] is True
    assert data["rows_checked"] == 5
    assert data["errors"] == []


def test_import_csv_then_read_stored_candles():
    client = _app().test_client()

    import_response = client.post("/api/jack-forex-data/import-csv", json={"csv_text": csv_template()})

    assert import_response.status_code == 200
    import_data = import_response.get_json()["data"]
    assert import_data["imported"] is True
    assert import_data["rows_imported"] == 5

    stored_response = client.get("/api/jack-forex-data/stored-candles?symbol=GBPJPY&timeframe=H4&limit=3")
    stored_data = stored_response.get_json()["data"]
    assert stored_response.status_code == 200
    assert stored_data["rows"] == 3
    assert stored_data["candles"][0]["symbol"] == "GBPJPY"


def test_stored_datasets_and_quality_report():
    client = _app().test_client()
    client.post("/api/jack-forex-data/import-csv", json={"csv_text": csv_template()})

    datasets_response = client.get("/api/jack-forex-data/stored-datasets")
    datasets_data = datasets_response.get_json()["data"]
    assert datasets_response.status_code == 200
    assert datasets_data["count"] >= 1

    quality_response = client.get("/api/jack-forex-data/stored-quality-report?symbol=GBPJPY&timeframe=H4")
    quality_data = quality_response.get_json()["data"]
    assert quality_response.status_code == 200
    assert quality_data["status"] == "stored_ready"
    assert quality_data["rows"] == 5
