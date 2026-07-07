"""
API Routes Module — Agent Gateway + OpenAPI-registered human routes.
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
    app.register_blueprint(jack_backtest_api)
