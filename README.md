<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

# MergenDB

[![PyPI version](https://img.shields.io/badge/PyPI-v0.6.1-blue?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![npm version](https://img.shields.io/npm/v/mergendb.svg?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/mergendb)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Tests](https://img.shields.io/badge/Tests-88%20Python%20%7C%2018%20Node.js%20(100%25%20Pass)-brightgreen.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![Author](https://img.shields.io/badge/Author-U%C4%9Fur%20T%C3%BCrker%20Kebeci-orange.svg?style=flat-square)](https://github.com/ugurturkerkebeci)

**MergenDB** is a lightweight, ultra-fast embedded columnar database engine and ecosystem designed to run massive analytical queries and multi-million row table scans on small, resource-constrained hardware. It delivers **zero external runtime dependencies** — no C compilers, no native C++ libraries, and no bulky runtimes across both Python and Node.js.

Whether you're querying a 10-million row dataset on a 500 MB RAM VPS, analyzing sensor telemetry on a Raspberry Pi, streaming analytics inside a modern Next.js/Express app, or embedding a blazing-fast local analytical store inside your Python application, MergenDB gives you columnar performance without the operational headache.

---

## 📦 Installation

### Python Engine & CLI
```bash
pip install --upgrade mergendb
```

### Node.js & TypeScript SDK
```bash
npm install mergendb
```

Requires **Python 3.8** or newer. Works seamlessly on Windows, macOS, Linux, and Docker.

---

## 💡 Why MergenDB? (The Problem with Row Stores)

Traditional embedded databases like SQLite store data row-by-row (`[id, name, age, address, notes, ...]`). When you run an analytical query like:

```sql
SELECT name, balance FROM users WHERE balance > 1000;
```

Even though you only care about `name` and `balance`, row stores must read **every single column of every row** off disk — including massive text columns like `address` and `notes`. On a 10-million row database, that translates to gigabytes of useless disk I/O and heavy memory exhaustion.

**MergenDB takes the modern columnar approach:**
1. **Column-Isolated I/O:** Every column is stored and compressed independently. Unqueried columns are never read from disk.
2. **ZoneMap Pruning:** Every block records `min_value` and `max_value`. If a block cannot contain matching rows, it is skipped with zero disk reads.
3. **1024-bit Block Bloom Filters:** Instant single-pass lookup index skips blocks that do not contain a queried ID, text, or UUID.
4. **Demand-Driven Late Materialization (`LazyColumnDict`):** In multi-column filters (`WHERE status = 'ACTIVE' AND balance > 50`), MergenDB checks `status` first. If no rows in the block match, `balance` and all other columns are never decompressed.
5. **Strictly Bounded Memory:** Data streams in small, tunable blocks (1,024–8,192 rows). Memory usage stays under **15–20 MB RAM**, whether your database is 100 MB or 100 GB.

---

## 🏛️ MergenDB v0.6+ Ecosystem Architecture

```text
+---------------------------------------------------------------------------------+
|                                 CLIENT LAYER                                    |
|   Python Library (mergendb)   |   Node.js / TS SDK   |   Mergen Studio (Web)    |
|   db.find() / db.sql()        |   db.sql`...`        |   phpMyAdmin UI Grid     |
+---------------------------------------+-----------------------------------------+
                                        | HTTP / REST (Zero-Dependency)
+---------------------------------------v-----------------------------------------+
|                                SERVER ENGINE                                    |
|   Multi-threaded HTTP Server  |  Smart Content-Negotiation  |  Progress Stream  |
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

## 5-Minute Quickstart

### 1. The Human-Friendly Python API

You don't need to manually define schemas or data types unless you want to. Just connect and insert:

```python
import mergendb

# 1. Connect to a database file (created automatically if it doesn't exist)
db = mergendb.connect("users.mgdb")

# 2. Insert records using plain Python dictionaries (Schema is auto-inferred!)
db.insert([
    {"id": 1, "name": "Alice", "role": "admin", "balance": 1500, "city": "San Francisco"},
    {"id": 2, "name": "Bob", "role": "engineer", "balance": 2400, "city": "New York"},
    {"id": 3, "name": "Charlie", "role": "designer", "balance": 1800, "city": "London"},
    {"id": 4, "name": "Diana", "role": "admin", "balance": 3200, "city": "Tokyo"},
])

print(f"Total Rows: {len(db)}")  # 4
print(f"Columns: {db.columns}")   # ['id', 'name', 'role', 'balance', 'city']
```

### 2. Querying with Simple Key-Value Filters (`.find`)

Find records with zero SQL boilerplate:

```python
# Multiple conditions: role == 'admin' AND city == 'Tokyo'
results = db.find(role="admin", city="Tokyo")
print(results.to_dicts())
# [{'id': 4, 'name': 'Diana', 'role': 'admin', 'balance': 3200, 'city': 'Tokyo'}]

# Fetch the first match directly as a dict
user = db.find_one(name="Alice")
print(user["city"])  # "San Francisco"
```

### 3. Full-Text Search Across All Text Columns (`.search`)

Search for any substring across all string columns with case-insensitivity:

```python
matches = db.search("admin")
matches.show()
```

### 4. Running Standard SQL Queries (`.sql`)

```python
result = db.sql("SELECT id, name, balance FROM users WHERE balance >= 50 ORDER BY id DESC")

# Print a formatted ASCII table
result.show()

# Iterate over matching rows
for row in result:
    print(row)

# Convert directly to a pandas DataFrame (if pandas is installed)
df = result.to_df()
```

### 5. Updating & Deleting Records (`.update`, `.delete`)

All row mutations execute with streaming block preservation to keep memory under 20 MB:

```python
# Update balance for matching records
updated = db.update({"balance": 999}, where="name = 'Alice'")
print(f"Updated {updated} records")

# Delete inactive or zero-balance records
deleted = db.delete(where="balance <= 0 OR active = false")
print(f"Deleted {deleted} records")
```

### 6. Modifying Table Schema (`.rename_column`, `.drop_column`, `.add_column`)

Instantly alter table layout without losing data:

```python
# Rename a column
db.rename_column("name", "full_name")

# Add a new column with a default value
db.add_column("country", "string", default="US")

# Drop an unneeded column
db.drop_column("city")
```

### 7. Diagnostics & Hardware Profiling (`mergendb.test()`, `mergen test`)

MergenDB includes an integrated, zero-dependency diagnostic suite and hardware benchmarking engine. In under 1 second, it verifies the entire engine pipeline (Zero-Copy mmap I/O, dictionary pushdown, ZoneMap skipping, mutations), tests the MergenQL network server over HTTP, and benchmarks your device's realistic processing capabilities:

```python
import mergendb

# Run full system diagnostics and hardware throughput benchmark
mergendb.test()
```

Or directly from the terminal or CLI REPL:
```bash
# From terminal
mergen test

# Inside interactive REPL
mergen> TEST;
```

#### Diagnostic Output Sample:
```text
==========================================================================
   [+] MERGENDB SYSTEM DIAGNOSTICS & HARDWARE PROFILER
==========================================================================
[*] Running engine core integrity checks...
    [+] Zero-Copy mmap I/O          : PASS
    [+] Dictionary Pushdown Engine : PASS
    [+] ZoneMap Block Pruning      : PASS
    [+] ACID Data & Schema Mutation: PASS
[*] Verifying MergenQL Network HTTP Server...
    [+] HTTP Endpoint /status      : PASS (Port 54664)
    [+] POST /query SQL Dispatch   : PASS
[*] Profiling device hardware and benchmarking throughput...

--------------------------------------------------------------------------
  [DEVICE HARDWARE SPECIFICATIONS & DETECTED ENVIRONMENT]
--------------------------------------------------------------------------
  * Operating System   : Windows 10 / Linux 6.x / macOS
  * CPU Architecture   : AMD64 / ARM64 (12 logical threads)
  * Python Runtime     : CPython 3.8+
  * Engine Version     : v0.5.3 (Pure Python / Zero-Dependency)

--------------------------------------------------------------------------
  [ESTIMATED PROCESSING SPEEDS FOR THIS HARDWARE]
--------------------------------------------------------------------------
  * Ingestion / Append : ~216,558 rows/sec
  * CSV / SQL Import   : ~220,762 rows/sec
  * Table Export       : ~749,968 rows/sec
  * Analytical Queries : ~1,417,836 rows/sec (Zero-Copy Column Scan)
  * Performance Tier   : A-Tier (Performance Desktop / Modern Laptop)
  * Optimal Block Size : 2,048 - 4,096 rows
  * Assessment         : High single-core speed and fast page cache.
--------------------------------------------------------------------------
  [SUCCESS] ALL CHECKS PASSED PERFECTLY in 0.68s
==========================================================================
```

### 8. Embedded Web UI: "Mergen Studio" (phpMyAdmin Edition)

MergenDB includes **Mergen Studio**, an ultra-fast, zero-dependency interactive web dashboard inspired by phpMyAdmin. Launch it with a single command:

```bash
# Start server and launch Mergen Studio
mergen serve
# Or specify a custom port
mergen serve 8765
```

Open your browser to:
👉 **`http://localhost:8765/studio`** (or simply `http://localhost:8765/`)

**Key Capabilities in Mergen Studio (phpMyAdmin Edition):**
- **🎯 Active Data File Selector:** Switch between `.mgdb` tables via the top navigation dropdown or sidebar. All tabs automatically bind to the selected table.
- **👁️ Browse (Gözat):** Interactive spreadsheet grid with pagination (`<< < Page 1/10 > >>`), sortable column headers (`▲▼`), row range indicators, and inline inspection.
- **📋 Structure (Yapı / Şema):** View column names, data types, nullability, block counts, and disk size. Add new columns dynamically with default values or drop unused columns.
- **🔍 SQL:** Large interactive query editor with one-click snippets (`SELECT *`, `COUNT(*)`, `GROUP BY + HAVING`, `Bloom Filter`, `Hash JOIN`), execution stats (`ms`, blocks scanned vs skipped via ZoneMaps), and `Ctrl+Enter` hotkey.
- **📥 Import (İçe Aktar):** Drag-and-drop or select `.csv`, `.sql`, or `.json` files to stream data directly into any `.mgdb` table.
- **📤 Export (Dışa Aktar):** One-click download of tables to `CSV`, `JSON`, `JSONL`, or `SQL Dump (INSERT statements)`.
- **⚙️ Operations (İşlemler):** Rename tables (`RENAME`), clear data while keeping schema (`TRUNCATE`), or permanently delete (`DROP`).
- **📈 Universal Percentage Progress Bar (%0.0 -> %100.0):** Active on **all waiting operations** (browse loading, SQL queries, import, export, table operations) showing live progress %, throughput (~rows/sec), and ETA countdown!

---

### 9. Universal Node.js & TypeScript Client SDK

MergenDB includes an official **zero-dependency** Node.js and TypeScript client SDK (`mergendb`). Connect your Node.js, Express, Next.js, or NestJS backend to MergenDB with full analytical SQL and document-style APIs:

```bash
# Install via npm
npm install mergendb
```

#### JavaScript / TypeScript Example:

```typescript
import { connect } from 'mergendb';

async function run() {
  // Connect to MergenDB server
  const db = connect('http://localhost:8765');

  // Ping server health
  const isHealthy = await db.ping();
  console.log('MergenDB status:', isHealthy ? 'ONLINE' : 'OFFLINE');

  // Analytical SQL Query with execution telemetry
  const result = await db.query(
    "SELECT sensor, COUNT(*), AVG(temperature) FROM telemetry GROUP BY sensor HAVING COUNT(*) > 100"
  );
  console.log(`Scanned in ${result.stats.execution_time_ms} ms (Pruned blocks: ${result.stats.blocks_skipped})`);
  console.table(result.rows);

  // Safe tagged template literals with parameter escaping
  const status = 'ACTIVE';
  const sensors = await db.sql`SELECT id, sensor, temperature FROM telemetry WHERE status = ${status}`;
  console.log(`Found ${sensors.row_count} active sensors`);

  // Document-style Table API
  const table = db.table('telemetry.mgdb');
  const activeSensors = await table.find({ status: 'ACTIVE' }, { limit: 10 });
  const count = await table.count({ status: 'ERROR' });

  // Administrative actions
  await table.truncate(); // Clear rows, preserve schema
  await table.drop();     // Drop table file
}

run().catch(console.error);
```

---

## Python API Reference

MergenDB provides both a clean, high-level developer API and low-level engine primitives.

### Top-Level Module Functions

```python
import mergendb

# Open or create a table
db = mergendb.connect("data.mgdb")
db = mergendb.open("data.mgdb")

# Direct queries without creating a connection object
res = mergendb.sql("SELECT * FROM 'data.mgdb' WHERE status = 'active'")
res = mergendb.find("data.mgdb", status="active", role="admin")
res = mergendb.search("data.mgdb", "search_term")

# Streaming data migration
mergendb.import_sql("dump.sql", "output.mgdb")
mergendb.import_sqlite("legacy.db", "output.mgdb", table_name="customers")
mergendb.import_csv("records.csv", "output.mgdb")

# Table exports
mergendb.export_csv("data.mgdb", "output.csv")
mergendb.export_json("data.mgdb", "output.jsonl")
mergendb.export_sql("data.mgdb", "output.sql")
```

---

### `mergendb.Table` / `mergendb.Database`

The primary object representing an `.mgdb` table.

| Method / Property | Description |
| :--- | :--- |
| `db.columns` | Returns a `List[str]` of column names. |
| `db.schema` | Returns the `Schema` object with column names and `DataType`s. |
| `db.row_count` / `len(db)` / `db.count()` | Returns the total number of rows. |
| `db.find(limit=None, **kwargs)` | Filters rows by exact key-value match. Returns `QueryResult`. |
| `db.find_one(**kwargs)` | Returns the first matching row as a `dict`, or `None`. |
| `db.first(where=None)` | Returns the first row in the table, optionally filtered. |
| `db.where(condition, limit=None)` | Filters by raw SQL condition (`"age > 21 AND active = 1"`). |
| `db.search(text, limit=None)` | Searches all string columns for substring `text`. |
| `db.select(*cols, where, order_by, limit)` | Fluent query builder. |
| `db.sql(query_str)` | Executes a standard SQL query string on this table. |
| `db.execute(query_or_sql)` | Executes SQL or MergenQL pipeline query. |
| `db.insert(data)` | Inserts a single dict, list of dicts, or list of row lists. Auto-creates table if missing. |
| `db.insert_many(rows, block_size=1024)` | Inserts a list of raw value rows into the columnar storage. |
| `db.update(set_values, where=None)` | Updates matching rows with `{col: val}` mapping. Returns updated count. |
| `db.delete(where=None)` | Deletes matching rows from the table. Returns deleted count. |
| `db.rename_column(old_name, new_name)` | Renames an existing column without data loss. |
| `db.drop_column(column_name)` | Removes a column from the schema and table file. |
| `db.add_column(column_name, data_type, default=None)` | Adds a new column with a default value. |
| `db.truncate()` | Clears all rows while keeping schema and structure intact. |
| `db.drop()` | Permanently deletes the table file from disk. |
| `db.rename(new_filepath)` | Renames the table file on disk. |
| `db.all(limit=None)` | Returns all rows as a list of dictionaries (`List[Dict[str, Any]]`). |
| `db.to_dicts(limit=None)` | Returns rows as dictionaries. |
| `db.to_list(limit=None)` | Returns rows as a raw list of lists (`List[List[Any]]`). |
| `db.to_df(limit=None)` | Converts rows into a `pandas.DataFrame`. |
| `db.show(limit=10)` | Prints a formatted ASCII table of the first `N` rows to console. |
| `db.export(output_path)` | Exports data based on extension (`.csv`, `.json`, `.sql`). |
| `db.export_csv(path)` | Exports data to CSV. |
| `db.export_json(path)` | Exports data to JSON Lines (`.jsonl`). |
| `db.export_sql(path)` | Exports data to SQL `CREATE TABLE` and `INSERT` statements. |

---

### `mergendb.QueryResult`

The container returned by all queries.

| Method / Property | Description |
| :--- | :--- |
| `len(result)` | Returns number of rows returned. |
| `for row in result:` | Directly iterate over rows. |
| `result[0]` | Access row by index. |
| `result.first` | Returns the first row list, or `None`. |
| `result.to_dicts()` | Converts rows to a `List[Dict[str, Any]]`. |
| `result.to_dict()` | Converts the first row to a `Dict[str, Any]`, or `None`. |
| `result.to_list()` | Returns raw `List[List[Any]]`. |
| `result.to_df()` | Converts result into a `pandas.DataFrame`. |
| `result.display(max_rows=50)` | Formats the result as an aligned ASCII table with execution stats. |
| `result.show(max_rows=50)` | Prints `display()` to stdout. |
| `result.stats` | Contains execution telemetry (`execution_time_ms`, `blocks_scanned`, `blocks_skipped`, `bytes_read`). |

---

## Interactive Command-Line Interface (REPL)

MergenDB includes an interactive terminal shell designed for database administrators and data exploration.

### Starting the CLI

```bash
# Start global shell
mergen

# Start shell directly attached to a table
mergen users.mgdb

# Run built-in diagnostic test suite
mergen test
```

When you enter the shell, the prompt displays your active table context:

```text
mergen[users.mgdb]>
```

### Complete CLI Command Reference

All commands can be terminated with an optional semicolon (`;`).

| Command | Description & Example |
| :--- | :--- |
| **`USE <table.mgdb>;`** | Switch active table context. <br>`USE orders.mgdb;` |
| **`SHOW TABLES;`** | Lists all `.mgdb` tables in the current directory with row counts and file sizes. |
| **`SHOW COLUMNS;`** <br> **`DESCRIBE;`** | Displays schema (columns, types, nullability) for the active table. <br>`SHOW COLUMNS;` or `SHOW COLUMNS FROM users;` |
| **`WHERE <condition>;`** | Instant query against the active table without typing `SELECT * FROM`. <br>`WHERE balance > 500 AND status = 'active';` |
| **`SELECT ...;`** | Standard SQL query with projection, filtering, ordering, and limits. <br>`SELECT id, name, balance WHERE balance > 100 ORDER BY balance DESC LIMIT 10;` |
| **`UPDATE ...;`** | Updates matching rows with streaming block safety. <br>`UPDATE users SET balance = 500 WHERE id = 1;` or `UPDATE SET balance = 500;` |
| **`DELETE ...;`** | Deletes matching rows from the active or specified table. <br>`DELETE FROM users WHERE balance <= 0;` or `DELETE WHERE balance <= 0;` |
| **`ALTER TABLE ...;`** | Modify table schema without data loss. <br>`ALTER TABLE users RENAME COLUMN old TO new;`<br>`ALTER TABLE users ADD COLUMN age INT DEFAULT 18;`<br>`ALTER TABLE users DROP COLUMN old_col;` |
| **`RENAME COLUMN ...;`**<br>**`DROP COLUMN ...;`**<br>**`ADD COLUMN ...;`** | Short forms directly against active table context.<br>`RENAME COLUMN old TO new;` |
| **`FROM ...;`** | MergenQL pipeline query. <br>`FROM users.mgdb \| WHERE age >= 18 \| SELECT name, age \| LIMIT 5` |
| **`IMPORT SQL <file.sql> <table.mgdb>;`** | Stream-imports raw MySQL / phpMyAdmin SQL dump into MergenDB with a live progress bar. <br>`IMPORT SQL backup.sql users.mgdb;` |
| **`IMPORT SQLITE <file.db> <table.mgdb> [tbl];`** | Imports an SQLite table into MergenDB. <br>`IMPORT SQLITE app.db customers.mgdb users;` |
| **`IMPORT CSV <file.csv> <table.mgdb>;`** | Imports a CSV file into MergenDB. <br>`IMPORT CSV logs.csv logs.mgdb;` |
| **`EXPORT <table.mgdb> TO CSV <file.csv>;`** | Exports table to CSV. <br>`EXPORT users.mgdb TO CSV users_backup.csv;` |
| **`EXPORT <table.mgdb> TO JSON <file.json>;`** | Exports table to JSON Lines. <br>`EXPORT users.mgdb TO JSON users.jsonl;` |
| **`EXPORT <table.mgdb> TO SQL <file.sql>;`** | Exports table to SQL DDL and INSERT statements. <br>`EXPORT users.mgdb TO SQL dump.sql;` |
| **`BENCHMARK <table.mgdb>;`** | Runs a live sequential I/O read and decompression benchmark. <br>`BENCHMARK users.mgdb;` |
| **`INFO <table.mgdb>;`** | Displays detailed compression ratios, block telemetry, and disk space saved. <br>`INFO users.mgdb;` |
| **`OPTIMIZE TABLE <table.mgdb>;`** | Defragments and repacks blocks into uniform block sizes. <br>`OPTIMIZE TABLE users.mgdb;` |
| **`COUNT <table.mgdb>;`** | Displays total row count. <br>`COUNT users.mgdb;` |
| **`TRUNCATE TABLE <table.mgdb>;`** | Clears all rows while preserving schema. <br>`TRUNCATE TABLE users.mgdb;` |
| **`RENAME TABLE <old> TO <new>;`** | Renames a table file. <br>`RENAME TABLE old_users.mgdb TO users.mgdb;` |
| **`DROP TABLE <table.mgdb>;`** | Permanently deletes a table file from disk. <br>`DROP TABLE temp.mgdb;` |
| **`EXPLAIN <query>;`** | Shows the query execution plan, pushdown ZoneMap predicates, and required columns. <br>`EXPLAIN SELECT name WHERE age > 30;` |
| **`STATUS;`** | Displays engine version, process PID, and total local storage usage. |
| **`SERVE [port];`** | Starts the built-in HTTP query server directly from the REPL. <br>`SERVE 8765;` |
| **`HELP;`** | Displays quick command reference. |
| **`EXIT;` / `QUIT;` / `\Q`** | Exits the shell. |

---

### Real-Time Live Progress Bar

When executing queries or data transfers in the CLI, MergenDB displays a dynamic, cross-platform progress bar:

```text
mergen[customers.mgdb]> SELECT name, city, balance WHERE city = 'New York' AND balance > 5000;

[*] Querying 'customers.mgdb': 9,350,762 / 9,350,762 rows [========================] 100.0% | 2,841,200 rows/s | ETA: 0s  
+--------------------+----------+---------+
| name               | city     | balance |
+--------------------+----------+---------+
| Alex Morgan        | New York | 12450   |
| Sarah Jenkins      | New York | 8900    |
+--------------------+----------+---------+
Returned 2 rows in 4.12 ms | Blocks: 1142 scanned, 0 skipped | Read: 21,410 KB
```

---

## Query Engine: MergenQL & Standard SQL

MergenDB supports two query paradigms:

### 1. Standard SQL
You can write familiar SQL queries:
```sql
SELECT id, name, (salary * 1.10) AS new_salary
FROM employees.mgdb
WHERE department = 'Engineering' AND salary < 120000
ORDER BY salary DESC
LIMIT 10;
```

### 2. MergenQL (Pipeline Syntax)
Inspired by Unix pipes and functional pipelines, MergenQL breaks queries into distinct, composable processing stages:

```text
FROM "employees.mgdb"
| WHERE department = 'Engineering' AND salary < 120000
| COMPUTE new_salary = (salary * 1.10)
| SELECT id, name, new_salary
| SORT salary DESC
| LIMIT 10
```

### Supported Operators & Expressions

- **Comparison Operators:** `=`, `==`, `!=`, `<>`, `>`, `>=`, `<`, `<=`, `LIKE` (supports `%` and `_` wildcards).
- **Logical Operators:** `AND`, `OR`, `NOT`, and parenthesized groups `( ... )`.
- **Arithmetic Operators:** `+`, `-`, `*`, `/`, `%`.
- **Aggregate Functions:** `COUNT(*)`, `SUM(col)`, `AVG(col)`, `MIN(col)`, `MAX(col)`, `MEDIAN(col)`, `STDDEV(col)` with multi-column `GROUP BY col1, col2` and `HAVING` filters.
- **Computed Columns:** `COMPUTE total = price * quantity`.
- **Streaming Hash JOIN:** In-memory hash join between tables with `[INNER|LEFT] JOIN <table> ON left_col = right_col`.

### Analytical SQL & Hash JOINs

MergenDB v0.5.8+ brings full analytical joins and aggregation filters:

```sql
-- Analytical Hash JOIN between two columnar tables
SELECT users.name, orders.item, orders.amount
FROM "users.mgdb"
LEFT JOIN "orders.mgdb" ON users.id = orders.user_id
WHERE users.city = 'Istanbul' AND orders.amount > 50
ORDER BY orders.amount DESC
LIMIT 10;
```

```sql
-- Multi-Column GROUP BY with HAVING clause filtering
SELECT department, city, COUNT(*), SUM(salary) AS total_sal
FROM "employees.mgdb"
GROUP BY department, city
HAVING total_sal > 100000
ORDER BY total_sal DESC;
```

Or using MergenQL pipeline syntax:
```text
FROM "users.mgdb"
| LEFT JOIN "orders.mgdb" ON id = user_id
| WHERE city = 'Istanbul' AND amount > 50
| SELECT name, item, amount
| SORT amount DESC
| LIMIT 10
```

### Multi-Column Filter Optimization (`LazyColumnDict`)

When executing compound filters like:
```sql
WHERE country = 'US' AND balance > 1000
```
MergenDB optimizes execution through **Demand-Driven Lazy Evaluation**:
1. It decompresses **only** the `country` column for the block.
2. If zero rows in the block have `country == 'US'`, the `AND` operator short-circuits.
3. The `balance` column (and all other columns in the table) are **never read from disk and never decompressed**.
4. On large tables, this cuts disk read volume and CPU decompression time by up to **90%**.

---

## Streaming Data Migration (Import & Export)

Migrating multi-gigabyte SQL dumps into embedded databases often crashes with `Out Of Memory` errors. MergenDB is engineered to stream large dumps line-by-line:

```python
from mergendb import import_sql, import_sqlite, import_csv

# Ingest a 10 GB MySQL / phpMyAdmin dump under 20 MB of RAM
import_sql("huge_production_dump.sql", "analytics.mgdb")

# Ingest an existing SQLite database table
import_sqlite("legacy_app.db", "customers.mgdb", table_name="customers")

# Ingest a CSV dataset
import_csv("telemetry.csv", "sensors.mgdb")
```

---

## Built-in HTTP REST API Server

MergenDB includes an asynchronous HTTP query server. This allows backend services written in **Node.js, Go, Rust, Java, C#, or PHP** to query local MergenDB files over JSON:

### Starting the Server

```bash
mergendb-server --port 8765
```

### Querying via `curl`

```bash
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, name, balance FROM \"users.mgdb\" WHERE balance > 100 LIMIT 2;"}'
```

### Response

```json
{
  "success": true,
  "columns": ["id", "name", "balance"],
  "rows": [
    [1, "Alice", 100],
    [5, "Emma", 250]
  ],
  "stats": {
    "execution_time_ms": 1.25,
    "rows_returned": 2,
    "blocks_scanned": 1,
    "blocks_skipped": 14,
    "bytes_read": 1024
  }
}
```

---

## Storage & Compression Architecture

MergenDB files (`.mgdb`) are structured into independent, immutable blocks:

```text
+-----------------------------------------------------------------------+
| Header: Magic (4B) | Version (2B) | Created (8B) | Schema JSON       |
+-----------------------------------------------------------------------+
| Block 0: Column Chunk 0 | Column Chunk 1 | ...                        |
+-----------------------------------------------------------------------+
| Block 1: Column Chunk 0 | Column Chunk 1 | ...                        |
+-----------------------------------------------------------------------+
| Footer: Block Offsets, Column Meta, ZoneMaps | Footer Len | Magic (4B)|
+-----------------------------------------------------------------------+
```

### Adaptive Compression Pipeline

When writing each column block, MergenDB analyzes the values and selects the encoding with the smallest byte size:

1. **Bit-Packed Booleans:** Stores boolean flags at 1 bit per value (8 values per byte).
2. **Delta / FoR:** Stores sequential numbers as offsets from `min_value`, reducing 8-byte integers to 1- or 2-byte deltas.
3. **Dictionary Encoding:** Ideal for low-cardinality text (gender, country, status). Stores unique strings once in a block dictionary and encodes rows as 1-byte indices.
4. **Run-Length Encoding (RLE):** Collapses repeated identical values into `(count, value)` pairs.
5. **Secondary Zlib Compression:** Applied with level 1 (fast throughput) to cold byte streams.

---

## Performance Benchmarks

Tested on an Intel Core i7 with 100,000 mixed telemetry records (12 columns: integers, floats, timestamps, statuses, long strings):

| Storage Format | Disk Size | Space Saved | 2-Column Query Disk Read | Peak RAM |
| :--- | :--- | :--- | :--- | :--- |
| **JSON Lines (`.jsonl`)** | 19.5 MB | 0% (Baseline) | 19.5 MB | Unbounded |
| **SQLite 3 (`.db`)** | 8.1 MB | 58.4% | 8.1 MB (reads full row) | ~30 MB |
| **MergenDB (`.mgdb`)** | **1.6 MB** | **91.5%** | **0.29 MB (pruned)** | **< 18 MB RAM** |

- **Exact Filter Scan Throughput:** ~50,000,000 rows/sec (single core)
- **Substring (`LIKE '%term%'`) Scan:** ~10,000,000 rows/sec (single core)
- **SQL Streaming Import Speed:** ~70,000–120,000 rows/sec on standard SSD

---

## 🚀 Version Updates & Release Comparisons

### Version Comparison: v0.6.0 vs v0.6.1

| Capability / Feature | v0.6.0 (Initial Node.js SDK Release) | v0.6.1 (phpMyAdmin Redesign & Full Ecosystem Parity) | Status & Impact |
| :--- | :--- | :--- | :--- |
| **Mergen Studio UI** | Heavy animations, blocking modal overlay stuck at 92% on page turns | ✅ **Authentic phpMyAdmin Architecture** | Clean, crisp, lightweight `#f5f7fa` styling with Mergen logo/icon; zero UI lockups |
| **UI CLI Parity** | Read-only schema and basic queries | ✅ **100% Full CLI Parity in Browser** | 10 dedicated tabs: Gözat, Yapı, SQL, Ara, Ekle, Dışa Aktar, İçe Aktar, İşlemler, Sunucu, Kılavuz |
| **Browser Pagination & Sort** | Blocked by progress modal, no sorting | ✅ **Instant Pagination & Column Sorting** | Instant `<< < [page] > >>` navigation; click headers to sort ASC/DESC on disk |
| **Data Mutations in UI** | CLI only | ✅ **Direct Insert & Row Deletion in UI** | Schema-driven dynamic insert form + one-click delete row in Browse tab |
| **Schema Alterations in UI** | CLI only | ✅ **Add, Drop, and Rename Columns in UI** | Full column lifecycle directly from the Yapı (Structure) tab |
| **Node.js SDK Feature Parity** | `query()`, `find()`, `count()` only | ✅ **100% Full Python Parity in JS/TS** | Added `insert()`, `search()`, `update()`, `delete()`, `addColumn()`, `renameColumn()`, `dropColumn()`, `benchmark()` |
| **Live Hardware Profiling** | CLI only | ✅ **Real-Time Profiler in UI & Node.js** | Browser-triggered benchmark test + `client.benchmark()` running live hardware speed test (1M+ rows/s) |
| **Multi-Language Guides** | Separate docs | ✅ **Embedded Runnables for All 4 Runtimes** | Side-by-side executable code examples for Python, Node.js / TypeScript, CLI, and REST API |
| **Total Test Suite** | 100 Tests (88 Py + 12 JS) | ✅ **106 Tests (88 Py + 18 JS, 100% Pass)** | Expanded end-to-end Node.js SDK test coverage with zero regressions |

---

### Version Comparison: v0.5.9 vs v0.6.0

| Capability / Architecture | v0.5.9 (Mergen Studio & Embedded Web UI) | v0.6.0 (Universal Node.js SDK & Production Polish) | Status & Impact |
| :--- | :--- | :--- | :--- |
| **Node.js & TypeScript SDK** | ❌ Python only | ✅ **Official `mergendb` Client Package** | Zero-dependency TypeScript/Node.js client for Express, Next.js, and NestJS |
| **Document-Style API in JS** | ❌ Not available | ✅ **Fluent `.find()`, `.count()` & Tagged SQL** | Safe parameterized queries via `db.sql\`...\`` and object-based row mapping |
| **CLI Shell Autocompletions** | ❌ Not available | ✅ **`mergen completions <shell>`** | Tab autocompletion for Bash, Zsh, PowerShell, and Fish |
| **One-Off Query Execution** | REPL only | ✅ **`mergen query "<SQL>"`** | Rapid shell querying without entering the interactive REPL prompt |
| **Hardware Diagnostic Accuracies** | Architecture only | ✅ **Exact CPU Model & RAM Sizing** | Accurate detection of Intel/AMD/Apple Silicon models via WMI/sysfs/sysctl |
| **Web UI (Mergen Studio)** | phpMyAdmin layout | ✅ **Standardized REST Payloads** | Consistent JSON error codes and `row_count` attributes across all endpoints |
| **Total Test Suite** | 83 Tests (100% pass) | ✅ **100 Tests (88 Python + 12 Node.js SDK, 100% pass)** | Complete end-to-end integration verification across Python and Node.js runtimes |

---

### Roadmap & Version Progression

| Version | Milestone | Key Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **v0.5.5** | CLI & Ingestion Polish | Universal `EXPORT [csv\|json\|sql]` syntax & extension resolution | ✅ Released |
| **v0.5.6** | Multi-Core Scan Engine | Zero-copy `mmap` ThreadPool scan + C-level `itertools.compress` | ✅ Released |
| **v0.5.7** | Bloom Filter Lookups | 1024-bit 4-hash block Bloom filters for instant text/UUID pruning | ✅ Released |
| **v0.5.8** | Analytical SQL & JOINs | In-Memory Hash JOIN (`INNER`/`LEFT`), Multi-Column GROUP BY, HAVING | ✅ Released |
| **v0.5.9** | Embedded Web UI | **Mergen Studio**: phpMyAdmin-style dashboard, active file selector & % progress bars | ✅ Released |
| **v0.6.0** | Universal Node.js SDK | **Node.js/TypeScript SDK** + CLI completions + Hardware profiling polish | ✅ Released |
| **v0.6.1** | phpMyAdmin Overhaul & Full Parity | **Authentic phpMyAdmin UI**, 100% CLI feature parity in UI and Node.js SDK, 106 tests | ✅ Released (Milestone Complete) |

---

## Running the Test Suite

MergenDB includes an embedded test suite with **106 comprehensive tests** (88 Python unit tests covering storage, compression algorithms, query planning, Bloom filters, and analytical joins + 18 end-to-end Node.js SDK integration tests):

```bash
# Run Python unit tests & hardware profiler via CLI
mergen test

# Or run via unittest
python -m unittest discover -s tests

# Run Node.js Client SDK integration tests
node sdks/nodejs/test.js
```

---

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed with ❤️ by [Uğur Türker Kebeci](https://github.com/ugurturkerkebeci).
