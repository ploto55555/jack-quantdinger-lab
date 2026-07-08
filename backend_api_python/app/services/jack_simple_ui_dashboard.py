from __future__ import annotations

import html
from typing import Any

from app.services.jack_research_dashboard_api import build_research_dashboard_v1


VERSION = "simple_ui_dashboard_v1"


def build_simple_ui_dashboard_html_v1(payload: dict[str, Any] | None = None) -> str:
    payload = payload or {}
    dashboard = build_research_dashboard_v1(payload)
    cards = dashboard.get("cards") or {}

    command = cards.get("command_card") or {}
    capital = cards.get("capital_card") or {}
    risk = cards.get("risk_card") or {}
    goal = cards.get("goal_card") or {}
    journal = cards.get("journal_card") or {}
    learning = cards.get("learning_card") or {}
    memory = cards.get("memory_card") or {}
    health = cards.get("system_health_card") or {}

    goal_rows = _goal_rows(goal.get("top_profiles") or [])
    focus_items = _list_items(command.get("items") or [])
    learning_items = _list_items((learning.get("behavior_notes") or []) + (learning.get("items") or []))
    health_items = _list_items(health.get("items") or [])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jack Personal AI Capital OS</title>
  <style>
    :root {{
      --bg:#000000;
      --panel:#0d0d0d;
      --panel2:#171717;
      --line:#2f2f2f;
      --text:#f5f5f5;
      --muted:#a3a3a3;
      --soft:#d4d4d4;
      --warn:#facc15;
      --bad:#f87171;
      --good:#86efac;
      --accent:#c084fc;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:#000000;
      color:var(--text);
      font-family:Consolas, Monaco, 'Courier New', monospace;
      font-size:14px;
    }}
    .wrap {{ max-width:1440px; margin:0 auto; padding:18px; }}
    .top {{ display:flex; justify-content:space-between; gap:14px; align-items:flex-start; margin-bottom:16px; }}
    h1 {{ margin:0; font-size:24px; letter-spacing:.08em; color:var(--accent); }}
    .sub {{ color:var(--muted); margin-top:6px; line-height:1.5; }}
    .badge {{ border:1px solid var(--line); background:#0d0d0d; padding:8px 10px; border-radius:10px; color:var(--soft); white-space:nowrap; }}
    .grid {{ display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:12px; }}
    .wide {{ grid-column:span 2; }}
    .full {{ grid-column:1 / -1; }}
    .card {{ border:1px solid var(--line); background:#0d0d0d; border-radius:14px; padding:14px; min-height:140px; box-shadow:0 0 0 1px rgba(158,240,26,.04),0 10px 30px rgba(0,0,0,.25); }}
    .card h2 {{ margin:0 0 10px; font-size:14px; color:var(--accent); letter-spacing:.08em; text-transform:uppercase; }}
    .value {{ font-size:28px; color:var(--text); margin:6px 0; }}
    .small {{ color:var(--muted); line-height:1.5; }}
    .status {{ display:inline-block; padding:4px 8px; border-radius:999px; border:1px solid var(--line); background:var(--panel2); color:var(--good); font-size:12px; }}
    .status.warn {{ color:var(--warn); }}
    ul {{ margin:8px 0 0; padding-left:18px; }}
    li {{ margin:5px 0; line-height:1.45; }}
    table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:8px 6px; text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-weight:normal; }}
    td {{ color:var(--text); }}
    .mono {{ color:var(--soft); }}
    .footer {{ margin-top:14px; color:var(--muted); font-size:12px; }}
    @media (max-width:1100px) {{ .grid {{ grid-template-columns:1fr 1fr; }} .wide {{ grid-column:span 2; }} }}
    @media (max-width:760px) {{ .grid {{ grid-template-columns:1fr; }} .wide,.full {{ grid-column:auto; }} .top {{ flex-direction:column; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>JACK PERSONAL AI CAPITAL OS</h1>
        <div class="sub">Research dashboard only. No broker connection. No live automation.</div>
      </div>
      <div class="badge">{_e(VERSION)} - {_e(dashboard.get('generated_at'))}</div>
    </div>

    <div class="grid">
      <section class="card">
        <h2>Daily Command</h2>
        <span class="status">{_e(command.get('status'))}</span>
        <div class="value">{_e(command.get('primary_value'))}</div>
        <div class="small">{_e(command.get('secondary_value'))}</div>
      </section>

      <section class="card">
        <h2>Capital Stage</h2>
        <span class="status">{_e(capital.get('status'))}</span>
        <div class="value">{_e(capital.get('primary_value'))}</div>
        <div class="small">{_e(capital.get('secondary_value'))}</div>
      </section>

      <section class="card">
        <h2>Risk Mode</h2>
        <span class="status">{_e(risk.get('status'))}</span>
        <div class="value">{_e(risk.get('primary_value'))}</div>
        <div class="small">{_e(risk.get('secondary_value'))}</div>
      </section>

      <section class="card wide">
        <h2>Goal Backtest</h2>
        <span class="status">{_e(goal.get('status'))}</span>
        <div class="value">{_e(goal.get('secondary_value'))} - {_e(goal.get('primary_value'))}</div>
        <div class="small">{_e((goal.get('items') or [''])[0])}</div>
      </section>

      <section class="card">
        <h2>System Health</h2>
        <span class="status warn">{_e(health.get('status'))}</span>
        <div class="value">{_e(health.get('primary_value'))}</div>
        <div class="small">{health_items}</div>
      </section>

      <section class="card full">
        <h2>Top Profiles For Goal Path</h2>
        <table>
          <thead><tr><th>Profile</th><th>Symbol</th><th>Status</th><th>Score</th><th>Possible</th><th>Use</th></tr></thead>
          <tbody>{goal_rows}</tbody>
        </table>
      </section>

      <section class="card wide">
        <h2>Today Focus</h2>
        {focus_items}
      </section>

      <section class="card">
        <h2>Journal</h2>
        <span class="status warn">{_e(journal.get('status'))}</span>
        <div class="value">{_e(journal.get('primary_value'))}</div>
        <div class="small">{_e(journal.get('secondary_value'))}</div>
      </section>

      <section class="card wide">
        <h2>Learning Notes</h2>
        {learning_items}
      </section>

      <section class="card">
        <h2>Memory</h2>
        <span class="status">{_e(memory.get('status'))}</span>
        <div class="value">{_clean_memory(memory.get('primary_value'))}</div>
        <div class="small">{_clean_memory(memory.get('secondary_value'))}</div>
      </section>
    </div>

    <div class="footer">{_e(dashboard.get('human_summary'))}</div>
  </div>
</body>
</html>"""


def _goal_rows(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows[:8]:
        out.append(
            "<tr>"
            f"<td class='mono'>{_e(row.get('profile_id'))}</td>"
            f"<td>{_e(row.get('symbol'))}</td>"
            f"<td>{_e(row.get('profile_status'))}</td>"
            f"<td>{_e(row.get('goal_fit_score'))}</td>"
            f"<td>{_e(row.get('target_possible'))}</td>"
            f"<td>{_e(row.get('recommended_use'))}</td>"
            "</tr>"
        )
    return "".join(out) or "<tr><td colspan='6'>No profiles</td></tr>"


def _list_items(items: list[Any]) -> str:
    if not items:
        return "<div class='small'>No items.</div>"
    return "<ul>" + "".join(f"<li>{_e(x)}</li>" for x in items if x is not None) + "</ul>"


def _e(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))

def _clean_memory(value: Any) -> str:
    if value is None:
        return "memory active"
    text = str(value)
    if text.strip().lower() in ["none", "items none", "items"]:
        return "memory active"
    return html.escape(text)