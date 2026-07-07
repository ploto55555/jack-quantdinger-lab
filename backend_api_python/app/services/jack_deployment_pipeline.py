"""Jack Strategy Deployment Pipeline service.

This is a non-trading control framework. It models the professional path from
backtest to paper trading to live approval, but it never places broker orders.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DeploymentStage(str, Enum):
    DRAFT = "draft"
    BACKTESTED = "backtested"
    VALIDATED = "validated"
    PAPER_TRADING = "paper_trading"
    SMALL_LIVE = "small_live"
    LIVE_APPROVED = "live_approved"
    PAUSED = "paused"
    RETIRED = "retired"


STAGE_ORDER = [
    DeploymentStage.DRAFT,
    DeploymentStage.BACKTESTED,
    DeploymentStage.VALIDATED,
    DeploymentStage.PAPER_TRADING,
    DeploymentStage.SMALL_LIVE,
    DeploymentStage.LIVE_APPROVED,
]


@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    current_stage: str
    requested_stage: str
    reason: str
    required_next_actions: list[str]
    manual_approval_required: bool = True
    live_execution_enabled: bool = False


@dataclass(frozen=True)
class PortfolioRiskDecision:
    allowed: bool
    mode: str
    reason: str
    max_risk_per_trade_percent: float
    max_total_open_risk_percent: float
    required_actions: list[str]
    live_execution_enabled: bool = False


def list_stages() -> list[dict[str, Any]]:
    return [
        {
            "stage": DeploymentStage.DRAFT.value,
            "label": "Draft",
            "allowed_actions": ["edit_prompt", "edit_code", "run_backtest"],
            "forbidden_actions": ["paper_trading", "live_trading", "broker_execution"],
        },
        {
            "stage": DeploymentStage.BACKTESTED.value,
            "label": "Backtested",
            "allowed_actions": ["review_metrics", "walk_forward_test", "manual_approve_to_validated"],
            "forbidden_actions": ["live_trading", "broker_execution"],
        },
        {
            "stage": DeploymentStage.VALIDATED.value,
            "label": "Validated",
            "allowed_actions": ["paper_trading_request", "manual_approve_to_paper"],
            "forbidden_actions": ["live_trading", "broker_execution"],
        },
        {
            "stage": DeploymentStage.PAPER_TRADING.value,
            "label": "Paper Trading",
            "allowed_actions": ["simulate_realtime_signals", "monitor_paper_pnl", "manual_approve_to_small_live"],
            "forbidden_actions": ["full_live_trading"],
        },
        {
            "stage": DeploymentStage.SMALL_LIVE.value,
            "label": "Small Live",
            "allowed_actions": ["tiny_risk_live_test", "monitor_execution", "manual_approve_to_live"],
            "forbidden_actions": ["large_position", "uncontrolled_live_trading"],
        },
        {
            "stage": DeploymentStage.LIVE_APPROVED.value,
            "label": "Live Approved",
            "allowed_actions": ["run_under_portfolio_risk_manager", "monitor", "pause"],
            "forbidden_actions": ["bypass_risk_manager", "self_promote"],
        },
        {
            "stage": DeploymentStage.PAUSED.value,
            "label": "Paused",
            "allowed_actions": ["review", "restart_with_manual_approval", "retire"],
            "forbidden_actions": ["new_entries"],
        },
        {
            "stage": DeploymentStage.RETIRED.value,
            "label": "Retired",
            "allowed_actions": ["archive", "review_history"],
            "forbidden_actions": ["trading", "paper_trading"],
        },
    ]


def sample_strategies() -> list[dict[str, Any]]:
    return [
        {
            "strategy_id": "gbpjpy-trend-breakout-v1",
            "name": "GBPJPY Trend Breakout v1",
            "stage": DeploymentStage.BACKTESTED.value,
            "symbol": "GBPJPY",
            "timeframe": "H4",
            "last_backtest": {
                "total_return_percent": 84.6,
                "max_drawdown_percent": -18.4,
                "profit_factor": 1.42,
                "number_of_trades": 287,
            },
            "live_execution_enabled": False,
        },
        {
            "strategy_id": "xauusd-pullback-v1",
            "name": "XAUUSD Pullback v1",
            "stage": DeploymentStage.DRAFT.value,
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "last_backtest": None,
            "live_execution_enabled": False,
        },
        {
            "strategy_id": "eurusd-range-v1",
            "name": "EURUSD Range v1",
            "stage": DeploymentStage.VALIDATED.value,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "last_backtest": {
                "total_return_percent": 41.2,
                "max_drawdown_percent": -9.6,
                "profit_factor": 1.31,
                "number_of_trades": 421,
            },
            "live_execution_enabled": False,
        },
    ]


def evaluate_promotion(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    current = _parse_stage(payload.get("current_stage"), DeploymentStage.DRAFT)
    requested = _parse_stage(payload.get("requested_stage"), DeploymentStage.BACKTESTED)
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    manual_approval = bool(payload.get("manual_approval", False))

    decision = _promotion_decision(current, requested, metrics, manual_approval)
    return asdict(decision)


def portfolio_risk_check(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get("mode", "normal")).lower()
    daily_loss_percent = _float(payload.get("daily_loss_percent"), 0.0)
    open_risk_percent = _float(payload.get("open_risk_percent"), 0.0)
    kill_switch = bool(payload.get("kill_switch", False))
    news_pause = bool(payload.get("news_pause", False))
    broker_healthy = bool(payload.get("broker_healthy", True))

    if kill_switch:
        return asdict(PortfolioRiskDecision(False, "pause", "Kill switch is active.", 0.0, 0.0, ["Keep all strategies paused."]))
    if news_pause:
        return asdict(PortfolioRiskDecision(False, "pause", "News pause is active.", 0.0, open_risk_percent, ["Wait until news window ends."]))
    if not broker_healthy:
        return asdict(PortfolioRiskDecision(False, "pause", "Broker/API health check failed.", 0.0, open_risk_percent, ["Fix broker/API connection before any execution."]))
    if daily_loss_percent <= -3.0:
        return asdict(PortfolioRiskDecision(False, "pause", "Daily loss limit breached.", 0.0, open_risk_percent, ["Stop new entries for the day."]))
    if open_risk_percent >= 3.0:
        return asdict(PortfolioRiskDecision(False, "defense", "Total open risk is already high.", 0.0, 3.0, ["Do not add new strategy risk."]))

    if mode == "attack":
        decision = PortfolioRiskDecision(True, "attack", "Risk check passed under attack mode.", 0.5, 3.0, ["Allow only approved strategies under risk manager."])
    elif mode == "defense":
        decision = PortfolioRiskDecision(True, "defense", "Risk check passed under defense mode.", 0.1, 1.0, ["Reduce position size.", "Do not add correlated exposure."])
    elif mode == "pause":
        decision = PortfolioRiskDecision(False, "pause", "Account mode is pause.", 0.0, 0.0, ["Manual review required."])
    else:
        decision = PortfolioRiskDecision(True, "normal", "Risk check passed under normal mode.", 0.25, 2.0, ["Allow only approved strategies under risk manager."])

    return asdict(decision)


def _promotion_decision(current: DeploymentStage, requested: DeploymentStage, metrics: dict[str, Any], manual_approval: bool) -> PromotionDecision:
    if current in {DeploymentStage.PAUSED, DeploymentStage.RETIRED}:
        return PromotionDecision(False, current.value, requested.value, "Paused/retired strategy cannot self-promote.", ["Create a new version or manually restart review."])

    if requested == DeploymentStage.LIVE_APPROVED:
        return PromotionDecision(False, current.value, requested.value, "Live approval is disabled in v1 skeleton.", ["Complete paper trading and small-live modules first."])

    if not _is_next_stage(current, requested):
        return PromotionDecision(False, current.value, requested.value, "Only one-stage promotion is allowed.", ["Move through each validation stage in order."])

    if not manual_approval:
        return PromotionDecision(False, current.value, requested.value, "Manual approval by Jack is required.", ["Set manual_approval=true after review."])

    if requested == DeploymentStage.BACKTESTED:
        return PromotionDecision(True, current.value, requested.value, "Draft can be marked backtested after a completed run.", ["Review metrics before validation."])

    if requested == DeploymentStage.VALIDATED:
        trades = int(_float(metrics.get("number_of_trades"), 0.0))
        profit_factor = _float(metrics.get("profit_factor"), 0.0)
        max_drawdown = _float(metrics.get("max_drawdown_percent"), -100.0)
        if trades < 50 or profit_factor < 1.15 or max_drawdown < -30.0:
            return PromotionDecision(False, current.value, requested.value, "Backtest metrics are not strong enough for validation.", ["Improve strategy or run longer data.", "Check out-of-sample period."])
        return PromotionDecision(True, current.value, requested.value, "Metrics pass basic validation gate.", ["Run paper trading next."])

    if requested == DeploymentStage.PAPER_TRADING:
        return PromotionDecision(True, current.value, requested.value, "Validated strategy can enter paper trading.", ["Monitor real-time simulated signals."])

    if requested == DeploymentStage.SMALL_LIVE:
        return PromotionDecision(False, current.value, requested.value, "Small-live is intentionally locked in v1.", ["Build broker sandbox and kill switch first."])

    return PromotionDecision(False, current.value, requested.value, "Unsupported promotion request.", ["Review pipeline rules."])


def _is_next_stage(current: DeploymentStage, requested: DeploymentStage) -> bool:
    try:
        return STAGE_ORDER.index(requested) == STAGE_ORDER.index(current) + 1
    except ValueError:
        return False


def _parse_stage(value: Any, default: DeploymentStage) -> DeploymentStage:
    try:
        return DeploymentStage(str(value).lower())
    except ValueError:
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
