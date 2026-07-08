from flask import Response


def get_jack_brain_front_ui_html() -> Response:
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Jack QuantDinger Brain UI</title>
  <style>
    body {
      margin: 0;
      background: #05070a;
      color: #e8edf2;
      font-family: Consolas, Monaco, monospace;
    }

    .wrap {
      padding: 16px;
    }

    .top {
      border: 1px solid #263241;
      background: #0b1118;
      padding: 14px;
      margin-bottom: 12px;
    }

    h1 {
      margin: 0 0 8px 0;
      font-size: 20px;
    }

    .note {
      color: #94a3b8;
      font-size: 12px;
      margin-bottom: 12px;
    }

    .grid {
      display: grid;
      grid-template-columns: 280px 1fr 380px;
      gap: 12px;
      height: calc(100vh - 130px);
    }

    .panel {
      border: 1px solid #263241;
      background: #080d13;
      padding: 12px;
      overflow: auto;
    }

    .panel h2 {
      font-size: 14px;
      margin: 0 0 10px 0;
      color: #f8fafc;
    }

    label {
      display: block;
      font-size: 11px;
      color: #9fb2c7;
      margin-top: 8px;
      margin-bottom: 4px;
    }

    input, select, textarea {
      width: 100%;
      box-sizing: border-box;
      background: #05070a;
      color: #e8edf2;
      border: 1px solid #2c3b4c;
      padding: 8px;
      font-family: Consolas, Monaco, monospace;
    }

    textarea {
      height: 90px;
      resize: vertical;
    }

    button {
      background: #102235;
      color: #e8edf2;
      border: 1px solid #37516b;
      padding: 9px 10px;
      cursor: pointer;
      font-family: Consolas, Monaco, monospace;
      width: 100%;
      margin-top: 8px;
    }

    button:hover {
      background: #18324d;
    }

    .card {
      border: 1px solid #223041;
      background: #060a0f;
      padding: 10px;
      margin-bottom: 10px;
    }

    .card-title {
      font-size: 12px;
      color: #93c5fd;
      margin-bottom: 6px;
    }

    pre {
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      color: #dbeafe;
      margin: 0;
    }

    .status {
      color: #facc15;
    }

    .good {
      color: #86efac;
    }

    iframe {
      width: 100%;
      height: 100%;
      border: 1px solid #263241;
      background: #000;
    }
  </style>
</head>

<body>
  <div class="wrap">
    <div class="top">
      <h1>Jack QuantDinger Lab — Backend Brain Front UI</h1>
      <div class="note">
        Personal research support only. No broker connection. No auto trading.
      </div>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>Brain Controls</h2>

        <label>Symbol</label>
        <select id="symbol">
          <option value="GBPJPY">GBPJPY</option>
          <option value="USDJPY">USDJPY</option>
          <option value="GBPUSD">GBPUSD</option>
          <option value="EURUSD">EURUSD</option>
          <option value="XAUUSD">XAUUSD</option>
        </select>

        <label>Profile ID</label>
        <select id="profile_id">
          <option value="GBPJPY_H4_UP_V1">GBPJPY_H4_UP_V1</option>
          <option value="USDJPY_H4_UP_V1">USDJPY_H4_UP_V1</option>
          <option value="GBPUSD_H4_UP_V1">GBPUSD_H4_UP_V1</option>
          <option value="EURUSD_H4_UP_V1">EURUSD_H4_UP_V1</option>
          <option value="XAUUSD_H4_UP_V1">XAUUSD_H4_UP_V1</option>
        </select>

        <label>Setup Quality</label>
        <select id="setup_quality">
          <option value="A+">A+</option>
          <option value="S">S</option>
          <option value="A">A</option>
          <option value="B">B</option>
        </select>

        <label>Equity</label>
        <input id="equity" value="500" />

        <label>Peak Equity</label>
        <input id="peak_equity" value="500" />

        <label>Target Equity</label>
        <input id="target_equity" value="1000000" />

        <label>Ask Backend Brain</label>
        <textarea id="user_question">Explain this backtest result in simple language.</textarea>

        <button onclick="loadContext()">Load Brain Context</button>
        <button onclick="explainBacktest()">Explain Backtest</button>
        <button onclick="createJournalDraft()">Create Journal Draft</button>
        <button onclick="openSimpleDashboard()">Open Simple Dashboard</button>

        <div class="card">
          <div class="card-title">Status</div>
          <pre id="status">Ready.</pre>
        </div>
      </div>

      <div class="panel">
        <h2>Simple Dashboard Preview</h2>
        <iframe id="dashboardFrame"></iframe>
      </div>

      <div class="panel">
        <h2>Backend Brain Result</h2>

        <div class="card">
          <div class="card-title">Command / Risk</div>
          <pre id="commandBox">Waiting...</pre>
        </div>

        <div class="card">
          <div class="card-title">Brain Summary</div>
          <pre id="summaryBox">Waiting...</pre>
        </div>

        <div class="card">
          <div class="card-title">Memory / Journal</div>
          <pre id="memoryBox">Waiting...</pre>
        </div>

        <div class="card">
          <div class="card-title">Raw JSON</div>
          <pre id="rawBox">Waiting...</pre>
        </div>
      </div>
    </div>
  </div>

