from __future__ import annotations

from html import escape
from typing import Any, Dict, List

from flask import Response

from app.services.jack_strategy_library import list_strategy_candidates_v1


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{value}{suffix}"


def _money(value: Any) -> str:
    try:
        return "${:,.0f}".format(float(value))
    except (TypeError, ValueError):
        return "—"


def _class_for_role(role: str) -> str:
    if "safe" in role:
        return "safe"
    if "main" in role:
        return "main"
    if "aggressive" in role or "attack" in role:
        return "attack"
    if "m5" in role or "execution" in role:
        return "execution"
    return "research"


def get_backtest_dashboard_data_v1() -> Dict[str, Any]:
    result = list_strategy_candidates_v1({"symbol": "GBPJPY", "limit": 20})
    candidates: List[Dict[str, Any]] = result.get("candidates", [])

    rows = []
    for c in candidates:
        bt = c.get("backtest_summary", {})
        goal = c.get("goal_use", {})
        rows.append(
            {
                "rank": c.get("rank"),
                "id": c.get("id"),
                "role": c.get("role"),
                "mode": goal.get("mode"),
                "execution_timeframe": c.get("execution_timeframe"),
                "trades": bt.get("trades"),
                "win_rate_percent": bt.get("win_rate_percent"),
                "profit_factor": bt.get("profit_factor"),
                "total_pips": bt.get("total_pips"),
                "max_drawdown_percent": bt.get("max_drawdown_percent"),
                "max_losing_streak": bt.get("max_losing_streak"),
                "positive_years": bt.get("positive_years"),
                "aggressive_compounding_500_start": bt.get("aggressive_compounding_500_start"),
                "summary": c.get("summary"),
                "when_to_use": goal.get("when_to_use"),
                "when_to_block": goal.get("when_to_block"),
            }
        )

    return {
        "version": "backtest_dashboard_data_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": "GBPJPY",
        "candidate_count": len(rows),
        "rows": rows,
        "risk_notice": "Research dashboard only. Results are historical backtest candidates, not live trade instructions.",
    }


