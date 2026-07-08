from __future__ import annotations

from flask import Response


def get_jack_beta_terminal_ui_html() -> Response:
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jack QuantDinger Lab Beta Terminal</title>
  <style>
    :root {
      --bg: #0b0f14;
      --panel: #111821;
      --panel2: #151f2b;
      --border: #243244;
      --text: #dbe7f3;
      --muted: #7f91a6;
      --green: #16c784;
      --red: #ea3943;
      --yellow: #f5c542;
      --blue: #4c8dff;
      --purple: #a970ff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      overflow: hidden;
    }

    .app {
      height: 100vh;
      display: grid;
      grid-template-rows: 48px 1fr 260px;
      grid-template-columns: 310px 1fr;
      grid-template-areas:
        "top top"
        "left charts"
        "bottom bottom";
    }

    .topbar {
      grid-area: top;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
      background: #0e141c;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
    }

    .brand {
      font-weight: 700;
      color: #ffffff;
      letter-spacing: .4px;
    }

    .top-controls {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    select, input, button, textarea {
      background: #0b1118;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 7px 9px;
      font-size: 12px;
    }

    button {
      cursor: pointer;
    }

    button.primary {
      background: var(--blue);
      border-color: var(--blue);
      color: white;
      font-weight: 700;
    }

    button.green {
      background: #0f8f61;
      border-color: #0f8f61;
      color: white;
      font-weight: 700;
    }

    .badge {
      padding: 5px 8px;
      border-radius: 999px;
      background: #162233;
      color: var(--muted);
      border: 1px solid var(--border);
      font-size: 11px;
    }

    .badge.safe {
      color: var(--green);
      border-color: rgba(22,199,132,.35);
    }

    .left {
      grid-area: left;
      background: var(--panel);
      border-right: 1px solid var(--border);
      overflow: auto;
      padding: 12px;
    }

    .section-title {
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .8px;
      margin: 12px 0 8px;
    }

    .watch-card {
      border: 1px solid var(--border);
      background: #0c121a;
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 8px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 4px;
    }

    .symbol {
      font-weight: 700;
      color: #fff;
    }

    .small {
      font-size: 11px;
      color: var(--muted);
    }

    .status-green { color: var(--green); }
    .status-yellow { color: var(--yellow); }
    .status-red { color: var(--red); }

    .chat-box {
      display: grid;
      gap: 8px;
    }

    textarea {
      width: 100%;
      min-height: 78px;
      resize: vertical;
      line-height: 1.4;
    }

    .quick-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }

    .charts {
      grid-area: charts;
      padding: 10px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 10px;
      background: #080c11;
    }

    .chart {
      background:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px),
        #0d131b;
      background-size: 38px 38px;
      border: 1px solid var(--border);
      border-radius: 10px;
      position: relative;
      overflow: hidden;
      padding: 12px;
    }

    .chart-title {
      font-size: 12px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      position: relative;
      z-index: 2;
    }

    .fake-line {
      position: absolute;
      left: 6%;
      right: 6%;
      top: 48%;
      height: 2px;
      background: linear-gradient(90deg, var(--green), var(--blue), var(--purple));
      transform: rotate(-5deg);
      opacity: .75;
    }

    .fake-line.down {
      transform: rotate(7deg);
      background: linear-gradient(90deg, var(--red), var(--yellow));
    }

    .chart-watermark {
      position: absolute;
      bottom: 14px;
      right: 16px;
      font-size: 22px;
      color: rgba(255,255,255,.045);
      font-weight: 800;
    }

    .bottom {
      grid-area: bottom;
      background: var(--panel);
      border-top: 1px solid var(--border);
      display: grid;
      grid-template-rows: 40px 1fr;
    }

    .tabs {
      display: flex;
      gap: 4px;
      padding: 6px 10px 0;
      border-bottom: 1px solid var(--border);
      overflow-x: auto;
    }

    .tab {
      padding: 8px 12px;
      border: 1px solid var(--border);
      border-bottom: none;
      border-radius: 8px 8px 0 0;
      color: var(--muted);
      background: #0d141d;
      font-size: 12px;
      cursor: pointer;
      white-space: nowrap;
    }

    .tab.active {
      color: white;
      background: var(--panel2);
    }

    .tab-content {
      padding: 12px;
      overflow: auto;
      background: var(--panel2);
      font-family: Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
    }

    .row {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }

    .row input {
      width: 100%;
    }

    .muted {
      color: var(--muted);
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="topbar">
      <div class="brand">Jack QuantDinger Lab · Beta Terminal</div>
      <div class="top-controls">
        <select id="symbol">
          <option>GBPJPY</option>
          <option>XAUUSD</option>
          <option>USDJPY</option>
          <option>GBPUSD</option>
          <option>EURUSD</option>
        </select>
        <input id="equity" value="500" style="width:90px" />
        <input id="target" value="1000000" style="width:110px" />
        <span class="badge safe">Research Only</span>
        <span class="badge">No Broker</span>
        <span class="badge">No Auto Trading</span>
      </div>
    </div>

    <aside class="left">
      <div class="section-title">AI Market Watch</div>

      <div class="watch-card">
        <div>
          <div class="symbol">GBPJPY</div>
          <div class="small">H4_UP_V1 · Candidate</div>
        </div>
        <div class="status-green">A+</div>
      </div>

      <div class="watch-card">
        <div>
          <div class="symbol">XAUUSD</div>
          <div class="small">NY Momentum · Research</div>
        </div>
        <div class="status-yellow">WATCH</div>
      </div>

      <div class="watch-card">
        <div>
          <div class="symbol">USDJPY</div>
          <div class="small">Breakout · Research</div>
        </div>
        <div class="status-yellow">WAIT</div>
      </div>

      <div class="section-title">Research Goal</div>
      <div class="chat-box">
        <textarea id="goal">daytrade 20 pips per day</textarea>
        <button class="primary" onclick="runStrategyResearch()">Run Strategy Research</button>
        <button onclick="runMarketContext()">Market Context</button>
      </div>

      <div class="section-title">Capital Path</div>
      <div class="row">
        <input id="dailyGrowth" value="5" />
        <input id="days" value="90" />
      </div>
      <button class="green" onclick="runCapitalPath()">Run Capital Simulator</button>

      <div class="quick-grid">
        <button onclick="runJournal()">Journal</button>
        <button onclick="runMemory()">Memory</button>
        <button onclick="runBrain()">Brain</button>
        <button onclick="clearOutput()">Clear</button>
      </div>

      <div class="section-title">Brain Status</div>
      <div class="small">Mode: <span class="status-green">Personal Research</span></div>
      <div class="small">Broker: <span class="status-red">False</span></div>
      <div class="small">Auto Trading: <span class="status-red">False</span></div>
      <div class="small">Memory: <span class="status-green">Enabled</span></div>
    </aside>

    <main class="charts">
      <div class="chart">
        <div class="chart-title"><span>Chart 1 · Entry / Signal</span><span>M15</span></div>
        <div class="fake-line"></div>
        <div class="chart-watermark">ENTRY</div>
      </div>

      <div class="chart">
        <div class="chart-title"><span>Chart 2 · Setup Strategy</span><span>H1</span></div>
        <div class="fake-line down"></div>
        <div class="chart-watermark">SETUP</div>
      </div>

      <div class="chart">
        <div class="chart-title"><span>Chart 3 · Higher TF Context</span><span>H4 / D1</span></div>
        <div class="fake-line"></div>
        <div class="chart-watermark">CONTEXT</div>
      </div>

      <div class="chart">
        <div class="chart-title"><span>Chart 4 · Equity / Drawdown</span><span>Backtest</span></div>
        <div class="fake-line"></div>
        <div class="chart-watermark">EQUITY</div>
      </div>
    </main>

    <section class="bottom">
      <div class="tabs">
        <div class="tab active" onclick="setTab(this, 'Overview')">Overview</div>
        <div class="tab" onclick="setTab(this, 'Performance')">Performance</div>
        <div class="tab" onclick="setTab(this, 'Trades')">Trades</div>
        <div class="tab" onclick="setTab(this, 'Properties')">Properties</div>
        <div class="tab" onclick="setTab(this, 'Goal Path')">Goal Path</div>
        <div class="tab" onclick="setTab(this, 'Strategy Research')">Strategy Research</div>
        <div class="tab" onclick="setTab(this, 'Journal')">Journal</div>
        <div class="tab" onclick="setTab(this, 'Memory')">Memory</div>
        <div class="tab" onclick="setTab(this, 'News')">News</div>
        <div class="tab" onclick="setTab(this, 'Calendar')">Calendar</div>
        <div class="tab" onclick="setTab(this, 'Logs')">Logs</div>
      </div>
      <div id="output" class="tab-content">Beta Terminal ready.

Use left buttons:
- Run Strategy Research
- Run Capital Simulator
- Market Context
- Journal
- Memory
- Brain</div>
    </section>
  </div>

<script>
  const output = document.getElementById("output");

  function pretty(data) {
    output.textContent = JSON.stringify(data, null, 2);
  }

  function setLoading(name) {
    output.textContent = "Loading " + name + "...";
  }

  function getSymbol() {
    return document.getElementById("symbol").value;
  }

  function getEquity() {
    return document.getElementById("equity").value || "500";
  }

  function getTarget() {
    return document.getElementById("target").value || "1000000";
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    return await res.json();
  }

  async function runStrategyResearch() {
    setLoading("Strategy Research");
    const goal = encodeURIComponent(document.getElementById("goal").value);
    const equity = getEquity();
    const url = `/api/jack-brain/strategy-research-v1?goal_text=${goal}&target_pips_per_day=20&start_equity=${equity}&backtest_years=10`;
    pretty(await fetchJson(url));
  }

  async function runCapitalPath() {
    setLoading("Capital Path");
    const equity = getEquity();
    const target = getTarget();
    const daily = document.getElementById("dailyGrowth").value || "5";
    const days = document.getElementById("days").value || "90";
    const url = `/api/jack-brain/capital-compounding-v1?start_equity=${equity}&daily_growth_percent=${daily}&days=${days}&target_equity=${target}`;
    pretty(await fetchJson(url));
  }

  async function runMarketContext() {
    setLoading("Market Context");
    const symbol = getSymbol();
    pretty(await fetchJson(`/api/jack-brain/market-context-v1?symbol=${symbol}`));
  }

  async function runJournal() {
    setLoading("Journal");
    const symbol = getSymbol();
    pretty(await fetchJson(`/api/jack-brain/list-journal-v1?symbol=${symbol}`));
  }

  async function runMemory() {
    setLoading("Memory");
    const symbol = getSymbol();
    pretty(await fetchJson(`/api/jack-brain/search-memory-v1?query=${symbol}`));
  }

  async function runBrain() {
    setLoading("Brain Context");
    const symbol = getSymbol();
    const equity = getEquity();
    const target = getTarget();
    pretty(await fetchJson(`/api/jack-brain/context-v1?symbol=${symbol}&equity=${equity}&target_equity=${target}`));
  }

  function clearOutput() {
    output.textContent = "Cleared.";
  }

  function setTab(el, name) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    el.classList.add("active");
    output.textContent = name + " tab selected. Use left action buttons to load backend data.";
  }
</script>
</body>
</html>
    """
    return Response(html, mimetype="text/html")
