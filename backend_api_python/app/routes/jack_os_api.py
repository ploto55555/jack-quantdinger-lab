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
  <title>Jack Personal OS — Terminal Dashboard</title>
  <style>
    :root {
      --bg: #030405;
      --panel: #080c10;
      --panel2: #0d1318;
      --panel3: #111a21;
      --line: #24313b;
      --line2: #3a4b59;
      --text: #e8f7ff;
      --muted: #8da1ad;
      --green: #39ff7f;
      --blue: #4fc3ff;
      --yellow: #ffd35c;
      --red: #ff6673;
      --orange: #ff9d52;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: #030405;
      color: var(--text);
      font-family: Consolas, "Courier New", ui-monospace, monospace;
      overflow: hidden;
    }
    .screen {
      width: 100vw;
      height: 100vh;
      padding: 10px;
      display: grid;
      grid-template-rows: 34px 122px 1fr 24px;
      gap: 8px;
      background:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px),
        radial-gradient(circle at 20% 0%, #101b22 0, #030405 38%);
      background-size: 24px 24px, 24px 24px, cover;
    }
    .bar, .box {
      border: 1px solid var(--line);
      background: rgba(8,12,16,.94);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.018), 0 10px 35px rgba(0,0,0,.25);
    }
    .bar {
      display: grid;
      grid-template-columns: 300px 1fr 210px 180px;
      align-items: center;
      padding: 0 12px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .brand { color: var(--green); font-weight: 900; }
    .live { color: var(--yellow); text-align: right; }
    .safe { color: var(--red); text-align: right; }
    .top {
      display: grid;
      grid-template-columns: 1.35fr repeat(5, 1fr);
      gap: 8px;
      min-height: 0;
    }
    .intro { padding: 14px 16px; }
    .kicker { color: var(--green); font-size: 11px; font-weight: 900; letter-spacing: .15em; }
    h1 { margin: 7px 0 7px; font-size: 25px; line-height: 1; }
    .intro p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.45; }
    .stat { padding: 12px; display: grid; grid-template-rows: 26px 1fr 19px; min-width: 0; }
    .label { color: var(--muted); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; }
    .value { font-size: 27px; font-weight: 900; align-self: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .hint { color: var(--muted); font-size: 10px; }
    .green { color: var(--green); } .blue { color: var(--blue); } .yellow { color: var(--yellow); } .red { color: var(--red); } .orange { color: var(--orange); }
    .main {
      min-height: 0;
      display: grid;
      grid-template-columns: 1.05fr 1.35fr 1.15fr 1.05fr;
      grid-template-rows: 1fr 1fr;
      gap: 8px;
      grid-template-areas:
        "input setup terminal rules"
        "input tools terminal stages";
    }
    .box { min-height: 0; overflow: hidden; }
    .boxhead {
      height: 32px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 10px;
      background: rgba(17,26,33,.72);
      font-size: 12px;
      font-weight: 900;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .tag { color: var(--muted); border: 1px solid var(--line2); border-radius: 999px; padding: 2px 7px; font-size: 10px; font-weight: 600; }
    .body { padding: 10px; height: calc(100% - 32px); overflow: auto; }
    .input { grid-area: input; }
    .setup { grid-area: setup; }
    .tools { grid-area: tools; }
    .terminalWrap { grid-area: terminal; }
    .rules { grid-area: rules; }
    .stages { grid-area: stages; }
    .formgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    label { display: block; color: var(--muted); font-size: 10px; margin-bottom: 5px; letter-spacing: .04em; text-transform: uppercase; }
    input {
      width: 100%;
      background: #030608;
      border: 1px solid var(--line2);
      color: var(--text);
      border-radius: 4px;
      padding: 9px 8px;
      font-family: inherit;
      font-weight: 900;
      outline: none;
    }
    input:focus { border-color: var(--blue); box-shadow: 0 0 0 2px rgba(79,195,255,.14); }
    button {
      width: 100%;
      margin: 9px 0;
      padding: 10px;
      border: 1px solid rgba(57,255,127,.45);
      border-radius: 4px;
      color: #021208;
      background: linear-gradient(90deg, var(--green), var(--blue));
      font-family: inherit;
      font-weight: 900;
      cursor: pointer;
    }
    .kv { border: 1px solid var(--line); background: #05080b; }
    .row { min-height: 30px; display: grid; grid-template-columns: 120px 1fr; border-bottom: 1px dashed rgba(141,161,173,.18); }
    .row:last-child { border-bottom: 0; }
    .row span { padding: 8px; font-size: 12px; }
    .row span:first-child { color: var(--muted); }
    .row span:last-child { font-weight: 900; text-align: right; }
    .warn { margin-top: 9px; border: 1px solid rgba(255,102,115,.48); color: #ffc4ca; background: rgba(255,102,115,.08); padding: 10px; font-size: 11px; line-height: 1.45; }
    .scorebar { height: 18px; background: #030608; border: 1px solid var(--line2); margin-bottom: 10px; position: relative; }
    .scorefill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--red), var(--yellow), var(--green)); transition: width .15s ease; }
    .checkgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
    .check { border: 1px solid var(--line); background: #05080b; padding: 8px; font-size: 11px; color: var(--muted); min-height: 36px; }
    .check b { color: var(--text); display: block; margin-bottom: 3px; }
    .tool { display: grid; grid-template-columns: 1fr 44px; gap: 8px; align-items: center; border-bottom: 1px solid rgba(141,161,173,.14); padding: 7px 0; }
    .tool:last-child { border-bottom: 0; }
    .tool strong { font-size: 12px; color: var(--text); }
    .tool small { display: block; color: var(--muted); font-size: 10px; line-height: 1.25; margin-top: 2px; }
    .off { justify-self: end; color: var(--yellow); border: 1px solid rgba(255,211,92,.4); padding: 3px 7px; border-radius: 999px; font-size: 10px; }
    .terminal {
      height: 100%;
      background: #020303;
      border: 1px solid #183021;
      padding: 10px;
      overflow: auto;
    }
    pre { margin: 0; white-space: pre-wrap; color: #baffc9; font-size: 11px; line-height: 1.48; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { border-bottom: 1px solid rgba(141,161,173,.16); padding: 7px 5px; text-align: left; }
    th { color: var(--muted); font-weight: 600; }
    td:last-child, th:last-child { text-align: right; }
    .footer { display: grid; grid-template-columns: 1fr 1fr 1fr; align-items: center; color: var(--muted); font-size: 11px; padding: 0 4px; }
    .footer span:nth-child(2) { text-align: center; color: var(--green); }
    .footer span:nth-child(3) { text-align: right; color: var(--red); }
    @media (max-width: 1100px) {
      body { overflow: auto; }
      .screen { height: auto; min-height: 100vh; grid-template-rows: auto auto auto auto; }
      .bar, .top, .main, .footer { grid-template-columns: 1fr; grid-template-areas: none; }
      .input, .setup, .tools, .terminalWrap, .rules, .stages { grid-area: auto; }
      .box { min-height: 260px; }
    }
  </style>
</head>
<body>
  <div class="screen">
    <div class="bar">
      <div class="brand">JACK PERSONAL AI CAPITAL OS</div>
      <div>FX / GOLD / CAPITAL DISCIPLINE TERMINAL</div>
      <div class="live">PUBLIC LOCAL PREVIEW</div>
      <div class="safe">AUTO TRADE OFF</div>
    </div>

    <div class="top">
      <div class="box intro">
        <div class="kicker">Jack Personal AI Capital OS / Local Preview</div>
        <h1>Manual Decision Dashboard</h1>
        <p>AI calculates, warns, and drafts. Jack decides. Auto trading is OFF. No broker execution in v1.</p>
      </div>
      <div class="box stat"><div class="label">Capital Mode</div><div id="mode" class="value yellow">WAIT</div><div class="hint">attack / normal / defense / pause</div></div>
      <div class="box stat"><div class="label">Setup Grade</div><div id="grade" class="value blue">--</div><div class="hint">0–20 Abu-style scan</div></div>
      <div class="box stat"><div class="label">Risk %</div><div id="risk" class="value green">0.00%</div><div class="hint">planning only</div></div>
      <div class="box stat"><div class="label">Allowed</div><div id="allowedTop" class="value yellow">--</div><div class="hint">manual approval required</div></div>
      <div class="box stat"><div class="label">Tools</div><div id="toolTop" class="value orange">6 OFF</div><div class="hint">registry only</div></div>
    </div>

    <div class="main">
      <div class="box input">
        <div class="boxhead"><span>Risk Input</span><span class="tag">public api</span></div>
        <div class="body">
          <div class="formgrid">
            <div><label>Equity USD</label><input id="equity" type="number" value="500" /></div>
            <div><label>Drawdown %</label><input id="drawdown" type="number" value="0" /></div>
            <div><label>Setup Score 0–20</label><input id="score" type="number" value="17" /></div>
            <div><label>Losing Streak</label><input id="streak" type="number" value="0" /></div>
          </div>
          <button onclick="calculate()">CALCULATE JACK RISK MODE</button>
          <div class="kv">
            <div class="row"><span>Allowed</span><span id="allowed">--</span></div>
            <div class="row"><span>Mode Note</span><span id="note">--</span></div>
            <div class="row"><span>Grade Note</span><span id="gradeNote">--</span></div>
          </div>
          <div class="warn">Safety Rule: planning and review only. It cannot execute live trades, cannot auto-place orders, and cannot bypass Jack approval.</div>
        </div>
      </div>

      <div class="box setup">
        <div class="boxhead"><span>Setup Quality Map</span><span id="scoreText" class="tag">score -- / 20</span></div>
        <div class="body">
          <div class="scorebar"><div id="scoreFill" class="scorefill"></div></div>
          <div class="checkgrid">
            <div class="check"><b>0–9 NO TRADE</b>Low quality. Protect capital.</div>
            <div class="check"><b>10–13 WATCH</b>Interesting, but not enough.</div>
            <div class="check"><b>14–16 A</b>Good setup, normal risk.</div>
            <div class="check"><b>17–18 A+</b>High quality, attack allowed.</div>
            <div class="check"><b>19–20 S</b>Rare best setup, still manual.</div>
            <div class="check"><b>Risk Rule</b>Drawdown/streak can force defense or pause.</div>
          </div>
        </div>
      </div>

      <div class="box tools">
        <div class="boxhead"><span>Jack Tool Registry</span><span id="toolCount" class="tag">loading</span></div>
        <div id="tools" class="body"></div>
      </div>

      <div class="box terminalWrap">
        <div class="boxhead"><span>Decision Terminal</span><span class="tag">v0.2 dense</span></div>
        <div class="body"><div class="terminal"><pre id="terminal">BOOTING JACK OS...
API /api/jack-os/tools
API /api/jack-os/grade-setup
API /api/jack-os/risk-decision
STATE waiting for local scan...</pre></div></div>
      </div>

      <div class="box rules">
        <div class="boxhead"><span>Operating Rules</span><span class="tag">v1 safety</span></div>
        <div class="body">
          <table>
            <tr><th>Rule</th><th>Status</th></tr>
            <tr><td>Live order execution</td><td class="red">OFF</td></tr>
            <tr><td>Auto trade</td><td class="red">OFF</td></tr>
            <tr><td>Draft plan</td><td class="yellow">OFF</td></tr>
            <tr><td>Risk calculator</td><td class="green">ON</td></tr>
            <tr><td>Setup score</td><td class="green">ON</td></tr>
            <tr><td>User approval</td><td class="green">REQUIRED</td></tr>
          </table>
        </div>
      </div>

      <div class="box stages">
        <div class="boxhead"><span>Capital Stage Guide</span><span class="tag">personal</span></div>
        <div class="body">
          <table>
            <tr><th>Equity</th><th>A+</th><th>S</th></tr>
            <tr><td>$500–2k</td><td>2–3%</td><td>3–5%</td></tr>
            <tr><td>$2k–10k</td><td>2–3%</td><td>3–5%</td></tr>
            <tr><td>$10k–100k</td><td>2–3%</td><td>3–4%</td></tr>
            <tr><td>$100k–1M</td><td>1–2%</td><td>2–3%</td></tr>
            <tr><td>$1M+</td><td>0.75–1%</td><td>1.5–2%</td></tr>
          </table>
        </div>
      </div>
    </div>

    <div class="footer">
      <span>Jack Personal OS Preview — QuantDinger fork</span>
      <span>Snowball System: every trade becomes future data</span>
      <span>No broker execution in v1</span>
    </div>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);
    const terminal = $('terminal');
    function log(line) { terminal.textContent += "\n" + line; terminal.scrollTop = terminal.scrollHeight; }
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
      $('toolTop').textContent = tools.length + ' OFF';
      $('tools').innerHTML = tools.map(t => `
        <div class="tool">
          <div><strong>${t.id}</strong><small>${t.description}</small></div>
          <div class="off">${t.enabled ? 'ON' : 'OFF'}</div>
        </div>`).join('');
      log('TOOLS_LOADED ' + tools.map(t => t.id).join(' | '));
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
      $('allowedTop').textContent = r.allowed ? 'YES' : 'NO';
      $('allowedTop').className = r.allowed ? 'value green' : 'value red';
      $('note').textContent = r.note;
      $('gradeNote').textContent = g.note;
      $('scoreText').textContent = 'score ' + g.score + ' / 20';
      $('scoreFill').style.width = Math.max(0, Math.min(100, g.score * 5)) + '%';
      log('SCAN score=' + g.score + ' grade=' + g.grade + ' mode=' + r.mode + ' risk=' + r.risk_percent + '% allowed=' + r.allowed);
    }
    ['equity','drawdown','score','streak'].forEach(id => $(id).addEventListener('input', calculate));
    loadTools().then(calculate).catch(err => log('ERROR ' + err.message));
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