<script>
function params() {
  return new URLSearchParams({
    symbol: document.getElementById("symbol").value,
    profile_id: document.getElementById("profile_id").value,
    setup_quality: document.getElementById("setup_quality").value,
    equity: document.getElementById("equity").value,
    peak_equity: document.getElementById("peak_equity").value,
    target_equity: document.getElementById("target_equity").value,
    user_question: document.getElementById("user_question").value
  }).toString();
}

function setStatus(text) {
  document.getElementById("status").innerText = text;
}

function showResult(data) {
  document.getElementById("rawBox").innerText = JSON.stringify(data, null, 2);

  document.getElementById("commandBox").innerText =
    "command: " + (data.command || "n/a") + "\\n" +
    "risk_mode: " + (data.risk_mode || "n/a") + "\\n" +
    "llm_enabled: " + (data.llm_enabled ?? "n/a") + "\\n" +
    "provider: " + (data.provider || "n/a");

  document.getElementById("summaryBox").innerText =
    data.summary || JSON.stringify(data.input || data, null, 2);

  document.getElementById("memoryBox").innerText =
    "memory_used: " + JSON.stringify(data.memory_used ?? "n/a") + "\\n" +
    "journal_ready: " + JSON.stringify(data.journal_ready ?? "n/a") + "\\n" +
    "next_action: " + (data.next_action || "n/a") + "\\n" +
    "save_status: " + (data.save_status || "n/a");
}

async function loadContext() {
  setStatus("Loading context...");
  const url = "/api/jack-brain/context-v1?" + params();
  const res = await fetch(url);
  const data = await res.json();
  showResult(data);
  setStatus("Brain context loaded.");
}

async function explainBacktest() {
  setStatus("Explaining backtest...");
  const url = "/api/jack-brain/explain-backtest-v1?" + params();
  const res = await fetch(url);
  const data = await res.json();
  showResult(data);
  setStatus("Backtest explanation loaded.");
}

async function createJournalDraft() {
  setStatus("Creating journal draft...");
  const url = "/api/jack-brain/decision-journal-draft-v1?" + params();
  const res = await fetch(url);
  const data = await res.json();
  showResult(data);
  setStatus("Journal draft created.");
}

function openSimpleDashboard() {
  const url = "/api/jack-backtest/simple-ui-dashboard-v1?" + params();
  document.getElementById("dashboardFrame").src = url;
  setStatus("Simple dashboard opened.");
}

openSimpleDashboard();
</script>
</body>
</html>
"""
    return Response(html, mimetype="text/html")
