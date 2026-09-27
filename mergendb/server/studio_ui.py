"""
Mergen Studio: Zero-dependency, fast, lightweight phpMyAdmin-style Web UI for MergenDB.
Served by `mergen serve` or `mergendb-server` at http://localhost:8765/studio.
"""

STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MergenDB | phpMyAdmin Edition</title>
  <link rel="icon" href="/logo.png" type="image/png">
  <style>
    :root {
      --pma-blue: #235a81;
      --pma-dark-blue: #1b4463;
      --pma-light-blue: #e8f0f8;
      --pma-border: #ccd8e4;
      --pma-table-border: #d0d7de;
      --pma-text: #222222;
      --pma-text-muted: #555555;
      --pma-bg-light: #f5f7fa;
      --pma-bg-white: #ffffff;
      --pma-header-bg: #235a81;
      --pma-success: #28a745;
      --pma-danger: #dc3545;
      --pma-warning: #ffc107;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-code: "Consolas", "Monaco", "Courier New", monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--pma-bg-light);
      color: var(--pma-text);
      font-family: var(--font-family);
      font-size: 13px;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* Top Progress Bar (Zero blocking, ultra-snappy) */
    #topProgressBar {
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
      width: 0%;
      background: #00d2ff;
      box-shadow: 0 0 6px #00d2ff;
      z-index: 9999;
      transition: width 0.15s ease-out;
      display: none;
    }

    /* phpMyAdmin Classic Header */
    header {
      background: var(--pma-header-bg);
      color: #ffffff;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.15);
      user-select: none;
    }
    .brand-section {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-logo-img {
      height: 28px;
      width: 28px;
      object-fit: contain;
      filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .pma-tag {
      background: rgba(255, 255, 255, 0.2);
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }

    /* Breadcrumbs & Active Table Dropdown */
    .header-center {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 0, 0, 0.15);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
    }
    .header-center select {
      background: #ffffff;
      color: #222;
      border: 1px solid #aaa;
      padding: 3px 6px;
      border-radius: 3px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .status-badge {
      display: flex;
      align-items: center;
      gap: 5px;
      background: rgba(40, 167, 69, 0.25);
      border: 1px solid #28a745;
      color: #98ff98;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
    }
    .status-dot {
      width: 7px;
      height: 7px;
      background: #28a745;
      border-radius: 50%;
    }

    /* Main Container (Sidebar + Content) */
    .main-wrapper {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    /* Sidebar Navigation Tree */
    aside {
      width: 250px;
      min-width: 250px;
      background: var(--pma-bg-white);
      border-right: 1px solid var(--pma-border);
      display: flex;
      flex-direction: column;
      user-select: none;
    }
    .sidebar-header {
      background: #eef3f7;
      border-bottom: 1px solid var(--pma-border);
      padding: 8px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }
    .btn-icon {
      background: #ffffff;
      border: 1px solid #ccd8e4;
      padding: 3px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      color: #333;
    }
    .btn-icon:hover {
      background: #e6edf5;
      border-color: #99afc4;
    }
    .sidebar-filter {
      padding: 6px 10px;
      background: #fafbfc;
      border-bottom: 1px solid var(--pma-border);
    }
    .sidebar-filter input {
      width: 100%;
      padding: 4px 8px;
      border: 1px solid #ccc;
      border-radius: 3px;
      font-size: 12px;
    }

    .table-list {
      flex: 1;
      overflow-y: auto;
      padding: 4px 0;
    }
    .table-node {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 12px;
      cursor: pointer;
      font-size: 12px;
      border-bottom: 1px solid #f1f4f8;
      transition: background 0.1s;
    }
    .table-node:hover {
      background: #eef4f9;
    }
    .table-node.active {
      background: #d8e6f3;
      font-weight: 700;
      color: var(--pma-blue);
      border-left: 3px solid var(--pma-blue);
    }
    .table-node-name {
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
    }
    .table-row-count {
      background: #e2e8f0;
      color: #4a5568;
      font-size: 10px;
      padding: 1px 5px;
      border-radius: 10px;
      font-family: var(--font-code);
    }

    /* Content Area & Tabs */
    .content-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: #f8fafc;
    }

    /* phpMyAdmin Classic Tabs Bar */
    .pma-tabs {
      background: #edf2f7;
      border-bottom: 1px solid var(--pma-border);
      display: flex;
      flex-wrap: wrap;
      padding: 6px 12px 0 12px;
      gap: 2px;
      user-select: none;
    }
    .pma-tab {
      padding: 6px 12px;
      background: #e2e8f0;
      border: 1px solid var(--pma-border);
      border-bottom: none;
      border-radius: 4px 4px 0 0;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      color: #334155;
      display: flex;
      align-items: center;
      gap: 5px;
      margin-bottom: -1px;
    }
    .pma-tab:hover {
      background: #f1f5f9;
    }
    .pma-tab.active {
      background: #ffffff;
      color: var(--pma-blue);
      border-top: 2px solid var(--pma-blue);
      border-bottom: 1px solid #ffffff;
    }

    /* Tab Panes */
    .tab-content {
      flex: 1;
      overflow-y: auto;
      padding: 14px 18px;
    }
    .tab-pane {
      display: none;
    }
    .tab-pane.active {
      display: block;
    }

    /* phpMyAdmin Toolbar & Pagination */
    .toolbar-box {
      background: #ffffff;
      border: 1px solid var(--pma-border);
      border-radius: 4px;
      padding: 8px 12px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }
    .pagination-controls {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .pagination-controls button, .btn-action {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      padding: 4px 10px;
      border-radius: 3px;
      font-size: 12px;
      cursor: pointer;
      font-weight: 600;
      color: #334155;
    }
    .pagination-controls button:hover:not(:disabled), .btn-action:hover {
      background: #e2e8f0;
      border-color: #94a3b8;
    }
    .pagination-controls button:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .page-input {
      width: 44px;
      padding: 3px 4px;
      text-align: center;
      border: 1px solid #cbd5e1;
      border-radius: 3px;
      font-size: 12px;
    }

    /* Table Grid Styling */
    .table-container {
      background: #ffffff;
      border: 1px solid var(--pma-border);
      border-radius: 4px;
      overflow-x: auto;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    table.pma-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }
    table.pma-grid th {
      background: #e8eff6;
      color: var(--pma-dark-blue);
      border-bottom: 2px solid var(--pma-border);
      border-right: 1px solid #e2e8f0;
      padding: 7px 10px;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }
    table.pma-grid th:hover {
      background: #d9e5f0;
    }
    table.pma-grid td {
      border-bottom: 1px solid #edf2f7;
      border-right: 1px solid #edf2f7;
      padding: 6px 10px;
      white-space: nowrap;
      max-width: 320px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    table.pma-grid tr:nth-child(even) {
      background: #fbfcfd;
    }
    table.pma-grid tr:hover {
      background: #f1f6fa;
    }
    .btn-row-action {
      background: none;
      border: none;
      cursor: pointer;
      font-size: 11px;
      padding: 2px 4px;
      border-radius: 2px;
    }
    .btn-row-action:hover {
      background: #e2e8f0;
    }

    /* Cards & Forms */
    .card-box {
      background: #ffffff;
      border: 1px solid var(--pma-border);
      border-radius: 4px;
      padding: 16px;
      margin-bottom: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--pma-dark-blue);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #edf2f7;
      padding-bottom: 6px;
    }
    .form-group {
      margin-bottom: 12px;
    }
    .form-group label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      margin-bottom: 4px;
      color: #334155;
    }
    .form-group input, .form-group select, .form-group textarea {
      width: 100%;
      padding: 6px 10px;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      font-size: 13px;
      font-family: inherit;
    }
    .form-row {
      display: flex;
      gap: 12px;
    }
    .form-row > * {
      flex: 1;
    }
    .btn-submit {
      background: var(--pma-blue);
      color: #ffffff;
      border: none;
      padding: 7px 16px;
      border-radius: 4px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-submit:hover {
      background: var(--pma-dark-blue);
    }
    .btn-danger {
      background: var(--pma-danger);
      color: #ffffff;
      border: none;
      padding: 7px 16px;
      border-radius: 4px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-danger:hover {
      background: #bd2130;
    }

    /* SQL Editor */
    .sql-editor-container textarea {
      width: 100%;
      height: 140px;
      font-family: var(--font-code);
      font-size: 13px;
      padding: 10px;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      resize: vertical;
      background: #fafbfc;
    }
    .sql-snippets {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
      margin-bottom: 12px;
    }
    .sql-snippet-btn {
      background: #edf2f7;
      border: 1px solid #cbd5e1;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-family: var(--font-code);
    }
    .sql-snippet-btn:hover {
      background: #e2e8f0;
      border-color: #94a3b8;
    }

    /* SQL Query Telemetry Banner */
    .telemetry-bar {
      background: #e8f4fd;
      border: 1px solid #b6d4fe;
      color: #084298;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      margin-top: 10px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 16px;
      font-family: var(--font-code);
    }

    /* Documentation Code Boxes */
    .doc-lang-tabs {
      display: flex;
      gap: 4px;
      border-bottom: 2px solid #cbd5e1;
      margin-bottom: 12px;
    }
    .doc-lang-tab {
      padding: 6px 14px;
      cursor: pointer;
      font-weight: 600;
      border-radius: 4px 4px 0 0;
      background: #e2e8f0;
    }
    .doc-lang-tab.active {
      background: var(--pma-blue);
      color: #ffffff;
    }
    .code-box {
      background: #1e293b;
      color: #f8fafc;
      padding: 14px;
      border-radius: 6px;
      font-family: var(--font-code);
      font-size: 12px;
      overflow-x: auto;
      line-height: 1.5;
      position: relative;
    }
    .btn-copy-code {
      position: absolute;
      top: 8px;
      right: 8px;
      background: rgba(255,255,255,0.15);
      color: #fff;
      border: none;
      padding: 3px 8px;
      border-radius: 3px;
      font-size: 11px;
      cursor: pointer;
    }
    .btn-copy-code:hover {
      background: rgba(255,255,255,0.3);
    }

    /* Notification Toast */
    #toastMsg {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #1e293b;
      color: #ffffff;
      padding: 10px 18px;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      font-size: 13px;
      display: none;
      align-items: center;
      gap: 8px;
      z-index: 10000;
    }

    /* Modal for New Table / Create Column */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.4);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9000;
    }
    .modal-card {
      background: #ffffff;
      border-radius: 6px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.2);
      width: 480px;
      max-width: 95%;
      overflow: hidden;
    }
    .modal-head {
      background: #eef3f7;
      padding: 10px 16px;
      font-weight: 700;
      font-size: 14px;
      border-bottom: 1px solid var(--pma-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .modal-body {
      padding: 16px;
    }
  </style>
</head>
<body>

  <!-- Top Slim Progress Bar -->
  <div id="topProgressBar"></div>

  <!-- phpMyAdmin Classic Header -->
  <header>
    <div class="brand-section">
      <img src="/logo.png" alt="MergenDB" class="brand-logo-img" onerror="this.style.display='none'">
      <span class="brand-title">MergenDB</span>
      <span class="pma-tag">phpMyAdmin Edition</span>
    </div>

    <!-- Active Table Selector & Breadcrumbs -->
    <div class="header-center">
      <span>🏠 <b>127.0.0.1</b></span>
      <span>»</span>
      <span>📁 mergendb</span>
      <span>»</span>
      <span>📄 Aktif Tablo:</span>
      <select id="activeTableSelect" onchange="changeActiveTable(this.value)">
        <option value="">(Tablo Seçin)</option>
      </select>
    </div>

    <div class="header-right">
      <div class="status-badge">
        <div class="status-dot"></div>
        <span id="headerStatusText">v__MERGEN_VERSION__ Çevrimiçi</span>
      </div>
      <button class="btn-icon" onclick="switchTab('status')">🩺 Sunucu</button>
      <button class="btn-icon" onclick="switchTab('docs')">📚 Kılavuz (Docs)</button>
    </div>
  </header>

  <!-- Main Application Wrapper -->
  <div class="main-wrapper">

    <!-- Sidebar: Local .mgdb Table Tree -->
    <aside>
      <div class="sidebar-header">
        <button class="btn-icon" onclick="openNewTableModal()">➕ Yeni Tablo</button>
        <button class="btn-icon" onclick="loadTables()" title="Yenile">🔄</button>
      </div>
      <div class="sidebar-filter">
        <input type="text" id="sidebarFilter" placeholder="Tabloları filtrele..." oninput="filterTables()">
      </div>
      <div class="table-list" id="sidebarTableList">
        <!-- Loaded via JavaScript -->
      </div>
    </aside>

    <!-- Content Area & Navigation Tabs -->
    <main class="content-area">

      <!-- Navigation Tabs (phpMyAdmin Standard) -->
      <nav class="pma-tabs">
        <div class="pma-tab active" data-tab="browse" onclick="switchTab('browse')">
          <span>👁️</span> Gözat (Browse)
        </div>
        <div class="pma-tab" data-tab="structure" onclick="switchTab('structure')">
          <span>📋</span> Yapı (Structure)
        </div>
        <div class="pma-tab" data-tab="sql" onclick="switchTab('sql')">
          <span>🔍</span> SQL
        </div>
        <div class="pma-tab" data-tab="search" onclick="switchTab('search')">
          <span>🔎</span> Ara (Search)
        </div>
        <div class="pma-tab" data-tab="insert" onclick="switchTab('insert')">
          <span>➕</span> Ekle (Insert)
        </div>
        <div class="pma-tab" data-tab="export" onclick="switchTab('export')">
          <span>📤</span> Dışa Aktar (Export)
        </div>
        <div class="pma-tab" data-tab="import" onclick="switchTab('import')">
          <span>📥</span> İçe Aktar (Import)
        </div>
        <div class="pma-tab" data-tab="operations" onclick="switchTab('operations')">
          <span>⚙️</span> İşlemler (Operations)
        </div>
        <div class="pma-tab" data-tab="status" onclick="switchTab('status')">
          <span>🩺</span> Sunucu & Test
        </div>
        <div class="pma-tab" data-tab="docs" onclick="switchTab('docs')">
          <span>📚</span> Kılavuz & Ekosistem
        </div>
      </nav>

      <!-- Tab Panes -->
      <div class="tab-content">

        <!-- 1. GÖZAT (BROWSE) TAB -->
        <div class="tab-pane active" id="pane-browse">
          <div class="toolbar-box">
            <div class="pagination-controls">
              <button id="btnFirst" onclick="changePage(1)">« İlk</button>
              <button id="btnPrev" onclick="changePage(currentPage - 1)">‹ Önceki</button>
              <span style="font-size: 12px; margin: 0 4px;">Sayfa:</span>
              <input type="number" id="pageNumberInput" class="page-input" value="1" min="1" onchange="changePage(parseInt(this.value))">
              <span id="pageTotalText" style="font-size: 12px; color: #666;">/ 1</span>
              <button id="btnNext" onclick="changePage(currentPage + 1)">Sonraki ›</button>
              <button id="btnLast" onclick="changePage(totalPages)">Son »</button>

              <span style="margin-left: 12px; font-size: 12px;">Satır:</span>
              <select id="limitSelect" onchange="pageLimit = parseInt(this.value); changePage(1);" style="padding: 2px 4px; font-size: 12px;">
                <option value="25">25</option>
                <option value="50" selected>50</option>
                <option value="100">100</option>
                <option value="250">250</option>
              </select>
            </div>

            <div id="browseInfoText" style="font-size: 12px; color: var(--pma-text-muted);">
              Tablo yükleniyor...
            </div>

            <div>
              <button class="btn-action" onclick="loadBrowseData()">🔄 Yenile</button>
            </div>
          </div>

          <div class="table-container" id="browseGridContainer">
            <div style="padding: 3rem; text-align: center; color: #888;">
              Sol taraftan bir .mgdb tablosu seçin veya yeni oluşturun.
            </div>
          </div>
        </div>

        <!-- 2. YAPI (STRUCTURE) TAB -->
        <div class="tab-pane" id="pane-structure">
          <div class="card-box">
            <div class="card-title">
              <span>Sütun Listesi & Şema Tanımı (<span id="structTableName">Tablo</span>)</span>
              <span id="structTableInfo" style="font-size: 12px; font-weight: normal; color: #666;">0 blok • 0 satır</span>
            </div>
            <div class="table-container" style="margin-bottom: 16px;">
              <table class="pma-grid">
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

            <!-- Add Column Inline Form -->
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 12px;">
              <h4 style="margin-bottom: 8px; font-size: 13px;">➕ Tabloya Yeni Sütun Ekle (ALTER TABLE ADD COLUMN)</h4>
              <div class="form-row">
                <div class="form-group" style="margin-bottom: 0;">
                  <label>Sütun Adı</label>
                  <input type="text" id="newColName" placeholder="örn: status, score, created_at">
                </div>
                <div class="form-group" style="margin-bottom: 0;">
                  <label>Veri Tipi</label>
                  <select id="newColType">
                    <option value="STRING">STRING</option>
                    <option value="INT64">INT64</option>
                    <option value="FLOAT64">FLOAT64</option>
                    <option value="BOOL">BOOL</option>
                    <option value="TIMESTAMP">TIMESTAMP</option>
                  </select>
                </div>
                <div class="form-group" style="margin-bottom: 0;">
                  <label>Varsayılan Değer (Opsiyonel)</label>
                  <input type="text" id="newColDefault" placeholder="örn: ACTIVE, 0, true">
                </div>
                <div style="display: flex; align-items: flex-end;">
                  <button class="btn-submit" onclick="handleAddColumn()">Sütun Ekle</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. SQL TAB -->
        <div class="tab-pane" id="pane-sql">
          <div class="card-box">
            <div class="card-title">
              <span>SQL / MergenQL Sorgu Çalıştırıcı</span>
              <span style="font-size: 11px; color: #888;">Kısayol: <b>Ctrl + Enter</b></span>
            </div>

            <div class="sql-editor-container">
              <textarea id="sqlQueryText" placeholder="SELECT * FROM table LIMIT 25;"></textarea>
            </div>

            <div class="sql-snippets">
              <span style="font-size: 11px; color: #666; display: flex; align-items: center; margin-right: 4px;">Şablonlar:</span>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('SELECT *')">SELECT *</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('COUNT')">COUNT(*)</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('WHERE')">WHERE Filtre</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('GROUP_BY')">GROUP BY + HAVING</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('BLOOM')">Bloom Filter Lookup</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('JOIN')">Hash JOIN</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('UPDATE')">UPDATE</button>
              <button class="sql-snippet-btn" onclick="setSqlSnippet('DELETE')">DELETE</button>
            </div>

            <div style="display: flex; justify-content: flex-end; gap: 8px;">
              <button class="btn-action" onclick="document.getElementById('sqlQueryText').value=''">Temizle</button>
              <button class="btn-submit" onclick="runSqlQuery()">Git / Çalıştır (Execute)</button>
            </div>

            <!-- SQL Results Area -->
            <div id="sqlExecutionTelemetry" style="display: none;" class="telemetry-bar">
              <span>⏱️ Süre: <b id="sqlTime">0 ms</b></span>
              <span>📊 Dönen Satır: <b id="sqlRowsCount">0</b></span>
              <span>🔍 Taranan Blok: <b id="sqlBlocksScanned">0</b></span>
              <span>⚡ Atlanan (ZoneMap/Bloom): <b id="sqlBlocksSkipped">0</b></span>
              <span>💾 Okunan Bayt: <b id="sqlBytesRead">0 B</b></span>
            </div>

            <div class="table-container" id="sqlResultContainer" style="margin-top: 12px; display: none;"></div>
          </div>
        </div>

        <!-- 4. ARA (SEARCH / FIND) TAB -->
        <div class="tab-pane" id="pane-search">
          <div class="card-box">
            <div class="card-title">
              <span>Tablo İçi Arama (CLI .search() & .find())</span>
            </div>

            <!-- Full-text search across all columns -->
            <div style="margin-bottom: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 12px;">
              <h4 style="margin-bottom: 6px; font-size: 13px;">🔍 1. Genel Metin Araması (Tüm Sütunlarda Alt Dize / LIKE)</h4>
              <div style="display: flex; gap: 8px;">
                <input type="text" id="fulltextSearchInput" placeholder="Aramak istediğiniz metni veya ID'yi girin..." style="flex: 1; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 4px;">
                <button class="btn-submit" onclick="executeSearchFullText()">Hemen Ara</button>
              </div>
            </div>

            <!-- Column-wise filter search -->
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 12px;">
              <h4 style="margin-bottom: 8px; font-size: 13px;">🎯 2. Sütuna Göre Kesin Eşleşme (CLI .find() Karşılığı)</h4>
              <div id="columnFiltersContainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-bottom: 12px;">
                <!-- Generated dynamically from schema -->
              </div>
              <button class="btn-submit" onclick="executeSearchColumns()">Kriterlere Göre Filtrele</button>
            </div>

            <!-- Search Results Table -->
            <div class="table-container" id="searchResultContainer" style="margin-top: 16px; display: none;"></div>
          </div>
        </div>

        <!-- 5. EKLE (INSERT) TAB -->
        <div class="tab-pane" id="pane-insert">
          <div class="card-box">
            <div class="card-title">
              <span>Yeni Satır Ekle (INSERT INTO <span id="insertTableName">Tablo</span>)</span>
            </div>
            <p style="font-size: 12px; color: #666; margin-bottom: 14px;">Aktif tablonun şemasına göre sütun değerlerini girin ve doğrudan veritabanına kaydedin.</p>
            <form id="insertRowForm" onsubmit="handleInsertRow(event)">
              <div id="insertFieldsContainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 16px;">
                <!-- Generated dynamically -->
              </div>
              <div style="display: flex; gap: 10px;">
                <button type="submit" class="btn-submit">💾 Satırı Kaydet</button>
                <button type="button" class="btn-action" onclick="document.getElementById('insertRowForm').reset()">Temizle</button>
              </div>
            </form>
          </div>
        </div>

        <!-- 6. DIŞA AKTAR (EXPORT) TAB -->
        <div class="tab-pane" id="pane-export">
          <div class="card-box">
            <div class="card-title">
              <span>Veri Dışa Aktar (EXPORT)</span>
            </div>
            <p style="font-size: 12px; color: #666; margin-bottom: 14px;">Seçilen tablonun verilerini anında tarayıcınız üzerinden indirin.</p>
            <div class="form-row" style="max-width: 500px; margin-bottom: 16px;">
              <div class="form-group">
                <label>Hedef Tablo</label>
                <input type="text" id="exportTargetTable" readonly style="background: #eef3f7; font-weight: 600;">
              </div>
              <div class="form-group">
                <label>Format</label>
                <select id="exportFormatSelect">
                  <option value="csv">CSV (Virgülle Ayrılmış Değerler)</option>
                  <option value="json">JSON (Array of Objects)</option>
                  <option value="jsonl">JSON Lines (.jsonl)</option>
                  <option value="sql">SQL Dump (INSERT INTO ifadeleri)</option>
                </select>
              </div>
            </div>
            <button class="btn-submit" onclick="executeExportDownload()">📥 Doğrudan İndir (Export)</button>
          </div>
        </div>

        <!-- 7. İÇE AKTAR (IMPORT) TAB -->
        <div class="tab-pane" id="pane-import">
          <div class="card-box">
            <div class="card-title">
              <span>Veri İçe Aktar (IMPORT)</span>
            </div>
            <p style="font-size: 12px; color: #666; margin-bottom: 14px;">Harici dosyaları (.csv, .sql, .json) veya ham metni doğrudan sütunsal .mgdb tablosuna aktarın.</p>
            <div class="form-row" style="max-width: 600px; margin-bottom: 14px;">
              <div class="form-group">
                <label>Hedef Tablo Adı</label>
                <input type="text" id="importTargetTable">
              </div>
              <div class="form-group">
                <label>Format</label>
                <select id="importFormatSelect">
                  <option value="csv">CSV (.csv)</option>
                  <option value="sql">SQL Dump (.sql)</option>
                  <option value="json">JSON / JSONL (.json, .jsonl)</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>Dosyadan Seç</label>
              <input type="file" id="importFileInput" accept=".csv,.sql,.json,.jsonl" style="background: #fff;">
            </div>

            <div class="form-group">
              <label>Veya Metin Yapıştır (Opsiyonel)</label>
              <textarea id="importContentText" style="height: 100px; font-family: var(--font-code); font-size: 12px;" placeholder="id,name,age..."></textarea>
            </div>

            <button class="btn-submit" onclick="executeImportData()">📤 İçe Aktarmayı Başlat</button>
            <div id="importResultStatus" style="margin-top: 12px; font-size: 12px; font-weight: 600;"></div>
          </div>
        </div>

        <!-- 8. İŞLEMLER (OPERATIONS) TAB -->
        <div class="tab-pane" id="pane-operations">
          <div class="card-box">
            <div class="card-title">
              <span>Tablo İşlemleri (<span id="opTableName">Tablo</span>)</span>
            </div>

            <!-- Rename Table -->
            <div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #edf2f7;">
              <h4 style="font-size: 13px; margin-bottom: 6px;">✏️ Tabloyu Yeniden Adlandır (RENAME TABLE)</h4>
              <div style="display: flex; gap: 8px; max-width: 450px;">
                <input type="text" id="opNewTableName" placeholder="Yeni tablo adı (örn: users_v2)">
                <button class="btn-action" onclick="handleRenameTable()">Yeniden Adlandır</button>
              </div>
            </div>

            <!-- Truncate Table -->
            <div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #edf2f7;">
              <h4 style="font-size: 13px; margin-bottom: 6px; color: #b45309;">⚠️ Tabloyu Boşalt (TRUNCATE TABLE)</h4>
              <p style="font-size: 12px; color: #666; margin-bottom: 8px;">Tablodaki tüm satırları sıfırlar ancak sütun şemasını ve tanımları korur.</p>
              <button class="btn-action" style="color: #b45309; border-color: #f59e0b;" onclick="handleTruncateTable()">Tabloyu Boşalt (Truncate)</button>
            </div>

            <!-- Drop Table -->
            <div>
              <h4 style="font-size: 13px; margin-bottom: 6px; color: var(--pma-danger);">🗑️ Tabloyu Kalıcı Olarak Sil (DROP TABLE)</h4>
              <p style="font-size: 12px; color: #666; margin-bottom: 8px;">Tabloyu ve diskteki tüm veri bloklarını kalıcı olarak siler.</p>
              <button class="btn-danger" onclick="handleDropTable()">Tabloyu Tamamen Sil (Drop)</button>
            </div>
          </div>
        </div>

        <!-- 9. SUNUCU & TEST (STATUS) TAB -->
        <div class="tab-pane" id="pane-status">
          <div class="card-box">
            <div class="card-title">
              <span>Sistem Bilgileri & Canlı Donanım Hız Testi (Profiler)</span>
              <button class="btn-submit" onclick="runLiveHardwareBenchmark()">🚀 Canlı Hız Testi Başlat (Benchmark)</button>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 18px;">
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;">İşlemci (CPU)</div>
                <div id="statCpu" style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 2px;">Algılanıyor...</div>
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;">Sistem Belleği (RAM)</div>
                <div id="statRam" style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 2px;">Algılanıyor...</div>
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;">İşletim Sistemi</div>
                <div id="statOs" style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 2px;">Algılanıyor...</div>
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;">Motor Sürümü</div>
                <div id="statVer" style="font-size: 13px; font-weight: 700; color: var(--pma-blue); margin-top: 2px;">v__MERGEN_VERSION__</div>
              </div>
            </div>

            <!-- Live Benchmark Results Area -->
            <div id="liveBenchCard" style="display: none; background: #eef6fc; border: 1px solid #bce0fd; border-radius: 6px; padding: 16px;">
              <h4 style="color: #0369a1; margin-bottom: 12px; font-size: 14px;">⚡ Bu Cihaz Üzerinde Ölçülen Hızlar:</h4>
              <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 12px;">
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;">Sıralı Veri Yazma (Append)</span>
                  <div id="benchIngest" style="font-size: 16px; font-weight: 800; color: #0284c7;">-</div>
                </div>
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;">CSV / SQL Akış İçe Aktarma</span>
                  <div id="benchImport" style="font-size: 16px; font-weight: 800; color: #0284c7;">-</div>
                </div>
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;">Dışa Aktarma (Export)</span>
                  <div id="benchExport" style="font-size: 16px; font-weight: 800; color: #0284c7;">-</div>
                </div>
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;">Analitik Sütun Taraması (Scan)</span>
                  <div id="benchScan" style="font-size: 16px; font-weight: 800; color: #16a34a;">-</div>
                </div>
              </div>
              <div style="font-size: 12px; color: #334155; line-height: 1.4;">
                <b>Performans Katmanı:</b> <span id="benchTier">-</span><br>
                <b>Önerilen Blok Boyutu:</b> <span id="benchBlock">-</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 10. KILAVUZ & EKOSİSTEM (DOCS & LANGUAGES) TAB -->
        <div class="tab-pane" id="pane-docs">
          <div class="card-box">
            <div class="card-title">
              <span>Desteklenen Diller & Ekosistem Kullanım Kılavuzu</span>
            </div>
            <p style="font-size: 12px; color: #666; margin-bottom: 16px;">
              MergenDB, sıfır dış bağımlılıkla Python, Node.js / TypeScript, Shell CLI ve REST API üzerinden %100 fonksiyon desteği sunar.
            </p>

            <div class="doc-lang-tabs">
              <div class="doc-lang-tab active" data-lang="python" onclick="switchDocLang('python')">🐍 Python API</div>
              <div class="doc-lang-tab" data-lang="nodejs" onclick="switchDocLang('nodejs')">⚡ Node.js / TypeScript</div>
              <div class="doc-lang-tab" data-lang="cli" onclick="switchDocLang('cli')">💻 Mergen CLI</div>
              <div class="doc-lang-tab" data-lang="rest" onclick="switchDocLang('rest')">🌐 HTTP / REST (cURL)</div>
            </div>

            <!-- Python Docs -->
            <div id="doc-pane-python" class="doc-pane">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('pythonSnippet')">Kopyala</button>
<pre id="pythonSnippet"># Kurulum: pip install --upgrade mergendb
import mergendb

# 1. Bağlantı kur veya tablo aç (Yoksa otomatik oluşturulur)
db = mergendb.connect("users.mgdb")

# 2. Satır Ekleme (Şema otomatik algılanır)
db.insert([
    {"id": 1, "name": "Alice", "role": "admin", "score": 95.5, "active": True},
    {"id": 2, "name": "Bob", "role": "developer", "score": 88.0, "active": True},
])

# 3. Hızlı Arama & Filtreleme (Boilerplate yok)
admins = db.find(role="admin", active=True)
alice = db.find_one(name="Alice")
matches = db.search("admin")  # Tüm metin sütunlarında LIKE araması

# 4. Standart Analitik SQL
res = db.sql("SELECT role, COUNT(*), AVG(score) FROM users GROUP BY role HAVING COUNT(*) > 0")
res.show() # ASCII tablo çıktısı

# 5. Güncelleme & Silme
db.update({"score": 99.0}, where="name = 'Alice'")
db.delete(where="active = False")

# 6. Dışa ve İçe Aktarma
db.export_csv("users.csv")
mergendb.from_csv("users.csv", "users_backup.mgdb")

# 7. Donanım Hız Testi
mergendb.benchmark()</pre>
              </div>
            </div>

            <!-- Node.js / TypeScript Docs -->
            <div id="doc-pane-nodejs" class="doc-pane" style="display: none;">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('nodejsSnippet')">Kopyala</button>
<pre id="nodejsSnippet">// Kurulum: npm install mergendb
// 0 Dış Bağımlılık - Node.js yerleşik HTTP/HTTPS üzerinde çalışır
const { connect } = require('mergendb');
// veya TypeScript: import { connect } from 'mergendb';

async function main() {
  const db = connect('http://localhost:8765');

  // 1. Bağlantı Sağlık Kontrolü & Donanım Hız Testi
  const isHealthy = await db.ping();
  const benchmark = await db.benchmark();

  // 2. Tablo İşleyicisi
  const users = db.table('users.mgdb');

  // 3. Satır Ekleme (Direct Object Insert)
  await users.insert([
    { id: 1, name: 'Alice', role: 'admin', score: 95.5, active: true },
    { id: 2, name: 'Bob', role: 'developer', score: 88.0, active: true }
  ]);

  // 4. Doküman Tarzı Filtreleme & Arama
  const admins = await users.find({ role: 'admin', active: true });
  const single = await users.findOne({ id: 1 });
  const searchResults = await users.search('admin'); // Full-text substring search

  // 5. Parametreli Güvenli SQL (Tagged Template Literal)
  const targetRole = 'admin';
  const sqlRes = await db.sql`SELECT * FROM users WHERE role = ${targetRole}`;
  console.table(sqlRes.rows);

  // 6. Güncelleme, Silme ve Şema Değişiklikleri
  await users.update({ score: 99.5 }, "name = 'Alice'");
  await users.delete("score < 50");
  await users.addColumn('country', 'STRING', 'TR');
  await users.renameColumn('country', 'nation');

  // 7. Dışa Aktarma
  const csvData = await users.export('csv');
}

main().catch(console.error);</pre>
              </div>
            </div>

            <!-- CLI Docs -->
            <div id="doc-pane-cli" class="doc-pane" style="display: none;">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('cliSnippet')">Kopyala</button>
<pre id="cliSnippet"># 1. Mergen Studio & REST Sunucusunu Başlatma
mergen serve
mergen serve 8765

# 2. Canlı Donanım ve Hız Testi
mergen test
mergen benchmark

# 3. Tekil SQL Sorgusu Çalıştırma (REPL'e girmeden)
mergen query "SELECT * FROM users WHERE role = 'admin';"

# 4. Kabuk Otomatik Tamamlama (Completions)
mergen completions bash >> ~/.bashrc
mergen completions powershell >> $PROFILE

# 5. Etkileşimli Terminal REPL
mergen users.mgdb
mergen> SELECT role, COUNT(*) FROM users GROUP BY role;
mergen> EXPORT users TO csv users.csv;
mergen> IMPORT users csv new_data.csv;</pre>
              </div>
            </div>

            <!-- REST Docs -->
            <div id="doc-pane-rest" class="doc-pane" style="display: none;">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('restSnippet')">Kopyala</button>
<pre id="restSnippet"># 1. SQL Sorgusu Gönderme (POST /query)
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users.mgdb WHERE score > 80;"}'

# 2. Tablo Listesi & Blok İstatistikleri (GET /tables)
curl http://localhost:8765/tables

# 3. Sayfalı Veri Okuma (GET /table_data)
curl "http://localhost:8765/table_data?table=users.mgdb&page=1&limit=50"

# 4. Doğrudan CSV/JSON Dışa Aktarma (GET /export)
curl "http://localhost:8765/export?table=users.mgdb&format=csv" -o users.csv

# 5. Satır Ekleme (POST /operation)
curl -X POST http://localhost:8765/operation \
  -H "Content-Type: application/json" \
  -d '{"op": "insert", "table": "users.mgdb", "row": {"id": 3, "name": "Charlie", "score": 91.0}}'</pre>
              </div>
            </div>

          </div>
        </div>

      </div>
    </main>
  </div>

  <!-- Toast Notification -->
  <div id="toastMsg">✓ İşlem tamamlandı</div>

  <!-- New Table Modal -->
  <div class="modal-overlay" id="newTableModal">
    <div class="modal-card">
      <div class="modal-head">
        <span>➕ Yeni .mgdb Tablosu Oluştur</span>
        <button class="btn-icon" onclick="closeNewTableModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Tablo Adı</label>
          <input type="text" id="modalNewTableName" placeholder="örn: orders, sensors, customers">
        </div>
        <div class="form-group">
          <label>İlk Sütun Tanımı</label>
          <div class="form-row">
            <input type="text" id="modalColName1" value="id" placeholder="Sütun Adı">
            <select id="modalColType1">
              <option value="INT64">INT64</option>
              <option value="STRING">STRING</option>
              <option value="FLOAT64">FLOAT64</option>
              <option value="BOOL">BOOL</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>İkinci Sütun Tanımı</label>
          <div class="form-row">
            <input type="text" id="modalColName2" value="name" placeholder="Sütun Adı">
            <select id="modalColType2">
              <option value="STRING">STRING</option>
              <option value="INT64">INT64</option>
              <option value="FLOAT64">FLOAT64</option>
              <option value="BOOL">BOOL</option>
            </select>
          </div>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px;">
          <button class="btn-action" onclick="closeNewTableModal()">İptal</button>
          <button class="btn-submit" onclick="submitCreateNewTable()">Tabloyu Oluştur</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    // State
    let activeTable = '';
    let tablesList = [];
    let currentPage = 1;
    let pageLimit = 50;
    let totalRows = 0;
    let totalPages = 1;
    let currentSchema = [];
    let sortColumn = '';
    let sortDirection = 'asc';

    // Top progress bar (non-blocking, fast)
    function startProgress() {
      const p = document.getElementById('topProgressBar');
      p.style.display = 'block';
      p.style.width = '30%';
    }
    function endProgress() {
      const p = document.getElementById('topProgressBar');
      p.style.width = '100%';
      setTimeout(() => {
        p.style.display = 'none';
        p.style.width = '0%';
      }, 150);
    }

    function showToast(msg) {
      const t = document.getElementById('toastMsg');
      t.textContent = msg;
      t.style.display = 'flex';
      setTimeout(() => { t.style.display = 'none'; }, 2500);
    }

    function escapeHtml(str) {
      if (str === null || str === undefined) return '<i style="color:#aaa">NULL</i>';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Init App
    window.addEventListener('DOMContentLoaded', () => {
      loadServerStatus();
      loadTables();

      // Keyboard Shortcut Ctrl+Enter for SQL
      document.getElementById('sqlQueryText').addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          e.preventDefault();
          runSqlQuery();
        }
      });
    });

    // Tab Switching
    function switchTab(tabId) {
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
      } else if (tabId === 'search') {
        renderSearchInputs();
      } else if (tabId === 'insert') {
        renderInsertInputs();
      } else if (tabId === 'export') {
        document.getElementById('exportTargetTable').value = activeTable;
      } else if (tabId === 'import') {
        document.getElementById('importTargetTable').value = activeTable ? activeTable.replace(/\.mgdb$/, '') : '';
      } else if (tabId === 'operations') {
        document.getElementById('opTableName').textContent = activeTable || '(Seçilmedi)';
      } else if (tabId === 'status') {
        loadServerStatus();
      }
    }

    // Load Tables
    async function loadTables() {
      startProgress();
      try {
        const res = await fetch('/tables');
        const data = await res.json();
        tablesList = data.tables || [];
        renderSidebar();
        updateActiveTableDropdown();

        if (!activeTable && tablesList.length > 0) {
          setActiveTable(tablesList[0].table);
        }
      } catch (err) {
        console.error('Error loading tables:', err);
      } finally {
        endProgress();
      }
    }

    function renderSidebar() {
      const container = document.getElementById('sidebarTableList');
      if (tablesList.length === 0) {
        container.innerHTML = `<div style="padding: 1rem; color: #888; text-align: center;">Tablo bulunamadı.</div>`;
        return;
      }
      container.innerHTML = tablesList.map(t => `
        <div class="table-node ${activeTable === t.table ? 'active' : ''}" onclick="setActiveTable('${t.table}')">
          <div class="table-node-name" title="${t.table}">
            <span>📄</span>
            <span>${t.table}</span>
          </div>
          <span class="table-row-count">${Number(t.rows).toLocaleString()}</span>
        </div>
      `).join('');
    }

    function filterTables() {
      const q = document.getElementById('sidebarFilter').value.toLowerCase();
      const filtered = tablesList.filter(t => t.table.toLowerCase().includes(q));
      const container = document.getElementById('sidebarTableList');
      container.innerHTML = filtered.map(t => `
        <div class="table-node ${activeTable === t.table ? 'active' : ''}" onclick="setActiveTable('${t.table}')">
          <div class="table-node-name">
            <span>📄</span>
            <span>${t.table}</span>
          </div>
          <span class="table-row-count">${Number(t.rows).toLocaleString()}</span>
        </div>
      `).join('');
    }

    function updateActiveTableDropdown() {
      const sel = document.getElementById('activeTableSelect');
      sel.innerHTML = tablesList.map(t => `
        <option value="${t.table}" ${t.table === activeTable ? 'selected' : ''}>${t.table} (${Number(t.rows).toLocaleString()} satır)</option>
      `).join('');
      if (!activeTable && tablesList.length > 0) {
        sel.value = tablesList[0].table;
      }
    }

    function changeActiveTable(tbl) {
      if (tbl) setActiveTable(tbl);
    }

    function setActiveTable(tbl) {
      activeTable = tbl;
      currentPage = 1;
      sortColumn = '';
      sortDirection = 'asc';
      renderSidebar();
      document.getElementById('activeTableSelect').value = tbl;
      document.getElementById('structTableName').textContent = tbl;
      document.getElementById('insertTableName').textContent = tbl;
      document.getElementById('opTableName').textContent = tbl;
      document.getElementById('exportTargetTable').value = tbl;
      document.getElementById('importTargetTable').value = tbl.replace(/\.mgdb$/, '');

      const activeTab = document.querySelector('.pma-tab.active');
      const tabId = activeTab ? activeTab.dataset.tab : 'browse';
      if (tabId === 'browse') loadBrowseData();
      else if (tabId === 'structure') loadStructureData();
      else if (tabId === 'search') renderSearchInputs();
      else if (tabId === 'insert') renderInsertInputs();
    }

    // 1. Gözat (Browse)
    async function loadBrowseData() {
      if (!activeTable) return;
      startProgress();

      try {
        let url = `/table_data?table=${encodeURIComponent(activeTable)}&page=${currentPage}&limit=${pageLimit}`;
        if (sortColumn) {
          url += `&sort_col=${encodeURIComponent(sortColumn)}&sort_dir=${sortDirection}`;
        }
        const res = await fetch(url);
        const data = await res.json();

        if (data.error) {
          document.getElementById('browseGridContainer').innerHTML = `<div style="padding: 2rem; color: var(--pma-danger);">Hata: ${data.error}</div>`;
          return;
        }

        totalRows = data.total_rows || 0;
        totalPages = Math.max(1, Math.ceil(totalRows / pageLimit));
        if (currentPage > totalPages) currentPage = totalPages;

        document.getElementById('pageNumberInput').value = currentPage;
        document.getElementById('pageNumberInput').max = totalPages;
        document.getElementById('pageTotalText').textContent = `/ ${totalPages}`;
        
        const startRow = totalRows === 0 ? 0 : (currentPage - 1) * pageLimit + 1;
        const endRow = Math.min(currentPage * pageLimit, totalRows);
        document.getElementById('browseInfoText').textContent = `${startRow.toLocaleString()} - ${endRow.toLocaleString()} / ${totalRows.toLocaleString()} satır gösteriliyor`;

        document.getElementById('btnFirst').disabled = currentPage <= 1;
        document.getElementById('btnPrev').disabled = currentPage <= 1;
        document.getElementById('btnNext').disabled = currentPage >= totalPages;
        document.getElementById('btnLast').disabled = currentPage >= totalPages;

        renderGridTable(document.getElementById('browseGridContainer'), data.columns, data.rows, true);
      } catch (err) {
        document.getElementById('browseGridContainer').innerHTML = `<div style="padding: 2rem; color: var(--pma-danger);">Bağlantı Hatası: ${err.message}</div>`;
      } finally {
        endProgress();
      }
    }

    function changePage(page) {
      const p = Math.max(1, Math.min(totalPages, page));
      currentPage = p;
      loadBrowseData();
    }

    function handleSort(col) {
      if (sortColumn === col) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      } else {
        sortColumn = col;
        sortDirection = 'asc';
      }
      loadBrowseData();
    }

    function renderGridTable(container, columns, rows, enableActions = false) {
      if (!columns || columns.length === 0) {
        container.innerHTML = `<div style="padding: 2rem; text-align: center; color: #888;">Tabloda sütun bulunamadı.</div>`;
        return;
      }
      if (!rows || rows.length === 0) {
        container.innerHTML = `<div style="padding: 2rem; text-align: center; color: #888;">Tabloda gösterilecek satır yok (0 kayıt).</div>`;
        return;
      }

      let html = `<table class="pma-grid"><thead><tr>`;
      if (enableActions) {
        html += `<th style="width: 70px; text-align: center;">Eylemler</th>`;
      }
      columns.forEach(col => {
        const isSorted = sortColumn === col;
        const arrow = isSorted ? (sortDirection === 'asc' ? ' ▲' : ' ▼') : '';
        html += `<th onclick="handleSort('${col}')" title="Sıralamak için tıklayın">${col}${arrow}</th>`;
      });
      html += `</tr></thead><tbody>`;

      rows.forEach((row, rowIdx) => {
        html += `<tr>`;
        if (enableActions) {
          // Identify row identifier if present (id column or first column)
          const firstVal = row[0];
          const firstCol = columns[0];
          html += `<td style="text-align: center;">
            <button class="btn-row-action" title="Satırı Sil" onclick="deleteRow('${firstCol}', '${firstVal}')">🗑️</button>
            <button class="btn-row-action" title="JSON Kopyala" onclick="copyRowJson(${rowIdx})">📋</button>
          </td>`;
        }
        row.forEach(val => {
          html += `<td>${escapeHtml(val)}</td>`;
        });
        html += `</tr>`;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
      container.dataset.cachedRows = JSON.stringify(rows);
      container.dataset.cachedCols = JSON.stringify(columns);
    }

    function copyRowJson(idx) {
      const container = document.getElementById('browseGridContainer');
      const rows = JSON.parse(container.dataset.cachedRows || '[]');
      const cols = JSON.parse(container.dataset.cachedCols || '[]');
      if (rows[idx]) {
        const obj = {};
        cols.forEach((c, i) => { obj[c] = rows[idx][i]; });
        navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
        showToast('✓ Satır JSON olarak kopyalandı');
      }
    }

    async function deleteRow(colName, colVal) {
      if (!confirm(`Bu satırı silmek istediğinize emin misiniz?\n(${colName} = ${colVal})`)) return;
      startProgress();
      try {
        const whereClause = isNaN(colVal) ? `${colName} = '${colVal}'` : `${colName} = ${colVal}`;
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'delete', table: activeTable, where: whereClause })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          loadBrowseData();
          loadTables();
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('Silme işlemi başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 2. Yapı (Structure)
    async function loadStructureData() {
      if (!activeTable) return;
      startProgress();

      try {
        const res = await fetch(`/table_schema?table=${encodeURIComponent(activeTable)}`);
        const data = await res.json();
        currentSchema = data.columns || [];

        document.getElementById('structTableInfo').textContent = `${data.blocks_count || 0} blok • ${(data.rows || 0).toLocaleString()} satır • ${formatBytes(data.bytes || 0)}`;

        const tbody = document.getElementById('structureTableBody');
        tbody.innerHTML = currentSchema.map((col, idx) => `
          <tr>
            <td><b>${idx + 1}</b></td>
            <td><code style="font-weight: 700; color: var(--pma-blue);">${col.name}</code></td>
            <td><span class="table-row-count" style="background:#e0f2fe; color:#0369a1; font-weight:600;">${col.type}</span></td>
            <td>${col.nullable ? 'Evet' : 'Hayır'}</td>
            <td>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="promptRenameColumn('${col.name}')">✏️ Yeniden Adlandır</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px; color: var(--pma-danger);" onclick="handleDropColumn('${col.name}')">🗑️ Sil</button>
            </td>
          </tr>
        `).join('');
      } catch (err) {
        console.error('Failed to load structure:', err);
      } finally {
        endProgress();
      }
    }

    async function handleAddColumn() {
      const name = document.getElementById('newColName').value.trim();
      const type = document.getElementById('newColType').value;
      const defVal = document.getElementById('newColDefault').value.trim();

      if (!name) return alert('Lütfen sütun adını girin');
      startProgress();

      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'add_column',
            table: activeTable,
            name: name,
            type: type,
            default: defVal || null
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          document.getElementById('newColName').value = '';
          document.getElementById('newColDefault').value = '';
          loadStructureData();
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('Sütun ekleme başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function promptRenameColumn(oldName) {
      const newName = prompt(`'${oldName}' sütununun yeni adını girin:`, oldName);
      if (!newName || newName === oldName) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'rename_column',
            table: activeTable,
            old_name: oldName,
            new_name: newName
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          loadStructureData();
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('İşlem başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function handleDropColumn(colName) {
      if (!confirm(`'${colName}' sütununu silmek istediğinize emin misiniz?`)) return;
      startProgress();

      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'drop_column', table: activeTable, name: colName })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          loadStructureData();
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('Sütun silme başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 3. SQL Tab
    function setSqlSnippet(type) {
      const t = activeTable || 'table';
      const pure = t.replace(/\.mgdb$/, '');
      const editor = document.getElementById('sqlQueryText');
      switch (type) {
        case 'SELECT *':
          editor.value = `SELECT * FROM ${pure} LIMIT 50;`; break;
        case 'COUNT':
          editor.value = `SELECT COUNT(*) AS total_rows FROM ${pure};`; break;
        case 'WHERE':
          editor.value = `SELECT * FROM ${pure} WHERE id > 0 LIMIT 25;`; break;
        case 'GROUP_BY':
          editor.value = `SELECT category, COUNT(*), AVG(amount) FROM ${pure} GROUP BY category HAVING COUNT(*) > 1;`; break;
        case 'BLOOM':
          editor.value = `SELECT * FROM ${pure} WHERE client = 'TargetClient';`; break;
        case 'JOIN':
          editor.value = `SELECT a.id, a.name, b.amount FROM table_a a INNER JOIN table_b b ON a.id = b.user_id;`; break;
        case 'UPDATE':
          editor.value = `UPDATE ${pure} SET status = 'ACTIVE' WHERE id = 1;`; break;
        case 'DELETE':
          editor.value = `DELETE FROM ${pure} WHERE id = 999;`; break;
      }
      editor.focus();
    }

    async function runSqlQuery() {
      const sql = document.getElementById('sqlQueryText').value.trim();
      if (!sql) return alert('Lütfen çalıştırılacak SQL sorgusunu yazın');

      startProgress();
      const tele = document.getElementById('sqlExecutionTelemetry');
      const resContainer = document.getElementById('sqlResultContainer');

      try {
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: sql, active_table: activeTable })
        });
        const data = await res.json();

        if (!data.success) {
          tele.style.display = 'none';
          resContainer.style.display = 'block';
          resContainer.innerHTML = `<div style="padding: 1rem; color: var(--pma-danger); font-family: var(--font-code);"><b>Hata:</b><br>${data.error}</div>`;
          return;
        }

        const stats = data.stats || {};
        document.getElementById('sqlTime').textContent = `${stats.execution_time_ms || 0} ms`;
        document.getElementById('sqlRowsCount').textContent = (data.rows ? data.rows.length : (data.row_count || 0)).toLocaleString();
        document.getElementById('sqlBlocksScanned').textContent = (stats.blocks_scanned || 0);
        document.getElementById('sqlBlocksSkipped').textContent = (stats.blocks_skipped || 0);
        document.getElementById('sqlBytesRead').textContent = formatBytes(stats.bytes_read || 0);

        tele.style.display = 'flex';
        resContainer.style.display = 'block';
        renderGridTable(resContainer, data.columns, data.rows, false);
      } catch (err) {
        tele.style.display = 'none';
        resContainer.style.display = 'block';
        resContainer.innerHTML = `<div style="padding: 1rem; color: var(--pma-danger);">Bağlantı Hatası: ${err.message}</div>`;
      } finally {
        endProgress();
      }
    }

    // 4. Ara (Search)
    async function renderSearchInputs() {
      if (!activeTable) return;
      if (currentSchema.length === 0) {
        await loadStructureData();
      }
      const container = document.getElementById('columnFiltersContainer');
      container.innerHTML = currentSchema.map(col => `
        <div class="form-group" style="margin-bottom: 0;">
          <label style="font-family: var(--font-code);">${col.name} (${col.type})</label>
          <input type="text" class="search-col-input" data-col="${col.name}" placeholder="Değer...">
        </div>
      `).join('');
    }

    async function executeSearchFullText() {
      const term = document.getElementById('fulltextSearchInput').value.trim();
      if (!term) return alert('Lütfen arama terimi girin');

      startProgress();
      try {
        if (currentSchema.length === 0) await loadStructureData();
        const strCols = currentSchema.filter(c => c.type === 'STRING').map(c => c.name);
        if (strCols.length === 0) {
          alert('Bu tabloda metin (STRING) türünde aranabilir sütun bulunamadı.');
          return;
        }

        const pure = activeTable.replace(/\.mgdb$/, '');
        const conditions = strCols.map(c => `${c} LIKE '%${term}%'`).join(' OR ');
        const sql = `SELECT * FROM ${pure} WHERE ${conditions} LIMIT 100;`;

        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: sql, active_table: activeTable })
        });
        const data = await res.json();
        const container = document.getElementById('searchResultContainer');
        container.style.display = 'block';
        renderGridTable(container, data.columns, data.rows, false);
      } catch (err) {
        alert('Arama başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function executeSearchColumns() {
      const inputs = document.querySelectorAll('.search-col-input');
      const conditions = [];
      inputs.forEach(inp => {
        const val = inp.value.trim();
        const col = inp.dataset.col;
        if (val) {
          if (isNaN(val)) conditions.push(`${col} = '${val}'`);
          else conditions.push(`${col} = ${val}`);
        }
      });

      if (conditions.length === 0) return alert('Lütfen en az bir sütun için arama değeri girin');

      startProgress();
      try {
        const pure = activeTable.replace(/\.mgdb$/, '');
        const sql = `SELECT * FROM ${pure} WHERE ${conditions.join(' AND ')} LIMIT 100;`;
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: sql, active_table: activeTable })
        });
        const data = await res.json();
        const container = document.getElementById('searchResultContainer');
        container.style.display = 'block';
        renderGridTable(container, data.columns, data.rows, false);
      } catch (err) {
        alert('Filtreleme başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 5. Ekle (Insert)
    async function renderInsertInputs() {
      if (!activeTable) return;
      if (currentSchema.length === 0) {
        await loadStructureData();
      }
      const container = document.getElementById('insertFieldsContainer');
      container.innerHTML = currentSchema.map(col => {
        let inputField = '';
        if (col.type === 'BOOL') {
          inputField = `<select name="${col.name}"><option value="true">True</option><option value="false">False</option></select>`;
        } else if (col.type === 'INT64') {
          inputField = `<input type="number" step="1" name="${col.name}" placeholder="örn: 100">`;
        } else if (col.type === 'FLOAT64') {
          inputField = `<input type="number" step="any" name="${col.name}" placeholder="örn: 49.99">`;
        } else {
          inputField = `<input type="text" name="${col.name}" placeholder="Metin girin...">`;
        }
        return `
          <div class="form-group" style="margin-bottom: 0;">
            <label>${col.name} <span style="font-weight:normal; color:#888;">(${col.type})</span></label>
            ${inputField}
          </div>
        `;
      }).join('');
    }

    async function handleInsertRow(e) {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);
      const rowObj = {};

      currentSchema.forEach(col => {
        let raw = formData.get(col.name);
        if (raw !== null && raw !== '') {
          if (col.type === 'INT64') rowObj[col.name] = parseInt(raw);
          else if (col.type === 'FLOAT64') rowObj[col.name] = parseFloat(raw);
          else if (col.type === 'BOOL') rowObj[col.name] = (raw === 'true' || raw === '1');
          else rowObj[col.name] = raw;
        }
      });

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'insert', table: activeTable, row: rowObj })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          form.reset();
          loadTables();
          if (confirm('Satır başarıyla eklendi! Gözat sekmesine geçip yeni satırı görmek ister misiniz?')) {
            switchTab('browse');
          }
        } else {
          alert('Ekleme Hatası: ' + data.error);
        }
      } catch (err) {
        alert('İşlem başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 6. Dışa Aktar (Export)
    function executeExportDownload() {
      if (!activeTable) return alert('Lütfen aktif bir tablo seçin');
      const fmt = document.getElementById('exportFormatSelect').value;
      window.location.href = `/export?table=${encodeURIComponent(activeTable)}&format=${fmt}`;
      showToast('📥 ' + activeTable + ' ' + fmt.toUpperCase() + ' olarak indiriliyor...');
    }

    // 7. İçe Aktar (Import)
    async function executeImportData() {
      const target = document.getElementById('importTargetTable').value.trim();
      const fmt = document.getElementById('importFormatSelect').value;
      const fileInp = document.getElementById('importFileInput');
      const textInp = document.getElementById('importContentText').value.trim();
      const statusEl = document.getElementById('importResultStatus');

      if (!target) return alert('Lütfen hedef tablo adını girin');

      let content = '';
      if (fileInp.files.length > 0) {
        content = await fileInp.files[0].text();
      } else if (textInp) {
        content = textInp;
      } else {
        return alert('Lütfen bir dosya seçin veya içeriği metin kutusuna yapıştırın');
      }

      startProgress();
      statusEl.style.color = '#333';
      statusEl.textContent = 'İçe aktarılıyor...';

      try {
        const res = await fetch('/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ table: target, format: fmt, content: content })
        });
        const data = await res.json();

        if (data.success) {
          statusEl.style.color = 'var(--pma-success)';
          statusEl.textContent = `✓ Başarılı: ${data.rows_imported.toLocaleString()} satır aktarıldı (${data.execution_time_ms} ms)`;
          showToast('✓ İçe aktarma tamamlandı');
          loadTables();
          setActiveTable(target.endsWith('.mgdb') ? target : target + '.mgdb');
        } else {
          statusEl.style.color = 'var(--pma-danger)';
          statusEl.textContent = `Hata: ${data.error}`;
        }
      } catch (err) {
        statusEl.style.color = 'var(--pma-danger)';
        statusEl.textContent = `Bağlantı Hatası: ${err.message}`;
      } finally {
        endProgress();
      }
    }

    // 8. İşlemler (Operations)
    async function handleRenameTable() {
      const newName = document.getElementById('opNewTableName').value.trim();
      if (!newName) return alert('Lütfen yeni tablo adını girin');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'rename', table: activeTable, new_name: newName })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          document.getElementById('opNewTableName').value = '';
          loadTables();
          setActiveTable(newName.endsWith('.mgdb') ? newName : newName + '.mgdb');
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('İşlem başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function handleTruncateTable() {
      if (!confirm(`DİKKAT: '${activeTable}' tablosundaki TÜM veriler silinecek!\nDevam etmek istiyor musunuz?`)) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'truncate', table: activeTable })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          loadBrowseData();
          loadTables();
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('İşlem başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function handleDropTable() {
      if (!confirm(`DİKKAT: '${activeTable}' tablosu ve dosyası KALICI OLARAK silinecek!\nBu işlem geri alınamaz!`)) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'drop', table: activeTable })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          activeTable = '';
          loadTables();
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('İşlem başarısız: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // Modal Create Table
    function openNewTableModal() {
      document.getElementById('newTableModal').style.display = 'flex';
    }
    function closeNewTableModal() {
      document.getElementById('newTableModal').style.display = 'none';
    }
    async function submitCreateNewTable() {
      const name = document.getElementById('modalNewTableName').value.trim();
      const col1Name = document.getElementById('modalColName1').value.trim();
      const col1Type = document.getElementById('modalColType1').value;
      const col2Name = document.getElementById('modalColName2').value.trim();
      const col2Type = document.getElementById('modalColType2').value;

      if (!name) return alert('Lütfen tablo adını girin');
      if (!col1Name) return alert('En az bir sütun adı gereklidir');

      const columns = [{ name: col1Name, type: col1Type }];
      if (col2Name) columns.push({ name: col2Name, type: col2Type });

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'create_table', table: name, columns: columns })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ ' + data.message);
          closeNewTableModal();
          await loadTables();
          setActiveTable(name.endsWith('.mgdb') ? name : name + '.mgdb');
        } else {
          alert('Hata: ' + data.error);
        }
      } catch (err) {
        alert('Tablo oluşturulamadı: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 9. Sunucu Durumu & Canlı Donanım Testi (Benchmark)
    async function loadServerStatus() {
      try {
        const res = await fetch('/status');
        const st = await res.json();
        document.getElementById('statCpu').textContent = st.cpu || 'Algılanamadı';
        document.getElementById('statRam').textContent = st.ram_gb ? `${st.ram_gb} GB` : 'Bilinmiyor';
        document.getElementById('statOs').textContent = st.os || 'OS';
        document.getElementById('statVer').textContent = `v${st.version || st.engine_version || '__MERGEN_VERSION__'}`;
        document.getElementById('headerStatusText').textContent = `v${st.version || '__MERGEN_VERSION__'} Çevrimiçi`;
      } catch (e) {
        console.error('Status fetch error:', e);
      }
    }

    async function runLiveHardwareBenchmark() {
      startProgress();
      showToast('⏳ Canlı donanım hız testi çalıştırılıyor...');

      try {
        const res = await fetch('/status?benchmark=1');
        const data = await res.json();
        const b = data.benchmark;

        if (b) {
          document.getElementById('liveBenchCard').style.display = 'block';
          document.getElementById('benchIngest').textContent = `~${Number(b.ingest_rate).toLocaleString()} satır/sn`;
          document.getElementById('benchImport').textContent = `~${Number(b.import_rate).toLocaleString()} satır/sn`;
          document.getElementById('benchExport').textContent = `~${Number(b.export_rate).toLocaleString()} satır/sn`;
          document.getElementById('benchScan').textContent = `~${Number(b.scan_rate).toLocaleString()} satır/sn`;
          document.getElementById('benchTier').textContent = b.tier;
          document.getElementById('benchBlock').textContent = b.rec_block;
          showToast('✓ Hız testi tamamlandı!');
        } else {
          alert('Benchmark verisi alınamadı.');
        }
      } catch (err) {
        alert('Benchmark hatası: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 10. Kılavuz (Docs)
    function switchDocLang(lang) {
      document.querySelectorAll('.doc-lang-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.lang === lang);
      });
      document.querySelectorAll('.doc-pane').forEach(p => {
        p.style.display = (p.id === 'doc-pane-' + lang) ? 'block' : 'none';
      });
    }

    function copySnippet(id) {
      const text = document.getElementById(id).textContent;
      navigator.clipboard.writeText(text);
      showToast('✓ Kod panoya kopyalandı');
    }

    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  </script>
</body>
</html>
"""

try:
    from mergendb import __version__ as _version
except Exception:
    _version = "0.6.2"

STUDIO_HTML = STUDIO_HTML.replace("__MERGEN_VERSION__", _version)

