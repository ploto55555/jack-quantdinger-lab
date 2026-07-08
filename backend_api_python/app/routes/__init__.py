"""
API Routes Module â€” Agent Gateway + OpenAPI-registered human routes.
"""
from flask import Flask


def register_routes(app: Flask):
    """Register Agent Gateway and human web API (via flask-smorest)."""
    from app.openapi import init_openapi
    init_openapi(app)

    from app.routes.agent_v1 import register as register_agent_v1
    register_agent_v1(app)

    from app.routes.jack_os_api import jack_os_api
    app.register_blueprint(jack_os_api)

    from app.routes.jack_backtest_api import jack_backtest_api
    from app.routes.jack_brain_api import jack_brain_api
    app.register_blueprint(jack_backtest_api)
    app.register_blueprint(jack_brain_api)

    from app.routes.jack_setup_study_api import jack_setup_study_api
    app.register_blueprint(jack_setup_study_api)

    from app.routes.jack_data_api import jack_data_api
    app.register_blueprint(jack_data_api)

    from app.routes.jack_forex_data_api import jack_forex_data_api
    app.register_blueprint(jack_forex_data_api)

    from app.routes.jack_forex_import_page import jack_forex_import_page
    app.register_blueprint(jack_forex_import_page)
