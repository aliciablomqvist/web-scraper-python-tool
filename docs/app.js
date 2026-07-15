const state = { manifest: null, rows: [], siteKey: null };

const els = {
  totalRows: document.getElementById("stat-total-rows"),
  totalSites: document.getElementById("stat-total-sites"),
  updated: document.getElementById("stat-updated"),
  siteSelect: document.getElementById("site-select"),
  search: document.getElementById("search"),
  theadRow: document.getElementById("thead-row"),
  tbody: document.getElementById("tbody"),
  rowCount: document.getElementById("row-count"),
  chartTitle: document.getElementById("chart-title"),
  chart: document.getElementById("chart"),
  emptyState: document.getElementById("empty-state"),
};

const LINK_COLUMNS = new Set(["Source URL", "Link to Documentary"]);
const CHART_CANDIDATES = ["Language", "Type", "Published year", "Topic", "Category"];

async function main() {
  const manifest = await fetch("data/manifest.json").then((r) => r.json()).catch(() => null);
  if (!manifest || !Object.keys(manifest.sites || {}).length) {
    els.emptyState.style.display = "block";
    document.getElementById("data-panel").style.display = "none";
    return;
  }
  state.manifest = manifest;

  const siteKeys = Object.keys(manifest.sites);
  els.totalSites.textContent = siteKeys.length;
  els.totalRows.textContent = siteKeys.reduce((sum, k) => sum + manifest.sites[k].count, 0);
  els.updated.textContent = formatDate(manifest.generated_at);

  els.siteSelect.innerHTML = siteKeys
    .map((k) => `<option value="${k}">${manifest.sites[k].name}</option>`)
    .join("");
  els.siteSelect.addEventListener("change", () => loadSite(els.siteSelect.value));
  els.search.addEventListener("input", render);

  await loadSite(siteKeys[0]);
}

async function loadSite(key) {
  state.siteKey = key;
  const rows = await fetch(`data/${key}.json`).then((r) => r.json()).catch(() => []);
  state.rows = rows;
  render();
  renderChart();
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function filteredRows() {
  const q = els.search.value.trim().toLowerCase();
  if (!q) return state.rows;
  return state.rows.filter((row) =>
    Object.values(row).some((v) => String(v).toLowerCase().includes(q))
  );
}

function render() {
  const rows = filteredRows();
  const columns = rows.length ? Object.keys(rows[0]) : state.rows.length ? Object.keys(state.rows[0]) : [];

  els.theadRow.innerHTML = columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("");

  const shown = rows.slice(0, 200);
  els.tbody.innerHTML = shown
    .map(
      (row) =>
        "<tr>" +
        columns
          .map((c) => {
            const value = row[c] ?? "";
            if (LINK_COLUMNS.has(c) && value) {
              return `<td><a href="${escapeAttr(value)}" target="_blank" rel="noopener">Öppna länk</a></td>`;
            }
            return `<td title="${escapeAttr(String(value))}">${escapeHtml(truncate(String(value), 80))}</td>`;
          })
          .join("") +
        "</tr>"
    )
    .join("");

  els.rowCount.textContent = `Visar ${shown.length} av ${rows.length} rader${
    rows.length !== state.rows.length ? ` (filtrerat från ${state.rows.length})` : ""
  }`;
}

function renderChart() {
  const field = CHART_CANDIDATES.find((f) => state.rows.some((r) => r[f]));
  if (!field || !state.rows.length) {
    els.chart.innerHTML = "";
    els.chartTitle.textContent = "Ingen kategorisk data hittad för diagram";
    return;
  }

  els.chartTitle.textContent = `Fördelning: ${field}`;

  const counts = {};
  for (const row of state.rows) {
    const raw = (row[field] || "").toString();
    for (const part of raw.split(",")) {
      const key = part.trim();
      if (!key) continue;
      counts[key] = (counts[key] || 0) + 1;
    }
  }

  const top = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const max = top.length ? top[0][1] : 1;

  els.chart.innerHTML = top
    .map(
      ([name, count]) => `
      <div class="bar-row">
        <div class="name" title="${escapeAttr(name)}">${escapeHtml(name)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${(count / max) * 100}%"></div></div>
        <div class="count">${count}</div>
      </div>`
    )
    .join("");
}

function truncate(text, n) {
  return text.length > n ? text.slice(0, n) + "…" : text;
}

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function escapeAttr(str) {
  return escapeHtml(str);
}

main();
