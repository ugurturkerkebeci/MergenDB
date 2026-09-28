<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

# MergenDB

[![PyPI version](https://img.shields.io/badge/PyPI-v0.6.5-blue?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![npm version](https://img.shields.io/badge/npm-v0.6.5-blue?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/mergendb)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Tests](https://img.shields.io/badge/Tests-89%20Python%20%7C%2018%20Node.js%20(100%25%20Pass)-brightgreen.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![Author](https://img.shields.io/badge/Author-U%C4%9Fur%20T%C3%BCrker%20Kebeci-orange.svg?style=flat-square)](https://github.com/ugurturkerkebeci)

**MergenDB** is an ultra-compact, high-performance embedded columnar database engine designed to process massive analytical workloads and multi-million row table scans on resource-constrained hardware. It delivers **strict zero external runtime dependencies** -- requiring no C compilers, no native C++ binaries, and no bulky runtimes across both Python and Node.js.

Whether querying a 10-million row dataset on a 500 MB RAM VPS, analyzing telemetry streams on an edge Raspberry Pi, running real-time analytical reporting in Node.js/TypeScript, or managing hierarchical databases through the browser in **Mergen Studio**, MergenDB provides columnar speed with bounded memory guarantees.

---

## What Is New in v0.6.5

1. **Hierarchical Database Containers & Nested Sub-tables:**
   - Organize data just like modern RDBMS platforms: **Databases -> Tables -> Nested Sub-tables** (e.g. `okul.ogrenciler.a_sinifi`).
   - Store root records or partition sub-groups into isolated columnar files while preserving relational hierarchy.
   - Comprehensive SQL support: `SHOW DATABASES;`, `CREATE DATABASE <name>;`, `DROP DATABASE <name>;`, `USE <name>;`, `SHOW TABLES [FROM <name>];`.
   - Native dot-notation resolution across Python (`mergendb.database()`, `table.create_subtable()`), Node.js (`client.database()`, `table.createSubtable()`), CLI, REST server, and Studio Web UI.

2. **Zero-Memory Chunked Streaming Import & Export Engine:**
   - Dedicated `DataExporter` streaming engine utilizing HTTP Chunked Transfer Encoding (`Transfer-Encoding: chunked`).
   - Tables of arbitrary size stream directly to disk or network sockets without ever accumulating full datasets into memory buffers.
   - Dedicated `/import_stream` endpoint accepts raw chunked streams in 64 KB blocks directly from network sockets to temporary disk files, eliminating browser V8 heap bloat and preventing GPU/compositor memory crashes.
   - Live **0% to 100% upload progress telemetry** with transferred byte counters in Mergen Studio.

3. **Mergen Studio Web Dashboard Enhancements:**
   - Complete phpMyAdmin-style tree hierarchy sidebar with collapsible database, table, and sub-table nodes.
   - Visual creation modals: **+ DB**, **+ Table**, and **+ Sub**.
   - Streamlined DOM rendering without dataset string serialization, protecting browser memory.
   - Comprehensive internationalization: **English (Default)**, **German (Deutsch)**, and **Turkish (Turkce)**.
   - Strict Zero-Emoji policy enforced across all interfaces, logs, and documentation.

4. **Node.js & TypeScript SDK 100% Parity:**
   - Added `DatabaseHandle`, `database()`, `listDatabases()`, `createDatabase()`, `dropDatabase()`.
   - Added `createSubtable()`, `subtable()`, `listSubtables()`.
   - Added zero-memory file stream operations: `exportToFile(destPath)` and `importFile(filePath)` powered by standard library streams (`pipe`).

---

## Zero-Dependency Installation

MergenDB requires **zero external packages or compilers** (`dependencies: {}`). It runs purely on the standard library of Python and Node.js.

### Python Engine & CLI
```bash
# Install via PyPI
pip install --upgrade mergendb

# Run interactive CLI REPL directly:
python -m mergendb

# Start HTTP server & Mergen Studio:
python -m mergendb serve 8765

# Run embedded diagnostics & hardware benchmark:
python -m mergendb test
```

### Node.js & TypeScript SDK
```bash
# Install SDK via npm
npm install mergendb

# Run server or open studio directly via npx:
npx mergendb serve 8765
npx mergendb studio 8765
```

Requires **Python 3.8+** and/or **Node.js 16+**. Works out-of-the-box on Windows, macOS, Linux, and Docker with zero additional setup.

---

## Why MergenDB? (The Problem with Row Stores)

Traditional embedded databases like SQLite store data row-by-row (`[id, name, age, address, notes, ...]`). When running analytical queries:

```sql
SELECT name, balance FROM users WHERE balance > 1000;
```

Even though you only care about `name` and `balance`, row stores must read **every single column of every row** off disk -- including massive text fields like `address` and `notes`. On a 10-million row database, that translates to gigabytes of unnecessary disk I/O and heavy memory exhaustion.

**MergenDB utilizes the columnar approach:**
1. **Column-Isolated I/O:** Every column is stored and compressed independently. Unqueried columns are never read from disk.
2. **ZoneMap Pruning:** Every block records `min_value` and `max_value`. If a block cannot contain matching rows, it is skipped with zero disk reads.
3. **1024-bit Block Bloom Filters:** Instant single-pass lookup index skips blocks that do not contain a queried ID, text, or UUID.
4. **Demand-Driven Late Materialization (`LazyColumnDict`):** In multi-column filters (`WHERE status = 'ACTIVE' AND balance > 50`), MergenDB evaluates `status` first. If no rows in the block match, `balance` and all other columns are never decompressed.
5. **Strictly Bounded Memory:** Data streams in small, tunable blocks (1,024-8,192 rows). Memory usage stays under **15-20 MB RAM**, whether the database is 100 MB or 100 GB.

---

## MergenDB Ecosystem Architecture

```text
+---------------------------------------------------------------------------------+
|                                 CLIENT LAYER                                    |
|   Python Library (mergendb)   |   Node.js / TS SDK   |   Mergen Studio (Web)    |
|   db.find() / db.sql()        |   db.sql`...`        |   phpMyAdmin UI Tree     |
+---------------------------------------+-----------------------------------------+
                                        | HTTP / REST (Zero-Dependency)
+---------------------------------------v-----------------------------------------+
|                                SERVER ENGINE                                    |
|   Multi-threaded HTTP Server  |  Chunked Stream Transfer    |  Progress Stream  |
|   GET /export (Chunked)       |  POST /import_stream (Raw)  |  Hierarchical DB  |
+---------------------------------------+-----------------------------------------+
                                        | Analytical AST / Execution Plans
+---------------------------------------v-----------------------------------------+
|                              ANALYTICAL ENGINE                                  |
|   In-Memory Hash JOINs        |  Multi-Column GROUP BY / HAVING                 |
|   ZoneMap & Bloom Pruning     |  Vectorized Column Evaluation                   |
+---------------------------------------+-----------------------------------------+
                                        | Zero-Copy mmap & Block I/O
+---------------------------------------v-----------------------------------------+
|                        STORAGE & ADAPTIVE COMPRESSION                           |
|   Bit-Packed Booleans         |  Delta / Frame-of-Reference (FoR)               |
|   Block Dictionary Encoding   |  Run-Length Encoding (RLE)                      |
|   Secondary Zlib Stream       |  ZoneMap & Bloom Header (.mgdb)                 |
+---------------------------------------------------------------------------------+
```

---

## Hierarchical Database & Nested Sub-tables System

MergenDB supports multi-tier hierarchical data management matching traditional relational databases while retaining columnar performance:

```text
[DB] okul
 |-- [TBL] ogretmenler (1,200 rows)
 \-- [TBL] ogrenciler (4,500 rows)
      |-- [SUB] a_sinifi (32 rows)
      \-- [SUB] b_sinifi (30 rows)
```

### Python API
```python
import mergendb

# 1. Create or open database container
okul = mergendb.create_database("okul")

# 2. Create tables inside database
ogretmenler = okul.create_table("ogretmenler", [
    ("id", "INT64"),
    ("name", "STRING"),
    ("branch", "STRING")
])
ogrenciler = okul.create_table("ogrenciler", [
    ("id", "INT64"),
    ("name", "STRING"),
    ("grade_level", "INT32")
])

# 3. Insert records directly
ogrenciler.insert([
    {"id": 1, "name": "Ali", "grade_level": 5},
    {"id": 2, "name": "Veli", "grade_level": 5},
])

# 4. Create nested sub-tables inside a table
a_sinifi = ogrenciler.create_subtable("a_sinifi", [
    ("student_id", "INT64"),
    ("score", "FLOAT64")
])
a_sinifi.insert([{"student_id": 1, "score": 95.5}])

# 5. Access via dot-notation
tbl = mergendb.connect("okul.ogrenciler.a_sinifi")
results = tbl.find(student_id=1)
print(results)
```

### SQL Commands
```sql
SHOW DATABASES;
CREATE DATABASE okul;
USE okul;
SHOW TABLES;
CREATE TABLE ogrenciler (id BIGINT, name TEXT);
INSERT INTO ogrenciler VALUES (1, 'Ali');
SELECT * FROM ogrenciler;
```

---

## Zero-Memory Streaming Import & Export

When handling multi-gigabyte datasets, traditional engines often buffer entire payloads into RAM, leading to memory exhaustion and browser compositor crashes. MergenDB resolves this with true streaming architecture:

### 1. Chunked Export (`GET /export`)
The server reads column blocks and yields encoded byte chunks directly into the HTTP response socket using standard HTTP Chunked Transfer Encoding. Server-side memory usage remains strictly bounded (< 1 MB RAM) regardless of table size.

```bash
# Stream table directly to disk
curl -N "http://localhost:8765/export?table=okul.ogrenciler&format=csv" -o ogrenciler.csv
curl -N "http://localhost:8765/export?table=okul.ogrenciler&format=json" -o ogrenciler.json
curl -N "http://localhost:8765/export?table=okul.ogrenciler&format=sql" -o ogrenciler.sql
```

### 2. Zero-Memory Import (`POST /import_stream`)
Mergen Studio streams the raw native `File` object directly over an HTTP socket using `XMLHttpRequest`. The server buffers incoming bytes in 64 KB chunks directly to a temporary file on disk, parses it with `DataImporter`, and indexes columnar blocks without consuming V8 heap memory.

```bash
# Direct zero-memory streaming upload
curl -X POST "http://localhost:8765/import_stream?table=okul.ogrenciler&format=csv" \
  --data-binary @large_dataset.csv
```

---

## 5-Minute Quickstart

### 1. Python API
```python
import mergendb

# 1. Connect to table (Auto-created if not exists)
db = mergendb.connect("telemetry.mgdb")

# 2. Insert records (Schema is auto-inferred)
db.insert([
    {"id": 1, "sensor": "TEMP-01", "reading": 23.5, "active": True},
    {"id": 2, "sensor": "TEMP-02", "reading": 28.1, "active": True},
    {"id": 3, "sensor": "TEMP-01", "reading": 24.0, "active": False},
])

# 3. Document-Style Queries
active_sensors = db.find(sensor="TEMP-01", active=True)
first = db.find_one(sensor="TEMP-02")
matches = db.search("TEMP")  # Substring search across all text columns

# 4. Analytical SQL
res = db.sql("SELECT sensor, COUNT(*), AVG(reading) FROM telemetry GROUP BY sensor")
res.show()

# 5. Zero-Memory File Streaming
db.export_csv("telemetry_export.csv")
mergendb.from_csv("telemetry_export.csv", "backup.mgdb")

# 6. Live Hardware Diagnostics
mergendb.benchmark()
```

### 2. Node.js & TypeScript SDK
```javascript
const { connect } = require('mergendb');

async function main() {
  const client = connect('http://localhost:8765');

  // Database Container Operations
  await client.createDatabase('analytics');
  const analyticsDb = client.database('analytics');

  // Create Table
  await analyticsDb.createTable('metrics', [
    { name: 'id', type: 'INT64' },
    { name: 'host', type: 'STRING' },
    { name: 'cpu_usage', type: 'FLOAT64' }
  ]);

  const metrics = analyticsDb.table('metrics');
  await metrics.insert([
    { id: 1, host: 'prod-api-1', cpu_usage: 42.5 },
    { id: 2, host: 'prod-api-2', cpu_usage: 78.1 }
  ]);

  // Nested Sub-table
  await metrics.createSubtable('hourly', [
    { name: 'metric_id', type: 'INT64' },
    { name: 'val', type: 'FLOAT64' }
  ]);
  const hourly = metrics.subtable('hourly');
  await hourly.insert([{ metric_id: 1, val: 41.2 }]);

  // Zero-Memory File Streaming
  await metrics.exportToFile('metrics_stream.csv', 'csv');
  await metrics.importFile('metrics_stream.csv', 'csv');

  // Analytical Query
  const summary = await client.sql`SELECT host, AVG(cpu_usage) FROM analytics.metrics GROUP BY host`;
  console.table(summary.rows);
}

main().catch(console.error);
```

### 3. Mergen CLI REPL
```bash
# Launch interactive REPL
mergen

# Inside REPL:
SHOW DATABASES;
CREATE DATABASE okul;
USE okul;
CREATE TABLE ogrenciler (id BIGINT, name TEXT, score DOUBLE);
INSERT INTO ogrenciler VALUES (1, 'Alice', 95.5), (2, 'Bob', 82.0);
SELECT * FROM ogrenciler;
EXPORT ogrenciler TO CSV;
EXPORT ogrenciler TO JSON;
EXPORT ogrenciler TO SQL;
```

---

## Adaptive Compression Pipeline

When writing column blocks, MergenDB analyzes incoming values and applies the most optimal encoding scheme:

1. **Bit-Packed Booleans:** Stores boolean flags at 1 bit per value (8 values per byte).
2. **Delta / FoR (Frame-of-Reference):** Stores sequential numbers as offsets from `min_value`, reducing 8-byte integers to 1- or 2-byte deltas.
3. **Block Dictionary Encoding:** Optimal for low-cardinality text (gender, country, status). Stores unique strings once in a block dictionary and encodes rows as 1-byte indices.
4. **Run-Length Encoding (RLE):** Collapses repeated identical values into `(count, value)` pairs.
5. **Secondary Zlib Compression:** Applied to compressed byte streams for secondary compaction.

---

## Performance Benchmarks

Tested on an Intel Core i5 / i7 with 100,000 mixed telemetry records (12 columns: integers, floats, timestamps, statuses, long strings):

| Storage Format | Disk Size | Space Saved | 2-Column Query Disk Read | Peak RAM |
| :--- | :--- | :--- | :--- | :--- |
| **JSON Lines (`.jsonl`)** | 19.5 MB | 0% (Baseline) | 19.5 MB | Unbounded |
| **SQLite 3 (`.db`)** | 8.1 MB | 58.4% | 8.1 MB (reads full row) | ~30 MB |
| **MergenDB (`.mgdb`)** | **1.6 MB** | **91.5%** | **0.29 MB (pruned)** | **< 15 MB RAM** |

- **Exact Filter Scan Throughput:** ~50,000,000 rows/sec (single core)
- **Substring (`LIKE '%term%'`) Scan:** ~10,000,000 rows/sec (single core)
- **SQL Streaming Import Speed:** ~70,000-120,000 rows/sec on standard SSD

---

## Version Changelog & Release Progression

| Version | Milestone | Key Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **v0.5.8** | Analytical SQL & JOINs | In-Memory Hash JOIN (`INNER`/`LEFT`), Multi-Column GROUP BY, HAVING | Released |
| **v0.5.9** | Embedded Web UI | Initial **Mergen Studio** web interface | Released |
| **v0.6.0** | Universal Node.js SDK | Zero-dependency Node.js/TypeScript SDK + CLI runner | Released |
| **v0.6.1** | phpMyAdmin Overhaul | 100% CLI feature parity in browser and Node.js SDK, 106 tests | Released |
| **v0.6.2** | Multi-Runtime & Zero-Dependency | `python -m mergendb` & `npx mergendb` runners, `autoStart: true`, `GET /query` | Released |
| **v0.6.3** | Official Identity & i18n | Official Logo, strict zero-emoji policy, English/German/Turkish localization | Released |
| **v0.6.4** | Hierarchical Architecture | Database containers, nested sub-tables, and streaming export/import | Released |
| **v0.6.5** | Zero-Memory Streaming Engine | **Zero-Memory Chunked Streaming Engine**, crash-free browser file upload with live % progress bar, 107 tests (100% pass) | **Current Release** |

---

## Running the Test Suite

MergenDB includes an embedded test suite with **107 comprehensive tests** (89 Python unit tests covering storage, compression algorithms, query planning, Bloom filters, hierarchical databases, sub-tables, and analytical joins + 18 end-to-end Node.js SDK integration tests):

```bash
# Run Python unit tests via unittest
python -m unittest discover -s tests

# Run Node.js Client SDK integration tests
node sdks/nodejs/test.js
```

---

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed by [Ugur Turker Kebeci](https://github.com/ugurturkerkebeci).
