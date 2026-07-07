"""Simple browser page for importing Forex CSV and running a stored backtest."""
from __future__ import annotations

from flask import Blueprint, Response


jack_forex_import_page = Blueprint("jack_forex_import_page", __name__)


@jack_forex_import_page.get("/jack-forex-import")
def page():
    return Response(_HTML, mimetype="text/html")


_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jack Forex Import</title>
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #07110f; color: #e8fff6; }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    p { color: #9cc8b8; line-height: 1.5; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
    .card { border: 1px solid #1f4b3f; border-radius: 16px; background: #0d1d19; padding: 16px; box-shadow: 0 18px 50px rgba(0,0,0,.28); }
    label { display: block; color: #b8e7d6; margin-bottom: 6px; font-size: 13px; }
    input, textarea, button { width: 100%; border-radius: 10px; border: 1px solid #2a6655; background: #07110f; color: #e8fff6; font: inherit; }
    input { padding: 10px 12px; }
    textarea { height: 330px; padding: 12px; resize: vertical; line-height: 1.4; }
    button { cursor: pointer; padding: 12px 14px; background: #00a878; border-color: #00d094; color: #04100c; font-weight: 800; }
    button.secondary { background: #142923; color: #dffcef; border-color: #2a6655; }
    button.danger { background: #40301c; color: #ffe0b0; border-color: #7b5627; }
    .row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 12px; }
    .actions { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }
    pre { white-space: pre-wrap; overflow: auto; max-height: 520px; background: #050b0a; border: 1px solid #1f4b3f; padding: 14px; border-radius: 12px; color: #d9fff1; }
    .metric { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 12px 0; }
    .box { border: 1px solid #244f44; border-radius: 12px; padding: 12px; background: #081411; }
    .box b { display: block; font-size: 12px; color: #8fcab5; margin-bottom: 6px; }
    .box span { font-size: 20px; color: #fff; }
    .ok { color: #2af0a4; }
    .bad { color: #ffb870; }
    @media (max-width: 900px) { .grid, .row, .actions, .metric { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Jack Forex Import</h1>
    <p>Paste Forex CSV, import it into the local store, then run a simple stored-candle backtest. No Postman needed.</p>

    <div class="grid">
      <div class="card">
        <div class="row">
          <div><label>Symbol</label><input id="symbol" value="GBPJPY" /></div>
          <div><label>Timeframe</label><input id="timeframe" value="H4" /></div>
          <div><label>Initial Capital</label><input id="capital" value="10000" /></div>
        </div>

        <label>CSV Text</label>
        <textarea id="csv"></textarea>

        <div class="actions">
          <button onclick="loadTemplate()">Load Template</button>
          <button onclick="importCsv()">Import CSV</button>
          <button class="secondary" onclick="checkStored()">Check Stored</button>
          <button class="secondary" onclick="runBacktest()">Run Backtest</button>
        </div>
        <div class="actions">
          <button class="danger" onclick="clearOutput()">Clear Output</button>
        </div>
      </div>

      <div class="card">
        <h2>Result</h2>
        <div id="metrics" class="metric"></div>
        <pre id="out">Click Load Template first.</pre>
      </div>
    </div>
  </div>

<script>
const out = document.getElementById('out');
const metrics = document.getElementById('metrics');

function show(obj) {
  out.textContent = JSON.stringify(obj, null, 2);
}
function clearOutput() {
  out.textContent = '';
  metrics.innerHTML = '';
}
function getSymbol() { return document.getElementById('symbol').value.trim().toUpperCase() || 'GBPJPY'; }
function getTimeframe() { return document.getElementById('timeframe').value.trim().toUpperCase() || 'H4'; }
function getCapital() { return document.getElementById('capital').value.trim() || '10000'; }

async function loadTemplate() {
  const res = await fetch('/api/jack-forex-data/csv-template');
  const json = await res.json();
  document.getElementById('csv').value = json.data.csv_text;
  show({message: 'Template loaded. You can now click Import CSV.', preview: json.data.example_rows});
}

async function importCsv() {
  const csvText = document.getElementById('csv').value;
  const res = await fetch('/api/jack-forex-data/import-csv', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({csv_text: csvText})
  });
  const json = await res.json();
  show(json);
}

async function checkStored() {
  const res = await fetch(`/api/jack-forex-data/stored-candles?symbol=${encodeURIComponent(getSymbol())}&timeframe=${encodeURIComponent(getTimeframe())}&limit=20`);
  const json = await res.json();
  show(json);
}

async function runBacktest() {
  const res = await fetch(`/api/jack-backtest/run-forex-stored?symbol=${encodeURIComponent(getSymbol())}&timeframe=${encodeURIComponent(getTimeframe())}&initial_capital=${encodeURIComponent(getCapital())}`);
  const json = await res.json();
  show(json);
  renderMetrics(json.data && json.data.summary ? json.data.summary : {});
}

function renderMetrics(s) {
  const items = [
    ['Status', s.status || '-'],
    ['Candles', s.number_of_candles ?? '-'],
    ['Return %', s.total_return_percent ?? '-'],
    ['Max DD %', s.max_drawdown_percent ?? '-'],
    ['Final Equity', s.final_equity ?? '-'],
    ['Start', s.start_date || '-'],
    ['End', s.end_date || '-'],
    ['Trades', s.number_of_trades ?? '-']
  ];
  metrics.innerHTML = items.map(([k,v]) => `<div class="box"><b>${k}</b><span>${v}</span></div>`).join('');
}

loadTemplate();
</script>
</body>
</html>"""
