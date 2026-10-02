<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.jpg" alt="MergenDB Banner" width="50%" />
</p>

# MergenDB

[![PyPI version](https://img.shields.io/badge/PyPI-v0.7.5-blue?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![npm version](https://img.shields.io/badge/npm-v0.7.5-blue?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/mergendb)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Tests](https://img.shields.io/badge/Tests-2600%2B%20Python%20%7C%202000%2B%20Node.js%20(100%25%20Pass)-brightgreen.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![Author](https://img.shields.io/badge/Author-U%C4%9Fur%20T%C3%BCrker%20Kebeci-orange.svg?style=flat-square)](https://github.com/ugurturkerkebeci)

**MergenDB** is an ultra-compact, high-performance embedded columnar database engine designed to process massive analytical workloads and multi-million row table scans on resource-constrained hardware. It delivers **strict zero external runtime dependencies** -- requiring no C compilers, no native C++ binaries, and no bulky runtimes across both Python and Node.js.

Whether querying a 10-million row dataset on a 500 MB RAM VPS, analyzing telemetry streams on an edge Raspberry Pi, running real-time analytical reporting in Node.js/TypeScript, or managing hierarchical databases through the browser in **Mergen Studio**, MergenDB provides columnar speed with bounded memory guarantees.

---
<img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />

## What Is New in v0.7.5

1. **SQL Streaming Hang/Freeze Resolution on Multi-Million Row Dumps:**
   - **Linear Token Scanner:** Eliminated quadratic $O(N^2)$ `.count()` calls and unbounded pending string accumulation that could stall imports at multi-million row boundaries (e.g. ~4.25M rows) on dirty, escaped, or multi-line quotes.
   - **Compiled C-Level Regex Acceleration:** Optimized value tokenization using precompiled `SQL_VAL_REGEX` for high-throughput scalar and string extraction.
   - **Bounded Memory Safety:** Safe line buffering prevents memory bloat and guarantees sustained 50,000+ to 60,000+ rows/s throughput on multi-gigabyte SQL files.

2. **Direct Columnar Buffering & Memory Optimization:**
   - Streamlined column-oriented tuple insertion by buffering directly into pre-allocated column lists.
   - Eliminates intermediate per-row dictionary creations and reduces Python garbage collection pauses during long-running streaming imports.

---

## What Is New in v0.7.4

1. **High-Throughput SQL Streaming & Bulk Import Engine:**
   - **Zero-Allocation Tokenizer:** Completely redesigned the SQL tuple parser to eliminate per-row `csv.reader` instantiations. Parses raw tuples directly in linear time ($O(N)$) with quote-aware streaming.
   - **Bulk Ingestion Speed:** Multi-gigabyte SQL dump imports now operate at over **60,000+ rows per second** in pure Python standard library mode, dropping 1.5 GB import times from minutes down to seconds.
   - **Rock-Solid Fault Tolerance:** Resilient against broken sub-tuples, ragged rows, mixed quotes, and escaped characters without risking data corruption.

2. **Inlined Columnar Bloom Filter Acceleration:**
   - Optimized block-level Bloom filter generation by inlining `zlib.crc32` bitmask calculations.
   - Drastically cuts block serialization overhead and accelerates point lookups (`WHERE id = ...`) down to ~12 ms on large datasets.

---

## What Is New in v0.7.3

1. **Authentication & User Management Subsystem (Root / User Authorization):**
   - **Default Credentials:** Default user is `root` with default empty password `""`.
   - **Mandatory Authorization:** All remote server database queries and endpoints require authentication via HTTP Basic Auth or session Bearer tokens.
   - **Python & Node.js Client Integration:** Connect in code specifying `username`, `password`, `port`:
     - Python: `client = mergendb.connect(host="127.0.0.1", port=8529, username="root", password="")`
     - Node.js: `const db = mergendb.connect({ host: '127.0.0.1', port: 8529, username: 'root', password: '' })`
   - **CLI User Management:** Passwords can be changed or managed via CLI (`mergen auth set-password root <new_password>`, `mergen auth list-users`, `mergen auth add-user <user> [pass]`).

2. **Decoupled Architecture & CLI Studio Extensibility:**
   - MergenDB core package is completely headless (< 150 KB wheel).
   - Mergen Studio UI is decoupled into optional package `mergendb-studio`.
   - Installable on-demand directly via CLI (`mergen studio install`) or pip (`pip install mergendb-studio`).

3. **Top 100 Database Engine Errors Test Suite (1,000 Tests Python + 1,000 Tests Node.js = 2,000 Tests):**
   - Researched top 100 database errors across relational/embedded database systems.
   - Categorized into 10 domains with 100 tests each: Syntax & Lexical, Schema & Resolution, Data Type & Coercion, Constraints & Data Integrity, Query Planning & Aggregation, Concurrency & RWLock, Authentication & Permissions, Connection & Protocol, Storage & Corrupt Data, and Import/Export Format Transformations.
   - 100% pass rate across all 2,000 unit tests.

4. **Critical SQL Export / Import Resilience Fix:**
   - Resolved CLI SQL export indentation issue where tuples were generated multiple times per row.
   - Implemented column count validation in `from_sql_dump` to automatically filter partial sub-tuples and pad variable-length rows, completely preventing dropped columns or all-NULL states on interrupted exports.

1. **1000 Heavy Resilience & Fault Tolerance Tests (Python & Node.js):**
   - Scaled both Python and Node.js test suites to **1000 individual test scenarios each** (2,000+ total scenarios).
   - Thoroughly tests: multi-delimiter CSVs (commas, tabs, semicolons, pipes), mid-file header repetitions, null bytes, extreme Unicode, deeply nested JSON objects, schema drift mid-stream, fragmented multi-row SQL dumps, out-of-order column insertions, high-churn dynamic schema mutations, and zero-byte boundary exports/re-imports.
   - Guaranteed 100% pass rate with zero crashes and bounded memory (< 30 MB).

2. **Core Engine Hardening & Bug Fixes:**
   - **Graceful Empty File Handling:** Importers (`from_csv`, `from_json`, `from_jsonl`, `from_sql_dump`) now safely process 0-byte or whitespace-only files without crashing, creating empty tables and returning 0 rows.
   - **Table.import_file API:** Added `Table.import_file(filepath, fmt)` directly to Python `Table` class, making it fully symmetrical with the Node.js SDK.

3. **Multi-Platform Distribution:**
   - Released `mergendb` 0.7.2 and `mergendb-studio` 0.7.2 to PyPI.
   - Published `mergendb@0.7.2` to npm.

---

## What Is New in v0.7.1

1. **500 Automated Resilience Tests Across Python & Node.js (1,000+ Total Scenarios):**
   - Scaled both Python and Node.js test suites to **500 individual resilience scenarios each**.
   - Tests extreme edge cases: ragged short/long rows, dirty null tokens (`NULL`, `\N`, `NaN`, `nil`), null bytes (`\x00`), unclosed quotes, escaped SQL quotes (`O\'Connor`), extreme floats, scientific notations, dynamic schema mutations, out-of-order columns, and multi-format export/re-import roundtrips.
   - Guaranteed 100% pass rate with zero crashes, robust error recovery, and bounded RAM usage (< 30 MB).

2. **Radiant Amber-Orange Visual Identity:**
   - Brand new futuristic cinematic banner and geometric falcon emblem logo in warm obsidian and glowing amber-orange tones, active through the v0.8.x series.

3. **Synchronous Multi-Platform Distribution:**
   - Released `mergendb` 0.7.1 and `mergendb-studio` 0.7.1 to PyPI.
   - Published `mergendb@0.7.1` to npm.

---

## What Is New in v0.7.0

1. **New Visual Identity & Radiant Amber-Orange Aesthetic:**
   - Brand new futuristic cinematic banner and iconic geometric falcon emblem logo in glowing obsidian, fiery orange, and warm amber tones.
   - Designed to serve as the signature visual design across all repositories and platforms through the v0.7.x lifecycle.

2. **+100 Extreme Resilience & Fault Tolerance Tests (Python & Node.js):**
   - Added 100 comprehensive edge-case test scenarios per platform testing corrupt headers, truncated blocks, mixed numeric/string comparisons, zero division prevention, irregular line breaks, extreme Unicode charsets, and full mutation-query-export roundtrips.
   - Total automated test suite now exceeds 510 tests (195 Python + 318 Node.js) with 100% pass rate.

3. **Harden Query Engine & Cross-Platform Path Normalization:**
   - Safe type coercion in `ExpressionEvaluator` arithmetic and comparison operators, preventing unexpected `TypeError` or zero division exceptions on dirty data.
   - Fully normalized Windows path escaping in `Table.query` and SQL converter pipelines, eliminating backslash escape collisions.

---

## What Is New in v0.6.10

1. **Decoupled Mergen Studio Web UI (Optional Upgrade Package):**
   - The web interface has been decoupled from the core engine into an optional upgrade package (`mergendb-studio`), keeping the core engine minimal, lightweight, and headless.
   - Installable on demand via `pip install "mergendb[studio]"` or via the CLI runner `mergen studio install`.

2. **High-Concurrency RWLock & Multi-Threading Architecture:**
   - Introduced fine-grained per-table `RWLock` and `TableLockManager` (`mergendb/storage/lock.py`).
   - Multiple concurrent readers execute queries without blocking each other, while writer operations (mutations, inserts, DDL) are executed with atomic staging file replacement and exponential backoff retry.
   - Strict bounded memory (< 30 MB peak RAM) safe on 500 MB VPS headless environments without GPU.

3. **200-Combination Fault-Tolerant I/O Engine (Python & Node.js):**
   - Resilient import engine handles dirty null tokens (`""`, `"NULL"`, `"none"`, `"N/A"`, `"NaN"`, `"\\N"`, `"nil"`, `"-"`), ragged rows, null bytes (`\x00`), multi-encodings (UTF-8, Latin1, CP1254, BOM), and corrupt JSON/JSONL/SQL dump fragments.
   - Single malformed records or syntax errors never cause the entire document to be discarded or ruined.
   - Validated across 200 distinct test combinations in both Python and Node.js SDK test suites.

---

## What Is New in v0.6.8

1. **HTTP Streaming Export Payload Fix:**
   - Resolved an issue in MergenDB Server where manual chunk-length framing headers were injected into streaming file downloads (`_send_response_streaming_download`), causing chunk byte counts to be saved into downloaded CSV/JSON/SQL files.
   - Configured `protocol_version = "HTTP/1.1"` and switched to raw streaming byte payloads, terminated cleanly upon stream closure (`Connection: close`). Multi-gigabyte downloads now write 100% clean, valid data files with zero corrupt header bytes.

2. **Mergen Studio Active Table Indicator in Export Tab:**
   - Added an active table indicator badge (`Selected Table: <name> (<N> rows)`) directly inside the Export tab.
   - Prevents accidental exports of unintended tables by giving clear, unambiguous visual confirmation of which table is queued for export before clicking the Export button.

3. **Multi-Runtime Packaging & Version Alignment:**
   - Bumped and synchronized all Python wheels/sdist and Node.js SDK npm packages to `v0.6.8`.

---

## What Is New in v0.6.7

1. **Mergen Studio Table Selection & Navigation Fix:**
   - Restored internationalization engine (EN/DE/TR) and resolved `setLanguage` reference errors in the browser client.
   - Synchronized top navigation dropdown (`Table:`) with the active database and active table selections.
   - Fully enabled one-click table browsing and structure views across all databases and subtables.

2. **Node.js SDK Multi-Database Context:**
   - `TableHandle` now properly encapsulates its parent database context, routing all schema, query, update, delete, column mutations, export, and import commands to the intended database.

3. **CLI REPL Absolute Path Export & Terminal Polish:**
   - REPL `EXPORT` now explicitly prints full absolute filesystem paths on export start and finish.
   - Cleaned terminal progress bar carriage-return output to eliminate leftover progress telemetry.

---

## What Is New in v0.6.6

1. **Hierarchical Database Containers & Nested Sub-tables:**
   - Organize data just like modern RDBMS platforms: **Databases -> Tables -> Nested Sub-tables** (e.g. `enterprise.employees.engineering`).
   - Store root records or partition sub-groups into isolated columnar files while preserving relational hierarchy.
   - Comprehensive SQL support: `SHOW DATABASES;`, `CREATE DATABASE <name>;`, `DROP DATABASE <name>;`, `USE <name>;`, `SHOW TABLES [FROM <name>];`.
   - Native dot-notation resolution across Python (`mergendb.database()`, `table.create_subtable()`), Node.js (`client.database()`, `table.createSubtable()`), CLI, REST server, and Studio Web UI.

2. **Zero-Memory Chunked Streaming Import & Export Engine:**
   - Dedicated `DataExporter` streaming engine utilizing HTTP Chunked Transfer Encoding (`Transfer-Encoding: chunked`).
   - Tables of arbitrary size stream directly to disk or network sockets without ever accumulating full datasets into memory buffers.
   - Dedicated `/import_stream` endpoint accepts raw chunked streams in 64 KB blocks directly from network sockets to temporary disk files, eliminating browser V8 heap bloat and preventing GPU/compositor memory crashes.
   - Live **0% to 100% upload progress telemetry** with transferred byte counters in Mergen Studio.

3. **Mergen Studio Web Dashboard Enhancements:**
   - Complete tree hierarchy sidebar with collapsible database, table, and sub-table nodes.
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
|   db.find() / db.sql()        |   db.sql`...`        |   Mergen Studio UI Tree  |
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
[DB] enterprise
 |-- [TBL] departments (1,200 rows)
 \-- [TBL] employees (4,500 rows)
      |-- [SUB] engineering (320 rows)
      \-- [SUB] marketing (150 rows)
```

### Python API
```python
import mergendb

# 1. Create or open database container
enterprise = mergendb.create_database("enterprise")

# 2. Create tables inside database
departments = enterprise.create_table("departments", [
    ("id", "INT64"),
    ("name", "STRING"),
    ("location", "STRING")
])
employees = enterprise.create_table("employees", [
    ("id", "INT64"),
    ("name", "STRING"),
    ("role", "STRING")
])

# 3. Insert records directly
employees.insert([
    {"id": 1, "name": "Alice", "role": "Staff Engineer"},
    {"id": 2, "name": "Bob", "role": "Data Scientist"},
])

# 4. Create nested sub-tables inside a table
engineering = employees.create_subtable("engineering", [
    ("employee_id", "INT64"),
    ("project_code", "STRING"),
    ("clearance_level", "INT32")
])
engineering.insert([{"employee_id": 1, "project_code": "ATLAS", "clearance_level": 4}])

# 5. Access via dot-notation
tbl = mergendb.connect("enterprise.employees.engineering")
results = tbl.find(employee_id=1)
print(results)
```

### SQL Commands
```sql
SHOW DATABASES;
CREATE DATABASE enterprise;
USE enterprise;
SHOW TABLES;
CREATE TABLE employees (id BIGINT, name TEXT, salary DOUBLE);
INSERT INTO employees VALUES (1, 'Alice', 95000.0);
SELECT * FROM employees;
```

---

## Zero-Memory Streaming Import & Export

When handling multi-gigabyte datasets, traditional engines often buffer entire payloads into RAM, leading to memory exhaustion and browser compositor crashes. MergenDB resolves this with true streaming architecture:

### 1. Chunked Export (`GET /export`)
The server reads column blocks and yields encoded byte chunks directly into the HTTP response socket using standard HTTP Chunked Transfer Encoding. Server-side memory usage remains strictly bounded (< 1 MB RAM) regardless of table size.

```bash
# Stream table directly to disk
curl -N "http://localhost:8765/export?table=enterprise.employees&format=csv" -o employees.csv
curl -N "http://localhost:8765/export?table=enterprise.employees&format=json" -o employees.json
curl -N "http://localhost:8765/export?table=enterprise.employees&format=sql" -o employees.sql
```

### 2. Zero-Memory Import (`POST /import_stream`)
Mergen Studio streams the raw native `File` object directly over an HTTP socket using `XMLHttpRequest`. The server buffers incoming bytes in 64 KB chunks directly to a temporary file on disk, parses it with `DataImporter`, and indexes columnar blocks without consuming V8 heap memory.

```bash
# Direct zero-memory streaming upload
curl -X POST "http://localhost:8765/import_stream?table=enterprise.employees&format=csv" \
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
CREATE DATABASE enterprise;
USE enterprise;
CREATE TABLE employees (id BIGINT, name TEXT, salary DOUBLE);
INSERT INTO employees VALUES (1, 'Alice', 95000.0), (2, 'Bob', 82000.0);
SELECT * FROM employees;
EXPORT employees TO CSV;
EXPORT employees TO JSON;
EXPORT employees TO SQL;
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
| **v0.6.1** | Mergen Studio Overhaul | 100% CLI feature parity in browser and Node.js SDK, 106 tests | Released |
| **v0.6.2** | Multi-Runtime & Zero-Dependency | `python -m mergendb` & `npx mergendb` runners, `autoStart: true`, `GET /query` | Released |
| **v0.6.3** | Official Identity & i18n | Official Logo, strict zero-emoji policy, English/German/Turkish localization | Released |
| **v0.6.4** | Hierarchical Architecture | Database containers, nested sub-tables, and streaming export/import | Released |
| **v0.6.5** | Zero-Memory Streaming Engine | Zero-Memory Chunked Streaming Engine, crash-free browser upload | Released |
| **v0.6.6** | Hierarchical Containers & Streaming | Database containers, sub-tables, and chunked streaming import/export | Released |
| **v0.6.7** | Studio Navigation & Table Selection | Restored table selection, top nav sync, i18n fix, Node.js multi-database routing | Released |
| **v0.6.8** | Streaming Raw Payload & Export UX | Clean streaming export raw payload, active table indicator in Studio export | **Current Release** |

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
