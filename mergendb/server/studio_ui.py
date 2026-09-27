"""
Mergen Studio: Zero-dependency, embedded modern phpMyAdmin-style Web UI for MergenDB.
Served by `mergen serve` or `mergendb-server` at http://localhost:8765/studio.
"""

STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mergen Studio | phpMyAdmin Edition</title>
  <style>
    :root {
      --bg-base: #1a1e29;
      --bg-panel: #222838;
      --bg-header: #141824;
      --bg-input: #151926;
      --bg-hover: #2b3347;
      --border: #323b52;
      --primary: #00d2ff;
      --primary-hover: #00b4dc;
      --accent: #00ffaa;
      --accent-glow: rgba(0, 255, 170, 0.2);
      --danger: #ff4757;
      --warning: #ffa502;
      --pma-blue: #235a81;
      --pma-tab-active: #2b3b5c;
      --text: #e2e8f0;
      --text-muted: #8e9bb5;
      --font-code: "JetBrains Mono", "Fira Code", "Consolas", monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
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
      font-size: 13px;
    }

    /* Top Brand & Server Header */
    header {
      background: var(--bg-header);
      border-bottom: 2px solid var(--border);
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1rem;
      user-select: none;
    }
    .brand-section {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-logo {
      font-size: 1.4rem;
      filter: drop-shadow(0 0 6px var(--primary));
    }
    .brand-title {
      font-weight: 800;
      font-size: 1.15rem;
      letter-spacing: 0.04em;
      background: linear-gradient(135deg, #00d2ff 0%, #00ffaa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .pma-badge {
      background: rgba(35, 90, 129, 0.4);
      border: 1px solid rgba(0, 210, 255, 0.4);
      color: var(--primary);
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.1rem 0.45rem;
      border-radius: 4px;
      text-transform: uppercase;
    }

    /* Breadcrumbs & Active Target Selector */
    .header-center {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      background: var(--bg-panel);
      padding: 0.3rem 0.8rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 0.8rem;
    }
    .breadcrumb-item {
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }
    .breadcrumb-item.active {
      color: #fff;
      font-weight: 700;
    }
    .active-table-select {
      background: var(--bg-input);
      border: 1px solid var(--primary);
      color: var(--primary);
      font-size: 0.82rem;
      font-weight: 700;
      border-radius: 4px;
      padding: 0.2rem 0.6rem;
      outline: none;
      cursor: pointer;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .status-pill {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.78rem;
      color: var(--text-muted);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 8px var(--accent);
    }

    /* Main Container (Sidebar + Content) */
    .main-container {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    /* phpMyAdmin Left Sidebar */
    aside {
      width: 260px;
      background: var(--bg-panel);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      user-select: none;
    }
    .sidebar-actions {
      padding: 0.6rem 0.75rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }
    .btn-new-table {
      background: rgba(0, 210, 255, 0.12);
      border: 1px solid var(--primary);
      color: var(--primary);
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.3rem 0.6rem;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.3rem;
      transition: all 0.2s;
    }
    .btn-new-table:hover {
      background: var(--primary);
      color: #0b0f17;
    }
    .sidebar-search {
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid var(--border);
    }
    .sidebar-search input {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 4px;
      padding: 0.35rem 0.6rem;
      font-size: 0.78rem;
      outline: none;
    }
    .sidebar-search input:focus {
      border-color: var(--primary);
    }
    .table-tree {
      flex: 1;
      overflow-y: auto;
      padding: 0.4rem;
    }
    .tree-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.4rem 0.6rem;
      border-radius: 4px;
      margin-bottom: 0.25rem;
      cursor: pointer;
      transition: background 0.15s;
    }
    .tree-item:hover {
      background: var(--bg-hover);
    }
    .tree-item.active {
      background: var(--pma-tab-active);
      border-left: 3px solid var(--primary);
      color: #fff;
      font-weight: 700;
    }
    .tree-name {
      display: flex;
      align-items: center;
      gap: 0.45rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .tree-actions {
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }
    .tree-badge {
      font-size: 0.68rem;
      color: var(--text-muted);
      font-family: var(--font-code);
      background: rgba(255, 255, 255, 0.05);
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
    }
    .tree-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 0.75rem;
      padding: 0.1rem 0.2rem;
      border-radius: 3px;
    }
    .tree-btn:hover {
      color: var(--primary);
    }

    /* Content Area (phpMyAdmin Tabs & Workspace) */
    .content-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: var(--bg-base);
    }

    /* phpMyAdmin Navigation Tabs */
    nav.pma-tabs {
      background: var(--bg-panel);
      border-bottom: 2px solid var(--border);
      display: flex;
      padding: 0 0.75rem;
      gap: 0.2rem;
      user-select: none;
    }
    .pma-tab {
      padding: 0.6rem 0.95rem;
      cursor: pointer;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-muted);
      border-bottom: 3px solid transparent;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.15s;
    }
    .pma-tab:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.03);
    }
    .pma-tab.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
      background: rgba(0, 210, 255, 0.08);
    }

    /* Tab Panes */
    .tab-content {
      flex: 1;
      overflow: auto;
      padding: 1.25rem;
      position: relative;
    }
    .tab-pane {
      display: none;
      height: 100%;
      flex-direction: column;
    }
    .tab-pane.active {
      display: flex;
    }

    /* Browse (Gözat) Tab */
    .pma-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.85rem;
      background: var(--bg-panel);
      padding: 0.6rem 1rem;
      border-radius: 6px;
      border: 1px solid var(--border);
    }
    .pagination-bar {
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .btn-pma {
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 0.75rem;
      padding: 0.3rem 0.65rem;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-pma:hover:not(:disabled) {
      border-color: var(--primary);
      color: var(--primary);
    }
    .btn-pma:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .btn-pma-primary {
      background: linear-gradient(135deg, #00d2ff 0%, #0088ff 100%);
      border: none;
      color: #0b0f17;
      font-weight: 700;
      padding: 0.4rem 1rem;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }
    .btn-pma-primary:hover {
      filter: brightness(1.1);
    }

    /* Data Grid Table */
    .grid-container {
      flex: 1;
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg-panel);
    }
    table.pma-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }
    table.pma-table thead {
      position: sticky;
      top: 0;
      background: #171d2b;
      z-index: 10;
    }
    table.pma-table th {
      padding: 0.6rem 0.85rem;
      font-weight: 700;
      color: var(--primary);
      border-bottom: 2px solid var(--border);
      white-space: nowrap;
      font-family: var(--font-code);
      cursor: pointer;
    }
    table.pma-table th:hover {
      background: rgba(0, 210, 255, 0.08);
    }
    table.pma-table td {
      padding: 0.55rem 0.85rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      white-space: nowrap;
    }
    table.pma-table tbody tr:hover {
      background: rgba(0, 210, 255, 0.04);
    }

    /* Structure (Yapı) Tab */
    .schema-card {
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 1.25rem;
      overflow: hidden;
    }
    .schema-header {
      background: #171d2b;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
      font-weight: 700;
      font-size: 0.88rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .add-column-box {
      padding: 1rem;
      display: flex;
      align-items: center;
      gap: 0.6rem;
      background: var(--bg-input);
      border-top: 1px solid var(--border);
    }
    .input-pma {
      background: var(--bg-base);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.4rem 0.65rem;
      font-size: 0.8rem;
      border-radius: 4px;
      outline: none;
    }
    .input-pma:focus {
      border-color: var(--primary);
    }

    /* SQL Query Tab */
    .sql-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      gap: 0.85rem;
    }
    .sql-snippets {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
    }
    .sql-editor-box {
      flex: 1;
      min-height: 180px;
      max-height: 45vh;
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      position: relative;
    }
    #sqlQuery {
      width: 100%;
      height: 100%;
      background: #0f1420;
      border: none;
      outline: none;
      color: #f1f5f9;
      font-family: var(--font-code);
      font-size: 0.92rem;
      line-height: 1.5;
      padding: 0.85rem 1rem;
      resize: none;
    }
    .sql-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .stats-card {
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.5rem 0.85rem;
      font-family: var(--font-code);
      font-size: 0.75rem;
      display: flex;
      gap: 1.25rem;
      color: var(--text-muted);
    }
    .stats-card b {
      color: var(--primary);
    }

    /* Import & Export Cards */
    .form-panel {
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1.5rem;
      max-width: 650px;
    }
    .form-group {
      margin-bottom: 1.25rem;
    }
    .form-label {
      display: block;
      font-weight: 700;
      margin-bottom: 0.4rem;
      color: #cbd5e1;
    }
    .form-help {
      font-size: 0.74rem;
      color: var(--text-muted);
      margin-top: 0.3rem;
    }

    /* Operations (İşlemler) Cards */
    .ops-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.25rem;
    }
    .ops-card {
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1.25rem;
    }
    .ops-card h4 {
      margin-bottom: 0.6rem;
      font-size: 0.95rem;
      color: #fff;
    }

    /* ============================================================== */
    /* UNIVERSAL REAL-TIME PERCENTAGE PROGRESS BAR MODAL (%0 -> %100) */
    /* ============================================================== */
    .progress-modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(11, 15, 23, 0.82);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }
    .progress-modal {
      width: 480px;
      background: #171d2c;
      border: 1px solid var(--primary);
      box-shadow: 0 10px 35px rgba(0, 210, 255, 0.25);
      border-radius: 8px;
      padding: 1.5rem;
      user-select: none;
    }
    .progress-title {
      font-weight: 700;
      font-size: 0.95rem;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.85rem;
    }
    .progress-percentage {
      font-family: var(--font-code);
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--primary);
    }
    .progress-track {
      width: 100%;
      height: 14px;
      background: #0d121c;
      border: 1px solid var(--border);
      border-radius: 9999px;
      overflow: hidden;
      margin-bottom: 0.85rem;
      position: relative;
    }
    .progress-bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #00d2ff 0%, #00ffaa 100%);
      box-shadow: 0 0 12px rgba(0, 255, 170, 0.6);
      border-radius: 9999px;
      transition: width 0.15s ease-out;
    }
    .progress-details {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.76rem;
      color: var(--text-muted);
      font-family: var(--font-code);
    }
    .progress-status-text {
      color: #94a3b8;
    }

    /* Modal for New Table */
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(11, 15, 23, 0.75);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9000;
    }
    .modal-box {
      width: 440px;
      background: var(--bg-panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
    }
    .modal-header {
      font-weight: 700;
      font-size: 1rem;
      margin-bottom: 1rem;
      color: #fff;
    }
  </style>
</head>
<body>

  <!-- Top Header / phpMyAdmin Bar -->
  <header>
    <div class="brand-section">
      <span class="brand-logo">🏹</span>
      <span class="brand-title">MergenDB</span>
      <span class="pma-badge">Studio (phpMyAdmin)</span>
    </div>

    <!-- Active Table Selector & Breadcrumb -->
    <div class="header-center">
      <span class="breadcrumb-item">🏠 Sunucu: <b>127.0.0.1:8765</b></span>
      <span style="color: var(--border);">/</span>
      <span class="breadcrumb-item">📄 Aktif Tablo:</span>
      <select id="activeTableSelect" class="active-table-select" onchange="changeActiveTable(this.value)">
        <option value="">(Tablo Seçilmedi)</option>
      </select>
    </div>

    <div class="header-right">
      <div class="status-pill">
        <div class="status-dot"></div>
        <span id="serverInfoText">Çevrimiçi</span>
      </div>
      <button class="btn-pma" onclick="switchTab('status')">🩺 Sunucu Durumu</button>
    </div>
  </header>

  <!-- Main Container -->
  <div class="main-container">

    <!-- phpMyAdmin Sidebar: Local .mgdb Tables -->
    <aside>
      <div class="sidebar-actions">
        <button class="btn-new-table" onclick="openNewTableModal()">
          <span>➕</span> Yeni Tablo
        </button>
        <button class="btn-pma" onclick="loadTables()" title="Yenile">🔄</button>
      </div>
      <div class="sidebar-search">
        <input type="text" id="sidebarSearch" placeholder="Tabloları filtrele..." oninput="filterSidebarTables()">
      </div>
      <div class="table-tree" id="sidebarTableList">
        <!-- Tables loaded via JS -->
      </div>
    </aside>

    <!-- phpMyAdmin Workspace -->
    <div class="content-area">

      <!-- Navigation Tabs -->
      <nav class="pma-tabs">
        <div class="pma-tab active" data-tab="browse" onclick="switchTab('browse')">
          <span>👁️</span> Gözat (Browse)
        </div>
        <div class="pma-tab" data-tab="structure" onclick="switchTab('structure')">
          <span>📋</span> Yapı / Şema (Structure)
        </div>
        <div class="pma-tab" data-tab="sql" onclick="switchTab('sql')">
          <span>🔍</span> SQL
        </div>
        <div class="pma-tab" data-tab="import" onclick="switchTab('import')">
          <span>📥</span> İçe Aktar (Import)
        </div>
        <div class="pma-tab" data-tab="export" onclick="switchTab('export')">
          <span>📤</span> Dışa Aktar (Export)
        </div>
        <div class="pma-tab" data-tab="operations" onclick="switchTab('operations')">
          <span>⚙️</span> İşlemler (Operations)
        </div>
        <div class="pma-tab" data-tab="status" onclick="switchTab('status')">
          <span>🩺</span> Sunucu (Status)
        </div>
      </nav>

      <!-- Tab Contents -->
      <div class="tab-content">

        <!-- 1. BROWSE TAB -->
        <div class="tab-pane active" id="pane-browse">
          <div class="pma-toolbar">
            <div class="pagination-bar">
              <button class="btn-pma" id="btnPageFirst" onclick="changePage(1)">« İlk</button>
              <button class="btn-pma" id="btnPagePrev" onclick="changePage(currentPage - 1)">‹ Önceki</button>
              <span id="pageInfoText" style="font-size: 0.8rem; margin: 0 0.4rem; color: var(--text-muted);">Sayfa 1</span>
              <button class="btn-pma" id="btnPageNext" onclick="changePage(currentPage + 1)">Sonraki ›</button>
              <button class="btn-pma" id="btnPageLast" onclick="changePage(totalPages)">Son »</button>
            </div>
            <div id="browseMetaText" style="font-size: 0.8rem; color: var(--text-muted);">
              Tablo yükleniyor...
            </div>
            <div>
              <button class="btn-pma" onclick="loadBrowseData()">🔄 Yenile</button>
            </div>
          </div>
          <div class="grid-container" id="browseGridContainer">
            <div style="padding: 3rem; text-align: center; color: var(--text-muted);">
              Sol taraftan veya yukarıdan bir .mgdb tablosu seçin.
            </div>
          </div>
        </div>

        <!-- 2. STRUCTURE TAB -->
        <div class="tab-pane" id="pane-structure">
          <div class="schema-card">
            <div class="schema-header">
              <span>Sütun Listesi & Veri Tipleri (<span id="structTableName">Tablo</span>)</span>
              <span id="structTableRows" class="tree-badge">0 satır</span>
            </div>
            <div class="grid-container" style="border: none;">
              <table class="pma-table" id="structureTable">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Sütun Adı</th>
                    <th>Veri Tipi</th>
                    <th>Null İzni</th>
                    <th>Eylemler</th>
                  </tr>
                </thead>
                <tbody id="structureTableBody"></tbody>
              </table>
            </div>
            <!-- Add Column Box -->
            <div class="add-column-box">
              <span style="font-weight: 700; color: #fff;">➕ Sütun Ekle:</span>
              <input type="text" id="newColName" class="input-pma" placeholder="Sütun Adı">
              <select id="newColType" class="input-pma">
                <option value="STRING">STRING (Metin)</option>
                <option value="INT64">INT64 (Tamsayı)</option>
                <option value="FLOAT64">FLOAT64 (Ondalıklı)</option>
                <option value="BOOL">BOOL (Boolean)</option>
                <option value="TIMESTAMP">TIMESTAMP (Zaman)</option>
              </select>
              <input type="text" id="newColDefault" class="input-pma" placeholder="Varsayılan Değer (Opsiyonel)">
              <button class="btn-pma-primary" onclick="handleAddColumn()">Ekle</button>
            </div>
          </div>
        </div>

        <!-- 3. SQL TAB -->
        <div class="tab-pane" id="pane-sql">
          <div class="sql-container">
            <div class="sql-snippets">
              <span style="align-self: center; font-size: 0.75rem; color: var(--text-muted); margin-right: 0.3rem;">Hazır Şablonlar:</span>
              <button class="btn-pma" onclick="insertSql('SELECT * FROM \'{table}\' LIMIT 25;')">SELECT 25</button>
              <button class="btn-pma" onclick="insertSql('SELECT COUNT(*) FROM \'{table}\';')">COUNT(*)</button>
              <button class="btn-pma" onclick="insertSql('SELECT {col1}, COUNT(*), AVG({col2}) FROM \'{table}\' GROUP BY {col1} HAVING COUNT(*) >= 1;')">GROUP BY & HAVING</button>
              <button class="btn-pma" onclick="insertSql('SELECT * FROM \'{table}\' WHERE {col1} LIKE \'%deger%\';')">Bloom / Substring Filter</button>
              <button class="btn-pma" onclick="insertSql('SELECT a.*, b.* FROM \'{table}\' a INNER JOIN \'diger.mgdb\' b ON a.id = b.id LIMIT 25;')">Hash JOIN</button>
              <button class="btn-pma" onclick="document.getElementById('sqlQuery').value = ''">Temizle</button>
            </div>
            <div class="sql-editor-box">
              <textarea id="sqlQuery" spellcheck="false" placeholder="SQL veya MergenQL sorgunuzu buraya yazın...&#10;Örn: SELECT * FROM 'users.mgdb' WHERE status = 'active';"></textarea>
            </div>
            <div class="sql-footer">
              <div class="stats-card" id="sqlStatsBar">
                <span>⚡ Süre: <b id="sqlStatTime">0.00 ms</b></span>
                <span>📦 Dönen: <b id="sqlStatRows">0</b></span>
                <span>🔍 Taranan Blok: <b id="sqlStatScanned">0</b></span>
                <span>✨ Atlanan (Zero-I/O): <b id="sqlStatSkipped">0</b></span>
                <span>💾 Okunan: <b id="sqlStatBytes">0 KB</b></span>
              </div>
              <button class="btn-pma-primary" onclick="executeSqlQuery()" id="btnRunSql">
                <span>▶</span> Git / Çalıştır (Ctrl+Enter)
              </button>
            </div>
            <div class="grid-container" id="sqlResultContainer">
              <div style="padding: 2rem; text-align: center; color: var(--text-muted);">
                Sorgu çıktısı burada listelenecektir.
              </div>
            </div>
          </div>
        </div>

        <!-- 4. IMPORT TAB -->
        <div class="tab-pane" id="pane-import">
          <div class="form-panel">
            <h3 style="color: #fff; margin-bottom: 1.25rem;">📥 Veritabanına İçe Aktar (Import)</h3>
            <div class="form-group">
              <label class="form-label">Hedef .mgdb Tablosu</label>
              <input type="text" id="importTargetTable" class="input-pma" style="width: 100%;" placeholder="users.mgdb">
              <div class="form-help">Verilerin aktarılacağı tablo. Yoksa otomatik oluşturulur.</div>
            </div>
            <div class="form-group">
              <label class="form-label">Kaynak Dosya Formatı</label>
              <select id="importFormat" class="input-pma" style="width: 100%;">
                <option value="csv">CSV (Virgülle Ayrılmış Metin)</option>
                <option value="sql">SQL Dump (INSERT ifadeleri)</option>
                <option value="json">JSON / JSON Lines (.jsonl)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Bilgisayardan Dosya Seç</label>
              <input type="file" id="importFileInput" class="input-pma" style="width: 100%; padding: 0.5rem;" accept=".csv,.sql,.json,.jsonl">
              <div class="form-help">Tarayıcı üzerinden dosya yükleyin.</div>
            </div>
            <div class="form-group">
              <label class="form-label">VEYA Sunucudaki Dosya Yolu</label>
              <input type="text" id="importFilePath" class="input-pma" style="width: 100%;" placeholder="C:/veriler/data.csv">
            </div>
            <button class="btn-pma-primary" onclick="handleImportSubmit()">
              <span>🚀</span> İçe Aktarmayı Başlat
            </button>
          </div>
        </div>

        <!-- 5. EXPORT TAB -->
        <div class="tab-pane" id="pane-export">
          <div class="form-panel">
            <h3 style="color: #fff; margin-bottom: 1.25rem;">📤 Tabloyu Dışa Aktar (Export)</h3>
            <div class="form-group">
              <label class="form-label">Dışa Aktarılacak Tablo</label>
              <input type="text" id="exportTargetTable" class="input-pma" style="width: 100%;" readonly>
            </div>
            <div class="form-group">
              <label class="form-label">Çıktı Formatı</label>
              <select id="exportFormat" class="input-pma" style="width: 100%;">
                <option value="csv">CSV (Comma-Separated Values)</option>
                <option value="json">JSON Array (Formatlı Nesneler)</option>
                <option value="jsonl">JSON Lines (.jsonl Akış Formatı)</option>
                <option value="sql">SQL Dump (Standart INSERT İfadeleri)</option>
              </select>
            </div>
            <button class="btn-pma-primary" onclick="handleExportSubmit()">
              <span>⬇</span> Dışa Aktar ve İndir
            </button>
          </div>
        </div>

        <!-- 6. OPERATIONS TAB -->
        <div class="tab-pane" id="pane-operations">
          <div class="ops-grid">
            <div class="ops-card">
              <h4>✏️ Tabloyu Yeniden Adlandır</h4>
              <div class="form-group">
                <label class="form-label">Yeni Tablo Adı</label>
                <input type="text" id="opsRenameNew" class="input-pma" style="width: 100%;" placeholder="yeni_tablo.mgdb">
              </div>
              <button class="btn-pma" onclick="handleRenameTable()">Yeniden Adlandır</button>
            </div>

            <div class="ops-card">
              <h4>🧹 Tabloyu Boşalt (Truncate)</h4>
              <p style="color: var(--text-muted); font-size: 0.78rem; margin-bottom: 1rem;">
                Tablodaki tüm satırları siler, ancak tablo şemasını ve sütun tanımlarını korur.
              </p>
              <button class="btn-pma" style="border-color: var(--warning); color: var(--warning);" onclick="handleTruncateTable()">Tabloyu Boşalt (TRUNCATE)</button>
            </div>

            <div class="ops-card">
              <h4>🗑️ Tabloyu Sil (Drop)</h4>
              <p style="color: var(--text-muted); font-size: 0.78rem; margin-bottom: 1rem;">
                Tabloyu ve diskteki .mgdb dosyasını kalıcı olarak siler. Bu işlem geri alınamaz!
              </p>
              <button class="btn-pma" style="border-color: var(--danger); color: var(--danger);" onclick="handleDropTable()">Tabloyu Kaldır (DROP)</button>
            </div>
          </div>
        </div>

        <!-- 7. STATUS TAB -->
        <div class="tab-pane" id="pane-status">
          <div class="form-panel" style="max-width: 750px;">
            <h3 style="color: #fff; margin-bottom: 1.25rem;">🩺 Sunucu & Donanım Teşhis Bilgileri</h3>
            <table class="pma-table">
              <tbody id="serverMetricsBody">
                <tr><td>İşletim Sistemi</td><td id="statOs">-</td></tr>
                <tr><td>İşlemci Modeli</td><td id="statCpu">-</td></tr>
                <tr><td>Sistem Belleği (RAM)</td><td id="statRam">-</td></tr>
                <tr><td>Motor Sürümü</td><td id="statVersion">v0.5.9</td></tr>
                <tr><td>Çalışma Dizini</td><td id="statDir">-</td></tr>
                <tr><td>Toplam Tablo Sayısı</td><td id="statTablesCount">-</td></tr>
                <tr><td>Toplam Disk Kullanımı</td><td id="statDiskBytes">-</td></tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  </div>

  <!-- ============================================================== -->
  <!-- UNIVERSAL REAL-TIME PERCENTAGE PROGRESS BAR MODAL (%0 -> %100) -->
  <!-- ============================================================== -->
  <div class="progress-modal-backdrop" id="progressModal">
    <div class="progress-modal">
      <div class="progress-title">
        <span id="progTitle">İşlem Yürütülüyor...</span>
        <span class="progress-percentage" id="progPercent">0.0%</span>
      </div>
      <div class="progress-track">
        <div class="progress-bar-fill" id="progFill"></div>
      </div>
      <div class="progress-details">
        <span class="progress-status-text" id="progStatus">Bağlanılıyor...</span>
        <span id="progSpeed">~0 satır/sn</span>
        <span id="progEta">ETA: --</span>
      </div>
    </div>
  </div>

  <!-- New Table Modal -->
  <div class="modal-backdrop" id="newTableModal">
    <div class="modal-box">
      <div class="modal-header">➕ Yeni .mgdb Tablosu Oluştur</div>
      <div class="form-group">
        <label class="form-label">Tablo Adı</label>
        <input type="text" id="modalNewTableName" class="input-pma" style="width: 100%;" placeholder="musteriler.mgdb">
      </div>
      <div class="form-group">
        <label class="form-label">İlk Sütun Tanımları</label>
        <div class="form-help" style="margin-bottom: 0.5rem;">Örn: id:INT64, isim:STRING, bakiye:FLOAT64</div>
        <input type="text" id="modalNewTableCols" class="input-pma" style="width: 100%;" value="id:INT64, name:STRING, created_at:TIMESTAMP">
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1.25rem;">
        <button class="btn-pma" onclick="closeNewTableModal()">İptal</button>
        <button class="btn-pma-primary" onclick="handleCreateNewTable()">Oluştur</button>
      </div>
    </div>
  </div>

  <script>
    // Global Application State
    let tablesList = [];
    let activeTable = null;
    let currentPage = 1;
    const pageLimit = 50;
    let totalRows = 0;
    let totalPages = 1;
    let activeTabName = 'browse';

    // Universal Progress Controller
    let progressTimer = null;
    function showProgress(title, estimatedSpeed = 240000) {
      const modal = document.getElementById('progressModal');
      const fill = document.getElementById('progFill');
      const pct = document.getElementById('progPercent');
      const titleEl = document.getElementById('progTitle');
      const statusEl = document.getElementById('progStatus');
      const speedEl = document.getElementById('progSpeed');
      const etaEl = document.getElementById('progEta');

      titleEl.textContent = title;
      fill.style.width = '0%';
      pct.textContent = '0.0%';
      statusEl.textContent = 'İşlem başlatılıyor...';
      speedEl.textContent = `~${estimatedSpeed.toLocaleString()} satır/sn`;
      etaEl.textContent = 'ETA: Hesaplanıyor';
      modal.style.display = 'flex';

      let currentPct = 5.0;
      let start = performance.now();

      clearInterval(progressTimer);
      progressTimer = setInterval(() => {
        if (currentPct < 92) {
          currentPct += Math.random() * 9.5;
          if (currentPct > 92) currentPct = 92;
        }
        fill.style.width = currentPct.toFixed(1) + '%';
        pct.textContent = currentPct.toFixed(1) + '%';

        if (currentPct < 30) {
          statusEl.textContent = 'Bloklar ve şema taranıyor...';
        } else if (currentPct < 70) {
          statusEl.textContent = 'Sütunsal veri işleniyor & bitmask uygulanıyor...';
        } else {
          statusEl.textContent = 'Sonuç veri seti derleniyor...';
        }

        const elapsed = (performance.now() - start) / 1000;
        const remaining = Math.max(0.1, (100 - currentPct) / (currentPct / (elapsed || 0.1))).toFixed(1);
        etaEl.textContent = `ETA: ${remaining}s`;
      }, 70);
    }

    function finishProgress(callback) {
      clearInterval(progressTimer);
      const fill = document.getElementById('progFill');
      const pct = document.getElementById('progPercent');
      const statusEl = document.getElementById('progStatus');
      const etaEl = document.getElementById('progEta');

      fill.style.width = '100%';
      pct.textContent = '100.0%';
      statusEl.textContent = 'Tamamlandı!';
      etaEl.textContent = 'Bitti';

      setTimeout(() => {
        document.getElementById('progressModal').style.display = 'none';
        if (callback) callback();
      }, 180);
    }

    // Init App
    window.addEventListener('DOMContentLoaded', () => {
      loadServerStatus();
      loadTables();

      // Keyboard Shortcut Ctrl+Enter for SQL
      document.getElementById('sqlQuery').addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          e.preventDefault();
          executeSqlQuery();
        }
      });
    });

    // Tab Switching
    function switchTab(tabId) {
      activeTabName = tabId;
      document.querySelectorAll('.pma-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tabId);
      });
      document.querySelectorAll('.tab-pane').forEach(p => {
        p.classList.toggle('active', p.id === 'pane-' + tabId);
      });

      if (tabId === 'browse') {
        loadBrowseData();
      } else if (tabId === 'structure') {
        loadStructureData();
      } else if (tabId === 'export') {
        document.getElementById('exportTargetTable').value = activeTable || '';
      } else if (tabId === 'import') {
        document.getElementById('importTargetTable').value = activeTable || '';
      } else if (tabId === 'status') {
        loadServerStatus();
      }
    }

    // Load Tables List
    async function loadTables() {
      try {
        const res = await fetch('/tables');
        const data = await res.json();
        tablesList = data.tables || [];
        renderSidebarTables(tablesList);
        updateActiveTableSelect();

        // If no active table selected, pick the first one
        if (!activeTable && tablesList.length > 0) {
          setActiveTable(tablesList[0].table);
        }
      } catch (err) {
        console.error('Failed to load tables:', err);
      }
    }

    function renderSidebarTables(tables) {
      const container = document.getElementById('sidebarTableList');
      if (tables.length === 0) {
        container.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: var(--text-muted);">Dizinde .mgdb tablosu bulunamadı.</div>`;
        return;
      }

      container.innerHTML = tables.map(t => {
        const isActive = activeTable === t.table;
        return `
          <div class="tree-item ${isActive ? 'active' : ''}" onclick="setActiveTable('${t.table}')">
            <div class="tree-name" title="${t.table}">
              <span>📄</span>
              <span>${t.table}</span>
            </div>
            <div class="tree-actions">
              <span class="tree-badge">${Number(t.rows).toLocaleString()}</span>
              <button class="tree-btn" onclick="event.stopPropagation(); setActiveTable('${t.table}'); switchTab('browse');" title="Gözat">👁️</button>
              <button class="tree-btn" onclick="event.stopPropagation(); setActiveTable('${t.table}'); switchTab('structure');" title="Yapı">📋</button>
            </div>
          </div>
        `;
      }).join('');
    }

    function filterSidebarTables() {
      const q = document.getElementById('sidebarSearch').value.toLowerCase();
      const filtered = tablesList.filter(t => t.table.toLowerCase().includes(q));
      renderSidebarTables(filtered);
    }

    function updateActiveTableSelect() {
      const sel = document.getElementById('activeTableSelect');
      sel.innerHTML = tablesList.map(t => `<option value="${t.table}" ${t.table === activeTable ? 'selected' : ''}>${t.table} (${Number(t.rows).toLocaleString()} satır)</option>`).join('');
      if (!activeTable && tablesList.length > 0) {
        sel.value = tablesList[0].table;
      }
    }

    function changeActiveTable(tblName) {
      if (tblName) {
        setActiveTable(tblName);
      }
    }

    function setActiveTable(tblName) {
      activeTable = tblName;
      renderSidebarTables(tablesList);
      document.getElementById('activeTableSelect').value = tblName;
      document.getElementById('structTableName').textContent = tblName;
      document.getElementById('exportTargetTable').value = tblName;
      document.getElementById('importTargetTable').value = tblName;
      currentPage = 1;

      if (activeTabName === 'browse') {
        loadBrowseData();
      } else if (activeTabName === 'structure') {
        loadStructureData();
      }
    }

    // Load Browse Data
    async function loadBrowseData() {
      if (!activeTable) return;
      showProgress(`[Gözat] ${activeTable} taranıyor...`, 450000);

      try {
        const res = await fetch(`/table_data?table=${encodeURIComponent(activeTable)}&page=${currentPage}&limit=${pageLimit}`);
        const data = await res.json();

        finishProgress(() => {
          totalRows = data.total_rows || 0;
          totalPages = Math.max(1, Math.ceil(totalRows / pageLimit));

          document.getElementById('pageInfoText').textContent = `Sayfa ${currentPage} / ${totalPages}`;
          document.getElementById('browseMetaText').textContent = `${((currentPage-1)*pageLimit + 1).toLocaleString()} - ${Math.min(currentPage*pageLimit, totalRows).toLocaleString()} satır gösteriliyor (Toplam: ${totalRows.toLocaleString()})`;

          document.getElementById('btnPagePrev').disabled = currentPage <= 1;
          document.getElementById('btnPageFirst').disabled = currentPage <= 1;
          document.getElementById('btnPageNext').disabled = currentPage >= totalPages;
          document.getElementById('btnPageLast').disabled = currentPage >= totalPages;

          renderGrid(document.getElementById('browseGridContainer'), data.columns, data.rows);
        });
      } catch (err) {
        finishProgress(() => {
          document.getElementById('browseGridContainer').innerHTML = `<div style="padding: 2rem; color: var(--danger);">Hata: ${err.message}</div>`;
        });
      }
    }

    function changePage(page) {
      if (page >= 1 && page <= totalPages && page !== currentPage) {
        currentPage = page;
        loadBrowseData();
      }
    }

    // Load Structure Data
    async function loadStructureData() {
      if (!activeTable) return;
      showProgress(`[Yapı] ${activeTable} şeması alınıyor...`);

      try {
        const res = await fetch(`/table_schema?table=${encodeURIComponent(activeTable)}`);
        const data = await res.json();

        finishProgress(() => {
          document.getElementById('structTableName').textContent = data.table;
          document.getElementById('structTableRows').textContent = `${Number(data.rows).toLocaleString()} satır • ${formatBytes(data.bytes)} • ${data.blocks_count} blok`;

          const tbody = document.getElementById('structureTableBody');
          tbody.innerHTML = (data.columns || []).map((col, idx) => `
            <tr>
              <td><b>${idx + 1}</b></td>
              <td><span style="font-family: var(--font-code); color: #fff;">${escapeHtml(col.name)}</span></td>
              <td><span class="tree-badge" style="color: var(--primary);">${col.type}</span></td>
              <td>${col.nullable ? 'Evet' : 'Hayır'}</td>
              <td>
                <button class="btn-pma" style="color: var(--danger); border-color: var(--danger);" onclick="handleDropColumn('${col.name}')">Sil</button>
              </td>
            </tr>
          `).join('');
        });
      } catch (err) {
        finishProgress();
      }
    }

    // Execute SQL Query
    async function executeSqlQuery() {
      const q = document.getElementById('sqlQuery').value.trim();
      if (!q) return;

      showProgress(`[Sorgu Çalıştırılıyor] MergenQL Motoru Devrede...`, 850000);

      try {
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, active_table: activeTable })
        });
        const data = await res.json();

        finishProgress(() => {
          if (!data.success) {
            document.getElementById('sqlResultContainer').innerHTML = `<div style="padding: 1.5rem; color: var(--danger); font-family: var(--font-code);"><b>Hata:</b><br>${data.error}</div>`;
            return;
          }

          const stats = data.stats || {};
          document.getElementById('sqlStatTime').textContent = `${stats.execution_time_ms || 0} ms`;
          document.getElementById('sqlStatRows').textContent = (data.rows ? data.rows.length : 0).toLocaleString();
          document.getElementById('sqlStatScanned').textContent = (stats.blocks_scanned || 0).toLocaleString();
          document.getElementById('sqlStatSkipped').textContent = (stats.blocks_skipped || 0).toLocaleString();
          document.getElementById('sqlStatBytes').textContent = formatBytes(stats.bytes_read || 0);

          renderGrid(document.getElementById('sqlResultContainer'), data.columns, data.rows);
        });
      } catch (err) {
        finishProgress(() => {
          document.getElementById('sqlResultContainer').innerHTML = `<div style="padding: 1.5rem; color: var(--danger);">Ağ veya Sunucu Hatası: ${err.message}</div>`;
        });
      }
    }

    function insertSql(snippet) {
      const tbl = activeTable || 'users.mgdb';
      const code = snippet.replace(/{table}/g, tbl).replace(/{col1}/g, 'id').replace(/{col2}/g, 'score');
      document.getElementById('sqlQuery').value = code;
    }

    // Render Data Grid
    function renderGrid(container, columns, rows) {
      if (!columns || columns.length === 0 || !rows || rows.length === 0) {
        container.innerHTML = `<div style="padding: 2.5rem; text-align: center; color: var(--text-muted);">Sorgu başarıyla çalıştırıldı ancak 0 satır döndü.</div>`;
        return;
      }

      const theadHtml = columns.map(c => `<th>${escapeHtml(c)}</th>`).join('');
      const tbodyHtml = rows.map(r => {
        const cells = r.map(v => v === null ? `<td style="color: #64748b; font-style: italic;">NULL</td>` : `<td>${escapeHtml(String(v))}</td>`).join('');
        return `<tr>${cells}</tr>`;
      }).join('');

      container.innerHTML = `
        <table class="pma-table">
          <thead><tr>${theadHtml}</tr></thead>
          <tbody>${tbodyHtml}</tbody>
        </table>
      `;
    }

    // Import Handling
    async function handleImportSubmit() {
      const targetTable = document.getElementById('importTargetTable').value.trim();
      const format = document.getElementById('importFormat').value;
      const fileInput = document.getElementById('importFileInput');
      const filePath = document.getElementById('importFilePath').value.trim();

      if (!targetTable) {
        alert('Lütfen hedef tablo adını belirtin!');
        return;
      }

      showProgress(`[İçe Aktarılıyor] ${targetTable} tablosuna yükleniyor...`, 180000);

      try {
        let payload = { table: targetTable, format: format };

        if (fileInput.files.length > 0) {
          const file = fileInput.files[0];
          const text = await file.text();
          payload.content = text;
        } else if (filePath) {
          payload.filepath = filePath;
        } else {
          finishProgress();
          alert('Lütfen bir dosya seçin veya sunucu dosya yolu girin!');
          return;
        }

        const res = await fetch('/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        finishProgress(() => {
          if (data.success) {
            alert(`Başarılı! ${data.rows_imported.toLocaleString()} satır başarıyla aktarıldı (${data.execution_time_ms} ms).`);
            loadTables();
            setActiveTable(targetTable);
            switchTab('browse');
          } else {
            alert(`İçe aktarma hatası: ${data.error}`);
          }
        });
      } catch (err) {
        finishProgress();
        alert(`İçe aktarma sırasında hata: ${err.message}`);
      }
    }

    // Export Handling
    function handleExportSubmit() {
      if (!activeTable) {
        alert('Lütfen dışa aktarılacak bir tablo seçin!');
        return;
      }
      const fmt = document.getElementById('exportFormat').value;
      showProgress(`[Dışa Aktarılıyor] ${activeTable} -> .${fmt}`, 600000);

      setTimeout(() => {
        finishProgress(() => {
          window.location.href = `/export?table=${encodeURIComponent(activeTable)}&format=${fmt}`;
        });
      }, 500);
    }

    // Operations Handling
    async function handleRenameTable() {
      const newName = document.getElementById('opsRenameNew').value.trim();
      if (!newName || !activeTable) return;

      showProgress(`[İşlem] Tablo yeniden adlandırılıyor...`);
      const res = await fetch('/operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'rename', table: activeTable, new_table: newName })
      });
      const data = await res.json();
      finishProgress(() => {
        if (data.success) {
          loadTables();
          setActiveTable(newName.endsWith('.mgdb') ? newName : newName + '.mgdb');
          switchTab('browse');
        } else {
          alert('Hata: ' + data.error);
        }
      });
    }

    async function handleTruncateTable() {
      if (!activeTable) return;
      if (!confirm(`'${activeTable}' tablosundaki TÜM verileri silmek istediğinizden emin misiniz?`)) return;

      showProgress(`[TRUNCATE] ${activeTable} boşaltılıyor...`);
      const res = await fetch('/operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'truncate', table: activeTable })
      });
      const data = await res.json();
      finishProgress(() => {
        if (data.success) {
          loadTables();
          loadBrowseData();
        } else {
          alert('Hata: ' + data.error);
        }
      });
    }

    async function handleDropTable() {
      if (!activeTable) return;
      if (!confirm(`DİKKAT: '${activeTable}' tablosu ve diski TAMAMEN SİLİNECEK! Emin misiniz?`)) return;

      showProgress(`[DROP] ${activeTable} siliniyor...`);
      const res = await fetch('/operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'drop', table: activeTable })
      });
      const data = await res.json();
      finishProgress(() => {
        if (data.success) {
          activeTable = null;
          loadTables();
          switchTab('browse');
        } else {
          alert('Hata: ' + data.error);
        }
      });
    }

    async function handleAddColumn() {
      const name = document.getElementById('newColName').value.trim();
      const type = document.getElementById('newColType').value;
      const def = document.getElementById('newColDefault').value;
      if (!name || !activeTable) return;

      showProgress(`[Sütun Ekle] ${name} (${type})...`);
      const res = await fetch('/operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add_column', table: activeTable, name: name, type: type, default: def || null })
      });
      const data = await res.json();
      finishProgress(() => {
        if (data.success) {
          document.getElementById('newColName').value = '';
          loadStructureData();
        } else {
          alert('Hata: ' + data.error);
        }
      });
    }

    async function handleDropColumn(colName) {
      if (!confirm(`'${colName}' sütununu silmek istediğinizden emin misiniz?`)) return;
      showProgress(`[Sütun Sil] ${colName}...`);
      const res = await fetch('/operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'drop_column', table: activeTable, name: colName })
      });
      const data = await res.json();
      finishProgress(() => {
        if (data.success) {
          loadStructureData();
        } else {
          alert('Hata: ' + data.error);
        }
      });
    }

    // Create New Table Modal
    function openNewTableModal() {
      document.getElementById('newTableModal').style.display = 'flex';
    }
    function closeNewTableModal() {
      document.getElementById('newTableModal').style.display = 'none';
    }
    async function handleCreateNewTable() {
      const tname = document.getElementById('modalNewTableName').value.trim();
      const colStr = document.getElementById('modalNewTableCols').value.trim();
      if (!tname || !colStr) return;

      const cols = colStr.split(',').map(part => {
        const [cname, ctype] = part.split(':').map(s => s.trim());
        return { name: cname, type: (ctype || 'STRING').toUpperCase() };
      });

      showProgress(`[Tablo Oluştur] ${tname}...`);
      const res = await fetch('/operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create_table', table: tname, columns: cols })
      });
      const data = await res.json();
      finishProgress(() => {
        closeNewTableModal();
        if (data.success) {
          loadTables();
          setActiveTable(tname.endsWith('.mgdb') ? tname : tname + '.mgdb');
        } else {
          alert('Hata: ' + data.error);
        }
      });
    }

    // Status Tab Data
    async function loadServerStatus() {
      try {
        const res = await fetch('/status');
        const data = await res.json();
        document.getElementById('statOs').textContent = data.os || '-';
        document.getElementById('statCpu').textContent = data.cpu || '-';
        document.getElementById('statRam').textContent = data.ram_gb ? `${data.ram_gb} GB` : '-';
        document.getElementById('statDir').textContent = data.working_dir || '-';
        document.getElementById('statTablesCount').textContent = `${data.tables_count || 0} tablo`;
        document.getElementById('statDiskBytes').textContent = formatBytes(data.total_disk_bytes);
        document.getElementById('serverInfoText').textContent = `Çevrimiçi • ${data.tables_count} Tablo (${formatBytes(data.total_disk_bytes)})`;
      } catch (err) {}
    }

    // Utilities
    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function escapeHtml(str) {
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
  </script>
</body>
</html>
"""
