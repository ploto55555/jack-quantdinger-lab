from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


VERSION = "market_context_calendar_news_v1"


SYMBOL_CURRENCY_MAP = {
    "GBPJPY": ["GBP", "JPY"],
    "USDJPY": ["USD", "JPY"],
    "GBPUSD": ["GBP", "USD"],
    "EURUSD": ["EUR", "USD"],
    "XAUUSD": ["XAU", "USD"],
    "AUDJPY": ["AUD", "JPY"],
    "EURJPY": ["EUR", "JPY"],
    "USDCAD": ["USD", "CAD"],
    "USDCHF": ["USD", "CHF"],
}


HIGH_IMPACT_EVENT_TYPES = [
    {
        "event_type": "interest_rate_decision",
        "examples": ["FOMC", "BOJ", "BOE", "ECB"],
        "impact": "high",
        "why_it_matters": "Rate decisions can change currency direction and volatility.",
    },
    {
        "event_type": "inflation",
        "examples": ["CPI", "PPI"],
        "impact": "high",
        "why_it_matters": "Inflation can change rate expectations and move USD, JPY, gold, and indices.",
    },
    {
        "event_type": "employment",
        "examples": ["NFP", "Unemployment Rate", "Jobless Claims"],
        "impact": "high",
        "why_it_matters": "Employment data can move USD, yields, gold, and risk sentiment.",
    },
    {
        "event_type": "central_bank_speech",
        "examples": ["Fed Chair Speech", "BOJ Governor Speech", "ECB Speech"],
        "impact": "medium_high",
        "why_it_matters": "Central bank language can shift market expectation quickly.",
    },
    {
        "event_type": "risk_sentiment",
        "examples": ["Geopolitical shock", "Equity selloff", "Bond yield spike"],
        "impact": "medium_high",
        "why_it_matters": "Risk-on or risk-off conditions can change JPY pairs and gold behavior.",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _symbol(payload: dict[str, Any]) -> str:
    return str(payload.get("symbol") or "GBPJPY").upper().strip()


def _related_currencies(symbol: str) -> list[str]:
    return SYMBOL_CURRENCY_MAP.get(symbol, [])


def get_calendar_context_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = _symbol(payload)
    currencies = _related_currencies(symbol)

    relevant_events = []
    for event in HIGH_IMPACT_EVENT_TYPES:
        relevant_events.append(
            {
                **event,
                "status": "template_only_not_live_calendar",
                "related_to_symbol": True if currencies else False,
                "related_currencies": currencies,
            }
        )

    return {
        "version": VERSION,
        "ok": True,
        "module": "economic_calendar_context",
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "created_at": _now(),
        "symbol": symbol,
        "related_currencies": currencies,
        "calendar_status": "template_only_live_api_not_connected_yet",
        "events_to_watch": relevant_events,
        "warning": "This is not live calendar data yet. It is a backend context layer for later calendar API integration.",
    }


def get_news_context_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = _symbol(payload)
    currencies = _related_currencies(symbol)

    news_watch_topics = []
    if "USD" in currencies or symbol == "XAUUSD":
        news_watch_topics.extend(["US yields", "Fed policy", "CPI", "NFP", "risk sentiment"])
    if "JPY" in currencies:
        news_watch_topics.extend(["BOJ policy", "JPY intervention risk", "Japan yields", "risk-off flows"])
    if "GBP" in currencies:
        news_watch_topics.extend(["BOE policy", "UK inflation", "UK employment", "GBP risk sentiment"])
    if "EUR" in currencies:
        news_watch_topics.extend(["ECB policy", "Eurozone inflation", "EU growth data"])
    if symbol == "XAUUSD":
        news_watch_topics.extend(["gold safe haven demand", "real yields", "USD strength"])

    unique_topics = []
    for topic in news_watch_topics:
        if topic not in unique_topics:
            unique_topics.append(topic)

    return {
        "version": VERSION,
        "ok": True,
        "module": "market_news_context",
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "created_at": _now(),
        "symbol": symbol,
        "related_currencies": currencies,
        "news_status": "topic_watchlist_only_live_news_api_not_connected_yet",
        "news_watch_topics": unique_topics,
        "sample_ai_note": (
            f"For {symbol}, future AI should compare strategy performance with related news topics, "
            f"calendar events, volatility expansion, and risk-on/risk-off conditions."
        ),
        "warning": "This is not live news yet. It is a backend context layer for later real-time news API integration.",
    }


def get_market_context_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = _symbol(payload)
    calendar = get_calendar_context_v1({"symbol": symbol})
    news = get_news_context_v1({"symbol": symbol})

    return {
        "version": VERSION,
        "ok": True,
        "module": "market_context_brain",
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "created_at": _now(),
        "symbol": symbol,
        "calendar": calendar,
        "news": news,
        "event_aware_backtest_status": "planned_not_connected_yet",
        "ai_learning_goal": [
            "Tag backtest trades near high-impact events.",
            "Compare normal market vs news window performance.",
            "Save important market context into journal and memory.",
            "Learn which strategy profiles are sensitive to news and calendar events.",
        ],
        "next_action": "Later connect live news/calendar API, then tag each backtest trade with nearby event context.",
    }
