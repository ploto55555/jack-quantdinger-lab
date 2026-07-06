from app.services.jack_personal_os_rules import (
    JackMode,
    SetupGrade,
    decide_risk_percent,
    grade_setup,
)


def test_grade_setup_boundaries():
    assert grade_setup(0).grade == SetupGrade.NO_TRADE
    assert grade_setup(9).grade == SetupGrade.NO_TRADE
    assert grade_setup(10).grade == SetupGrade.WATCH
    assert grade_setup(13).grade == SetupGrade.WATCH
    assert grade_setup(14).grade == SetupGrade.A
    assert grade_setup(16).grade == SetupGrade.A
    assert grade_setup(17).grade == SetupGrade.A_PLUS
    assert grade_setup(18).grade == SetupGrade.A_PLUS
    assert grade_setup(19).grade == SetupGrade.S
    assert grade_setup(20).grade == SetupGrade.S


def test_risk_decision_pauses_on_large_drawdown():
    decision = decide_risk_percent(equity=1000, drawdown_percent=25, setup_score=20)
    assert decision.allowed is False
    assert decision.mode == JackMode.PAUSE
    assert decision.risk_percent == 0.0


def test_risk_decision_defense_on_losing_streak():
    decision = decide_risk_percent(equity=1000, drawdown_percent=0, setup_score=20, losing_streak=3)
    assert decision.allowed is True
    assert decision.mode == JackMode.DEFENSE
    assert decision.risk_percent == 1.5


def test_risk_decision_watch_is_not_allowed():
    decision = decide_risk_percent(equity=1000, drawdown_percent=0, setup_score=12)
    assert decision.allowed is False
    assert decision.risk_percent == 0.0


def test_risk_decision_attack_for_high_quality_low_drawdown():
    decision = decide_risk_percent(equity=1000, drawdown_percent=0, setup_score=18)
    assert decision.allowed is True
    assert decision.mode == JackMode.ATTACK
    assert decision.risk_percent == 2.0
