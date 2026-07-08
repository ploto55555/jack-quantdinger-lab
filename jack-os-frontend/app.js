const STORAGE_KEY = "jack-os-forward-tests-v1";
let activeFilter = "all";
let selectedId = null;

const sampleObservation = () => ({
  id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
  created_at: new Date().toISOString(),
  symbol: "GBPJPY",
  direction_bias: "bullish",
  strategy_candidate: "Trend Continuation / Pullback",
  setup_name: "H4 pullback + H1 compression",
  timeframe_context: "D1 bullish, H4 pullback zone, H1 compression, M15 awaiting confirmation",
  readiness_score: 78,
  signal_score: 74,
  market_phase: "trend pullback",
  entry_zone_note: "Research zone only. Wait for clean structure confirmation; no chase after impulsive movement.",
  invalidation_note: "Observation weakens if H1 structure breaks below the key pullback zone.",
  target_zone_note: "Next visible liquidity / resistance area for study and later review.",
  risk_note: "Manual decision required. Define invalidation first. Avoid oversized risk after losses.",
  ai_reason: "Saved because higher timeframe structure is constructive and lower timeframe compression may become a useful forward-test candidate.",
  ai_warning: "This is not mature confirmation. If price moves away before structure is clear, skip the observation.",
  status: "watching",
  result_r: "",
  result_note: "",
  reviewed_at: "",
  mode: "research",
  broker_status: "disconnected",
  decision_status: "manual_required",
  forward_test_only: true
});

function readRecords() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeRecords(records) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

function formatDate(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleString([], { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function renderRows() {
  const tbody = document.getElementById("forwardRows");
  const records = readRecords();
  const visible = activeFilter === "all" ? records : records.filter((record) => record.status === activeFilter);
  tbody.innerHTML = "";

  if (!visible.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="muted-text">No forward test observations yet. Save one observation to start building the Performance Brain data foundation.</td></tr>`;
    return;
  }

  visible.forEach((record) => {
    const row = document.createElement("tr");
    row.dataset.id = record.id;
    row.innerHTML = `
      <td>${formatDate(record.created_at)}</td>
      <td>${record.symbol}</td>
      <td>${record.direction_bias}</td>
      <td>${record.setup_name}</td>
      <td>${record.readiness_score}</td>
      <td>${record.status}</td>
      <td>${record.result_r || "--"}</td>
      <td>${record.mode} / ${record.broker_status}</td>
    `;
    row.addEventListener("click", () => selectRecord(record.id));
    tbody.appendChild(row);

    if (record.id === selectedId) {
      const detail = document.createElement("tr");
      detail.className = "detail-row";
      detail.innerHTML = `
        <td colspan="8">
          <div class="detail-grid">
            <div><strong>Why saved</strong>${record.ai_reason}</div>
            <div><strong>Invalidation</strong>${record.invalidation_note}</div>
            <div><strong>AI warning</strong>${record.ai_warning}</div>
            <div><strong>Safety</strong>Research mode. Broker disconnected. Manual decision required. Forward test only.</div>
          </div>
        </td>
      `;
      tbody.appendChild(detail);
    }
  });
}

function selectRecord(id) {
  selectedId = id;
  const record = readRecords().find((item) => item.id === id);
  if (!record) return;
  document.getElementById("reviewStatus").value = record.status || "watching";
  document.getElementById("reviewR").value = record.result_r || "";
  document.getElementById("reviewNote").value = record.result_note || "";
  renderRows();
}

function saveObservation() {
  const records = readRecords();
  const next = sampleObservation();
  records.unshift(next);
  writeRecords(records);
  selectedId = next.id;
  renderRows();
}

function saveReview() {
  if (!selectedId) return;
  const status = document.getElementById("reviewStatus").value;
  const resultR = document.getElementById("reviewR").value;
  const note = document.getElementById("reviewNote").value;
  const records = readRecords().map((record) => {
    if (record.id !== selectedId) return record;
    return {
      ...record,
      status,
      result_r: resultR,
      result_note: note,
      reviewed_at: status === "reviewed" ? new Date().toISOString() : record.reviewed_at
    };
  });
  writeRecords(records);
  renderRows();
}

function updateClock() {
  const now = new Date();
  document.getElementById("localDate").textContent = now.toLocaleDateString([], { weekday: "short", year: "numeric", month: "short", day: "2-digit" });
  document.getElementById("localTime").textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function checkBackend() {
  const target = document.getElementById("backendStatus");
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    target.textContent = res.ok ? "Backend: connected" : "Backend: unavailable";
    target.classList.toggle("ok", res.ok);
  } catch {
    target.textContent = "Backend: offline / frontend only";
  }
}

function setupNavigation() {
  const items = document.querySelectorAll(".nav-item");
  items.forEach((item) => {
    item.addEventListener("click", () => {
      items.forEach((x) => x.classList.remove("active"));
      item.classList.add("active");
    });
  });
}

function setupFilters() {
  const filters = document.querySelectorAll(".filter");
  filters.forEach((button) => {
    button.addEventListener("click", () => {
      filters.forEach((x) => x.classList.remove("active"));
      button.classList.add("active");
      activeFilter = button.dataset.filter;
      renderRows();
    });
  });
}

function setupCopyDraft() {
  document.getElementById("copyDraftBtn").addEventListener("click", async () => {
    const text = document.getElementById("studyDraft").textContent;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      console.log(text);
    }
  });
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("saveObservationBtn").addEventListener("click", saveObservation);
  document.getElementById("saveReviewBtn").addEventListener("click", saveReview);
  setupNavigation();
  setupFilters();
  setupCopyDraft();
  updateClock();
  setInterval(updateClock, 1000 * 30);
  checkBackend();
  renderRows();
});