def get_backtest_dashboard_html_v1() -> Response:
    data = get_backtest_dashboard_data_v1()
    rows = data.get("rows", [])

    cards_html = "".join(_render_card(row) for row in rows)
    table_html = "".join(_render_table_row(row) for row in rows)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jack AI Capital OS - Backtest Dashboard</title>
  <style>
    :root {{
      --bg: #07110f;
      --panel: #0f1d1a;
      --panel2: #132823;
      --text: #e9fff7;
      --muted: #93aaa3;
      --line: #28443d;
      --green: #61f2b2;
      --yellow: #f0d06a;
      --red: #ff7a7a;
      --blue: #75b7ff;
      --purple: #cda0ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top left, #15362d 0, var(--bg) 42%);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .wrap {{ max-width: 1380px; margin: 0 auto; padding: 24px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 20px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: -0.04em; }}
    .sub {{ color: var(--muted); line-height: 1.5; max-width: 760px; }}
    .badge {{ display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid var(--line); border-radius: 999px; background: rgba(255,255,255,0.04); color: var(--muted); font-size: 12px; white-space: nowrap; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 18px 0 24px; }}
    .card {{ background: linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.025)); border: 1px solid var(--line); border-radius: 18px; padding: 16px; min-height: 260px; box-shadow: 0 12px 40px rgba(0,0,0,.22); }}
    .card.main {{ border-color: rgba(97,242,178,.45); }}
    .card.safe {{ border-color: rgba(117,183,255,.45); }}
    .card.attack {{ border-color: rgba(255,122,122,.45); }}
    .card.execution {{ border-color: rgba(205,160,255,.45); }}
    .role {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 10px; }}
    .pill {{ font-size: 11px; padding: 5px 8px; border-radius: 999px; background: rgba(255,255,255,.07); color: var(--muted); border: 1px solid rgba(255,255,255,.08); }}
    .id {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; color: var(--text); line-height: 1.4; word-break: break-word; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 14px 0; }}
    .metric {{ background: rgba(0,0,0,.18); border: 1px solid rgba(255,255,255,.06); border-radius: 12px; padding: 10px; }}
    .metric small {{ display:block; color: var(--muted); font-size: 11px; margin-bottom: 4px; }}
    .metric b {{ font-size: 17px; }}
    .summary {{ color: var(--muted); line-height: 1.45; font-size: 13px; }}
    .section-title {{ margin: 26px 0 10px; font-size: 18px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 18px; background: rgba(255,255,255,.035); }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1040px; }}
    th, td {{ text-align: left; padding: 12px 12px; border-bottom: 1px solid rgba(255,255,255,.07); font-size: 13px; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; background: rgba(0,0,0,.18); position: sticky; top: 0; }}
    td.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }}
    .notice {{ margin-top: 16px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
    .footer-actions {{ display:flex; gap:10px; flex-wrap:wrap; margin: 20px 0; }}
    a.btn {{ color: var(--text); text-decoration:none; padding:10px 12px; border:1px solid var(--line); border-radius:12px; background:rgba(255,255,255,.05); font-size:13px; }}
    @media (max-width: 1050px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 720px) {{ .wrap {{ padding: 16px; }} .hero {{ flex-direction: column; }} .grid {{ grid-template-columns: 1fr; }} h1 {{ font-size: 23px; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div>
        <h1>Jack AI Capital OS · Backtest Result Dashboard</h1>
        <div class="sub">Strategy candidates saved from SRDC + Ketty + Granville research. This page is for research comparison and forward-test preparation only, not auto trading.</div>
      </div>
      <div class="badge">GBPJPY · {len(rows)} candidates · personal research only</div>
    </section>

    <div class="footer-actions">
      <a class="btn" href="/api/jack-brain/strategy-library-v1">Raw strategy library JSON</a>
      <a class="btn" href="/api/jack-brain/goal-path-v1?start_equity=500&target_equity=100000&current_equity=500&elapsed_days=0&total_days=365">Goal path JSON</a>
      <a class="btn" href="/api/jack-brain/strategy-selector-v2?start_equity=500&target_equity=100000&current_equity=500&peak_equity=500&elapsed_days=0&news_risk=low&market_quality=normal&d1_signal=long_only&h1_regime=trend&m15_signal=setup_forming&m5_signal=prepare">Selector v2 sample</a>
    </div>

    <section class="grid">{cards_html}</section>

    <h2 class="section-title">Full comparison table</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th><th>Strategy</th><th>Role</th><th>Mode</th><th>TF</th><th>Trades</th><th>Win</th><th>PF</th><th>Pips</th><th>Max DD</th><th>MLS</th><th>$500 aggressive</th>
          </tr>
        </thead>
        <tbody>{table_html}</tbody>
      </table>
    </div>
    <p class="notice">Risk notice: historical backtest numbers can fail in forward testing. This system is not broker-connected and does not auto-trade. Final execution must remain manual and verified.</p>
  </main>
</body>
</html>"""
    return Response(html, mimetype="text/html")


def _render_card(row: Dict[str, Any]) -> str:
    role = str(row.get("role", ""))
    css = _class_for_role(role)
    return f"""
    <article class="card {css}">
      <div class="role"><span class="pill">#{escape(str(row.get('rank')))} · {escape(str(row.get('mode')))}</span><span class="pill">{escape(str(row.get('execution_timeframe')))}</span></div>
      <div class="id">{escape(str(row.get('id')))}</div>
      <div class="metrics">
        <div class="metric"><small>Win rate</small><b>{_fmt(row.get('win_rate_percent'), '%')}</b></div>
        <div class="metric"><small>PF</small><b>{_fmt(row.get('profit_factor'))}</b></div>
        <div class="metric"><small>Max DD</small><b>{_fmt(row.get('max_drawdown_percent'), '%')}</b></div>
        <div class="metric"><small>Trades</small><b>{_fmt(row.get('trades'))}</b></div>
        <div class="metric"><small>Total pips</small><b>{_fmt(row.get('total_pips'))}</b></div>
        <div class="metric"><small>$500 model</small><b>{_money(row.get('aggressive_compounding_500_start'))}</b></div>
      </div>
      <div class="summary">{escape(str(row.get('summary') or ''))}</div>
    </article>"""


def _render_table_row(row: Dict[str, Any]) -> str:
    return f"""
    <tr>
      <td>{escape(str(row.get('rank')))}</td>
      <td class="mono">{escape(str(row.get('id')))}</td>
      <td>{escape(str(row.get('role')))}</td>
      <td>{escape(str(row.get('mode')))}</td>
      <td>{escape(str(row.get('execution_timeframe')))}</td>
      <td>{_fmt(row.get('trades'))}</td>
      <td>{_fmt(row.get('win_rate_percent'), '%')}</td>
      <td>{_fmt(row.get('profit_factor'))}</td>
      <td>{_fmt(row.get('total_pips'))}</td>
      <td>{_fmt(row.get('max_drawdown_percent'), '%')}</td>
      <td>{_fmt(row.get('max_losing_streak'))}</td>
      <td>{_money(row.get('aggressive_compounding_500_start'))}</td>
    </tr>"""
