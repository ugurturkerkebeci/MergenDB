"""
Mergen Studio: Zero-dependency, embedded modern dark-mode Web UI for MergenDB.
Served by `mergen serve` or `mergendb-server` at http://localhost:8765/studio.
"""

STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mergen Studio | Columnar Database Engine</title>
  <style>
    :root {
      --bg-base: #0b0f17;
      --bg-panel: #111726;
      --bg-input: #172033;
      --bg-hover: #1e293b;
      --border: #23324d;
      --primary: #00d2ff;
      --primary-glow: rgba(0, 210, 255, 0.25);
      --accent: #00ffaa;
      --accent-glow: rgba(0, 255, 170, 0.25);
      --danger: #ff4757;
      --warning: #ffa502;
      --text: #e2e8f0;
      --text-muted: #8899b5;
      --font-code: "JetBrains Mono", "Fira Code", "Consolas", monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-base);
      color: var(--text);
      font-family: var(--font-sans);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* Top Navbar */
    header {
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border);
      height: 54px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.25rem;
      user-select: none;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
    }
    .brand-icon {
      font-size: 1.5rem;
      filter: drop-shadow(0 0 6px var(--primary));
    }
    .brand-title {
      font-weight: 800;
      font-size: 1.1rem;
      letter-spacing: 0.05em;
      background: linear-gradient(135deg, #00d2ff 0%, #00ffaa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .brand-badge {
      background: rgba(0, 210, 255, 0.12);
      border: 1px solid rgba(0, 210, 255, 0.3);
      color: var(--primary);
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
      font-family: var(--font-code);
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .server-status {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 8px var(--accent);
    }

    /* Layout */
    .app-layout {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    /* Sidebar (Tables & Schemas) */
    aside {
      width: 290px;
      background: var(--bg-panel);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .sidebar-header {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .sidebar-title {
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
    }
    .btn-icon {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text-muted);
      border-radius: 6px;
      padding: 0.25rem 0.5rem;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-icon:hover {
      background: var(--bg-hover);
      color: var(--text);
      border-color: var(--primary);
    }
    .search-box {
      padding: 0.6rem 0.85rem;
      border-bottom: 1px solid var(--border);
    }
    .search-box input {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 6px;
      padding: 0.4rem 0.65rem;
      font-size: 0.8rem;
      outline: none;
    }
    .search-box input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }
    .table-list {
      flex: 1;
      overflow-y: auto;
      padding: 0.5rem;
    }
    .table-card {
      background: var(--bg-input);
      border: 1px solid transparent;
      border-radius: 8px;
      padding: 0.6rem 0.75rem;
      margin-bottom: 0.5rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .table-card:hover {
      border-color: var(--primary);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .table-card.active {
      border-color: var(--accent);
      background: rgba(0, 255, 170, 0.06);
    }
    .table-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.35rem;
    }
    .table-name {
      font-weight: 600;
      font-size: 0.88rem;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .table-badge {
      font-size: 0.7rem;
      color: var(--accent);
      font-family: var(--font-code);
      background: rgba(0, 255, 170, 0.1);
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
    }
    .table-meta {
      font-size: 0.72rem;
      color: var(--text-muted);
      display: flex;
      gap: 0.6rem;
      margin-bottom: 0.4rem;
    }
    .column-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 0.3rem;
    }
    .chip {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      font-size: 0.68rem;
      color: var(--text-muted);
      padding: 0.1rem 0.35rem;
      border-radius: 4px;
      font-family: var(--font-code);
    }

    /* Main Workspace */
    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: var(--bg-base);
    }

    /* Editor Section */
    .editor-section {
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      min-height: 220px;
      max-height: 45vh;
    }
    .editor-toolbar {
      padding: 0.5rem 1rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }
    .snippets-bar {
      display: flex;
      gap: 0.4rem;
      overflow-x: auto;
    }
    .btn-snippet {
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text-muted);
      font-size: 0.72rem;
      padding: 0.25rem 0.55rem;
      border-radius: 4px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }
    .btn-snippet:hover {
      border-color: var(--primary);
      color: var(--primary);
    }
    .btn-run {
      background: linear-gradient(135deg, #00d2ff 0%, #0099ff 100%);
      border: none;
      color: #0b0f17;
      font-weight: 700;
      font-size: 0.85rem;
      padding: 0.45rem 1.15rem;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.45rem;
      box-shadow: 0 2px 10px var(--primary-glow);
      transition: all 0.2s;
    }
    .btn-run:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 16px rgba(0, 210, 255, 0.45);
    }
    .editor-area {
      flex: 1;
      position: relative;
    }
    #queryEditor {
      width: 100%;
      height: 100%;
      background: #0d121d;
      border: none;
      outline: none;
      color: #f1f5f9;
      font-family: var(--font-code);
      font-size: 0.95rem;
      line-height: 1.5;
      padding: 0.85rem 1rem;
      resize: none;
    }

    /* Stats Bar */
    .stats-bar {
      padding: 0.5rem 1rem;
      background: #0d131f;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
    }
    .stat-items {
      display: flex;
      align-items: center;
      gap: 1.25rem;
      font-family: var(--font-code);
    }
    .stat-item b {
      color: var(--primary);
    }
    .stat-item.highlight b {
      color: var(--accent);
    }

    /* Results Grid Section */
    .results-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }
    .results-toolbar {
      padding: 0.45rem 1rem;
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .results-count {
      font-size: 0.78rem;
      color: var(--text-muted);
    }
    .export-btns {
      display: flex;
      gap: 0.4rem;
    }
    .btn-sm {
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 0.72rem;
      padding: 0.25rem 0.6rem;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-sm:hover {
      border-color: var(--primary);
      color: var(--primary);
    }
    .table-container {
      flex: 1;
      overflow: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }
    thead {
      position: sticky;
      top: 0;
      background: #131a2b;
      z-index: 10;
    }
    th {
      padding: 0.6rem 0.85rem;
      font-weight: 700;
      color: var(--primary);
      border-bottom: 2px solid var(--border);
      white-space: nowrap;
      font-family: var(--font-code);
    }
    td {
      padding: 0.55rem 0.85rem;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      white-space: nowrap;
      color: var(--text);
    }
    tbody tr:hover {
      background: rgba(0, 210, 255, 0.04);
    }
    .null-val {
      color: #64748b;
      font-style: italic;
    }
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--text-muted);
      gap: 0.75rem;
    }
    .empty-icon {
      font-size: 2.5rem;
      opacity: 0.4;
    }
    .error-banner {
      background: rgba(255, 71, 87, 0.12);
      border: 1px solid var(--danger);
      color: #ff6b81;
      padding: 0.85rem 1.25rem;
      margin: 1rem;
      border-radius: 8px;
      font-family: var(--font-code);
      font-size: 0.85rem;
    }
  </style>
</head>
<body>

  <!-- Top Navbar -->
  <header>
    <a href="#" class="brand">
      <span class="brand-icon">🏹</span>
      <span class="brand-title">MERGEN STUDIO</span>
      <span class="brand-badge" id="versionBadge">v0.5.9</span>
    </a>
    <div class="nav-actions">
      <div class="server-status">
        <div class="status-dot"></div>
        <span id="serverHost">http://localhost:8765</span>
      </div>
      <button class="btn-icon" onclick="openHealthModal()" title="System Diagnostics">💻 Hardware & Diagnostics</button>
    </div>
  </header>

  <!-- App Layout -->
  <div class="app-layout">

    <!-- Sidebar: Local .mgdb Tables -->
    <aside>
      <div class="sidebar-header">
        <span class="sidebar-title">Tables (.mgdb)</span>
        <button class="btn-icon" onclick="fetchTables()" title="Reload Tables">🔄</button>
      </div>
      <div class="search-box">
        <input type="text" id="tableSearch" placeholder="Filter tables..." oninput="filterTables()">
      </div>
      <div class="table-list" id="tableList">
        <div class="empty-state" style="padding: 2rem 0;">
          <span>Scanning directory...</span>
        </div>
      </div>
    </aside>

    <!-- Main Workspace -->
    <main>
      <!-- Query Editor Section -->
      <section class="editor-section">
        <div class="editor-toolbar">
          <div class="snippets-bar">
            <span style="font-size: 0.72rem; color: var(--text-muted); margin-right: 0.2rem; align-self: center;">Snippets:</span>
            <button class="btn-snippet" onclick="insertSnippet('SELECT * FROM \'{table}\' LIMIT 20;')">SELECT 20</button>
            <button class="btn-snippet" onclick="insertSnippet('SELECT {col1}, COUNT(*), AVG({col2}) FROM \'{table}\' GROUP BY {col1} HAVING COUNT(*) >= 1;')">GROUP BY + HAVING</button>
            <button class="btn-snippet" onclick="insertSnippet('SELECT * FROM \'{table}\' WHERE {col1} LIKE \'%value%\';')">Bloom / Substring Filter</button>
            <button class="btn-snippet" onclick="insertSnippet('SELECT a.*, b.* FROM \'{table}\' a INNER JOIN \'other.mgdb\' b ON a.id = b.id LIMIT 20;')">Hash JOIN</button>
          </div>
          <button class="btn-run" onclick="runQuery()" id="runBtn">
            <span>▶</span> Run (Ctrl+Enter)
          </button>
        </div>
        <div class="editor-area">
          <textarea id="queryEditor" spellcheck="false" placeholder="Write standard SQL or MergenQL query here...&#10;e.g. SELECT * FROM 'data.mgdb' LIMIT 10;"></textarea>
        </div>
      </section>

      <!-- Stats Bar -->
      <div class="stats-bar" id="statsBar">
        <div class="stat-items">
          <div class="stat-item highlight">Time: <b id="statTime">0.00 ms</b></div>
          <div class="stat-item">Rows: <b id="statRows">0</b></div>
          <div class="stat-item">Blocks Scanned: <b id="statScanned">0</b></div>
          <div class="stat-item">Blocks Skipped: <b id="statSkipped">0</b> (Zero I/O)</div>
          <div class="stat-item">Bytes Read: <b id="statBytes">0 KB</b></div>
        </div>
        <div id="statStatus">Ready</div>
      </div>

      <!-- Results Section -->
      <section class="results-section">
        <div class="results-toolbar">
          <span class="results-count" id="resultMeta">No query executed yet.</span>
          <div class="export-btns">
            <button class="btn-sm" onclick="exportResults('csv')">⬇ Export CSV</button>
            <button class="btn-sm" onclick="exportResults('json')">⬇ Export JSON</button>
          </div>
        </div>
        <div class="table-container" id="resultsContainer">
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <p>Write a query or select a table from the sidebar to inspect data</p>
          </div>
        </div>
      </section>
    </main>

  </div>

  <script>
    let currentTables = [];
    let selectedTable = null;
    let lastQueryResult = null;

    // Initialize
    window.addEventListener('DOMContentLoaded', () => {
      fetchStatus();
      fetchTables();

      // Keyboard shortcut Ctrl+Enter / Cmd+Enter
      document.getElementById('queryEditor').addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          e.preventDefault();
          runQuery();
        }
      });
    });

    async function fetchStatus() {
      try {
        const res = await fetch('/status');
        const data = await res.json();
        if (data.status === 'healthy') {
          document.getElementById('serverHost').textContent = `Online • ${data.tables_count} Tables (${formatBytes(data.total_disk_bytes)})`;
        }
      } catch (e) {
        document.getElementById('serverHost').textContent = 'Server Online';
      }
    }

    async function fetchTables() {
      const container = document.getElementById('tableList');
      try {
        const res = await fetch('/tables');
        const data = await res.json();
        currentTables = data.tables || [];
        renderTables(currentTables);

        // Auto select first table if none selected
        if (!selectedTable && currentTables.length > 0) {
          selectTable(currentTables[0].table);
        }
      } catch (err) {
        container.innerHTML = `<div class="error-banner">Failed to list tables: ${err.message}</div>`;
      }
    }

    function renderTables(tables) {
      const container = document.getElementById('tableList');
      if (tables.length === 0) {
        container.innerHTML = `<div class="empty-state" style="padding: 2rem 0;"><span>No .mgdb files in this directory.</span></div>`;
        return;
      }

      container.innerHTML = tables.map(t => {
        const isActive = selectedTable === t.table;
        const chips = (t.columns || []).slice(0, 5).map(c => `<span class="chip">${c}</span>`).join('');
        const extraCount = (t.columns || []).length > 5 ? `<span class="chip">+${t.columns.length - 5}</span>` : '';
        return `
          <div class="table-card ${isActive ? 'active' : ''}" onclick="selectTable('${t.table}')">
            <div class="table-card-header">
              <span class="table-name">📄 ${t.table}</span>
              <span class="table-badge">${Number(t.rows).toLocaleString()} rows</span>
            </div>
            <div class="table-meta">
              <span>💾 ${formatBytes(t.bytes)}</span>
              <span>🧱 ${t.blocks} blocks</span>
            </div>
            <div class="column-chips">${chips}${extraCount}</div>
          </div>
        `;
      }).join('');
    }

    function filterTables() {
      const q = document.getElementById('tableSearch').value.toLowerCase();
      const filtered = currentTables.filter(t => t.table.toLowerCase().includes(q) || (t.columns || []).some(c => c.toLowerCase().includes(q)));
      renderTables(filtered);
    }

    function selectTable(tableName) {
      selectedTable = tableName;
      renderTables(currentTables);
      const editor = document.getElementById('queryEditor');
      editor.value = `SELECT * FROM '${tableName}' LIMIT 50;`;
      runQuery();
    }

    function insertSnippet(snippet) {
      const editor = document.getElementById('queryEditor');
      const tbl = selectedTable || (currentTables.length > 0 ? currentTables[0].table : 'table.mgdb');
      const activeObj = currentTables.find(t => t.table === tbl);
      const col1 = activeObj && activeObj.columns && activeObj.columns.length > 0 ? activeObj.columns[0] : 'id';
      const col2 = activeObj && activeObj.columns && activeObj.columns.length > 1 ? activeObj.columns[1] : col1;

      let code = snippet.replace(/{table}/g, tbl).replace(/{col1}/g, col1).replace(/{col2}/g, col2);
      editor.value = code;
      editor.focus();
    }

    async function runQuery() {
      const editor = document.getElementById('queryEditor');
      const query = editor.value.trim();
      if (!query) return;

      const runBtn = document.getElementById('runBtn');
      const statStatus = document.getElementById('statStatus');
      const container = document.getElementById('resultsContainer');
      
      runBtn.disabled = true;
      runBtn.style.opacity = '0.6';
      statStatus.textContent = 'Executing query...';

      try {
        const t0 = performance.now();
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });
        const elapsed = (performance.now() - t0).toFixed(2);
        const data = await res.json();

        runBtn.disabled = false;
        runBtn.style.opacity = '1';

        if (!data.success) {
          container.innerHTML = `<div class="error-banner"><b>Execution Error:</b><br>${data.error}</div>`;
          statStatus.textContent = 'Error';
          return;
        }

        lastQueryResult = data;
        const stats = data.stats || {};
        document.getElementById('statTime').textContent = `${stats.execution_time_ms || elapsed} ms`;
        document.getElementById('statRows').textContent = (data.rows ? data.rows.length : 0).toLocaleString();
        document.getElementById('statScanned').textContent = (stats.blocks_scanned || 0).toLocaleString();
        document.getElementById('statSkipped').textContent = (stats.blocks_skipped || 0).toLocaleString();
        document.getElementById('statBytes').textContent = formatBytes(stats.bytes_read || 0);
        statStatus.textContent = 'Execution finished';

        renderResultTable(data.columns, data.rows);
      } catch (err) {
        runBtn.disabled = false;
        runBtn.style.opacity = '1';
        container.innerHTML = `<div class="error-banner"><b>Network or Server Error:</b><br>${err.message}</div>`;
        statStatus.textContent = 'Network Error';
      }
    }

    function renderResultTable(columns, rows) {
      const container = document.getElementById('resultsContainer');
      const meta = document.getElementById('resultMeta');

      if (!columns || columns.length === 0 || !rows || rows.length === 0) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><p>Query executed successfully, returned 0 rows.</p></div>`;
        meta.textContent = '0 rows returned';
        return;
      }

      meta.textContent = `${rows.length.toLocaleString()} rows returned • ${columns.length} columns`;

      const theadHtml = columns.map(col => `<th>${escapeHtml(col)}</th>`).join('');
      const tbodyHtml = rows.map(row => {
        const cells = row.map(val => {
          if (val === null || val === undefined) {
            return `<td><span class="null-val">NULL</span></td>`;
          }
          return `<td>${escapeHtml(String(val))}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
      }).join('');

      container.innerHTML = `
        <table>
          <thead><tr>${theadHtml}</tr></thead>
          <tbody>${tbodyHtml}</tbody>
        </table>
      `;
    }

    function exportResults(format) {
      if (!lastQueryResult || !lastQueryResult.rows || lastQueryResult.rows.length === 0) {
        alert('No query results available to export!');
        return;
      }
      const { columns, rows } = lastQueryResult;
      let content = '';
      let filename = `mergen_export_${Date.now()}.${format}`;

      if (format === 'csv') {
        const header = columns.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',');
        const body = rows.map(r => r.map(v => v === null ? '' : `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
        content = header + '\n' + body;
      } else {
        const objs = rows.map(r => {
          const o = {};
          columns.forEach((c, i) => o[c] = r[i]);
          return o;
        });
        content = JSON.stringify(objs, null, 2);
      }

      const blob = new Blob([content], { type: format === 'csv' ? 'text/csv' : 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    function openHealthModal() {
      const win = window.open('/status', '_blank');
    }

    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function escapeHtml(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
  </script>
</body>
</html>
"""
