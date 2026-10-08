<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="Mergen Studio Logo" width="260" />
</p>

# Mergen Studio

> **Official Interactive Web Management Dashboard Extension for the MergenDB Columnar Database**

[![PyPI version](https://img.shields.io/pypi/v/mergendb-studio.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb-studio/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb-studio.svg?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb-studio/)
[![Socket PyPI Security Badge](https://badge.socket.dev/pypi/package/mergendb)](https://socket.dev/pypi/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="Mergen Studio Banner" width="100%" />
</p>

**Mergen Studio** is the official graphical web administration dashboard for [MergenDB](https://pypi.org/project/mergendb/). It provides an interactive browser GUI to inspect hierarchical database containers, execute analytical SQL queries, visualize columnar table schemas, and perform streaming zero-memory imports and exports.

Decoupled from the headless core engine, Mergen Studio can be installed on demand when visual management is required, keeping the core `mergendb` package ultra-compact (< 150 KB).

---

## Features

- **Hierarchical Tree Navigation:** Visually browse databases, tables, and nested sub-tables (`database.table.subtable`) with one-click selection.
- **Interactive SQL Console:** Run full analytical queries with syntax highlighting, query history, and execution time benchmarks.
- **Dynamic Data Grid & Schema Inspector:** Inspect table structures and browse records with persistent column definitions even on empty tables.
- **Zero-Memory Streaming Engine:** Stream multi-gigabyte CSV, JSON, JSONL, and SQL dumps directly to disk or network sockets with real-time transfer progress tracking (0% to 100%) and zero browser heap crashes.
- **Authentication & Security:** Built-in Basic Auth and session token verification (default credentials: `root:`), with an interactive credentials modal for custom logins.
- **Full Localization:** Native support for English, German (Deutsch), and Turkish (Turkce).
- **Strict Zero-Emoji Policy:** Clean, professional interface built with text status tags (`[+]`, `[-]`, `[*]`).

---

## Installation

Install Mergen Studio directly via `pip`:

```bash
pip install --upgrade mergendb-studio
```

Or install as an optional extra alongside the core engine:

```bash
pip install --upgrade "mergendb[studio]"
```

Or install on demand via the Mergen CLI:

```bash
mergen studio install
```

---

## Quickstart & Usage

### 1. Start the MergenDB Server

```bash
mergen serve 8765
```

### 2. Open Mergen Studio

Navigate to the dashboard in your web browser:

```text
http://localhost:8765/studio
```

Log in with default credentials (`root` with an empty password), or authenticate with your custom configured credentials.

---

## Requirements

- Python 3.8+
- [mergendb](https://pypi.org/project/mergendb/) >= 0.8.8

---

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
