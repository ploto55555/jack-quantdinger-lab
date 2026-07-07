"""Jack OS helper API and local dashboard preview."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template_string, request

from app.services.jack_personal_os_registry import JACK_PERSONAL_OS_TOOLS
from app.services.jack_personal_os_rules import decide_risk_percent, grade_setup


jack_os_api = Blueprint("jack_os_api", __name__, url_prefix="/api/jack-os")

DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jack Personal OS — Dashboard Preview</title>
  <style>
    :root {
      --bg: #050607;
      --panel: #0d1117;
      --panel2: #111827;
      --line: #263241;
      --text: #eef6ff;
      --muted: #8fa3b7;
      --green: #31f58f;
      --blue: #53b7ff;
      --yellow: #ffd166;
      --red: #ff5f6d;
      --purple: #d18bff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at top left, #122031 0, #050607 38%, #020303 100%);
      color: var(--text);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      min-height: 100vh;
    }
    .shell { width: min(1440px, calc(100vw - 28px)); margin: 14px auto; }
    .topbar {
      display: grid;
      grid-template-columns: 1.35fr .8fr .8fr .8fr;
      gap: 10px;
      margin-bottom: 10px;
    }
    .card {
      background: linear-gradient(180deg, rgba(17,24,39,.96), rgba(8,12,18,.96));
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 18px 55px rgba(0,0,0,.34);
    }
    .hero { padding: 18px; }
    .eyebrow { color: var(--green); font-size: 12px; letter-spacing: .18em; text-transform: uppercase; }
    h1 { margin: 6px 0 5px; font-size: 28px; line-height: 1.05; }
    .sub { color: var(--muted); font-size: 13px; line-height: 1.5; }
    .metric { padding: 16px; display: flex; flex-direction: column; justify-content: space-between; min-height: 112px; }
    .metric .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .12em; }
    .metric .value { font-size: 30px; font-weight: 800; margin-top: 12px; }
    .value.green { color: var(--green); }
    .value.yellow { color: var(--yellow); }
    .value.red { color: var(--red); }
    .value.blue { color: var(--blue); }
    .grid { display: grid; grid-template-columns: 1fr 1.1fr .95fr; gap: 10px; }
    .section { padding: 16px; min-height: 260px; }
    .title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
    .title strong { font-size: 14px; letter-spacing: .08em; text-transform: uppercase; }
    .pill { border: 1px solid var(--line); color: var(--muted); border-radius: 999px; padding: 4px 9px; font-size: 11px; }
    .formgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    label { color: var(--muted); font-size: 11px; display: block; margin-bottom: 6px; }
    input {
      width: 100%; background: #050910; color: var(--text); border: 1px solid var(--line);
      border-radius: 10px; padding: 11px 12px; outline: none; font-family: inherit;
    }
    input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(83,183,255,.13); }
    button {
      width: 100%; margin-top: 10px; border: 0; border-radius: 10px; padding: 12px 14px;
      background: linear-gradient(90deg, #1fef86, #62c8ff); color: #041008; font-weight: 900;
      font-family: inherit; cursor: pointer;
    }
    .resultbox { margin-top: 13px; background: #050910; border: 1px solid var(--line); border-radius: 12px; padding: 13px; }
    .row { display: flex; justify-content: space-between; gap: 10px; padding: 7px 0; border-bottom: 1px dashed rgba(143,163,183,.22); }
    .row:last-child { border-bottom: 0; }
    .row span:first-child { color: var(--muted); }
    .row span:last-child { text-align: right; font-weight: 800; }
    .tools { display: grid; gap: 8px; }
    .tool {
      border: 1px solid var(--line); background: rgba(5,9,16,.88); border-radius: 11px; padding: 10px;
      display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center;
    }
    .tool small { display: block; color: var(--muted); margin-top: 4px; line-height: 1.35; }
    .off { color: var(--yellow); border: 1px solid rgba(255,209,102,.35); padding: 3px 8px; border-radius: 999px; font-size: 11px; }
    .warning {
      margin-top: 10px; border: 1px solid rgba(255,95,109,.42); background: rgba(255,95,109,.08);
      color: #ffc0c5; border-radius: 12px; padding: 12px; font-size: 12px; line-height: 1.55;
    }
    .terminal { margin-top: 10px; padding: 14px; background: #030506; border: 1px solid var(--line); border-radius: 14px; min-height: 185px; }
    .terminal pre { margin: 0; white-space: pre-wrap; color: #b9ffcf; font-size: 12px; line-height: 1.55; }
    .footer { margin-top: 10px; color: var(--muted); font-size: 11px; display: flex; justify-content: space-between; }
    @media (max-width: 980px) { .topbar, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="card hero">
        <div class="eyebrow">Jack Personal AI Capital OS / Local Preview</div>
        <h1>Manual Decision Dashboard</h1>
        <div class="sub">AI can calculate, warn, and draft. Jack decides. Auto trading is OFF. This page is public for local development and does not place orders.</div>
      </div>
      <div class="card metric"><div class="label">Capital Mode</div><div id="mode" class="value yellow">WAIT</div></div>
      <div class="card metric"><div class="label">Setup Grade</div><div id="grade" class="value blue">--</div></div>
      <div class="card metric"><div class="label">Risk %</div><div id="risk" class="value green">0.00%</div></div>
    </div>

    <div class="grid">
      <div class="card section">
        <div class="title"><strong>Risk Input</strong><span class="pill">public local API</span></div>
        <div class="formgrid">
          <div><label>Equity USD</label><input id="equity" type="number" value="500" /></div>
          <div><label>Drawdown %</label><input id="drawdown" type="number" value="0" /></div>
          <div><label>Setup Score 0–20</label><input id="score" type="number" value="17" /></div>
          <div><label>Losing Streak</label><input id="streak" type="number" value="0" /></div>
        </div>
        <button onclick="calculate()">CALCULATE JACK RISK MODE</button>
        <div class="resultbox">
          <div class="row"><span>Allowed</span><span id="allowed">--</span></div>
          <div class="row"><span>Mode Note</span><span id="note">--</span></div>
          <div class="row"><span>Grade Note</span><span id="gradeNote">--</span></div>
        </div>
        <div class="warning">Safety Rule: This dashboard is for planning and review only. It cannot execute live trades, cannot auto-place orders, and cannot bypass Jack approval.</div>
      </div>

      <div class="card section">
        <div class="title"><strong>Jack Tool Registry</strong><span id="toolCount" class="pill">loading</span></div>
        <div id="tools" class="tools"></div>
      </div>

      <div class="card section">
        <div class="title"><strong>Decision Terminal</strong><span class="pill">v0.1</span></div>
        <div class="terminal"><pre id="terminal">BOOTING JACK OS...
API: /api/jack-os/tools
API: /api/jack-os/grade-setup
API: /api/jack-os/risk-decision
</pre></div>
      </div>
    </div>

    <div class="footer">
      <span>Jack Personal OS Preview — QuantDinger fork</span>
      <span>No broker execution in v1</span>
    </div>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);
    const terminal = $('terminal');
    function log(line) { terminal.textContent += "\n" + line; }
    function modeClass(mode) {
      if (mode === 'attack') return 'value green';
      if (mode === 'defense') return 'value yellow';
      if (mode === 'pause') return 'value red';
      return 'value blue';
    }
    async function loadTools() {
      const res = await fetch('/api/jack-os/tools');
      const body = await res.json();
      const tools = body.data.tools || [];
      $('toolCount').textContent = tools.length + ' tools / disabled';
      $('tools').innerHTML = tools.map(t => `
        <div class="tool">
          <div><strong>${t.id}</strong><small>${t.description}</small></div>
          <div class="off">${t.enabled ? 'ON' : 'OFF'}</div>
        </div>`).join('');
      log('TOOLS LOADED: ' + tools.map(t => t.id).join(', '));
    }
    async function calculate() {
      const score = Number($('score').value || 0);
      const riskPayload = {
        equity: Number($('equity').value || 0),
        drawdown_percent: Number($('drawdown').value || 0),
        setup_score: score,
        losing_streak: Number($('streak').value || 0)
      };
      const [gradeRes, riskRes] = await Promise.all([
        fetch('/api/jack-os/grade-setup', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({score})}),
        fetch('/api/jack-os/risk-decision', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(riskPayload)})
      ]);
      const gradeBody = await gradeRes.json();
      const riskBody = await riskRes.json();
      const g = gradeBody.data;
      const r = riskBody.data;
      $('grade').textContent = String(g.grade).toUpperCase();
      $('mode').textContent = String(r.mode).toUpperCase();
      $('mode').className = modeClass(r.mode);
      $('risk').textContent = Number(r.risk_percent).toFixed(2) + '%';
      $('allowed').textContent = r.allowed ? 'YES — manual planning only' : 'NO';
      $('note').textContent = r.note;
      $('gradeNote').textContent = g.note;
      log('SCAN: score=' + g.score + ' grade=' + g.grade + ' mode=' + r.mode + ' risk=' + r.risk_percent + '% allowed=' + r.allowed);
    }
    loadTools().then(calculate).catch(err => log('ERROR: ' + err.message));
  </script>
</body>
</html>
"""


