from __future__ import annotations


def build_dashboard_preview_html_v1() -> str:
    return r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jack Capital OS Dashboard Preview</title>
  <style>
    :root {
      --bg: #070b10;
      --panel: #0d141c;
      --panel2: #121c27;
      --line: #253344;
      --text: #e6edf5;
      --muted: #8fa3b7;
      --green: #31d07b;
      --amber: #f4b84a;
      --red: #ff6b6b;
      --blue: #6aa9ff;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Consolas, Monaco, 'Courier New', monospace; }
    .wrap { width: 100%; max-width: 1480px; margin: 0 auto; padding: 18px; }
    .top { display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: end; border-bottom: 1px solid var(--line); padding-bottom: 14px; }
    h1 { margin: 0; font-size: 22px; letter-spacing: .04em; }
    .sub { margin-top: 6px; color: var(--muted); font-size: 13px; }
    .badge { border: 1px solid var(--line); background: var(--panel); padding: 8px 10px; font-size: 12px; color: var(--muted); }
    .grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }
    .metric { background: var(--panel); border: 1px solid var(--line); padding: 14px; min-height: 88px; }
    .metric .label { color: var(--muted); font-size: 12px; text-transform: uppercase; }
    .metric .value { font-size: 28px; margin-top: 8px; }
    .main { display: grid; grid-template-columns: 1.2fr .8fr; gap: 12px; margin-top: 12px; }
    .panel { background: var(--panel); border: 1px solid var(--line); padding: 14px; }
    .panel h2 { margin: 0 0 12px; font-size: 15px; color: var(--text); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--line); padding: 10px 8px; text-align: left; vertical-align: top; }
    th { color: var(--muted); font-weight: normal; text-transform: uppercase; font-size: 11px; }
    .active { color: var(--green); }
    .skip { color: var(--red); }
    .warn { color: var(--amber); }
    .muted { color: var(--muted); }
    .score { color: var(--blue); font-weight: bold; }
    .cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 12px; }
    .card { background: var(--panel2); border: 1px solid var(--line); padding: 12px; min-height: 190px; }
    .card .sym { font-size: 19px; font-weight: bold; }
    .card .pid { color: var(--muted); font-size: 11px; margin-top: 5px; min-height: 28px; }
    .kv { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 12px; font-size: 12px; }
    .kv div { background: #0a1017; border: 1px solid #1c2a38; padding: 7px; }
    .flag { display: inline-block; border: 1px solid var(--line); padding: 3px 6px; margin-top: 8px; font-size: 11px; color: var(--muted); }
    .focus { margin: 0; padding-left: 18px; color: var(--muted); font-size: 13px; line-height: 1.7; }
    .error { color: var(--red); background: #1c0d0d; border: 1px solid #4a2222; padding: 16px; margin-top: 16px; }
    @media (max-width: 1100px) { .grid4, .cards, .main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>JACK CAPITAL OS — RESEARCH DASHBOARD PREVIEW</h1>
        <div class="sub">One-screen status view. Research candidates only. No execution layer.</div>
      </div>
      <div class="badge" id="updated">loading...</div>
    </div>
    <div id="app"></div>
  </div>

<script>
function fmt(v){ return v === null || v === undefined ? '-' : v; }
function n(v){ return typeof v === 'number' ? v.toFixed(2) : fmt(v); }
function cls(status){ return status === 'active_candidate' ? 'active' : 'skip'; }
async function main(){
  const res = await fetch('/api/jack-backtest/dashboard-summary-v1');
  if(!res.ok){ throw new Error('API not ready: ' + res.status); }
  const json = await res.json();
  const d = json.data;
  document.getElementById('updated').textContent = d.created_at || 'ready';
  const s = d.summary || {};
  const cards = d.cards || [];
  const ranked = d.ranked_candidates || [];
  const attention = d.attention_items || [];
  document.getElementById('app').innerHTML = `
    <div class="grid4">
      <div class="metric"><div class="label">Active Candidates</div><div class="value active">${fmt(s.active_candidates)}</div></div>
      <div class="metric"><div class="label">Rejected For Now</div><div class="value skip">${fmt(s.rejected_for_now)}</div></div>
      <div class="metric"><div class="label">Best Current Profile</div><div class="value" style="font-size:16px">${fmt(s.best_current_profile)}</div></div>
      <div class="metric"><div class="label">Weakest Active</div><div class="value warn" style="font-size:16px">${fmt(s.weakest_active_profile)}</div></div>
    </div>

    <div class="cards">
      ${cards.map(c => `
        <div class="card">
          <div class="sym">${c.symbol}</div>
          <div class="pid">${c.title}</div>
          <div class="${cls(c.status)}" style="margin-top:8px;font-size:12px">${c.status}</div>
          <div class="kv">
            <div><span class="muted">Return</span><br>${n(c.result && c.result.return_percent)}%</div>
            <div><span class="muted">Max Drop</span><br>${n(c.result && c.result.max_drop_percent)}%</div>
            <div><span class="muted">Samples</span><br>${fmt(c.result && c.result.sample_count)}</div>
            <div><span class="muted">Ratio</span><br>${fmt(c.result && c.result.positive_negative_ratio)}</div>
          </div>
          <div class="flag">${(c.quality_flags || []).join(', ') || '-'}</div>
        </div>`).join('')}
    </div>

    <div class="main">
      <div class="panel">
        <h2>Ranked Candidates</h2>
        <table><thead><tr><th>Rank</th><th>Symbol</th><th>Profile</th><th>Score</th><th>Return</th><th>Max Drop</th><th>Samples</th></tr></thead>
        <tbody>${ranked.map((r,i)=>`<tr><td>${i+1}</td><td>${r.symbol}</td><td>${r.profile_id}</td><td class="score">${r.score}</td><td>${n(r.return_percent)}%</td><td>${n(r.max_drop_percent)}%</td><td>${fmt(r.sample_count)}</td></tr>`).join('')}</tbody></table>
      </div>
      <div class="panel">
        <h2>Attention Items</h2>
        ${attention.length ? `<table><tbody>${attention.map(a=>`<tr><td class="warn">${a.symbol}</td><td>${a.profile_id}<br><span class="muted">${(a.flags||[]).join(', ')}</span></td></tr>`).join('')}</tbody></table>` : '<div class="muted">No attention items.</div>'}
        <h2 style="margin-top:18px">Next Focus</h2>
        <ul class="focus">${(d.next_focus || []).map(x=>`<li>${x}</li>`).join('')}</ul>
      </div>
    </div>`;
}
main().catch(err => { document.getElementById('app').innerHTML = `<div class="error">${err.message}</div>`; });
</script>
</body>
</html>'''
