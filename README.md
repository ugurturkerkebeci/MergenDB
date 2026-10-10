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
[![Socket npm Security Badge](https://badge.socket.dev/npm/package/mergendb)](https://badge.socket.dev/npm/package/mergendb)
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

- **Sub-Second 100M+ Row Columnar Scans:** Point lookups and scalar filters (e.g. `WHERE phone = '0532...'` or `WHERE device_id = 5821049`) execute in **< 100 milliseconds on 100M+ row tables**, directly evaluating binary byte streams at C level (`bytes.translate`, `mmap`) with zero Python object allocation overhead.
- **Lazy Metadata Initialization (`LazyBlockList`):** Table opening overhead on multi-million row tables dropped from 3.5s to **0.0001 seconds**, deferring block parsing until individual blocks are accessed.
- **Selective Late Materialization:** Only matching rows decode dictionary values (`decode_dict_indices`), bypassing decompression of thousands of unneeded rows and speeding up sparse queries by up to **25x**.
- **Fault-Tolerant Streaming Ingestion (> 5M rows/s):** Robust parallel byte-range parser seamlessly processes ragged rows, escaped quotes, missing fields, null bytes (`\x00`), and diverse encodings without dropping tables or crashing.
- **Zero External Dependencies:** Built purely on standard library primitives (`zlib`, `struct`, `mmap`, `json`, `http`). Zero third-party runtime bloat in production environments.
- **Strictly Bounded Memory (< 20 MB RAM):** Data streams in configurable column blocks (1,024 to 65,536 rows). Peak memory never grows with database file size.
- **Hierarchical Database Architecture:** Organize data natively: `Databases -> Tables -> Nested Sub-tables` (e.g. `enterprise.orders.shipments`) with dot-notation SQL queries.
- **Zero-Memory Streaming Engine:** Stream multi-gigabyte CSV, JSON, JSONL, and SQL dumps directly to disk or HTTP sockets in 64 KB chunks without buffering datasets into memory.
- **Dual Query Paradigm:** Full standard SQL engine (joins, multi-column `GROUP BY`, `HAVING`, aggregations) alongside Pythonic and JavaScript document-style APIs (`find`, `find_one`, `search`, `insert`, `update`, `delete`, `upsert`).
- **Adaptive Columnar Compression:** Automatic per-column encoding pipeline (Bit-packed booleans, Delta/FoR integers, Block Dictionary, Run-Length Encoding, and secondary Zlib compaction) delivering up to **50:1 compression ratio**.
- **Dynamic Block Bloom Filters & ZoneMaps:** Skips irrelevant blocks during point lookups with zero disk reads.
- **Fine-Grained Concurrency (RWLock):** Concurrent lock-free readers execute simultaneously while atomic writers stage changes with automatic rollback safety.
- **Mergen Studio Web UI:** Visual database explorer, interactive SQL console, schema inspector, and streaming transfer manager.
- **Strict Zero-Emoji Policy:** Clean, professional interface built with deterministic status tags (`[+]`, `[-]`, `[*]`, `[!]`).

---

## Installation

### Python SDK & Core Engine

```bash
pip install --upgrade mergendb
```

To include the optional web dashboard extension:

```bash
pip install --upgrade "mergendb[studio]"
```

### Node.js & TypeScript SDK

```bash
npm install mergendb
```

---

## Quickstart

### Python Quickstart (Universal IoT Telemetry Example)

```python
import mergendb

# 1. Connect to local table (auto-created if absent)
telemetry = mergendb.connect("iot_telemetry.mgdb")

# 2. Define schema if empty
if telemetry.row_count == 0:
    telemetry.create_schema([
        ("device_id", "INT64"),
        ("station_code", "STRING"),
        ("temperature", "DOUBLE"),
        ("humidity", "DOUBLE"),
        ("is_active", "BOOLEAN")
    ])

# 3. Insert universal records
telemetry.insert([
    {"device_id": 101, "station_code": "US-EAST-01", "temperature": 21.4, "humidity": 48.2, "is_active": True},
    {"device_id": 102, "station_code": "EU-WEST-02", "temperature": 18.9, "humidity": 55.0, "is_active": True},
    {"device_id": 103, "station_code": "AP-SOUTH-01", "temperature": 31.2, "humidity": 72.1, "is_active": False}
])

# 4. Analytical SQL aggregation
res = telemetry.sql("""
    SELECT station_code, AVG(temperature) AS avg_temp, MAX(humidity) AS max_hum
    FROM iot_telemetry
    WHERE is_active = true
    GROUP BY station_code
    ORDER BY avg_temp DESC;
""")
print(res.display())

# 5. Fluent Query Builder
active_stations = (
    telemetry.query()
             .select("station_code", "temperature")
             .where("temperature > 20.0")
             .order_by("temperature", desc=True)
             .limit(10)
             .to_dicts()
)
print("Active Stations:", active_stations)
```

---

### Node.js & TypeScript Quickstart

```javascript
import { connect } from 'mergendb';

const db = connect({
  host: '127.0.0.1',
  port: 8765,
  user: 'root',
  password: ''
});

async function main() {
  // 1. Create table
  const telemetry = await db.createTable('iot_telemetry', [
    { name: 'device_id', type: 'INT64' },
    { name: 'station_code', type: 'STRING' },
    { name: 'temperature', type: 'DOUBLE' },
    { name: 'humidity', type: 'DOUBLE' },
    { name: 'is_active', type: 'BOOLEAN' }
  ]);

  // 2. Insert records
  await telemetry.insert([
    { device_id: 101, station_code: 'US-EAST-01', temperature: 21.4, humidity: 48.2, is_active: true },
    { device_id: 102, station_code: 'EU-WEST-02', temperature: 18.9, humidity: 55.0, is_active: true }
  ]);

  // 3. Safe parameterized SQL via tagged template literal
  const minTemp = 20.0;
  const results = await db.sql`
    SELECT station_code, AVG(temperature) AS avg_temp
    FROM iot_telemetry
    WHERE temperature >= ${minTemp} AND is_active = true
    GROUP BY station_code;
  `;
  console.table(results.toObjects());

  // 4. Fluent Query Builder
  const highTemp = await telemetry.query()
    .select('device_id', 'station_code', 'temperature')
    .where('temperature > 20.0')
    .orderBy('temperature', true)
    .limit(5)
    .toObjects();
  console.log('High Temp Readings:', highTemp);
}

main().catch(console.error);
```

---

## Complete Command & API Reference (Python vs JavaScript / TypeScript)

MergenDB maintains 100% feature symmetry across Python and Node.js/TypeScript:

### 1. Connection & Server Management

| Operation | Python | JavaScript / TypeScript (Node.js) | Description |
| :--- | :--- | :--- | :--- |
| **Embedded Connection** | `db = mergendb.connect("data.mgdb")` | *(Runs via HTTP server / REST)* | Connects or auto-creates a local embedded database table. |
| **Remote Client** | `client = mergendb.connect("http://127.0.0.1:8765")` | `const client = connect({ host: "127.0.0.1", port: 8765 })` | Connects to a running MergenDB instance over HTTP/REST. |
| **Server Diagnostics** | `client.status()` | `await client.status()` | Retrieves hardware diagnostics, CPU info, and database metrics. |
| **Scan Benchmark** | `client.benchmark()` | `await client.benchmark()` | Measures device columnar scan throughput (rows/sec). |

---

### 2. Database Containers & Schema Management

| Operation | Python | JavaScript / TypeScript (Node.js) | Description |
| :--- | :--- | :--- | :--- |
| **List Databases** | `mergendb.list_databases()` | `await client.listDatabases()` | Discovers all database container directories. |
| **Create Database** | `mergendb.create_database("finance")` | `await client.createDatabase("finance")` | Creates an isolated database container directory. |
| **Drop Database** | `mergendb.drop_database("finance")` | `await client.dropDatabase("finance")` | Permanently deletes a database container. |
| **Create Table** | `db.create_table("orders", [("id", "INT64")])` | `await db.createTable("orders", [{ name: "id", type: "INT64" }])` | Creates a new columnar table. |
| **List Tables** | `db.list_tables()` | `await db.listTables()` | Lists tables in workspace or active database. |
| **Drop Table** | `db.drop_table("orders")` | `await db.dropTable("orders")` | Permanently drops a table. |
| **Truncate Table** | `table.truncate()` | `await table.truncate()` | Empties all rows while preserving schema. |
| **Add Column** | `table.add_column("tax", "DOUBLE", default=0.0)` | `await table.addColumn("tax", "DOUBLE", 0.0)` | Adds new column without data rewrite. |
| **Drop Column** | `table.drop_column("tax")` | `await table.dropColumn("tax")` | Prunes column definition from table. |
| **Rename Column** | `table.rename_column("old_col", "new_col")` | `await table.renameColumn("old_col", "new_col")` | Renames column identifier without data loss. |

---

### 3. Data Mutation (CRUD & Optimization)

| Operation | Python | JavaScript / TypeScript (Node.js) | Description |
| :--- | :--- | :--- | :--- |
| **Single / Batch Insert** | `table.insert([{"id": 1, "sku": "A1"}])` | `await table.insert([{ id: 1, sku: "A1" }])` | Ingests dictionary/object records into column blocks. |
| **Chunked Batch Insert** | `table.batch_insert(rows, batch_size=5000)` | `await table.batchInsert(rows, 5000)` | Memory-safe chunked insertion for massive datasets. |
| **Atomic Upsert** | `table.upsert({"id": 1, "status": "shipped"}, key_column="id")` | `await table.upsert({ id: 1, status: "shipped" }, "id")` | Updates row if primary key exists; inserts if absent. |
| **Update Rows** | `table.update({"status": "archived"}, where="id > 100")` | `await table.update({ status: "archived" }, "id > 100")` | Updates matching records. |
| **Delete Rows** | `table.delete(where="status = 'cancelled'")` | `await table.delete("status = 'cancelled'")` | Deletes matching records. |

---

### 4. Querying & Analytics

| Operation | Python | JavaScript / TypeScript (Node.js) | Description |
| :--- | :--- | :--- | :--- |
| **Standard SQL** | `res = table.sql("SELECT * WHERE price > 50")` | `const res = await table.sql("SELECT * WHERE price > 50")` | Executes SQL on table. |
| **Find (Document Style)**| `rows = table.find(category="electronics", limit=10)` | `const rows = await table.find({ category: "electronics" }, { limit: 10 })` | Key-value matching filter. |
| **Find One** | `record = table.find_one(sku="SKU-001")` | `const record = await table.findOne({ sku: "SKU-001" })` | Retrieves first matching record. |
| **First Record** | `record = table.first(where="active = True")` | `const record = await table.first("active = true")` | Retrieves first matching record. |
| **Last Record** | `record = table.last(where="active = True")` | `const record = await table.last("active = true")` | Retrieves last matching record. |
| **Take N Rows** | `sample = table.take(5)` | `const sample = await table.take(5)` | Retrieves the first N rows as dictionary list. |
| **All Rows** | `all_rows = table.all(limit=100)` | `const all_rows = await table.all(100)` | Retrieves all rows up to limit. |
| **Check Exists (O(1))**| `has_admin = table.exists(role="admin")` | `const hasAdmin = await table.exists({ role: "admin" })` | Fast early-exit boolean check. |
| **Full-Text Search** | `matches = table.search("New York")` | `const matches = await table.search("New York")` | Substring search across all `STRING` columns. |
| **Pluck Columns** | `emails = table.pluck("email")` | `const emails = await table.pluck("email")` | Extracts single column as flat array without overhead. |
| **Distinct Values** | `regions = table.distinct("region")` | `const regions = await table.distinct("region")` | Returns unique column values as set-based list. |
| **Sum** | `table.sum("revenue", where="active = True")` | `await table.sum("revenue", "active = true")` | Sums numeric column. |
| **Average (Avg)** | `table.avg("latency")` | `await table.avg("latency")` | Computes column arithmetic mean. |
| **Min / Max** | `table.min("price")` / `table.max("price")` | `await table.min("price")` / `await table.max("price")` | Computes minimum or maximum value. |

---

### 5. Fluent Query Builder (`query()` / `builder()`)

Method-chaining syntax for readable analytical queries:

```python
# Python
orders = (
    table.query()
         .select("order_id", "customer_id", "total_amount", "status")
         .where("total_amount >= 150.00")
         .filter(status="completed")
         .order_by("total_amount", desc=True)
         .limit(20)
         .offset(40)
         .to_dicts()
)
```

```javascript
// JavaScript / TypeScript
const orders = await table.query()
  .select('order_id', 'customer_id', 'total_amount', 'status')
  .where('total_amount >= 150.00')
  .filter({ status: 'completed' })
  .orderBy('total_amount', true)
  .limit(20)
  .offset(40)
  .toObjects();
```

---

### 6. Zero-Memory Streaming File Transfers

Stream multi-gigabyte files directly to disk or network sockets without memory buffering:

| Operation | Python | JavaScript / TypeScript (Node.js) |
| :--- | :--- | :--- |
| **Export to CSV** | `table.export_csv("backup.csv")` | `await table.exportToFile("backup.csv", "csv")` |
| **Export to JSON** | `table.export_json("backup.json")` | `await table.exportToFile("backup.json", "json")` |
| **Export to JSON Lines** | `table.export_jsonl("backup.jsonl")` | `await table.exportToFile("backup.jsonl", "jsonl")` |
| **Export to SQL Dump** | `table.export_sql("backup.sql")` | `await table.exportToFile("backup.sql", "sql")` |
| **Import from CSV** | `table.import_csv("data.csv")` | `await table.importFile("data.csv", "csv")` |
| **Import from SQL Dump**| `table.import_sql("dump.sql")` | `await table.importFile("dump.sql", "sql")` |

---

## Interactive CLI REPL

Launch the interactive terminal shell:

```bash
mergen
```

```sql
mergen> SHOW TABLES;
mergen> USE iot_telemetry;                      -- Smart context: selects table 'iot_telemetry.mgdb'
mergen[iot_telemetry.mgdb]> WHERE device_id = 101;  -- Direct filter query on active table (ZoneMap pruned)
mergen[iot_telemetry.mgdb]> USE DATABASE analytics; -- Explicitly switch database container
mergen(analytics)> SHOW TABLES;
mergen(analytics)> USE TABLE metrics;          -- Explicitly select table inside database
mergen(analytics)[metrics.mgdb]> SELECT host, AVG(latency) FROM metrics GROUP BY host;
mergen(analytics)[metrics.mgdb]> EXPORT metrics TO CSV;
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

## Adaptive Columnar Compression

When persisting column blocks, MergenDB inspects data distributions and dynamically selects the optimal hardware encoding:

| Encoding | Targeted Data Type | Mechanics |
| :--- | :--- | :--- |
| **Bit-Packed Booleans** | Booleans | 1 bit per value (8 rows per byte) |
| **Delta / FoR** | Sequential & clustered integers | Frame-of-Reference offsets from block minimum |
| **Block Dictionary** | Low-cardinality text (status, category, country) | Stores unique values once; rows encoded as 1-byte indices |
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

- **Sub-Second Columnar Scan (100M+ Rows):** < 100ms point lookups, ~400,000,000 - 500,000,000 rows/second analytical scan.
- **Selective Late Materialization:** ~30,000,000 - 50,000,000 rows/second on complex multi-column filters.
- **Fault-Tolerant Parallel Import:** ~5,300,000+ rows/second on standard NVMe SSDs.
- **Streaming Table Export Speed:** ~5,600,000+ rows/second directly to disk or network sockets.

---

## Test Suite & Verification

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

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
