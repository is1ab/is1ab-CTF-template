/* Minimal viewer app (static HTML + vanilla JS)
 * Data source: ../data/index.json and ../data/progress.json in `viewer-data` branch.
 * No auth, no downloads, no private.yml access.
 */

const DATA_BASE = "../data";

// Sort state
let sortState = { column: null, direction: "asc" };

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function fetchJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return await res.json();
}

async function fetchText(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return await res.text();
}

function uniq(arr) {
  return Array.from(new Set(arr)).filter((x) => x !== "");
}

function humanSize(n) {
  const num = Number(n) || 0;
  const units = ["B", "KB", "MB", "GB"];
  let v = num;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function normalizeUser(s) {
  return String(s || "").trim().replace(/^@/, "");
}

function buildOption(selectEl, values, placeholder) {
  selectEl.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = "";
  opt0.textContent = placeholder;
  selectEl.appendChild(opt0);

  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  }
}

function matchesFilters(item, filters) {
  const q = filters.q.toLowerCase();
  if (q) {
    const hay = `${item.title} ${item.name} ${item.category} ${item.status} ${item.assignee || ""}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  if (filters.category && item.category !== filters.category) return false;
  if (filters.difficulty && item.difficulty !== filters.difficulty) return false;
  if (filters.status && item.status !== filters.status) return false;
  if (filters.ready && !item.ready_for_release) return false;
  if (filters.assignee) {
    if (normalizeUser(item.assignee) !== normalizeUser(filters.assignee)) return false;
  }
  return true;
}

function sortItems(items) {
  if (!sortState.column) return items;
  const col = sortState.column;
  const dir = sortState.direction === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    const va = String(a[col] || "").toLowerCase();
    const vb = String(b[col] || "").toLowerCase();
    if (va < vb) return -1 * dir;
    if (va > vb) return 1 * dir;
    return 0;
  });
}

function updateSortHeaders() {
  for (const th of document.querySelectorAll("th.sortable")) {
    const col = th.getAttribute("data-col");
    const existing = th.querySelector(".sort-indicator");
    if (existing) existing.remove();
    if (sortState.column === col) {
      const span = document.createElement("span");
      span.className = "sort-indicator";
      span.textContent = sortState.direction === "asc" ? " \u25B2" : " \u25BC";
      th.appendChild(span);
    }
  }
}

function rowHtml(item) {
  const owners = (item.owners || []).join(", ");
  return `
    <tr data-path="${escapeHtml(item.data_path)}" class="row">
      <td><a href="#" class="link" data-open="1">${escapeHtml(item.title || item.name)}</a><div class="muted">${escapeHtml(item.name)}</div></td>
      <td><span class="badge">${escapeHtml(item.category)}</span></td>
      <td>${escapeHtml(item.difficulty || "")}</td>
      <td>${escapeHtml(item.status || "planning")}</td>
      <td class="muted">${escapeHtml(owners)}</td>
      <td class="muted">${escapeHtml(item.assignee || "")}</td>
      <td class="muted">${escapeHtml(item.updated_at || "")}</td>
    </tr>
  `;
}

function renderMarkdownBasic(md) {
  const lines = String(md || "").split(/\r?\n/);
  let html = "";
  let inCode = false;
  let codeBuf = [];

  function flushCode() {
    if (!codeBuf.length) return;
    html += `<pre>${escapeHtml(codeBuf.join("\n"))}</pre>`;
    codeBuf = [];
  }

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        inCode = false;
        flushCode();
      } else {
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      codeBuf.push(line);
      continue;
    }

    if (line.startsWith("# ")) {
      html += `<h2>${escapeHtml(line.slice(2).trim())}</h2>`;
    } else if (line.startsWith("## ")) {
      html += `<h3>${escapeHtml(line.slice(3).trim())}</h3>`;
    } else if (line.startsWith("### ")) {
      html += `<h4>${escapeHtml(line.slice(4).trim())}</h4>`;
    } else if (line.trim() === "") {
      html += "";
    } else {
      html += `<p>${escapeHtml(line)}</p>`;
    }
  }

  if (inCode) flushCode();
  return html;
}

async function openDetail(item) {
  const base = `${DATA_BASE}/challenges/${item.category}/${item.name}`;
  const [publicYmlText, readmeText, filesJson] = await Promise.all([
    fetchText(`${base}/public.yml`),
    fetchText(`${base}/README.md`),
    fetchJson(`${base}/files.json`),
  ]);

  const files = (filesJson.items || []).map((f) => {
    return `<li class="muted">${escapeHtml(f.name)} · ${escapeHtml(humanSize(f.size))} · ${escapeHtml(f.modified_at)}</li>`;
  });

  const owners = (item.owners || []).join(", ");

  $("detail").innerHTML = `
    <div>
      <h2>${escapeHtml(item.title || item.name)}</h2>
      <div class="row">
        <div class="kv"><b>Category</b>: ${escapeHtml(item.category)}</div>
        <div class="kv"><b>Difficulty</b>: ${escapeHtml(item.difficulty || "")}</div>
        <div class="kv"><b>Status</b>: ${escapeHtml(item.status || "")}</div>
        <div class="kv"><b>Owners</b>: ${escapeHtml(owners)}</div>
        <div class="kv"><b>Assignee</b>: ${escapeHtml(item.assignee || "")}</div>
        <div class="kv"><b>Updated</b>: ${escapeHtml(item.updated_at || "")}</div>
      </div>

      <div class="card" style="margin-top: 12px">
        <div class="card-title">README</div>
        <div>${renderMarkdownBasic(readmeText)}</div>
      </div>

      <div class="card" style="margin-top: 12px">
        <div class="card-title">Attachments (listed only)</div>
        <ul>
          ${files.length ? files.join("\n") : '<li class="muted">No files/</li>'}
        </ul>
      </div>

      <div class="card" style="margin-top: 12px">
        <div class="card-title">public.yml (sanitized)</div>
        <pre>${escapeHtml(publicYmlText)}</pre>
      </div>
    </div>
  `;
}

function computeMetrics(indexItems) {
  const total = indexItems.length;
  const ready = indexItems.filter((x) => !!x.ready_for_release).length;
  const done = indexItems.filter((x) => ["completed", "deployed"].includes(String(x.status || ""))).length;
  return { total, ready, done };
}

function exportCsv(items) {
  const headers = ["Title", "Category", "Difficulty", "Status", "Owners", "Assignee", "Updated"];
  const rows = items.map((item) => [
    item.title || item.name,
    item.category,
    item.difficulty || "",
    item.status || "",
    (item.owners || []).join("; "),
    item.assignee || "",
    item.updated_at || "",
  ]);

  const escape = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const csv = [headers.map(escape).join(","), ...rows.map((r) => r.map(escape).join(","))].join("\n");

  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ctf-challenges-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function initTheme() {
  const saved = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
}

function renderList(indexItems) {
  const filters = {
    q: $("q").value || "",
    category: $("fCategory").value || "",
    difficulty: $("fDifficulty").value || "",
    status: $("fStatus").value || "",
    assignee: $("fAssignee").value || "",
    ready: $("fReady").checked,
  };

  const filtered = sortItems(indexItems.filter((it) => matchesFilters(it, filters)));
  $("listHint").textContent = `${filtered.length} / ${indexItems.length} shown`;
  $("tbody").innerHTML = filtered.map(rowHtml).join("\n");
  updateSortHeaders();

  // bind row clicks
  for (const tr of document.querySelectorAll("tr.row")) {
    tr.addEventListener("click", async (e) => {
      e.preventDefault();
      const path = tr.getAttribute("data-path") || "";
      const item = indexItems.find((x) => x.data_path === path);
      if (item) await openDetail(item);
    });
  }

  // bind CSV export
  $("exportBtn").onclick = () => exportCsv(filtered);
}

async function loadAll() {
  const [indexJson, progressJson] = await Promise.all([
    fetchJson(`${DATA_BASE}/index.json`),
    fetchJson(`${DATA_BASE}/progress.json`),
  ]);

  const items = indexJson.items || [];

  const projectName = progressJson?.project?.name || "";
  const genAt = progressJson.generated_at || indexJson.generated_at || "";
  $("subtitle").textContent = [projectName, genAt].filter(Boolean).join(" · ") || "";

  const m = computeMetrics(items);
  $("metricTotal").textContent = String(m.total);
  $("metricReady").textContent = String(m.ready);
  $("metricDone").textContent = String(m.done);
  $("metricGeneratedAt").textContent = genAt ? `Generated at ${genAt}` : "";

  const categories = uniq(items.map((x) => x.category)).sort();
  const diffs = uniq(items.map((x) => x.difficulty)).sort();
  const statuses = uniq(items.map((x) => x.status)).sort();

  buildOption($("fCategory"), categories, "All categories");
  buildOption($("fDifficulty"), diffs, "All difficulties");
  buildOption($("fStatus"), statuses, "All statuses");

  const rerender = () => renderList(items);
  for (const id of ["q", "fCategory", "fDifficulty", "fStatus", "fAssignee", "fReady"]) {
    $(id).addEventListener("input", rerender);
    $(id).addEventListener("change", rerender);
  }

  // bind sort headers
  for (const th of document.querySelectorAll("th.sortable")) {
    th.addEventListener("click", () => {
      const col = th.getAttribute("data-col");
      if (sortState.column === col) {
        sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
      } else {
        sortState.column = col;
        sortState.direction = "asc";
      }
      rerender();
    });
  }

  rerender();
  return { items };
}

async function main() {
  initTheme();

  $("themeBtn").addEventListener("click", toggleTheme);
  $("refreshBtn").addEventListener("click", async () => {
    await loadAll();
  });

  await loadAll();

  // auto refresh every 30s
  setInterval(() => {
    loadAll().catch(() => {});
  }, 30000);
}

main().catch((e) => {
  console.error(e);
  $("subtitle").textContent = `Error: ${e.message}`;
});
