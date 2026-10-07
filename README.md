<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="280" />
</p>

# MergenDB

> **The Ultra-Compact, High-Performance Embedded Columnar Database Engine & Vectorized SQL Processor for Python and Node.js**

[![PyPI version](https://img.shields.io/pypi/v/mergendb.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb.svg?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/mergendb.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![Socket PyPI Security Badge](https://badge.socket.dev/pypi/package/mergendb)](https://socket.dev/pypi/package/mergendb)
[![npm version](https://img.shields.io/npm/v/mergendb.svg?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/mergendb)
[![Socket npm Security Badge](https://badge.socket.dev/npm/package/mergendb)](https://socket.dev/npm/package/mergendb)
[![Dependencies](https://img.shields.io/badge/Dependencies-0%20(Zero)-success.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![Tests Passing](https://img.shields.io/badge/Tests-4600%2B%20(100%25%20Passed)-brightgreen.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

**MergenDB** is an ultra-compact, high-performance embedded columnar database engine engineered to process massive analytical workloads and multi-million row table scans on resource-constrained hardware. It delivers **strict zero external runtime dependencies** -- requiring no C compilers, no native C++ binaries, and no bulky runtimes across both Python and Node.js.

Whether scanning a 100-million row table on a 500 MB RAM VPS, streaming telemetry on an edge device, running real-time analytics in Node.js/TypeScript, or managing hierarchical databases through **Mergen Studio**, MergenDB provides columnar speed with bounded memory guarantees (< 20 MB peak RAM).

---

## Key Highlights

- **Vectorized Columnar Predicate Pushdown:** Point lookups and scalar filters (e.g. `WHERE token = "12345678901"` or `WHERE id = 5821049`) execute in **~1 second on 100M+ row tables**, directly evaluating binary byte streams at C level (`bytes.__contains__` Boyer-Moore-Horspool) without allocating Python string objects.
- **Zero External Dependencies:** Built purely on standard library primitives (`zlib`, `struct`, `mmap`, `json`, `http`). Zero third-party runtime bloat.
- **Strictly Bounded Memory (< 20 MB RAM):** Data streams in configurable column blocks (1,024 to 16,384 rows). Peak memory never grows with database file size.
- **Hierarchical Database Architecture:** Organize data natively: `Databases -> Tables -> Nested Sub-tables` (e.g. `enterprise.employees.engineering`) with dot-notation SQL queries.
- **Zero-Memory Streaming Engine:** Stream multi-gigabyte CSV, JSON, JSONL, and SQL dumps directly to disk or HTTP sockets in 64 KB chunks without buffering datasets into memory.
- **Dual Query Paradigm:** Full standard SQL engine (joins, multi-column `GROUP BY`, `HAVING`, aggregations) alongside Pythonic and JavaScript document-style APIs (`find`, `find_one`, `search`, `insert`, `update`, `delete`).
- **Adaptive Columnar Compression:** Automatic per-column encoding pipeline (Bit-packed booleans, Delta/FoR integers, Block Dictionary, Run-Length Encoding, and secondary Zlib compaction) delivering up to **50:1 compression ratio**.
- **1024-bit Block Bloom Filters & ZoneMaps:** Skips irrelevant blocks during point lookups with zero disk reads.
- **Fine-Grained Concurrency (RWLock):** Concurrent lock-free readers execute simultaneously while atomic writers stage changes with automatic rollback safety.
- **Mergen Studio Web UI:** Visual database explorer, interactive SQL console, schema inspector, and streaming transfer manager.

---

## Installation

### Python Engine & CLI

```bash
# Install core headless engine from PyPI
pip install --upgrade mergendb

# Optional: Install with Mergen Studio Web Management Dashboard
pip install --upgrade "mergendb[studio]"
```

### Node.js & TypeScript SDK

```bash
# Install official zero-dependency client SDK from npm
npm install mergendb
```

---

## Quickstart: Python

### 1. Basic Connect, Insert & SQL Querying

```python
import mergendb

# Connect to a table (auto-created on insert if it does not exist)
table = mergendb.connect("analytics.mgdb")

# Insert records - column data types are automatically inferred
table.insert([
    {"id": 1, "name": "Alice", "department": "Engineering", "salary": 95000, "active": True},
    {"id": 2, "name": "Bob", "department": "Design", "salary": 78000, "active": True},
    {"id": 3, "name": "Charlie", "department": "Engineering", "salary": 88000, "active": False},
    {"id": 4, "name": "Diana", "department": "Product", "salary": 110000, "active": True},
])

# Execute standard SQL with columnar filtering and sorting
result = table.sql("SELECT name, department, salary FROM analytics WHERE salary >= 85000 ORDER BY salary DESC;")
result.show()                  # Displays formatted ASCII table
records = result.to_dicts()    # Converts to Python dict list: [{'name': 'Diana', ...}]

# Analytical aggregations (Columnar GROUP BY)
summary = table.sql("SELECT department, COUNT(*), AVG(salary) FROM analytics GROUP BY department;")
summary.show()
```

### 2. Document-Style Lookups & Mutations

```python
# Instant point lookups
alice = table.find_one(name="Alice")
print(f"Alice: {alice['department']} | Salary: ${alice['salary']}")

# Multi-record query
engineers = table.find(department="Engineering")

# Full-text substring search across all columns
matches = table.search("Eng")

# Update records
table.update({"salary": 105000}, where="name = 'Alice'")

# Delete records
table.delete(where="active = False")
```

### 3. Streaming File Ingestion & Export

```python
# Export to CSV / JSON / SQL dump in streaming chunks
table.export_csv("backup.csv")
table.export_json("backup.json")
table.export_sql("backup.sql")

# Bulk ingest from CSV, SQLite, or SQL dumps at over 70,000+ rows/second
mergendb.from_csv("backup.csv", "restored.mgdb")
mergendb.from_sql_dump("dump.sql", "from_dump.mgdb")
```

---

## Quickstart: Node.js & TypeScript

The official Node.js driver is a pure HTTP/REST client built on native standard libraries (`http`, `https`, `stream`, `fs`) with **zero external npm dependencies**.

```javascript
const { connect } = require('mergendb');

async function main() {
  // Connect to running MergenDB instance (default: http://127.0.0.1:8765)
  const client = connect({
    host: '127.0.0.1',
    port: 8765,
    user: 'root',
    password: ''
  });

  const users = client.table('users.mgdb');

  // Insert records
  await users.insert([
    { id: 1, name: "Alice", role: "admin", department: "Engineering", salary: 95000 },
    { id: 2, name: "Bob", role: "user", department: "Design", salary: 78000 },
    { id: 3, name: "Charlie", role: "user", department: "Engineering", salary: 88000 },
    { id: 4, name: "Diana", role: "manager", department: "Product", salary: 110000 },
  ]);

  // Safe parameterized SQL using tagged template literals
  const minSalary = 80000;
  const res = await client.sql`SELECT name, department, salary FROM users.mgdb WHERE salary >= ${minSalary} ORDER BY salary DESC;`;
  console.table(res.rows);

  // Document methods
  const alice = await users.findOne({ name: "Alice" });
  console.log("Alice:", alice);

  // Update & Delete
  await users.update({ salary: 105000 }, "name = 'Alice'");
  await users.delete("role = 'user'");

  // Zero-memory streaming export and import
  await users.exportToFile("users_backup.csv", "csv");
  await users.importFile("users_backup.csv", "csv");
}

main().catch(console.error);
```

---

## Hierarchical Database Containers & Nested Sub-tables

MergenDB supports relational database hierarchy while retaining columnar performance:

```text
[DB] enterprise
 |-- [TBL] departments (1,200 rows)
 \-- [TBL] employees (4,500 rows)
      |-- [SUB] engineering (320 rows)
      \-- [SUB] marketing (150 rows)
```

```python
import mergendb

# 1. Create or open database container
enterprise = mergendb.create_database("enterprise")

# 2. Create tables inside database
employees = enterprise.create_table("employees", [
    ("id", "INT64"),
    ("name", "STRING"),
    ("role", "STRING")
])
employees.insert([{"id": 1, "name": "Alice", "role": "Lead Architect"}])

# 3. Create nested sub-tables
engineering = employees.create_subtable("engineering", [
    ("employee_id", "INT64"),
    ("project_code", "STRING")
])
engineering.insert([{"employee_id": 1, "project_code": "ATLAS"}])

# 4. Access via dot-notation
tbl = mergendb.connect("enterprise.employees.engineering")
print(tbl.find(employee_id=1))
```

---

## Mergen Studio Web Management Dashboard

Mergen Studio provides an interactive web-based graphical interface for database administration, visual table inspection, real-time query execution, and streaming file transfers.

```bash
# Launch server and access Studio
mergen serve 8765
```

Navigate to `http://localhost:8765/studio` in any browser:
- **Hierarchical Sidebar:** Expand and inspect databases, tables, and nested sub-tables.
- **SQL Console:** Syntax highlighting, query history, and execution benchmarks.
- **Data & Structure Browser:** Dynamic grid rendering column data types even for empty tables.
- **Streaming Transfer Hub:** Real-time upload/download progress counters with chunked memory safety.
- **Authentication:** Role-based access control (default credentials: `root:`).

---

## Interactive CLI REPL

Launch the interactive shell directly from your terminal:

```bash
mergen
```

```sql
mergen> SHOW DATABASES;
mergen> CREATE DATABASE analytics;
mergen> USE analytics;
mergen> CREATE TABLE metrics (id BIGINT, host TEXT, latency DOUBLE);
mergen> INSERT INTO metrics VALUES (1, 'prod-srv-01', 14.2), (2, 'prod-srv-02', 8.7);
mergen> SELECT host, AVG(latency) FROM metrics GROUP BY host;
mergen> EXPORT metrics TO CSV;
```

---

## Adaptive Columnar Compression

When persisting column blocks, MergenDB inspects data distributions and dynamically selects the optimal encoding:

| Encoding | Targeted Data Type | Mechanics |
| :--- | :--- | :--- |
| **Bit-Packed Booleans** | Booleans | 1 bit per value (8 rows per byte) |
| **Delta / FoR** | Sequential & clustered integers | Frame-of-Reference offsets from block minimum |
| **Block Dictionary** | Low-cardinality text (gender, country, status) | Stores unique values once; rows encoded as 1-byte indices |
| **Run-Length (RLE)** | Repeated consecutive values | Collapses sequences into `(count, value)` pairs |
| **Secondary Zlib** | Compressed payloads | Byte-level stream compaction |

---

## Performance Benchmarks

Measured on standard hardware with 100,000 mixed records (12 columns: integers, floats, timestamps, statuses, long strings):

| Storage Format | Disk Size | Space Saved | 2-Column Query Disk Read | Peak RAM |
| :--- | :--- | :--- | :--- | :--- |
| **JSON Lines (`.jsonl`)** | 19.5 MB | 0% (Baseline) | 19.5 MB | Unbounded |
| **SQLite 3 (`.db`)** | 8.1 MB | 58.4% | 8.1 MB (reads full row) | ~30 MB |
| **MergenDB (`.mgdb`)** | **1.6 MB** | **91.5%** | **0.29 MB (pruned)** | **< 15 MB RAM** |

- **Vectorized Predicate Pushdown (100M+ Rows):** ~1.0 second point lookups.
- **Exact Filter Scan Throughput:** ~50,000,000 rows/second (single CPU core).
- **SQL Streaming Import Speed:** ~70,000 - 120,000 rows/second on standard NVMe SSD.

---

## Test Suite & Reliability

MergenDB is verified with **over 4,600 automated tests** (2,600+ Python tests and 2,000+ Node.js tests) covering:
- Storage, block encoding, and adaptive compression roundtrips.
- Fault tolerance against ragged rows, corrupt headers, escaped SQL quotes, and zero-byte boundaries.
- Concurrency, thread safety, and RWLock staging verification.
- 100% pass rate across Windows, macOS, Linux, and Docker.

```bash
# Run Python test suite
python -m unittest discover -s tests

# Run Node.js SDK test suite
node sdks/nodejs/test.js
```

---

## License & Credits

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.

Developed by **[Uğur Türker Kebeci](https://github.com/ugurturkerkebeci)**.
