"""
Mergen Studio: Zero-dependency, fast, lightweight management Web UI for MergenDB.
Served by `mergen serve` or `mergendb-server` at http://localhost:8765/studio.
"""

STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MergenDB Studio</title>
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
      line-height: 1.5;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* Top Slim Progress Bar */
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

    /* Header */
    header {
      background: var(--pma-header-bg);
      color: #ffffff;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
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
      object-fit: cover;
      border-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.5px;
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
      gap: 10px;
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
    .lang-select {
      background: #ffffff;
      color: #222;
      border: 1px solid #aaa;
      padding: 3px 6px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-icon {
      background: rgba(255, 255, 255, 0.15);
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: #ffffff;
      padding: 3px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .btn-icon:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    /* Layout */
    .main-wrapper {
      display: flex;
      flex: 1;
      height: calc(100vh - 44px);
      overflow: hidden;
    }

    /* Sidebar */
    aside {
      width: 250px;
      background: #ffffff;
      border-right: 1px solid var(--pma-border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .sidebar-header {
      padding: 8px 10px;
      background: var(--pma-light-blue);
      border-bottom: 1px solid var(--pma-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .sidebar-header .btn-icon {
      background: #ffffff;
      color: var(--pma-blue);
      border: 1px solid var(--pma-border);
      font-weight: 600;
    }
    .sidebar-header .btn-icon:hover {
      background: #f0f4f8;
    }
    .sidebar-filter {
      padding: 6px 10px;
      border-bottom: 1px solid #eee;
    }
    .sidebar-filter input {
      width: 100%;
      padding: 4px 6px;
      font-size: 12px;
      border: 1px solid #ccc;
      border-radius: 3px;
    }
    .table-list {
      flex: 1;
      overflow-y: auto;
      padding: 4px 0;
    }
    .table-item {
      padding: 6px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      color: var(--pma-text);
      text-decoration: none;
      border-bottom: 1px solid #f9f9f9;
      font-size: 12px;
    }
    .table-item:hover {
      background: var(--pma-light-blue);
      color: var(--pma-blue);
    }
    .table-item.active {
      background: #d9e7f5;
      color: var(--pma-dark-blue);
      font-weight: 700;
      border-left: 3px solid var(--pma-blue);
    }
    .table-row-count {
      font-size: 11px;
      color: #666;
      background: #eee;
      padding: 1px 5px;
      border-radius: 10px;
    }

    /* Content Area */
    main.content-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: #fdfdfd;
    }

    /* Navigation Tabs */
    nav.pma-tabs {
      background: #e9eef2;
      border-bottom: 1px solid var(--pma-border);
      display: flex;
      padding: 6px 12px 0 12px;
      gap: 4px;
      overflow-x: auto;
      user-select: none;
    }
    .pma-tab {
      padding: 6px 14px;
      background: #dde5ed;
      border: 1px solid var(--pma-border);
      border-bottom: none;
      border-radius: 4px 4px 0 0;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      color: #333333;
      white-space: nowrap;
      transition: background 0.1s;
    }
    .pma-tab:hover {
      background: #edf3f8;
      color: var(--pma-blue);
    }
    .pma-tab.active {
      background: #ffffff;
      color: var(--pma-blue);
      border-top: 2px solid var(--pma-blue);
      margin-bottom: -1px;
      padding-bottom: 7px;
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

    /* Cards & Toolbars */
    .card-box {
      background: #ffffff;
      border: 1px solid var(--pma-border);
      border-radius: 4px;
      padding: 14px 16px;
      margin-bottom: 14px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .card-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--pma-blue);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #edf2f7;
      padding-bottom: 6px;
    }
    .toolbar-box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      padding: 8px 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .pagination-controls {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .pagination-controls button {
      background: #ffffff;
      border: 1px solid #ccd5df;
      padding: 3px 8px;
      border-radius: 3px;
      font-size: 12px;
      cursor: pointer;
      font-weight: 600;
    }
    .pagination-controls button:hover:not(:disabled) {
      background: #f1f5f9;
      border-color: var(--pma-blue);
    }
    .pagination-controls button:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .page-input {
      width: 44px;
      text-align: center;
      padding: 2px 4px;
      font-size: 12px;
      border: 1px solid #ccd5df;
      border-radius: 3px;
    }

    /* Data Tables */
    .table-container {
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--pma-table-border);
      background: #ffffff;
      border-radius: 3px;
    }
    table.pma-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }
    table.pma-grid th {
      background: #e9eef4;
      color: #333333;
      font-weight: 700;
      padding: 7px 10px;
      border: 1px solid var(--pma-table-border);
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }
    table.pma-grid th:hover {
      background: #dce5ee;
      color: var(--pma-blue);
    }
    table.pma-grid td {
      padding: 6px 10px;
      border: 1px solid var(--pma-table-border);
      white-space: nowrap;
      max-width: 320px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    table.pma-grid tr:nth-child(even) {
      background: #fbfcfd;
    }
    table.pma-grid tr:hover {
      background: #eef5fc !important;
    }

    /* Buttons & Inputs */
    .btn-action {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      padding: 5px 12px;
      border-radius: 3px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      color: #333;
    }
    .btn-action:hover {
      background: #f1f5f9;
      border-color: #94a3b8;
    }
    .btn-primary {
      background: var(--pma-blue);
      border: 1px solid var(--pma-dark-blue);
      color: #ffffff;
      padding: 6px 14px;
      border-radius: 3px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-primary:hover {
      background: var(--pma-dark-blue);
    }
    .btn-danger {
      background: #dc3545;
      border: 1px solid #bd2130;
      color: #ffffff;
      padding: 6px 14px;
      border-radius: 3px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-danger:hover {
      background: #c82333;
    }
    .form-group {
      margin-bottom: 12px;
    }
    .form-group label {
      display: block;
      font-weight: 600;
      margin-bottom: 4px;
      font-size: 12px;
      color: #333;
    }
    .form-control {
      width: 100%;
      padding: 6px 8px;
      border: 1px solid #ccc;
      border-radius: 3px;
      font-size: 12px;
      font-family: inherit;
    }
    .form-control:focus {
      outline: none;
      border-color: var(--pma-blue);
      box-shadow: 0 0 0 2px rgba(35, 90, 129, 0.2);
    }
    textarea.form-control {
      font-family: var(--font-code);
      resize: vertical;
    }

    /* Toast Notification */
    #toastNotification {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #235a81;
      color: #ffffff;
      padding: 10px 16px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      box-shadow: 0 3px 10px rgba(0,0,0,0.25);
      z-index: 10000;
      display: none;
      animation: fadeIn 0.2s;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* Modals */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.4);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9990;
    }
    .modal-card {
      background: #ffffff;
      border-radius: 5px;
      width: 520px;
      max-width: 95%;
      box-shadow: 0 5px 20px rgba(0,0,0,0.3);
      overflow: hidden;
      animation: fadeIn 0.15s ease-out;
    }
    .modal-header {
      background: var(--pma-header-bg);
      color: #ffffff;
      padding: 10px 14px;
      font-weight: 700;
      font-size: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-close {
      cursor: pointer;
      font-size: 16px;
      color: #ffffff;
      opacity: 0.8;
      border: none;
      background: none;
    }
    .modal-close:hover { opacity: 1; }
    .modal-body {
      padding: 16px;
      max-height: 70vh;
      overflow-y: auto;
    }
    .modal-footer {
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      padding: 10px 14px;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

    /* Documentation code blocks */
    .doc-lang-tabs {
      display: flex;
      gap: 6px;
      margin-bottom: 12px;
      border-bottom: 1px solid #ddd;
      padding-bottom: 6px;
    }
    .doc-lang-tab {
      padding: 5px 12px;
      border: 1px solid #ccc;
      background: #f1f5f9;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }
    .doc-lang-tab.active {
      background: var(--pma-blue);
      color: #ffffff;
      border-color: var(--pma-dark-blue);
    }
    .code-box {
      position: relative;
      background: #1e293b;
      color: #f8fafc;
      padding: 14px 16px;
      border-radius: 4px;
      font-family: var(--font-code);
      font-size: 12px;
      line-height: 1.5;
      overflow-x: auto;
    }
    .btn-copy-code {
      position: absolute;
      top: 10px;
      right: 10px;
      background: #334155;
      color: #ffffff;
      border: 1px solid #475569;
      padding: 3px 8px;
      border-radius: 3px;
      font-size: 11px;
      cursor: pointer;
    }
    .btn-copy-code:hover {
      background: #475569;
    }
  </style>
</head>
<body>

  <!-- Top Progress Bar -->
  <div id="topProgressBar"></div>

  <!-- Header -->
  <header>
    <div class="brand-section">
      <img src="/logo.png" alt="MergenDB" class="brand-logo-img" onerror="this.style.display='none'">
      <span class="brand-title">MergenDB</span>
    </div>

    <!-- Active Database & Table Breadcrumbs -->
    <div class="header-center">
      <span>Host: <b>127.0.0.1</b></span>
      <span>/</span>
      <span data-i18n="db_label">DB:</span>
      <select id="activeDbSelect" onchange="changeActiveDatabase(this.value)" style="padding: 2px 6px; font-size: 11px; font-weight: 600; border: 1px solid #ccc; border-radius: 3px;">
        <option value="default">default</option>
      </select>
      <span>/</span>
      <span data-i18n="active_table_label">Table:</span>
      <select id="activeTableSelect" onchange="changeActiveTable(this.value)" style="padding: 2px 6px; font-size: 11px; font-weight: 600; border: 1px solid #ccc; border-radius: 3px;">
        <option value="" data-i18n="select_table_option">(Select Table)</option>
      </select>
    </div>

    <div class="header-right">
      <div class="status-badge">
        <div class="status-dot"></div>
        <span id="headerStatusText">v__MERGEN_VERSION__ Online</span>
      </div>
      <select id="langSelect" onchange="setLanguage(this.value)" class="lang-select">
        <option value="en" selected>English</option>
        <option value="de">Deutsch</option>
        <option value="tr">Türkçe</option>
      </select>
      <button class="btn-icon" onclick="switchTab('status')" data-i18n="nav_server">Server</button>
      <button class="btn-icon" onclick="switchTab('docs')" data-i18n="nav_docs">Docs</button>
    </div>
  </header>

  <!-- Main Application Wrapper -->
  <div class="main-wrapper">

    <!-- Sidebar: Hierarchical Databases, Tables & Sub-tables Tree -->
    <aside>
      <div class="sidebar-header" style="display: flex; gap: 4px; flex-wrap: wrap;">
        <button class="btn-icon" onclick="openNewDbModal()" data-i18n="new_db_btn" style="flex: 1; padding: 4px 6px; font-size: 11px; text-align: center;">+ DB</button>
        <button class="btn-icon" onclick="openNewTableModal()" data-i18n="new_table_btn" style="flex: 1; padding: 4px 6px; font-size: 11px; text-align: center;">+ Table</button>
        <button class="btn-icon" onclick="openNewSubtableModal()" data-i18n="new_subtable_btn" style="flex: 1; padding: 4px 6px; font-size: 11px; text-align: center;">+ Sub</button>
        <button class="btn-icon" onclick="loadTables()" data-i18n="refresh_btn" title="Refresh" style="padding: 4px 8px; font-size: 11px;">R</button>
      </div>
      <div class="sidebar-filter">
        <input type="text" id="sidebarFilter" placeholder="Filter tables..." data-i18n-placeholder="filter_tables_ph" oninput="filterTables()">
      </div>
      <div class="table-list" id="sidebarTableList">
        <!-- Rendered via JavaScript: Hierarchical Tree -->
      </div>
    </aside>

    <!-- Content Area & Navigation Tabs -->
    <main class="content-area">

      <!-- Navigation Tabs -->
      <nav class="pma-tabs">
        <div class="pma-tab active" data-tab="browse" onclick="switchTab('browse')" data-i18n="tab_browse">Browse</div>
        <div class="pma-tab" data-tab="structure" onclick="switchTab('structure')" data-i18n="tab_structure">Structure</div>
        <div class="pma-tab" data-tab="sql" onclick="switchTab('sql')" data-i18n="tab_sql">SQL</div>
        <div class="pma-tab" data-tab="search" onclick="switchTab('search')" data-i18n="tab_search">Search</div>
        <div class="pma-tab" data-tab="insert" onclick="switchTab('insert')" data-i18n="tab_insert">Insert</div>
        <div class="pma-tab" data-tab="export" onclick="switchTab('export')" data-i18n="tab_export">Export</div>
        <div class="pma-tab" data-tab="import" onclick="switchTab('import')" data-i18n="tab_import">Import</div>
        <div class="pma-tab" data-tab="operations" onclick="switchTab('operations')" data-i18n="tab_operations">Operations</div>
        <div class="pma-tab" data-tab="status" onclick="switchTab('status')" data-i18n="tab_status">Server & Benchmark</div>
        <div class="pma-tab" data-tab="docs" onclick="switchTab('docs')" data-i18n="tab_docs">Docs & Ecosystem</div>
      </nav>

      <!-- Tab Panes -->
      <div class="tab-content">

        <!-- 1. BROWSE TAB -->
        <div class="tab-pane active" id="pane-browse">
          <div class="toolbar-box">
            <div class="pagination-controls">
              <button id="btnFirst" onclick="changePage(1)" data-i18n="page_first">« First</button>
              <button id="btnPrev" onclick="changePage(currentPage - 1)" data-i18n="page_prev">‹ Prev</button>
              <span style="font-size: 12px; margin: 0 4px;" data-i18n="page_label">Page:</span>
              <input type="number" id="pageNumberInput" class="page-input" value="1" min="1" onchange="changePage(parseInt(this.value))">
              <span id="pageTotalText" style="font-size: 12px; color: #666;">/ 1</span>
              <button id="btnNext" onclick="changePage(currentPage + 1)" data-i18n="page_next">Next ›</button>
              <button id="btnLast" onclick="changePage(totalPages)" data-i18n="page_last">Last »</button>

              <span style="margin-left: 12px; font-size: 12px;" data-i18n="rows_label">Rows:</span>
              <select id="limitSelect" onchange="pageLimit = parseInt(this.value); changePage(1);" style="padding: 2px 4px; font-size: 12px;">
                <option value="25">25</option>
                <option value="50" selected>50</option>
                <option value="100">100</option>
                <option value="250">250</option>
              </select>
            </div>

            <div id="browseInfoText" style="font-size: 12px; color: var(--pma-text-muted);" data-i18n="loading_table">
              Loading table...
            </div>

            <div>
              <button class="btn-action" onclick="loadBrowseData()" data-i18n="refresh_btn">Refresh</button>
            </div>
          </div>

          <div class="table-container" id="browseGridContainer">
            <!-- Rendered via JavaScript -->
          </div>
        </div>

        <!-- 2. STRUCTURE TAB -->
        <div class="tab-pane" id="pane-structure">
          <div class="card-box">
            <div class="card-title">
              <span data-i18n="table_columns_title">Table Schema & Columns</span>
              <span id="structTableInfo" style="font-size: 12px; font-weight: normal; color: #666;">-</span>
            </div>
            <div class="table-container">
              <table class="pma-grid" id="structureTable">
                <thead>
                  <tr>
                    <th style="width: 40px;">#</th>
                    <th data-i18n="col_name">Column Name</th>
                    <th data-i18n="col_type">Data Type</th>
                    <th data-i18n="col_nullable">Nullable</th>
                    <th data-i18n="col_actions">Actions</th>
                  </tr>
                </thead>
                <tbody id="structureTableBody">
                  <!-- Rendered via JavaScript -->
                </tbody>
              </table>
            </div>
          </div>

          <!-- Add Column Box -->
          <div class="card-box">
            <div class="card-title" data-i18n="add_column_title">Add Column</div>
            <div style="display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap;">
              <div class="form-group" style="margin-bottom:0; flex:1; min-width: 150px;">
                <label data-i18n="new_col_name">Column Name</label>
                <input type="text" id="newColName" class="form-control" placeholder="e.g. status">
              </div>
              <div class="form-group" style="margin-bottom:0; width: 140px;">
                <label data-i18n="new_col_type">Data Type</label>
                <select id="newColType" class="form-control">
                  <option value="INT">INT (Integer)</option>
                  <option value="BIGINT">BIGINT (64-bit)</option>
                  <option value="FLOAT">FLOAT</option>
                  <option value="DOUBLE">DOUBLE</option>
                  <option value="TEXT" selected>TEXT (String)</option>
                  <option value="BOOLEAN">BOOLEAN</option>
                  <option value="TIMESTAMP">TIMESTAMP</option>
                  <option value="UUID">UUID</option>
                </select>
              </div>
              <div class="form-group" style="margin-bottom:0; flex:1; min-width: 150px;">
                <label data-i18n="new_col_default">Default Value (Optional)</label>
                <input type="text" id="newColDefault" class="form-control" placeholder="NULL or default value">
              </div>
              <button class="btn-primary" onclick="handleAddColumn()" style="height: 31px;" data-i18n="btn_add_column">Add Column</button>
            </div>
          </div>
        </div>

        <!-- 3. SQL QUERY TAB -->
        <div class="tab-pane" id="pane-sql">
          <div class="card-box">
            <div class="card-title">
              <span data-i18n="sql_editor_title">SQL & MergenQL Query Console</span>
              <div style="display: flex; gap: 6px;">
                <button class="btn-action" onclick="formatSql()" data-i18n="btn_format">Format</button>
                <button class="btn-action" onclick="clearSql()" data-i18n="btn_clear">Clear</button>
              </div>
            </div>

            <!-- Quick Template Shortcuts -->
            <div style="margin-bottom: 8px; display: flex; gap: 6px; flex-wrap: wrap;">
              <span style="font-size: 11px; font-weight: 700; color: #666; align-self: center;" data-i18n="templates_label">Templates:</span>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('select_all')">SELECT *</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('count')">COUNT(*)</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('where')">WHERE Filter</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('group_by')">GROUP BY + HAVING</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('bloom')">Bloom Scan</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('join')">Hash JOIN</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('update')">UPDATE</button>
              <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="insertSqlTemplate('delete')">DELETE</button>
            </div>

            <textarea id="sqlQueryText" class="form-control" style="height: 120px; font-size: 13px; line-height: 1.4;" placeholder="SELECT * FROM table.mgdb LIMIT 20;"></textarea>

            <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 11px; color: #666;" data-i18n="ctrl_enter_hint">Press Ctrl+Enter to execute query</span>
              <button class="btn-primary" onclick="executeSql()" style="padding: 7px 18px;" data-i18n="btn_run_query">Run Query (Ctrl+Enter)</button>
            </div>
          </div>

          <!-- Query Execution Stats & Results -->
          <div id="queryStatsBox" style="display: none; background: #eef6fc; border: 1px solid #bce0fd; border-radius: 4px; padding: 8px 12px; margin-bottom: 12px; font-size: 12px;">
            <!-- Rendered via JavaScript -->
          </div>

          <div class="table-container" id="queryGridContainer">
            <!-- Results rendered here -->
          </div>
        </div>

        <!-- 4. SEARCH (FIND) TAB -->
        <div class="tab-pane" id="pane-search">
          <div class="card-box">
            <div class="card-title" data-i18n="search_fulltext_title">Full-Text Substring Search</div>
            <p style="font-size: 12px; color: #666; margin-bottom: 10px;" data-i18n="search_fulltext_desc">
              Performs rapid case-insensitive substring search across all string/text columns in the table.
            </p>
            <div style="display: flex; gap: 8px;">
              <input type="text" id="fullTextSearchInput" class="form-control" placeholder="Search term..." data-i18n-placeholder="search_term_ph">
              <button class="btn-primary" onclick="executeFullTextSearch()" data-i18n="btn_search">Search</button>
              <button class="btn-action" onclick="document.getElementById('fullTextSearchInput').value=''; executeFullTextSearch();" data-i18n="btn_reset">Reset</button>
            </div>
          </div>

          <div class="card-box">
            <div class="card-title" data-i18n="search_field_title">Filter by Exact Column Values</div>
            <div id="fieldFilterContainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin-bottom: 12px;">
              <!-- Generated from schema -->
            </div>
            <button class="btn-primary" onclick="executeFieldSearch()" data-i18n="btn_filter">Apply Filters</button>
          </div>

          <div class="table-container" id="searchGridContainer">
            <!-- Results rendered here -->
          </div>
        </div>

        <!-- 5. INSERT TAB -->
        <div class="tab-pane" id="pane-insert">
          <div class="card-box">
            <div class="card-title" data-i18n="insert_title">Insert New Record</div>
            <p style="font-size: 12px; color: #666; margin-bottom: 14px;" data-i18n="insert_desc">
              Fill in the field values according to table schema to append a new row into the active .mgdb table.
            </p>
            <form id="insertRecordForm" onsubmit="event.preventDefault(); handleInsertRecord();">
              <div id="insertFieldsContainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; margin-bottom: 16px;">
                <!-- Generated dynamically from table schema -->
              </div>
              <div style="display: flex; gap: 10px;">
                <button type="submit" class="btn-primary" data-i18n="btn_save_record">Save Record</button>
                <button type="button" class="btn-action" onclick="document.getElementById('insertRecordForm').reset()" data-i18n="btn_clear">Clear Form</button>
              </div>
            </form>
          </div>
        </div>

        <!-- 6. EXPORT TAB -->
        <div class="tab-pane" id="pane-export">
          <div class="card-box">
            <div class="card-title" data-i18n="export_title">Export Table Data</div>
            <p style="font-size: 12px; color: #666; margin-bottom: 16px;" data-i18n="export_desc">
              Stream and export columnar table data into standard portable file formats.
            </p>

            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
              <div style="border: 1px solid #ccd8e4; border-radius: 4px; padding: 12px; background: #fdfdfd;">
                <div style="font-weight: 700; margin-bottom: 4px;">CSV (Comma-Separated)</div>
                <p style="font-size: 11px; color: #666; margin-bottom: 10px;">Universal tabular data format compatible with Excel and Pandas.</p>
                <button class="btn-action" onclick="triggerDirectDownload('csv')" data-i18n="btn_download_csv">Download CSV</button>
              </div>

              <div style="border: 1px solid #ccd8e4; border-radius: 4px; padding: 12px; background: #fdfdfd;">
                <div style="font-weight: 700; margin-bottom: 4px;">JSON (Records Array)</div>
                <p style="font-size: 11px; color: #666; margin-bottom: 10px;">Array of key-value JSON objects for web applications.</p>
                <button class="btn-action" onclick="triggerDirectDownload('json')" data-i18n="btn_download_json">Download JSON</button>
              </div>

              <div style="border: 1px solid #ccd8e4; border-radius: 4px; padding: 12px; background: #fdfdfd;">
                <div style="font-weight: 700; margin-bottom: 4px;">JSON Lines (.jsonl)</div>
                <p style="font-size: 11px; color: #666; margin-bottom: 10px;">Streamable newline-delimited JSON format for large pipelines.</p>
                <button class="btn-action" onclick="triggerDirectDownload('jsonl')" data-i18n="btn_download_jsonl">Download JSONL</button>
              </div>

              <div style="border: 1px solid #ccd8e4; border-radius: 4px; padding: 12px; background: #fdfdfd;">
                <div style="font-weight: 700; margin-bottom: 4px;">SQL Dump (.sql)</div>
                <p style="font-size: 11px; color: #666; margin-bottom: 10px;">Complete DDL CREATE TABLE and INSERT statements.</p>
                <button class="btn-action" onclick="triggerDirectDownload('sql')" data-i18n="btn_download_sql">Download SQL</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 7. IMPORT TAB -->
        <div class="tab-pane" id="pane-import">
          <div class="card-box">
            <div class="card-title" data-i18n="import_title">Import Data into MergenDB</div>
            <p style="font-size: 12px; color: #666; margin-bottom: 14px;" data-i18n="import_desc">
              Ingest multi-megabyte CSV datasets or SQL dumps directly into compressed columnar storage with low memory overhead.
            </p>

            <div class="form-group">
              <label data-i18n="import_format_label">Source Format</label>
              <select id="importFormatSelect" class="form-control" style="width: 200px;">
                <option value="csv">CSV (Comma-Separated)</option>
                <option value="sql">SQL Dump (CREATE + INSERT)</option>
              </select>
            </div>

            <div class="form-group">
              <label data-i18n="import_file_label">Upload File</label>
              <input type="file" id="importFileInput" class="form-control" accept=".csv,.sql,.txt">
            </div>

            <div class="form-group">
              <label data-i18n="import_paste_label">Or Paste Content Directly</label>
              <textarea id="importPasteContent" class="form-control" style="height: 120px;" placeholder="Paste CSV lines or SQL INSERT statements here..."></textarea>
            </div>

            <div id="importProgressContainer" style="display: none; margin-bottom: 14px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 12px;">
              <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; margin-bottom: 6px;">
                <span id="importStatusText" style="color: #334155;">Streaming file to server...</span>
                <span id="importPercentText" style="color: var(--pma-blue);">0%</span>
              </div>
              <div style="background: #e2e8f0; border-radius: 3px; height: 10px; overflow: hidden;">
                <div id="importProgressBarFill" style="background: var(--pma-blue); width: 0%; height: 100%; transition: width 0.1s ease;"></div>
              </div>
            </div>

            <button class="btn-primary" id="btnStartImport" onclick="handleImportSubmit()" data-i18n="btn_start_import">Start Ingestion</button>
          </div>
        </div>

        <!-- 8. OPERATIONS TAB -->
        <div class="tab-pane" id="pane-operations">
          <div class="card-box">
            <div class="card-title" data-i18n="ops_rename_title">Rename Table</div>
            <div style="display: flex; gap: 10px; max-width: 400px;">
              <input type="text" id="renameTableInput" class="form-control" placeholder="New table name (e.g. archive_data)">
              <button class="btn-action" onclick="handleRenameTable()" data-i18n="btn_rename">Rename</button>
            </div>
          </div>

          <div class="card-box">
            <div class="card-title" data-i18n="ops_truncate_title">Truncate Table</div>
            <p style="font-size: 12px; color: #666; margin-bottom: 10px;" data-i18n="ops_truncate_desc">
              Clears all rows from the table while preserving schema and column definitions.
            </p>
            <button class="btn-action" style="color: var(--pma-danger);" onclick="handleTruncateTable()" data-i18n="btn_truncate">Truncate Table</button>
          </div>

          <div class="card-box" style="border-color: #fca5a5;">
            <div class="card-title" style="color: var(--pma-danger);" data-i18n="ops_drop_title">Drop Table Permanently</div>
            <p style="font-size: 12px; color: #666; margin-bottom: 10px;" data-i18n="ops_drop_desc">
              Permanently deletes the table and deletes the .mgdb file from disk. This action cannot be undone.
            </p>
            <button class="btn-danger" onclick="handleDropTable()" data-i18n="btn_drop">Drop Table</button>
          </div>
        </div>

        <!-- 9. SERVER & BENCHMARK TAB -->
        <div class="tab-pane" id="pane-status">
          <div class="card-box">
            <div class="card-title">
              <span data-i18n="server_diag_title">System Diagnostics & Hardware Specifications</span>
              <button class="btn-action" onclick="runLiveHardwareBenchmark()" data-i18n="btn_run_bench">Run Live Speed Benchmark</button>
            </div>

            <!-- Hardware Specs Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px;">
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;" data-i18n="stat_cpu">Processor (CPU)</div>
                <div id="statCpu" style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 2px;">Detecting...</div>
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;" data-i18n="stat_ram">System RAM</div>
                <div id="statRam" style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 2px;">Detecting...</div>
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;" data-i18n="stat_os">Operating System</div>
                <div id="statOs" style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 2px;">Detecting...</div>
              </div>
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px;">
                <div style="font-size: 11px; color: #666;" data-i18n="stat_engine_ver">Engine Version</div>
                <div id="statVer" style="font-size: 13px; font-weight: 700; color: var(--pma-blue); margin-top: 2px;">v__MERGEN_VERSION__</div>
              </div>
            </div>

            <!-- Live Benchmark Results Area -->
            <div id="liveBenchCard" style="display: none; background: #eef6fc; border: 1px solid #bce0fd; border-radius: 6px; padding: 16px;">
              <h4 style="color: #0369a1; margin-bottom: 12px; font-size: 14px;" data-i18n="bench_measured_title">Measured Throughput on this Hardware:</h4>
              <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 12px;">
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;" data-i18n="bench_ingest">Sequential Ingestion (Append)</span>
                  <div id="benchIngest" style="font-size: 16px; font-weight: 800; color: #0284c7;">-</div>
                </div>
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;" data-i18n="bench_import">CSV / SQL Streaming Import</span>
                  <div id="benchImport" style="font-size: 16px; font-weight: 800; color: #0284c7;">-</div>
                </div>
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;" data-i18n="bench_export">Table Export</span>
                  <div id="benchExport" style="font-size: 16px; font-weight: 800; color: #0284c7;">-</div>
                </div>
                <div style="background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #cbd5e1;">
                  <span style="font-size: 11px; color: #666;" data-i18n="bench_scan">Analytical Column Scan</span>
                  <div id="benchScan" style="font-size: 16px; font-weight: 800; color: #16a34a;">-</div>
                </div>
              </div>
              <div style="font-size: 12px; color: #334155; line-height: 1.4;">
                <b data-i18n="bench_tier_label">Performance Tier:</b> <span id="benchTier">-</span><br>
                <b data-i18n="bench_block_label">Recommended Block Size:</b> <span id="benchBlock">-</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 10. DOCS & ECOSYSTEM TAB -->
        <div class="tab-pane" id="pane-docs">
          <div class="card-box">
            <div class="card-title">
              <span data-i18n="docs_title">Supported Languages & Ecosystem Guides</span>
            </div>
            <p style="font-size: 12px; color: #666; margin-bottom: 16px;" data-i18n="docs_desc">
              MergenDB provides 100% feature support across Python, Node.js / TypeScript, Shell CLI, and REST API with zero external runtime dependencies.
            </p>

            <div class="doc-lang-tabs">
              <div class="doc-lang-tab active" data-lang="python" onclick="switchDocLang('python')">Python API</div>
              <div class="doc-lang-tab" data-lang="nodejs" onclick="switchDocLang('nodejs')">Node.js / TypeScript</div>
              <div class="doc-lang-tab" data-lang="cli" onclick="switchDocLang('cli')">Mergen CLI</div>
              <div class="doc-lang-tab" data-lang="rest" onclick="switchDocLang('rest')">HTTP / REST (cURL)</div>
            </div>

            <!-- Python Docs -->
            <div id="doc-pane-python" class="doc-pane">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('pythonSnippet')" data-i18n="btn_copy">Copy</button>
<pre id="pythonSnippet"># Install: pip install --upgrade mergendb
import mergendb

# 1. Connect to table (Auto-created if not exists)
db = mergendb.connect("users.mgdb")

# 2. Insert records (Schema is auto-inferred)
db.insert([
    {"id": 1, "name": "Alice", "role": "admin", "score": 95.5, "active": True},
    {"id": 2, "name": "Bob", "role": "developer", "score": 88.0, "active": True},
])

# 3. Fluent Document-Style Queries (Zero boilerplate)
admins = db.find(role="admin", active=True)
alice = db.find_one(name="Alice")
matches = db.search("admin")  # Case-insensitive substring search across all columns

# 4. Standard Analytical SQL
res = db.sql("SELECT role, COUNT(*), AVG(score) FROM users GROUP BY role HAVING COUNT(*) > 0")
res.show()  # Display ASCII table

# 5. Row Mutations
db.update({"score": 99.0}, where="name = 'Alice'")
db.delete(where="active = False")

# 6. Stream Migration
db.export_csv("users.csv")
mergendb.from_csv("users.csv", "users_backup.mgdb")

# 7. Hardware Diagnostics
mergendb.benchmark()</pre>
              </div>
            </div>

            <!-- Node.js / TypeScript Docs -->
            <div id="doc-pane-nodejs" class="doc-pane" style="display: none;">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('nodejsSnippet')" data-i18n="btn_copy">Copy</button>
<pre id="nodejsSnippet">// Install: npm install mergendb
// Zero external dependencies - Runs natively on Node.js standard library
const { connect } = require('mergendb');
// Or TypeScript: import { connect } from 'mergendb';

async function main() {
  const db = connect('http://localhost:8765');

  // 1. Connection Health & Hardware Status
  const isHealthy = await db.ping();
  const status = await db.status();
  console.log(`Connected to MergenDB ${status.version}`);

  // 2. Direct Table Operations
  const users = db.table('users.mgdb');
  await users.insert([
    { id: 1, name: 'Alice', role: 'admin', balance: 1500 },
    { id: 2, name: 'Bob', role: 'engineer', balance: 2400 }
  ]);

  // 3. Full-Text Search
  const matches = await users.search('Ali');

  // 4. Update & Delete
  await users.update({ balance: 1800 }, "name = 'Alice'");
  await users.delete("balance < 1000");

  // 5. Schema Alterations
  await users.addColumn('country', 'TEXT', 'TR');
  await users.renameColumn('country', 'nation');

  // 6. Analytical SQL & Tagged Template Literal
  const res = await db.sql`SELECT nation, COUNT(*), AVG(balance) FROM users GROUP BY nation`;
  console.table(res.rows);

  // 7. Live Hardware Benchmark
  const bench = await db.benchmark();
  console.log(`Scan throughput: ${bench.scan_throughput}`);
}

main().catch(console.error);</pre>
              </div>
            </div>

            <!-- CLI Docs -->
            <div id="doc-pane-cli" class="doc-pane" style="display: none;">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('cliSnippet')" data-i18n="btn_copy">Copy</button>
<pre id="cliSnippet"># 1. Start Interactive Shell
mergen

# Or run directly via Python module:
python -m mergendb

# 2. Start Studio Web Server
mergen serve 8765

# 3. One-Off Query Execution
mergen query "SELECT country, COUNT(*) FROM sales.mgdb GROUP BY country;"

# 4. Ingest External Datasets
mergen import csv telemetry.csv sensors.mgdb
mergen import sql dump.sql production.mgdb

# 5. Export Data
mergen export sensors.mgdb to csv sensors_out.csv
mergen export sensors.mgdb to json sensors_out.json

# 6. Run Hardware Profiler
mergen test</pre>
              </div>
            </div>

            <!-- REST API Docs -->
            <div id="doc-pane-rest" class="doc-pane" style="display: none;">
              <div class="code-box">
                <button class="btn-copy-code" onclick="copySnippet('restSnippet')" data-i18n="btn_copy">Copy</button>
<pre id="restSnippet"># 1. Healthcheck & Hardware Specifications
curl -X GET http://localhost:8765/status

# 2. Analytical SQL Query (POST JSON)
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT role, COUNT(*), AVG(score) FROM users.mgdb GROUP BY role;"}'

# 3. Analytical SQL Query (GET Query Param)
curl "http://localhost:8765/query?q=SELECT+*+FROM+users.mgdb+LIMIT+10"

# 4. Stream Export (CSV, JSON, JSONL, SQL)
curl -X GET "http://localhost:8765/export?table=users.mgdb&format=csv" -o users.csv

# 5. Fast Ingestion (POST File Content)
curl -X POST http://localhost:8765/import \
  -H "Content-Type: application/json" \
  -d '{"table": "telemetry.mgdb", "format": "csv", "content": "id,val\n1,10.5\n2,20.0\n"}'</pre>
              </div>
            </div>
          </div>
        </div>

      </div>
    </main>
  </div>

  <!-- Modal: Create New Database -->
  <div class="modal-overlay" id="modalNewDb">
    <div class="modal-card">
      <div class="modal-header">
        <span data-i18n="modal_new_db_title">Create New Database</span>
        <button class="modal-close" onclick="closeNewDbModal()">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label data-i18n="modal_db_name">Database Name</label>
          <input type="text" id="modalDbNameInput" class="form-control" placeholder="e.g. okul or analytics">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-action" onclick="closeNewDbModal()" data-i18n="btn_cancel">Cancel</button>
        <button class="btn-primary" onclick="submitCreateNewDb()" data-i18n="btn_create_db">Create Database</button>
      </div>
    </div>
  </div>

  <!-- Modal: Create New Table -->
  <div class="modal-overlay" id="modalNewTable">
    <div class="modal-card">
      <div class="modal-header">
        <span data-i18n="modal_new_table_title">Create New Table</span>
        <button class="modal-close" onclick="closeNewTableModal()">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label data-i18n="modal_target_db">Target Database</label>
          <select id="modalTableDbSelect" class="form-control">
            <option value="default">default</option>
          </select>
        </div>
        <div class="form-group">
          <label data-i18n="modal_table_name">Table Name</label>
          <input type="text" id="modalTableNameInput" class="form-control" placeholder="e.g. ogretmenler or ogrenciler">
        </div>
        <div class="form-group">
          <label data-i18n="modal_columns_label">Columns & Types</label>
          <div id="modalColumnsContainer">
            <div style="display: flex; gap: 8px; margin-bottom: 6px;">
              <input type="text" class="form-control col-name-input" placeholder="id" value="id">
              <select class="form-control col-type-input" style="width: 130px;">
                <option value="INT" selected>INT</option>
                <option value="BIGINT">BIGINT</option>
                <option value="TEXT">TEXT</option>
                <option value="FLOAT">FLOAT</option>
                <option value="DOUBLE">DOUBLE</option>
                <option value="BOOLEAN">BOOLEAN</option>
                <option value="TIMESTAMP">TIMESTAMP</option>
              </select>
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 6px;">
              <input type="text" class="form-control col-name-input" placeholder="name" value="name">
              <select class="form-control col-type-input" style="width: 130px;">
                <option value="INT">INT</option>
                <option value="TEXT" selected>TEXT</option>
                <option value="FLOAT">FLOAT</option>
                <option value="BOOLEAN">BOOLEAN</option>
              </select>
            </div>
          </div>
          <button type="button" class="btn-action" style="margin-top: 4px;" onclick="addModalColumnRow('modalColumnsContainer')" data-i18n="btn_add_field">+ Add Column</button>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-action" onclick="closeNewTableModal()" data-i18n="btn_cancel">Cancel</button>
        <button class="btn-primary" onclick="submitCreateNewTable()" data-i18n="btn_create_table">Create Table</button>
      </div>
    </div>
  </div>

  <!-- Modal: Create New Subtable -->
  <div class="modal-overlay" id="modalNewSubtable">
    <div class="modal-card">
      <div class="modal-header">
        <span data-i18n="modal_new_subtable_title">Create Nested Sub-table</span>
        <button class="modal-close" onclick="closeNewSubtableModal()">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label data-i18n="modal_parent_table">Parent Table</label>
          <select id="modalSubtableParentSelect" class="form-control">
            <!-- Populated via JS -->
          </select>
        </div>
        <div class="form-group">
          <label data-i18n="modal_subtable_name">Sub-table Name</label>
          <input type="text" id="modalSubtableNameInput" class="form-control" placeholder="e.g. a_sinifi or 2026_q1">
        </div>
        <div class="form-group">
          <label data-i18n="modal_columns_label">Columns & Types</label>
          <div id="modalSubtableColumnsContainer">
            <div style="display: flex; gap: 8px; margin-bottom: 6px;">
              <input type="text" class="form-control col-name-input" placeholder="id" value="id">
              <select class="form-control col-type-input" style="width: 130px;">
                <option value="INT" selected>INT</option>
                <option value="BIGINT">BIGINT</option>
                <option value="TEXT">TEXT</option>
                <option value="FLOAT">FLOAT</option>
                <option value="DOUBLE">DOUBLE</option>
                <option value="BOOLEAN">BOOLEAN</option>
              </select>
            </div>
          </div>
          <button type="button" class="btn-action" style="margin-top: 4px;" onclick="addModalColumnRow('modalSubtableColumnsContainer')" data-i18n="btn_add_field">+ Add Column</button>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-action" onclick="closeNewSubtableModal()" data-i18n="btn_cancel">Cancel</button>
        <button class="btn-primary" onclick="submitCreateNewSubtable()" data-i18n="btn_create_subtable">Create Sub-table</button>
      </div>
    </div>
  </div>

  <!-- Toast Notification Element -->
  <div id="toastNotification">Action completed</div>

  <script>
    // State
    let activeDatabase = 'default';
    let activeTable = '';
    let currentSchema = [];
    let currentPage = 1;
    let pageLimit = 50;
    let totalRows = 0;
    let totalPages = 1;
    let sortColumn = '';
    let sortDirection = 'asc';
    let currentLang = localStorage.getItem('mergendb_lang') || 'en';
    let currentGridRows = [];
    let currentGridCols = [];
    let databasesCache = [];
    let tablesCache = [];
    let expandedTables = new Set();

    // Progress Bar Indicator
    function startProgress() {
      const bar = document.getElementById('topProgressBar');
      if (bar) {
        bar.style.display = 'block';
        bar.style.width = '35%';
        setTimeout(() => { if (bar.style.display === 'block') bar.style.width = '75%'; }, 100);
      }
    }
    function updateTopProgress(pct) {
      const bar = document.getElementById('topProgressBar');
      if (bar) {
        bar.style.display = 'block';
        bar.style.width = `${Math.min(100, Math.max(5, pct))}%`;
      }
    }
    function endProgress() {
      const bar = document.getElementById('topProgressBar');
      if (bar) {
        bar.style.width = '100%';
        setTimeout(() => {
          bar.style.display = 'none';
          bar.style.width = '0%';
        }, 150);
      }
    }

    // Toast
    function showToast(msg) {
      const toast = document.getElementById('toastNotification');
      if (toast) {
        toast.textContent = msg;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 2400);
      }
    }

    // App Initialization
    window.addEventListener('DOMContentLoaded', async () => {
      setLanguage(currentLang);
      await loadTables();
      await loadServerStatus();

      // Keyboard Shortcut: Ctrl+Enter to run SQL
      const sqlEl = document.getElementById('sqlQueryText');
      if (sqlEl) {
        sqlEl.addEventListener('keydown', (e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            executeSql();
          }
        });
      }
    });

    // Tab Switching
    function switchTab(tabId) {
      document.querySelectorAll('.pma-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      const targetTab = document.querySelector(`.pma-tab[data-tab="${tabId}"]`);
      const targetPane = document.getElementById(`pane-${tabId}`);
      if (targetTab) targetTab.classList.add('active');
      if (targetPane) targetPane.classList.add('active');

      if (tabId === 'browse') loadBrowseData();
      else if (tabId === 'structure') loadStructureData();
      else if (tabId === 'search') setupSearchTab();
      else if (tabId === 'insert') setupInsertForm();
      else if (tabId === 'status') loadServerStatus();
    }

    // Load Databases and Hierarchical Tables Tree
    async function loadTables() {
      startProgress();
      try {
        // 1. Fetch Databases
        const dbRes = await fetch('/databases');
        const dbData = await dbRes.json();
        databasesCache = dbData.databases || [{ name: 'default', tables_count: 0, total_bytes: 0 }];
        if (dbData.active_database && !activeDatabase) {
          activeDatabase = dbData.active_database;
        }

        // Populate Database selectors
        const dbSelect = document.getElementById('activeDbSelect');
        if (dbSelect) {
          dbSelect.innerHTML = databasesCache.map(d => `<option value="${d.name}" ${d.name === activeDatabase ? 'selected' : ''}>${d.name}</option>`).join('');
        }
        const modalDbSel = document.getElementById('modalTableDbSelect');
        if (modalDbSel) {
          modalDbSel.innerHTML = databasesCache.map(d => `<option value="${d.name}" ${d.name === activeDatabase ? 'selected' : ''}>${d.name}</option>`).join('');
        }

        // 2. Fetch Tables
        const res = await fetch('/tables');
        const data = await res.json();
        tablesCache = data.tables || [];

        // Build Tree: Group by Database -> Root Tables -> Sub-tables
        renderSidebarTree();

        // Populate Table Header Select
        populateHeaderTableSelect();

        // Populate Subtable Parent Select
        populateSubtableParentSelect();

        // If no active table selected yet, select first available
        if (!activeTable && tablesCache.length > 0) {
          const firstInDb = tablesCache.find(t => t.database === activeDatabase) || tablesCache[0];
          selectActiveTable(firstInDb.full_name || firstInDb.table, firstInDb.database);
        }
      } catch (err) {
        console.error('Failed to load databases and tables:', err);
      } finally {
        endProgress();
      }
    }

    function renderSidebarTree() {
      const listEl = document.getElementById('sidebarTableList');
      if (!listEl) return;

      const filterVal = (document.getElementById('sidebarFilter') ? document.getElementById('sidebarFilter').value : '').toLowerCase().trim();

      // Group tables by database
      const dbMap = {};
      databasesCache.forEach(d => { dbMap[d.name] = []; });
      if (!dbMap['default']) dbMap['default'] = [];

      tablesCache.forEach(t => {
        const db = t.database || 'default';
        if (!dbMap[db]) dbMap[db] = [];
        dbMap[db].push(t);
      });

      let html = '';
      for (const [dbName, tbls] of Object.entries(dbMap)) {
        // Group tables and their subtables
        const rootTables = tbls.filter(t => t.type !== 'subtable' && !t.parent);
        const subTables = tbls.filter(t => t.type === 'subtable' || t.parent);

        const isCurrentDb = (dbName === activeDatabase);

        html += `
          <div class="db-group-header" style="padding: 6px 8px; background: #e2e8f0; font-weight: 700; font-size: 11px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #cbd5e1; cursor: pointer;" onclick="changeActiveDatabase('${dbName}')">
            <span>[DB] <b>${escapeHtml(dbName)}</b></span>
            <span style="font-size: 10px; background: #cbd5e1; padding: 1px 5px; border-radius: 3px;">${tbls.length} tbls</span>
          </div>
        `;

        if (rootTables.length === 0 && subTables.length === 0) {
          html += `<div style="padding: 6px 14px; font-size: 11px; color: #94a3b8; font-style: italic;">(No tables in database)</div>`;
          continue;
        }

        rootTables.forEach(t => {
          const tName = t.name || t.full_name || t.table.replace('.mgdb', '');
          const fullPath = t.full_name || t.table;
          const childSubs = subTables.filter(s => s.parent === tName || s.full_name.startsWith(tName + '.'));

          const matchesFilter = !filterVal || tName.toLowerCase().includes(filterVal) || childSubs.some(s => s.name.toLowerCase().includes(filterVal));
          if (!matchesFilter) return;

          const isActive = (activeTable === fullPath || activeTable === t.table);
          const hasChildren = childSubs.length > 0;
          const isExpanded = expandedTables.has(fullPath) || hasChildren;

          html += `
            <div class="table-item ${isActive ? 'active' : ''}" style="padding-left: 12px; display: flex; justify-content: space-between; align-items: center;" onclick="selectActiveTable('${fullPath}', '${dbName}')">
              <span style="display: flex; align-items: center; gap: 4px;">
                ${hasChildren ? `<span onclick="event.stopPropagation(); toggleSubtableExpand('${fullPath}')" style="cursor: pointer; font-weight: bold; font-size: 10px; width: 12px;">${isExpanded ? '▼' : '►'}</span>` : '<span style="width: 12px;"></span>'}
                <span style="font-size: 11px; font-weight: 600;">[TBL] ${escapeHtml(tName)}</span>
              </span>
              <span class="table-row-count">${(t.rows || 0).toLocaleString()}</span>
            </div>
          `;

          // Render child sub-tables if expanded
          if (hasChildren && isExpanded) {
            childSubs.forEach(s => {
              const sName = s.name || s.full_name.split('.').pop();
              const sFullPath = s.full_name || s.table;
              const isSubActive = (activeTable === sFullPath);

              html += `
                <div class="table-item ${isSubActive ? 'active' : ''}" style="padding-left: 28px; background: #f8fafc; border-left: 2px solid var(--pma-blue);" onclick="selectActiveTable('${sFullPath}', '${dbName}')">
                  <span style="font-size: 11px; color: #475569;">↳ [SUB] <b>${escapeHtml(sName)}</b></span>
                  <span class="table-row-count" style="background: #e0f2fe; color: #0284c7;">${(s.rows || 0).toLocaleString()}</span>
                </div>
              `;
            });
          }
        });
      }

      listEl.innerHTML = html || `<div style="padding: 12px; color: #888; text-align: center; font-size: 11px;">(No matching tables)</div>`;
    }

    function toggleSubtableExpand(tblPath) {
      if (expandedTables.has(tblPath)) {
        expandedTables.delete(tblPath);
      } else {
        expandedTables.add(tblPath);
      }
      renderSidebarTree();
    }

    function populateHeaderTableSelect() {
      const selectEl = document.getElementById('activeTableSelect');
      if (!selectEl) return;
      const prevVal = activeTable || selectEl.value;
      selectEl.innerHTML = `<option value="">${t('select_table_option')}</option>` +
        tablesCache.map(tbl => {
          const val = tbl.full_name || tbl.table;
          const label = tbl.type === 'subtable' ? `  ↳ ${tbl.full_name}` : tbl.full_name || tbl.table;
          return `<option value="${val}" ${val === prevVal ? 'selected' : ''}>${label}</option>`;
        }).join('');
    }

    function populateSubtableParentSelect() {
      const sel = document.getElementById('modalSubtableParentSelect');
      if (!sel) return;
      const rootTables = tablesCache.filter(t => t.type !== 'subtable');
      sel.innerHTML = rootTables.map(t => {
        const val = t.full_name || t.table.replace('.mgdb', '');
        return `<option value="${val}">${val} (${t.database || 'default'})</option>`;
      }).join('');
    }

    function changeActiveDatabase(dbName) {
      activeDatabase = dbName;
      const dbSel = document.getElementById('activeDbSelect');
      if (dbSel) dbSel.value = dbName;

      // Select first table in this database if current active table is not in it
      const inThisDb = tablesCache.filter(t => (t.database || 'default') === dbName);
      if (inThisDb.length > 0) {
        selectActiveTable(inThisDb[0].full_name || inThisDb[0].table, dbName);
      } else {
        activeTable = '';
        renderSidebarTree();
        populateHeaderTableSelect();
        switchTab('browse');
      }
    }

    function selectActiveTable(fullTableName, dbName) {
      activeTable = fullTableName;
      if (dbName) activeDatabase = dbName;

      const selTable = document.getElementById('activeTableSelect');
      if (selTable) selTable.value = fullTableName;
      const selDb = document.getElementById('activeDbSelect');
      if (selDb && dbName) selDb.value = dbName;

      renderSidebarTree();

      currentPage = 1;
      const activeTab = document.querySelector('.pma-tab.active');
      const tabName = activeTab ? activeTab.dataset.tab : 'browse';
      switchTab(tabName);
    }

    function changeActiveTable(val) {
      if (val) {
        const tbl = tablesCache.find(t => (t.full_name === val || t.table === val));
        selectActiveTable(val, tbl ? tbl.database : activeDatabase);
      }
    }

    function filterTables() {
      renderSidebarTree();
    }

    // Modal Control: New Database
    function openNewDbModal() {
      const el = document.getElementById('modalNewDb');
      if (el) el.classList.add('active');
    }
    function closeNewDbModal() {
      const el = document.getElementById('modalNewDb');
      if (el) el.classList.remove('active');
    }
    async function submitCreateNewDb() {
      const name = document.getElementById('modalDbNameInput').value.trim();
      if (!name) return alert('Please enter database name');
      startProgress();
      try {
        const res = await fetch('/database', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'create', name: name })
        });
        const data = await res.json();
        if (data.success) {
          showToast(`Database '${name}' created`);
          closeNewDbModal();
          document.getElementById('modalDbNameInput').value = '';
          activeDatabase = name;
          await loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Failed to create database: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // Modal Control: New Sub-table
    function openNewSubtableModal() {
      populateSubtableParentSelect();
      const el = document.getElementById('modalNewSubtable');
      if (el) el.classList.add('active');
    }
    function closeNewSubtableModal() {
      const el = document.getElementById('modalNewSubtable');
      if (el) el.classList.remove('active');
    }
    async function submitCreateNewSubtable() {
      const parentTable = document.getElementById('modalSubtableParentSelect').value.trim();
      const subName = document.getElementById('modalSubtableNameInput').value.trim();
      if (!subName) return alert('Please enter sub-table name');

      const colRows = document.querySelectorAll('#modalSubtableColumnsContainer > div');
      const cols = [];
      colRows.forEach(row => {
        const name = row.querySelector('.col-name-input').value.trim();
        const type = row.querySelector('.col-type-input').value;
        if (name) cols.push({ name: name, type: type, nullable: true });
      });
      if (cols.length === 0) return alert('At least one column is required');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'create_subtable',
            parent_table: parentTable,
            table: subName,
            columns: cols,
            database: activeDatabase
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Sub-table created');
          closeNewSubtableModal();
          document.getElementById('modalSubtableNameInput').value = '';
          const fullSubPath = `${parentTable}.${subName}`;
          expandedTables.add(parentTable);
          await loadTables();
          selectActiveTable(fullSubPath, activeDatabase);
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Failed to create sub-table: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // Modal Control: New Table
    function openNewTableModal() {
      const el = document.getElementById('modalNewTable');
      if (el) el.classList.add('active');
    }
    function closeNewTableModal() {
      const el = document.getElementById('modalNewTable');
      if (el) el.classList.remove('active');
    }
    function addModalColumnRow(containerId = 'modalColumnsContainer') {
      const container = document.getElementById(containerId);
      if (!container) return;
      const row = document.createElement('div');
      row.style.cssText = 'display: flex; gap: 8px; margin-bottom: 6px;';
      row.innerHTML = `
        <input type="text" class="form-control col-name-input" placeholder="col_name">
        <select class="form-control col-type-input" style="width: 130px;">
          <option value="INT">INT</option>
          <option value="BIGINT">BIGINT</option>
          <option value="TEXT" selected>TEXT</option>
          <option value="FLOAT">FLOAT</option>
          <option value="DOUBLE">DOUBLE</option>
          <option value="BOOLEAN">BOOLEAN</option>
          <option value="TIMESTAMP">TIMESTAMP</option>
        </select>
        <button type="button" class="btn-action" style="padding: 2px 6px; color: var(--pma-danger);" onclick="this.parentElement.remove()">X</button>
      `;
      container.appendChild(row);
    }
    async function submitCreateNewTable() {
      const dbName = document.getElementById('modalTableDbSelect') ? document.getElementById('modalTableDbSelect').value : activeDatabase;
      const tblName = document.getElementById('modalTableNameInput').value.trim();
      if (!tblName) return alert('Please enter table name');

      const colRows = document.querySelectorAll('#modalColumnsContainer > div');
      const cols = [];
      colRows.forEach(row => {
        const name = row.querySelector('.col-name-input').value.trim();
        const type = row.querySelector('.col-type-input').value;
        if (name) cols.push({ name: name, type: type, nullable: true });
      });
      if (cols.length === 0) return alert('At least one column is required');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'create_table',
            table: tblName,
            database: dbName,
            columns: cols
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Table created');
          closeNewTableModal();
          document.getElementById('modalTableNameInput').value = '';
          activeDatabase = dbName;
          await loadTables();
          selectActiveTable(tblName, dbName);
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Failed to create table: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 1. Browse (Pagination & Sorting with zero DOM memory leaks)
    async function loadBrowseData() {
      const container = document.getElementById('browseGridContainer');
      if (!activeTable) {
        if (container) container.innerHTML = `<div style="padding: 24px; text-align: center; color: #888;">${t('select_table_option')}</div>`;
        const info = document.getElementById('browseInfoText');
        if (info) info.textContent = '-';
        return;
      }

      startProgress();
      try {
        let url = `/table_data?table=${encodeURIComponent(activeTable)}&database=${encodeURIComponent(activeDatabase)}&page=${currentPage}&limit=${pageLimit}`;
        if (sortColumn) {
          url += `&sort_col=${encodeURIComponent(sortColumn)}&sort_dir=${sortDirection}`;
        }

        const res = await fetch(url);
        const data = await res.json();

        if (data.error) {
          if (container) container.innerHTML = `<div style="padding: 16px; color: var(--pma-danger);">Error: ${escapeHtml(data.error)}</div>`;
          return;
        }

        totalRows = data.total_rows || 0;
        totalPages = Math.max(1, Math.ceil(totalRows / pageLimit));
        currentPage = data.page || 1;

        const pageInput = document.getElementById('pageNumberInput');
        if (pageInput) pageInput.value = currentPage;
        const totalTxt = document.getElementById('pageTotalText');
        if (totalTxt) totalTxt.textContent = `/ ${totalPages.toLocaleString()}`;
        const infoTxt = document.getElementById('browseInfoText');
        if (infoTxt) infoTxt.textContent = `${totalRows.toLocaleString()} rows • ${totalPages.toLocaleString()} pages`;

        const bFirst = document.getElementById('btnFirst');
        const bPrev = document.getElementById('btnPrev');
        const bNext = document.getElementById('btnNext');
        const bLast = document.getElementById('btnLast');
        if (bFirst) bFirst.disabled = (currentPage <= 1);
        if (bPrev) bPrev.disabled = (currentPage <= 1);
        if (bNext) bNext.disabled = (currentPage >= totalPages);
        if (bLast) bLast.disabled = (currentPage >= totalPages);

        renderGrid(container, data.columns, data.rows, true);
      } catch (err) {
        console.error('Failed to load table data:', err);
      } finally {
        endProgress();
      }
    }

    function changePage(p) {
      if (p < 1) p = 1;
      if (p > totalPages) p = totalPages;
      if (p === currentPage && document.getElementById('pageNumberInput') && document.getElementById('pageNumberInput').value == p) return;
      currentPage = p;
      loadBrowseData();
    }

    function handleHeaderSort(col) {
      if (sortColumn === col) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      } else {
        sortColumn = col;
        sortDirection = 'asc';
      }
      currentPage = 1;
      loadBrowseData();
    }

    // High performance grid rendering: NEVER stores serialized data in DOM dataset!
    function renderGrid(container, columns, rows, enableRowActions = false) {
      if (!container) return;
      if (!rows || rows.length === 0) {
        container.innerHTML = `<div style="padding: 24px; text-align: center; color: #888;">(Empty table / Zero rows returned)</div>`;
        currentGridRows = [];
        currentGridCols = [];
        return;
      }

      currentGridRows = rows;
      currentGridCols = columns;

      let html = `<table class="pma-grid"><thead><tr>`;
      if (enableRowActions) {
        html += `<th style="width: 75px; text-align: center;">${t('action')}</th>`;
      }
      columns.forEach(col => {
        const sortIndicator = (sortColumn === col) ? (sortDirection === 'asc' ? ' ▲' : ' ▼') : '';
        html += `<th onclick="handleHeaderSort('${col}')">${escapeHtml(col)}${sortIndicator}</th>`;
      });
      html += `</tr></thead><tbody>`;

      rows.forEach((row, rIdx) => {
        html += `<tr>`;
        if (enableRowActions) {
          const firstColVal = row[0] !== undefined ? row[0] : rIdx;
          html += `<td style="text-align: center;">
            <button class="btn-action" style="padding: 1px 5px; font-size: 11px;" onclick="copyRowJson(${rIdx})" title="${t('copy_json_btn')}">JSON</button>
            <button class="btn-action" style="padding: 1px 5px; font-size: 11px; color: var(--pma-danger);" onclick="deleteRow('${columns[0]}', '${escapeHtml(String(firstColVal))}')" title="${t('delete_btn')}">X</button>
          </td>`;
        }
        row.forEach(val => {
          html += `<td>${escapeHtml(val)}</td>`;
        });
        html += `</tr>`;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
    }

    function copyRowJson(idx) {
      if (currentGridRows[idx]) {
        const obj = {};
        currentGridCols.forEach((c, i) => { obj[c] = currentGridRows[idx][i]; });
        navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
        showToast(t('copied_toast'));
      }
    }

    async function deleteRow(colName, colVal) {
      if (!confirm(`${t('confirm_delete_row')}
(${colName} = ${colVal})`)) return;
      startProgress();
      try {
        const whereClause = isNaN(colVal) ? `${colName} = '${colVal}'` : `${colName} = ${colVal}`;
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'delete', table: activeTable, database: activeDatabase, where: whereClause })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Row deleted');
          loadBrowseData();
          loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Delete failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 2. Structure
    async function loadStructureData() {
      if (!activeTable) return;
      startProgress();
      try {
        const res = await fetch(`/table_schema?table=${encodeURIComponent(activeTable)}&database=${encodeURIComponent(activeDatabase)}`);
        const data = await res.json();
        currentSchema = data.columns || [];

        const structInfo = document.getElementById('structTableInfo');
        if (structInfo) {
          structInfo.textContent = `${data.blocks_count || 0} blocks • ${(data.rows || 0).toLocaleString()} rows • ${formatBytes(data.bytes || 0)}`;
        }

        const tbody = document.getElementById('structureTableBody');
        if (tbody) {
          tbody.innerHTML = currentSchema.map((col, idx) => `
            <tr>
              <td><b>${idx + 1}</b></td>
              <td><code style="font-weight: 700; color: var(--pma-blue);">${col.name}</code></td>
              <td><span class="table-row-count" style="background:#e0f2fe; color:#0369a1; font-weight:600;">${col.type}</span></td>
              <td>${col.nullable ? 'Yes' : 'No'}</td>
              <td>
                <button class="btn-action" style="padding: 2px 6px; font-size: 11px;" onclick="promptRenameColumn('${col.name}')">${t('rename_btn')}</button>
                <button class="btn-action" style="padding: 2px 6px; font-size: 11px; color: var(--pma-danger);" onclick="handleDropColumn('${col.name}')">${t('delete_btn')}</button>
              </td>
            </tr>
          `).join('');
        }
      } catch (err) {
        console.error('Failed to load table schema:', err);
      } finally {
        endProgress();
      }
    }

    async function handleAddColumn() {
      const name = document.getElementById('newColName').value.trim();
      const type = document.getElementById('newColType').value;
      const defVal = document.getElementById('newColDefault').value.trim();
      if (!name) return alert('Please enter column name');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'add_column',
            table: activeTable,
            database: activeDatabase,
            name: name,
            type: type,
            default: defVal || null
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Column added');
          document.getElementById('newColName').value = '';
          document.getElementById('newColDefault').value = '';
          loadStructureData();
          loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Operation failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function promptRenameColumn(oldName) {
      const newName = prompt(`Enter new name for column '${oldName}':`, oldName);
      if (!newName || newName === oldName) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'rename_column',
            table: activeTable,
            database: activeDatabase,
            old_name: oldName,
            new_name: newName
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Column renamed');
          loadStructureData();
          loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Rename failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function handleDropColumn(colName) {
      if (!confirm(`${t('confirm_drop_col')} '${colName}'?`)) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'drop_column',
            table: activeTable,
            database: activeDatabase,
            name: colName
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Column dropped');
          loadStructureData();
          loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Drop failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 3. SQL Query Console
    function insertSqlTemplate(type) {
      const tbl = activeTable || 'table.mgdb';
      const area = document.getElementById('sqlQueryText');
      if (!area) return;
      if (type === 'select_all') area.value = `SELECT * FROM "${tbl}" LIMIT 50;`;
      else if (type === 'count') area.value = `SELECT COUNT(*) AS total_rows FROM "${tbl}";`;
      else if (type === 'where') area.value = `SELECT * FROM "${tbl}" WHERE id > 10 ORDER BY id DESC LIMIT 20;`;
      else if (type === 'group_by') area.value = `SELECT status, COUNT(*), AVG(balance) FROM "${tbl}" GROUP BY status HAVING COUNT(*) > 1;`;
      else if (type === 'bloom') area.value = `SELECT * FROM "${tbl}" WHERE name = 'Alice';`;
      else if (type === 'join') area.value = `SELECT t1.id, t1.name, t2.amount FROM "${tbl}" AS t1 INNER JOIN "orders.mgdb" AS t2 ON t1.id = t2.user_id;`;
      else if (type === 'update') area.value = `UPDATE "${tbl}" SET status = 'ACTIVE' WHERE balance > 100;`;
      else if (type === 'delete') area.value = `DELETE FROM "${tbl}" WHERE balance <= 0;`;
      area.focus();
    }

    function formatSql() {
      const area = document.getElementById('sqlQueryText');
      if (!area) return;
      let sql = area.value.trim();
      sql = sql.replace(/\s+/g, ' ');
      ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'SET'].forEach(k => {
        const re = new RegExp(`\\b${k}\\b`, 'gi');
        sql = sql.replace(re, `\n${k}`);
      });
      area.value = sql.trim();
    }

    function clearSql() {
      const area = document.getElementById('sqlQueryText');
      if (area) area.value = '';
      const stats = document.getElementById('queryStatsBox');
      if (stats) stats.style.display = 'none';
      const grid = document.getElementById('queryGridContainer');
      if (grid) grid.innerHTML = '';
    }

    async function executeSql() {
      const area = document.getElementById('sqlQueryText');
      const query = area ? area.value.trim() : '';
      if (!query) return;

      startProgress();
      const statsBox = document.getElementById('queryStatsBox');
      const gridBox = document.getElementById('queryGridContainer');
      if (statsBox) statsBox.style.display = 'none';
      if (gridBox) gridBox.innerHTML = '';

      try {
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query, active_table: activeTable, database: activeDatabase })
        });
        const data = await res.json();

        if (data.success) {
          const stats = data.stats || {};
          if (statsBox) {
            statsBox.style.display = 'block';
            statsBox.style.background = '#eef6fc';
            statsBox.style.borderColor = '#bce0fd';
            statsBox.innerHTML = `
              <b>Execution Time:</b> ${stats.execution_time_ms} ms &nbsp;•&nbsp;
              <b>Returned Rows:</b> ${data.row_count || 0} &nbsp;•&nbsp;
              <b>Blocks Scanned:</b> ${stats.blocks_scanned || 0} &nbsp;•&nbsp;
              <b>Blocks Pruned:</b> ${stats.blocks_skipped || 0} &nbsp;•&nbsp;
              <b>Bytes Read:</b> ${formatBytes(stats.bytes_read || 0)}
            `;
          }
          renderGrid(gridBox, data.columns, data.rows, false);
          loadTables();
        } else {
          if (statsBox) {
            statsBox.style.display = 'block';
            statsBox.style.background = '#fef2f2';
            statsBox.style.borderColor = '#fca5a5';
            statsBox.innerHTML = `<span style="color: var(--pma-danger); font-weight:700;">Query Error:</span> ${escapeHtml(data.error || 'Execution failed')}`;
          }
        }
      } catch (err) {
        if (statsBox) {
          statsBox.style.display = 'block';
          statsBox.innerHTML = `<span style="color: var(--pma-danger);">Execution error: ${err.message}</span>`;
        }
      } finally {
        endProgress();
      }
    }

    // 4. Search & Find Tab
    async function setupSearchTab() {
      if (!activeTable) return;
      if (currentSchema.length === 0) {
        const res = await fetch(`/table_schema?table=${encodeURIComponent(activeTable)}&database=${encodeURIComponent(activeDatabase)}`);
        const data = await res.json();
        currentSchema = data.columns || [];
      }

      const container = document.getElementById('fieldFilterContainer');
      if (container) {
        container.innerHTML = currentSchema.map(col => `
          <div>
            <label style="font-size: 11px; font-weight:600; color:#555;">${col.name} (${col.type})</label>
            <input type="text" class="form-control field-search-input" data-col="${col.name}" placeholder="Value...">
          </div>
        `).join('');
      }
    }

    async function executeFullTextSearch() {
      const term = document.getElementById('fullTextSearchInput').value.trim();
      if (!term) {
        loadBrowseData();
        return;
      }

      startProgress();
      try {
        const sql = `SELECT * FROM "${activeTable}" WHERE search = '${term}' LIMIT 100;`;
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: sql, active_table: activeTable, database: activeDatabase })
        });
        const data = await res.json();
        renderGrid(document.getElementById('searchGridContainer'), data.columns, data.rows, false);
      } catch (err) {
        alert('Search error: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function executeFieldSearch() {
      const inputs = document.querySelectorAll('.field-search-input');
      const conditions = [];

      inputs.forEach(inp => {
        const val = inp.value.trim();
        const col = inp.dataset.col;
        if (val) {
          conditions.push(isNaN(val) ? `${col} = '${val}'` : `${col} = ${val}`);
        }
      });

      if (conditions.length === 0) return alert('Please enter at least one filter value');

      startProgress();
      try {
        const sql = `SELECT * FROM "${activeTable}" WHERE ${conditions.join(' AND ')} LIMIT 100;`;
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: sql, active_table: activeTable, database: activeDatabase })
        });
        const data = await res.json();
        renderGrid(document.getElementById('searchGridContainer'), data.columns, data.rows, false);
      } catch (err) {
        alert('Filter error: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 5. Insert Form
    async function setupInsertForm() {
      if (!activeTable) return;
      if (currentSchema.length === 0) {
        const res = await fetch(`/table_schema?table=${encodeURIComponent(activeTable)}&database=${encodeURIComponent(activeDatabase)}`);
        const data = await res.json();
        currentSchema = data.columns || [];
      }

      const container = document.getElementById('insertFieldsContainer');
      if (container) {
        container.innerHTML = currentSchema.map(col => `
          <div class="form-group">
            <label>${col.name} <span style="font-weight:normal; color:#888;">(${col.type})</span></label>
            <input type="${col.type === 'INT' || col.type === 'BIGINT' ? 'number' : 'text'}" 
                   class="form-control insert-field-input" 
                   data-col="${col.name}" 
                   placeholder="${col.nullable ? 'NULL' : 'Value required'}">
          </div>
        `).join('');
      }
    }

    async function handleInsertRecord() {
      const inputs = document.querySelectorAll('.insert-field-input');
      const record = {};

      inputs.forEach(inp => {
        const col = inp.dataset.col;
        const val = inp.value.trim();
        if (val !== '') {
          record[col] = isNaN(val) ? val : Number(val);
        }
      });

      if (Object.keys(record).length === 0) return alert('Please fill in at least one field');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'insert',
            table: activeTable,
            database: activeDatabase,
            records: [record]
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Record inserted');
          document.getElementById('insertRecordForm').reset();
          loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Insert failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 6. Direct Chunked Streaming Downloads (Zero RAM / Zero GPU memory)
    function triggerDirectDownload(format) {
      if (!activeTable) return alert(t('select_table_option'));
      window.location.href = `/export?table=${encodeURIComponent(activeTable)}&database=${encodeURIComponent(activeDatabase)}&format=${format}`;
    }

    // 7. Streaming Import Handling (Zero V8 Memory Buffering, Real 0-100% Progress Bar)
    async function handleImportSubmit() {
      if (!activeTable) return alert(t('select_table_option'));
      const format = document.getElementById('importFormatSelect').value;
      const fileInput = document.getElementById('importFileInput');
      const pasteContent = document.getElementById('importPasteContent').value.trim();

      const progContainer = document.getElementById('importProgressContainer');
      const progText = document.getElementById('importStatusText');
      const progPct = document.getElementById('importPercentText');
      const progFill = document.getElementById('importProgressBarFill');
      const btnImport = document.getElementById('btnStartImport');

      // Case A: File Selected -> Native Streaming via XMLHttpRequest (Zero V8 RAM / GPU impact)
      if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        if (progContainer) {
          progContainer.style.display = 'block';
          progFill.style.background = 'var(--pma-blue)';
          progFill.style.width = '0%';
          progText.textContent = `Streaming '${file.name}' to server...`;
          progPct.textContent = '0%';
        }
        if (btnImport) btnImport.disabled = true;
        startProgress();

        const xhr = new XMLHttpRequest();
        const uploadUrl = `/import_stream?table=${encodeURIComponent(activeTable)}&format=${encodeURIComponent(format)}&database=${encodeURIComponent(activeDatabase)}`;
        xhr.open('POST', uploadUrl);

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            if (progPct) progPct.textContent = `${pct}% (${formatBytes(e.loaded)} / ${formatBytes(e.total)})`;
            if (progFill) progFill.style.width = `${pct}%`;
            updateTopProgress(pct);
            if (pct >= 100 && progText) {
              progText.textContent = 'Processing and indexing columnar blocks...';
            }
          }
        };

        xhr.onload = () => {
          endProgress();
          if (btnImport) btnImport.disabled = false;
          if (xhr.status >= 200 && xhr.status < 300) {
            let res;
            try { res = JSON.parse(xhr.responseText); } catch(e) { res = { rows_imported: 0, execution_time_ms: 0 }; }
            if (progText) progText.textContent = `Completed! ${(res.rows_imported || 0).toLocaleString()} rows imported in ${res.execution_time_ms} ms.`;
            if (progFill) {
              progFill.style.width = '100%';
              progFill.style.background = '#16a34a';
            }
            showToast(`Import successful: ${(res.rows_imported || 0).toLocaleString()} rows`);
            fileInput.value = '';
            setTimeout(() => { if (progContainer) progContainer.style.display = 'none'; }, 4000);
            loadTables();
            loadBrowseData();
          } else {
            if (progText) progText.textContent = 'Import failed';
            if (progFill) progFill.style.background = '#dc2626';
            alert('Import failed: ' + xhr.responseText);
          }
        };

        xhr.onerror = () => {
          endProgress();
          if (btnImport) btnImport.disabled = false;
          if (progText) progText.textContent = 'Network error during upload';
          if (progFill) progFill.style.background = '#dc2626';
          alert('Network connection error during streaming upload');
        };

        // Send raw file stream directly from disk to network: 0 MB memory overhead!
        xhr.send(file);
        return;
      }

      // Case B: Pasted Text
      if (pasteContent) {
        startProgress();
        if (btnImport) btnImport.disabled = true;
        try {
          const res = await fetch('/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              table: activeTable,
              database: activeDatabase,
              format: format,
              content: pasteContent
            })
          });
          const data = await res.json();
          if (data.success) {
            showToast(`Import completed: ${(data.rows_imported || 0).toLocaleString()} rows`);
            document.getElementById('importPasteContent').value = '';
            loadBrowseData();
            loadTables();
          } else {
            alert('Import failed: ' + data.error);
          }
        } catch (err) {
          alert('Import error: ' + err.message);
        } finally {
          endProgress();
          if (btnImport) btnImport.disabled = false;
        }
        return;
      }

      alert('Please choose a file or paste content to import.');
    }

        // 8. Operations (Rename, Truncate, Drop)
    async function handleRenameTable() {
      const newName = document.getElementById('renameTableInput').value.trim();
      if (!newName) return alert('Please enter new table name');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'rename', old_name: activeTable, new_name: newName })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Table renamed');
          document.getElementById('renameTableInput').value = '';
          activeTable = newName.endsWith('.mgdb') ? newName : newName + '.mgdb';
          await loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Rename failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function handleTruncateTable() {
      if (!confirm(`${t('confirm_truncate')} '${activeTable}'?`)) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'truncate', table: activeTable })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Table truncated');
          loadBrowseData();
          loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Truncate failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    async function handleDropTable() {
      if (!confirm(`${t('confirm_drop_table')} '${activeTable}'?`)) return;

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op: 'drop', table: activeTable })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Table deleted');
          activeTable = '';
          await loadTables();
          switchTab('browse');
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Drop failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 9. Server Status & Benchmark
    async function loadServerStatus() {
      try {
        const res = await fetch('/status');
        const st = await res.json();
        document.getElementById('statCpu').textContent = st.cpu || 'Not detected';
        document.getElementById('statRam').textContent = st.ram_gb ? `${st.ram_gb} GB` : 'Unknown';
        document.getElementById('statOs').textContent = st.os || 'OS';
        document.getElementById('statVer').textContent = `v${st.version || st.engine_version || '__MERGEN_VERSION__'}`;
        document.getElementById('headerStatusText').textContent = `v${st.version || '__MERGEN_VERSION__'} ${t('online_text')}`;
      } catch (e) {
        console.error('Status fetch error:', e);
      }
    }

    async function runLiveHardwareBenchmark() {
      startProgress();
      showToast('Running live speed benchmark...');

      try {
        const res = await fetch('/status?benchmark=1');
        const data = await res.json();
        const b = data.benchmark;

        if (b) {
          document.getElementById('liveBenchCard').style.display = 'block';
          document.getElementById('benchIngest').textContent = b.ingest_throughput || '-';
          document.getElementById('benchImport').textContent = b.import_throughput || '-';
          document.getElementById('benchExport').textContent = b.export_throughput || '-';
          document.getElementById('benchScan').textContent = b.scan_throughput || '-';
          document.getElementById('benchTier').textContent = b.tier || 'A-Tier';
          document.getElementById('benchBlock').textContent = b.optimal_block_size || '2,048 - 4,096';
          showToast('Benchmark completed');
        }
      } catch (err) {
        alert('Benchmark failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // 10. Documentation Tabs & Helpers
    function switchDocLang(lang) {
      document.querySelectorAll('.doc-lang-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.doc-pane').forEach(p => p.style.display = 'none');

      document.querySelector(`.doc-lang-tab[data-lang="${lang}"]`).classList.add('active');
      document.getElementById(`doc-pane-${lang}`).style.display = 'block';
    }

    // Create New Table Modal
    function openNewTableModal() {
      document.getElementById('modalNewTable').style.display = 'flex';
      document.getElementById('modalTableNameInput').focus();
    }
    function closeNewTableModal() {
      document.getElementById('modalNewTable').style.display = 'none';
    }

    function addModalColumnRow() {
      const container = document.getElementById('modalColumnsContainer');
      const div = document.createElement('div');
      div.style.cssText = 'display: flex; gap: 8px; margin-bottom: 6px;';
      div.innerHTML = `
        <input type="text" class="form-control col-name-input" placeholder="col_name">
        <select class="form-control col-type-input" style="width: 130px;">
          <option value="INT">INT</option>
          <option value="BIGINT">BIGINT</option>
          <option value="TEXT" selected>TEXT</option>
          <option value="FLOAT">FLOAT</option>
          <option value="DOUBLE">DOUBLE</option>
          <option value="BOOLEAN">BOOLEAN</option>
          <option value="TIMESTAMP">TIMESTAMP</option>
        </select>
        <button type="button" class="btn-action" style="padding: 2px 6px; color: var(--pma-danger);" onclick="this.parentElement.remove()">X</button>
      `;
      container.appendChild(div);
    }

    async function submitCreateNewTable() {
      const name = document.getElementById('modalTableNameInput').value.trim();
      if (!name) return alert('Please enter table name');

      const colNames = document.querySelectorAll('.col-name-input');
      const colTypes = document.querySelectorAll('.col-type-input');
      const columns = [];

      for (let i = 0; i < colNames.length; i++) {
        const cName = colNames[i].value.trim();
        const cType = colTypes[i].value;
        if (cName) {
          columns.push({ name: cName, type: cType });
        }
      }

      if (columns.length === 0) return alert('Please define at least one column');

      startProgress();
      try {
        const res = await fetch('/operation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            op: 'create_table',
            table: name,
            columns: columns
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Table created');
          closeNewTableModal();
          activeTable = name.endsWith('.mgdb') ? name : name + '.mgdb';
          await loadTables();
        } else {
          alert('Error: ' + data.error);
        }
      } catch (err) {
        alert('Table creation failed: ' + err.message);
      } finally {
        endProgress();
      }
    }

    // Utility Helpers
    function escapeHtml(str) {
      if (str === null || str === undefined) return '<i style="color:#aaa;">NULL</i>';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function copySnippet(id) {
      const text = document.getElementById(id).textContent;
      navigator.clipboard.writeText(text);
      showToast(t('copied_toast'));
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
    _version = "0.6.3"

STUDIO_HTML = STUDIO_HTML.replace("__MERGEN_VERSION__", _version)