def _tool_to_dict(tool):
    return {
        "id": tool.id,
        "category": tool.category,
        "label": tool.label,
        "description": tool.description,
        "risk_level": tool.risk_level,
        "read_only": tool.read_only,
        "enabled": tool.enabled,
        "safety": tool.safety,
    }


def _json_payload() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@jack_os_api.get("/")
def dashboard_shortcut():
    return render_template_string(DASHBOARD_HTML)


@jack_os_api.get("/dashboard")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@jack_os_api.get("/tools")
def tools():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "enabled": False,
            "auth_required": False,
            "tools": [_tool_to_dict(t) for t in JACK_PERSONAL_OS_TOOLS],
        },
    })


@jack_os_api.post("/grade-setup")
def setup_grade():
    payload = _json_payload()
    result = grade_setup(_to_int(payload.get("score"), 0))
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "score": result.score,
            "grade": result.grade.value,
            "note": result.note,
            "auth_required": False,
        },
    })


@jack_os_api.post("/risk-decision")
def risk_decision():
    payload = _json_payload()
    result = decide_risk_percent(
        equity=_to_float(payload.get("equity"), 0.0),
        drawdown_percent=_to_float(payload.get("drawdown_percent"), 0.0),
        setup_score=_to_int(payload.get("setup_score"), 0),
        losing_streak=_to_int(payload.get("losing_streak"), 0),
    )
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "allowed": result.allowed,
            "mode": result.mode.value,
            "risk_percent": result.risk_percent,
            "note": result.note,
            "auth_required": False,
        },
    })
