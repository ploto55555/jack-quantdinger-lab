from __future__ import annotations

from flask import Response


def get_four_chart_dashboard_html_v1() -> Response:
    html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Jack AI Capital OS - Stable Four Chart Dashboard</title>
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#070b10;--bar:#0d1520;--panel:#0f1722;--card:#080d14;--line:#233044;--line2:#334155;--text:#dbe7f3;--muted:#8b98a8;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--cyan:#38bdf8;--purple:#a78bfa}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;overflow:hidden}.app{height:100vh;display:grid;grid-template-rows:74px minmax(0,1fr) 230px}.bar{display:flex;gap:7px;align-items:center;padding:6px 8px;background:var(--bar);border-bottom:1px solid var(--line);flex-wrap:wrap}.brand{font-weight:900;font-size:13px;white-space:nowrap}.sym{width:92px;background:#050910;border:1px solid var(--line);color:var(--text);border-radius:6px;padding:6px 8px;font-weight:800}.btn,.pill,.tog{border:1px solid var(--line);background:#121b28;color:var(--text);border-radius:6px;padding:6px 9px;font-size:12px;cursor:pointer;text-decoration:none}.pill{cursor:default;color:var(--muted)}.tog.on{background:#1d4ed8;border-color:#60a5fa}.tog.off{opacity:.48}.health{margin-left:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap}.badge{border:1px solid var(--line);border-radius:999px;padding:5px 8px;font-size:11px;font-weight:800;background:#0b1220;color:var(--muted);white-space:nowrap}.ok{color:var(--green);border-color:#14532d;background:#052e16}.warn{color:var(--yellow);border-color:#713f12;background:#2b1b05}.bad{color:var(--red);border-color:#7f1d1d;background:#2b0505}.blue{color:#93c5fd;border-color:#1d4ed8;background:#071326}.muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:8px;padding:8px;background:#05080d;min-height:0}.card{position:relative;border:1px solid var(--line);background:var(--card);border-radius:8px;overflow:hidden;min-height:220px}.head{position:absolute;left:8px;right:8px;top:7px;display:flex;gap:6px;align-items:center;z-index:3;pointer-events:none}.tfTitle{font-weight:900;background:rgba(15,23,34,.95);border:1px solid var(--line);border-radius:6px;padding:4px 7px;font-size:12px}.tag,.mini{background:rgba(15,23,34,.95);border:1px solid var(--line);border-radius:999px;padding:4px 7px;font-size:11px;color:var(--muted)}.mini{margin-left:auto;border-radius:6px}.chart{width:100%;height:100%}.overlay{position:absolute;left:8px;bottom:24px;right:8px;z-index:2;color:var(--muted);font-size:11px;pointer-events:none}.tvlogo{position:absolute;left:8px;bottom:6px;font-weight:900;font-size:11px;color:#dbe7f3;opacity:.45;z-index:2}.pulse{animation:pulse 1.1s linear infinite}@keyframes pulse{50%{opacity:.45}}
.term{display:grid;grid-template-rows:44px 35px 1fr;background:var(--panel);border-top:1px solid var(--line);min-height:0}.strip{display:grid;grid-template-columns:repeat(4,1fr) 2fr;gap:8px;padding:6px 8px;border-bottom:1px solid var(--line);background:#0b131e}.box{border:1px solid var(--line);background:#101824;border-radius:7px;padding:5px 8px;min-width:0}.k{font-size:10px;color:var(--muted);text-transform:uppercase}.v{font-size:14px;font-weight:900;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.read{font-size:12px;color:#cbd5e1;line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tabs{display:flex;background:#080d14;border-bottom:1px solid var(--line);padding-left:8px;overflow-x:auto}.tab{padding:9px 13px;color:var(--muted);font-size:12px;cursor:pointer;white-space:nowrap}.tab.active{background:#101824;color:var(--text);border:1px solid var(--line);border-bottom:0;border-radius:8px 8px 0 0}.body{overflow:auto;padding:8px}.tbl{width:100%;border-collapse:collapse;font-size:12px}.tbl th,.tbl td{padding:7px 9px;border-bottom:1px solid #223044;text-align:left;vertical-align:top}.tbl th{width:220px;color:var(--muted);background:#0d1520}.list{margin:0;padding:0;list-style:none}.list li{padding:7px 9px;border-bottom:1px solid #223044;color:#cbd5e1;font-size:12px}.small{font-size:11px;color:var(--muted)}
@media(max-width:1000px){html,body{overflow:auto}.app{height:auto;min-height:100vh;grid-template-rows:auto 1240px 390px}.grid{grid-template-columns:1fr;grid-template-rows:repeat(4,300px)}.strip{grid-template-columns:repeat(2,1fr)}.health{margin-left:0}}
</style>
</head>
<body>
<div class="app">
 <div class="bar">
  <div class="brand">JACK AI CAPITAL OS</div>
  <input id="symbol" class="sym" value="GBPJPY" />
  <button class="btn" onclick="loadAll(true)">Refresh</button>
  <button class="btn" onclick="fitAll()">Fit</button>
  <a id="dailyLink" class="btn" target="_blank">Daily Summary</a>
  <span class="pill">STEP 55C · STABLE CHART LAYER</span>
  <button class="tog on" data-ind="ema50" onclick="toggleInd('ema50')">EMA50</button>
  <button class="tog on" data-ind="ema20" onclick="toggleInd('ema20')">EMA20</button>
  <button class="tog off" data-ind="sma14" onclick="toggleInd('sma14')">SMA14</button>
  <button class="tog off" data-ind="sma20" onclick="toggleInd('sma20')">SMA20</button>
  <button class="tog on" data-ind="bb" onclick="toggleInd('bb')">BB</button>
  <div class="health">
   <span id="systemBadge" class="badge warn">SYSTEM CHECKING</span>
   <span id="tickBadge" class="badge warn">TICK —</span>
   <span id="spreadBadge" class="badge">SPREAD —</span>
   <span id="sessionBadge" class="badge">SESSION —</span>
   <span id="finalBadge" class="badge blue">RESEARCH ONLY</span>
  </div>
 </div>
 <div class="grid">
  <div class="card"><div class="head"><span class="tfTitle">D1</span><span id="tagD1" class="tag">INIT</span><span id="srcD1" class="tag">waiting</span><span id="miniD1" class="mini">—</span></div><div id="chartD1" class="chart"></div><div id="ovD1" class="overlay">initializing D1 chart...</div><div class="tvlogo">TV</div></div>
  <div class="card"><div class="head"><span class="tfTitle">H1</span><span id="tagH1" class="tag">INIT</span><span id="srcH1" class="tag">waiting</span><span id="miniH1" class="mini">—</span></div><div id="chartH1" class="chart"></div><div id="ovH1" class="overlay">initializing H1 chart...</div><div class="tvlogo">TV</div></div>
  <div class="card"><div class="head"><span class="tfTitle">M15</span><span id="tagM15" class="tag">INIT</span><span id="srcM15" class="tag">waiting</span><span id="miniM15" class="mini">—</span></div><div id="chartM15" class="chart"></div><div id="ovM15" class="overlay">initializing M15 chart...</div><div class="tvlogo">TV</div></div>
  <div class="card"><div class="head"><span class="tfTitle">M5</span><span id="tagM5" class="tag">INIT</span><span id="srcM5" class="tag">waiting</span><span id="miniM5" class="mini">—</span></div><div id="chartM5" class="chart"></div><div id="ovM5" class="overlay">initializing M5 chart...</div><div class="tvlogo">TV</div></div>
 </div>
 <div class="term">
  <div class="strip"><div class="box"><div class="k">D1</div><div class="v" id="d1">—</div></div><div class="box"><div class="k">H1</div><div class="v" id="h1">—</div></div><div class="box"><div class="k">M15</div><div class="v" id="m15">—</div></div><div class="box"><div class="k">M5</div><div class="v" id="m5">—</div></div><div class="box"><div class="k">AI / Data Read</div><div class="read" id="read">Loading stable data health...</div></div></div>
  <div class="tabs"><div class="tab active" onclick="showTab('overview',this)">Overview</div><div class="tab" onclick="showTab('live',this)">Live</div><div class="tab" onclick="showTab('candles',this)">Candles</div><div class="tab" onclick="showTab('indicators',this)">Indicators</div><div class="tab" onclick="showTab('warnings',this)">Warnings</div><div class="tab" onclick="showTab('debug',this)">Debug</div></div>
  <div class="body" id="body">Loading...</div>
 </div>
</div>
<script>
const TFS=['D1','H1','M15','M5'];
let SHOW={ema50:true,ema20:true,sma14:false,sma20:false,bb:true};
let TAB='overview';
let charts={};
let state={health:null,candles:{},indicators:{},errors:{},lastRefresh:null};
let livePriceLineByTf={};

function q(id){return document.getElementById(id)}
function symbol(){return (q('symbol').value||'GBPJPY').trim().toUpperCase().replace('/','').replace('_','')}
function f(v){return(v===null||v===undefined||v==='')?'—':String(v)}
function n(v){const x=Number(v);return Number.isFinite(x)?x:null}
function cls(status){const s=String(status||'').toUpperCase();if(s.includes('OK')||s.includes('LIVE')||s.includes('OPEN'))return'ok';if(s.includes('PARTIAL')||s.includes('STALE')||s.includes('HIGH')||s.includes('WARN')||s.includes('CHECK'))return'warn';if(s.includes('OFF')||s.includes('FAILED')||s.includes('ERROR')||s.includes('MISSING')||s.includes('CLOSED'))return'bad';return''}
function setBadge(id,text,status){const el=q(id); if(!el)return; el.textContent=text; el.className='badge '+cls(status||text)}
function tvTime(t){if(typeof t==='number')return Math.floor(t);const d=new Date(t);if(!isNaN(d.getTime()))return Math.floor(d.getTime()/1000);return Math.floor(Date.now()/1000)}
function fmtPrice(v){const x=n(v);return x===null?'—':x.toFixed(3)}
function cacheKey(tf,type){return `jack55c_${symbol()}_${tf}_${type}`}
function saveCache(tf,type,value){try{localStorage.setItem(cacheKey(tf,type),JSON.stringify(value||[]))}catch(e){}}
function loadCache(tf,type){try{return JSON.parse(localStorage.getItem(cacheKey(tf,type))||'[]')}catch(e){return[]}}
async function fetchJson(url,timeout=7000){const c=new AbortController();const t=setTimeout(()=>c.abort(),timeout);try{const r=await fetch(url,{signal:c.signal,cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return await r.json()}finally{clearTimeout(t)}}
function endpoint(path){return path}

function initChart(tf){
 if(charts[tf])return;
 const el=q('chart'+tf);
 if(!window.LightweightCharts){q('ov'+tf).textContent='Chart library not loaded. Check internet/CDN.';return}
 const chart=LightweightCharts.createChart(el,{layout:{background:{color:'#080d14'},textColor:'#cbd5e1'},grid:{vertLines:{color:'#111827'},horzLines:{color:'#1b2533'}},rightPriceScale:{borderColor:'#263241'},timeScale:{borderColor:'#263241',timeVisible:true,secondsVisible:false},crosshair:{mode:LightweightCharts.CrosshairMode.Normal}});
 const candle=chart.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',borderUpColor:'#22c55e',borderDownColor:'#ef4444',wickUpColor:'#22c55e',wickDownColor:'#ef4444'});
 const series={ema50:chart.addLineSeries({color:'#3b82f6',lineWidth:2,title:'EMA50'}),ema20:chart.addLineSeries({color:'#38bdf8',lineWidth:1,title:'EMA20'}),sma14:chart.addLineSeries({color:'#eab308',lineWidth:1,title:'SMA14'}),sma20:chart.addLineSeries({color:'#f97316',lineWidth:1,title:'SMA20'}),bbUpper:chart.addLineSeries({color:'#a78bfa',lineWidth:1,title:'BB Upper'}),bbMiddle:chart.addLineSeries({color:'#a78bfa',lineWidth:1,title:'BB Mid'}),bbLower:chart.addLineSeries({color:'#a78bfa',lineWidth:1,title:'BB Lower'})};
 charts[tf]={chart,candle,series,loaded:false,lastLiveLine:null};
 new ResizeObserver(()=>chart.applyOptions({width:Math.max(10,el.clientWidth),height:Math.max(10,el.clientHeight)})).observe(el);
 chart.applyOptions({width:Math.max(10,el.clientWidth),height:Math.max(10,el.clientHeight)});
}
function candleRowsToData(rows){return(rows||[]).map(x=>({time:tvTime(x.timestamp||x.time),open:n(x.open),high:n(x.high),low:n(x.low),close:n(x.close)})).filter(x=>[x.open,x.high,x.low,x.close].every(Number.isFinite))}
function lineData(series){return(series||[]).map(x=>({time:tvTime(x.timestamp||x.time),value:n(x.value)})).filter(x=>Number.isFinite(x.value))}
function setTfStatus(tf,text,status){const tag=q('tag'+tf);tag.textContent=text;tag.className='tag '+cls(status||text);}
function renderCandles(tf,rows,source,fit=false){initChart(tf);const pack=charts[tf];if(!pack)return;const data=candleRowsToData(rows);if(!data.length){q('ov'+tf).textContent='No candle data. Showing blank chart without crashing.';setTfStatus(tf,'NO DATA','bad');return false}pack.candle.setData(data);pack.loaded=true;if(fit)pack.chart.timeScale().fitContent();const last=data[data.length-1];q('mini'+tf).textContent=`Close ${fmtPrice(last.close)} · ${data.length} bars`;q('src'+tf).textContent=source||'candles ok';q('ov'+tf).textContent='';setTfStatus(tf,'OK','ok');return true}
function renderIndicators(tf,indPack){initChart(tf);const pack=charts[tf];if(!pack)return;const ind=((indPack||{}).indicators)||{};pack.series.ema50.setData(SHOW.ema50?lineData(ind.ema50):[]);pack.series.ema20.setData(SHOW.ema20?lineData(ind.ema20):[]);pack.series.sma14.setData(SHOW.sma14?lineData(ind.sma14):[]);pack.series.sma20.setData(SHOW.sma20?lineData(ind.sma20):[]);pack.series.bbUpper.setData(SHOW.bb?lineData(ind.bb_upper):[]);pack.series.bbMiddle.setData(SHOW.bb?lineData(ind.bb_middle):[]);pack.series.bbLower.setData(SHOW.bb?lineData(ind.bb_lower):[])}
function updateLiveLines(price,status){const p=n(price);if(p===null)return;TFS.forEach(tf=>{initChart(tf);const pack=charts[tf];if(!pack)return;if(pack.lastLiveLine){try{pack.candle.removePriceLine(pack.lastLiveLine)}catch(e){}}let color=status==='LIVE'?'#22c55e':status==='STALE'?'#eab308':'#8b98a8';pack.lastLiveLine=pack.candle.createPriceLine({price:p,color,lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,axisLabelVisible:true,title:'Live'});const mini=q('mini'+tf); if(mini && !mini.textContent.includes('bars')) mini.textContent='Live '+fmtPrice(p);});}
async function loadTimeframe(tf,manual=false){initChart(tf);q('ov'+tf).textContent='loading '+tf+' candles...';q('ov'+tf).classList.add('pulse');setTfStatus(tf,'LOADING','warn');let usedCache=false;
 try{const limit=tf==='H1'?260:tf==='D1'?220:220;const data=await fetchJson(endpoint(`/api/jack-brain/latest-candles-v1?symbol=${encodeURIComponent(symbol())}&timeframes=${tf}&limit=${limit}`),6500);const pack=((data.timeframes||{})[tf])||{};const rows=pack.candles||[];if(pack.ok&&rows.length){state.candles[tf]=pack;saveCache(tf,'candles',rows);renderCandles(tf,rows,(pack.file_name||'csv candles'),manual||!charts[tf].loaded)}else{throw new Error(pack.error||'empty candles')}}catch(e){state.errors[tf]='candles: '+e.message;const cached=loadCache(tf,'candles');usedCache=!!cached.length;if(usedCache){renderCandles(tf,cached,'LAST GOOD CACHE',false);setTfStatus(tf,'STALE','warn');q('ov'+tf).textContent='Data request failed. Showing last good cached candles.'}else{q('ov'+tf).textContent='Candle load failed: '+e.message;setTfStatus(tf,'FAILED','bad')}}
 try{const ind=await fetchJson(endpoint(`/api/jack-brain/indicator-overlay-v1?symbol=${encodeURIComponent(symbol())}&timeframe=${tf}&limit=260`),6500);if(ind.ok){state.indicators[tf]=ind;saveCache(tf,'indicators',ind);renderIndicators(tf,ind)}else{throw new Error('indicator empty')}}catch(e){const cached=loadCache(tf,'indicators');if(cached&&cached.indicators){state.indicators[tf]=cached;renderIndicators(tf,cached);state.errors[tf]=(state.errors[tf]||'')+' indicators cache used'}else{state.errors[tf]=(state.errors[tf]||'')+' indicators: '+e.message}}
 q('ov'+tf).classList.remove('pulse');
}
async function loadHealth(){try{const h=await fetchJson(endpoint(`/api/jack-brain/live-health-v1?symbol=${encodeURIComponent(symbol())}&timeframes=D1,H1,M15,M5&stale_after_seconds=15`),4500);state.health=h;setBadge('systemBadge',h.system_status||'SYSTEM —',h.system_status);setBadge('tickBadge','TICK '+f(h.tick_status)+(h.tick_age_seconds!=null?` ${h.tick_age_seconds}s`:''),h.tick_status);setBadge('spreadBadge','SPREAD '+f(h.spread_pips),h.spread_status);setBadge('sessionBadge',f(h.session),h.market_status);setBadge('finalBadge','RESEARCH ONLY','blue');q('read').textContent=`${h.system_status} · ${h.tick_status} · ${h.candle_status} · ${h.final_command}`;updateLiveLines(h.price,h.tick_status);renderTerm();return h}catch(e){setBadge('systemBadge','BACKEND ERROR','bad');q('read').textContent='Backend health failed: '+e.message;state.errors.health=e.message;renderTerm();return null}}
async function loadAiRead(){try{const d=await fetchJson(endpoint(`/api/jack-brain/ai-live-guide-v1?symbol=${encodeURIComponent(symbol())}`),6500);const text=(d.summary||d.ai_read||d.message||JSON.stringify(d).slice(0,240));q('read').textContent=String(text).replace(/buy now|sell now/ig,'research only');}catch(e){}}
function renderTerm(){const h=state.health||{};TFS.forEach(tf=>{const c=state.candles[tf]||{};const last=c.latest_candle||((c.candles||[]).slice(-1)[0])||{};q(tf.toLowerCase()).textContent=(c.ok?'OK':'—')+' '+f(last.timestamp||'')+' '+fmtPrice(last.close)});let body='';if(TAB==='overview'){body=`<table class="tbl"><tr><th>System</th><td>${f(h.system_status)}</td></tr><tr><th>Tick</th><td>${f(h.tick_status)} · age ${f(h.tick_age_seconds)}s · source ${f(h.tick_source)}</td></tr><tr><th>Price</th><td>bid ${f(h.bid)} · ask ${f(h.ask)} · mid ${f(h.mid)} · spread ${f(h.spread_pips)}</td></tr><tr><th>Session</th><td>${f(h.session)} · ${f(h.market_status)}</td></tr><tr><th>Command</th><td>${f(h.final_command)} · no auto trading</td></tr></table>`}
 else if(TAB==='live'){body=`<pre>${escapeHtml(JSON.stringify(h,null,2))}</pre>`}
 else if(TAB==='candles'){body='<table class="tbl"><tr><th>TF</th><th>Status</th><th>File</th><th>Rows</th><th>Latest</th></tr>'+TFS.map(tf=>{const c=state.candles[tf]||{};const last=c.latest_candle||((c.candles||[]).slice(-1)[0])||{};return`<tr><td>${tf}</td><td>${c.ok?'OK':'CHECK'}</td><td>${f(c.file_name)}</td><td>${f(c.returned_rows||c.candles?.length)}</td><td>${f(last.timestamp)} · ${fmtPrice(last.close)}</td></tr>`}).join('')+'</table>'}
 else if(TAB==='indicators'){body='<table class="tbl"><tr><th>TF</th><th>Status</th><th>Latest RSI</th><th>Latest EMA50</th></tr>'+TFS.map(tf=>{const i=state.indicators[tf]||{};const lv=i.latest_values||{};return`<tr><td>${tf}</td><td>${i.ok?'OK':'PARTIAL'}</td><td>${f(lv.rsi14?.value)}</td><td>${f(lv.ema50?.value)}</td></tr>`}).join('')+'</table>'}
 else if(TAB==='warnings'){const warnings=(h.warnings||[]);body='<ul class="list">'+(warnings.length?warnings.map(x=>`<li>${escapeHtml(String(x))}</li>`).join(''):'<li>No current health warnings.</li>')+'</ul>'}
 else{body=`<pre>${escapeHtml(JSON.stringify({health:state.health,errors:state.errors,lastRefresh:state.lastRefresh},null,2))}</pre>`}q('body').innerHTML=body}
function escapeHtml(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function showTab(name,el){TAB=name;document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));el.classList.add('active');renderTerm()}
function toggleInd(name){SHOW[name]=!SHOW[name];document.querySelectorAll(`[data-ind="${name}"]`).forEach(b=>{b.classList.toggle('on',SHOW[name]);b.classList.toggle('off',!SHOW[name])});TFS.forEach(tf=>renderIndicators(tf,state.indicators[tf]||loadCache(tf,'indicators')))}
function fitAll(){TFS.forEach(tf=>{if(charts[tf])charts[tf].chart.timeScale().fitContent()})}
async function loadAll(manual=false){state.lastRefresh=new Date().toISOString();q('dailyLink').href=`/api/jack-brain/daily-ai-summary-v1?symbol=${encodeURIComponent(symbol())}`;TFS.forEach(tf=>initChart(tf));await loadHealth();await Promise.all(TFS.map(tf=>loadTimeframe(tf,manual)));await loadHealth();loadAiRead();renderTerm()}
function start(){if(!window.LightweightCharts){q('body').textContent='Chart library not loaded. Check browser internet/CDN.';return}TFS.forEach(tf=>initChart(tf));loadAll(true);setInterval(loadHealth,2500);setInterval(()=>TFS.forEach(tf=>loadTimeframe(tf,false)),15000);setInterval(loadAiRead,30000)}
window.addEventListener('load',start);
</script>
</body>
</html>'''
    return Response(html, mimetype="text/html")
