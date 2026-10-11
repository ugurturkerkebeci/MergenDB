<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="Mergen Studio Logo" width="260" />
</p>

# Mergen Studio (v1.0.0 Production Release)

> **Official Interactive Web Management Dashboard Extension for the MergenDB Columnar & Vector Database**

[![PyPI version](https://img.shields.io/pypi/v/mergendb-studio.svg?style=flat-square&logo=pypi&logoColor=white&cacheSeconds=300)](https://pypi.org/project/mergendb-studio/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb-studio.svg?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb-studio/)
[![Socket PyPI Security Badge](https://badge.socket.dev/pypi/package/mergendb)](https://socket.dev/pypi/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="Mergen Studio Banner" width="100%" />
</p>

## The v1.0.0 Milestone

**Mergen Studio** is the official graphical web administration dashboard for [MergenDB](https://pypi.org/project/mergendb/). In v1.0.0, Mergen Studio has been completely redesigned with a modern **deep ultraviolet and neon purple theme**, supporting interactive schema visualization for both columnar tabular data and **AI vector embeddings**.

Decoupled from the headless core engine, Mergen Studio can be installed on demand when visual management is required, keeping the core `mergendb` package ultra-compact (< 150 KB).

---

## Features in v1.0.0

- **Ultraviolet Cyberpunk Aesthetic:** Sleek, responsive dark mode interface optimized for large data exploration.
- **Vector & Columnar Schema Explorer:** Inspect column types, compression ratios, ZoneMap min/max boundaries, and vector dimensions.
- **Interactive SQL & MergenQL Console:** Execute analytical queries with syntax highlighting and instant tabular result rendering.
- **Hierarchical Database Navigator:** Browse databases, tables, and nested sub-tables (`database.table.subtable`) with a single click.
- **Zero-Memory Streaming Ingestion & Export:** Drag-and-drop CSV/JSON files to import directly into columnar storage with bounded memory.
- **Real-Time Hardware Metrics:** Monitor live CPU utilization, system RAM, active table locks, and disk throughput.

---

## Installation

Install Mergen Studio as an optional extra alongside MergenDB:

```bash
pip install --upgrade mergendb-studio
```

Or install with the core database bundle:

```bash
pip install --upgrade "mergendb[studio]"
```

---

## Quickstart

Start the interactive web dashboard on your machine:

```bash
mergendb studio
```

Or start the server with Studio UI enabled:

```bash
mergendb server --port 8765 --ui
```

Navigate to `http://localhost:8765` in your browser to open the dashboard.

---

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
