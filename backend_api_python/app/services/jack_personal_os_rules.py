"""Small rule helpers for Jack Personal OS.

This module is a safe standalone draft. It is not imported by the running app yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class JackMode(str, Enum):
    PAUSE = "pause"
    DEFENSE = "defense"
    NORMAL = "normal"
    ATTACK = "attack"


class SetupGrade(str, Enum):
    NO_TRADE = "no_trade"
    WATCH = "watch"
    A = "a"
    A_PLUS = "a_plus"
    S = "s"


@dataclass(frozen=True)
class SetupScoreResult:
    score: int
    grade: SetupGrade
    note: str


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    mode: JackMode
    risk_percent: float
    note: str


def grade_setup(score: int) -> SetupScoreResult:
    """Map a 0-20 checklist score into a simple setup grade."""
    score = max(0, min(20, int(score)))
    if score <= 9:
        return SetupScoreResult(score, SetupGrade.NO_TRADE, "Below minimum quality threshold.")
    if score <= 13:
        return SetupScoreResult(score, SetupGrade.WATCH, "Watch only; wait for more confirmation.")
    if score <= 16:
        return SetupScoreResult(score, SetupGrade.A, "Valid idea, but not the highest quality.")
    if score <= 18:
        return SetupScoreResult(score, SetupGrade.A_PLUS, "High quality setup.")
    return SetupScoreResult(score, SetupGrade.S, "Top quality setup; still requires manual approval.")


def decide_risk_percent(
    equity: float,
    drawdown_percent: float,
    setup_score: int,
    losing_streak: int = 0,
) -> RiskDecision:
    """Return a conservative first-pass risk decision.

    This is only a planning helper. It does not connect to any broker or order flow.
    """
    if equity <= 0:
        return RiskDecision(False, JackMode.PAUSE, 0.0, "Equity must be positive.")

    setup = grade_setup(setup_score)
    drawdown = abs(float(drawdown_percent))
    losing_streak = max(0, int(losing_streak))

    if drawdown >= 25 or losing_streak >= 5:
        return RiskDecision(False, JackMode.PAUSE, 0.0, "Pause mode triggered by drawdown or streak.")
    if drawdown >= 15 or losing_streak >= 3:
        mode = JackMode.DEFENSE
    elif setup.grade in {SetupGrade.A_PLUS, SetupGrade.S} and drawdown < 5:
        mode = JackMode.ATTACK
    else:
        mode = JackMode.NORMAL

    base = {
        SetupGrade.NO_TRADE: 0.0,
        SetupGrade.WATCH: 0.0,
        SetupGrade.A: 1.0,
        SetupGrade.A_PLUS: 2.0,
        SetupGrade.S: 3.0,
    }[setup.grade]

    if mode == JackMode.DEFENSE:
        base *= 0.5
    if mode == JackMode.PAUSE:
        base = 0.0

    allowed = base > 0
    return RiskDecision(allowed, mode, base, setup.note)
