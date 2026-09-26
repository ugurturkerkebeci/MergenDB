<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

# MergenDB

[![PyPI version](https://img.shields.io/pypi/v/mergendb.svg?color=blue&style=flat-square)](https://pypi.org/project/mergendb/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb.svg?color=blue&style=flat-square)](https://pypi.org/project/mergendb/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Author](https://img.shields.io/badge/Author-U%C4%9Fur%20T%C3%BCrker%20Kebeci-orange.svg?style=flat-square)](https://github.com/ugurturkerkebeci)

MergenDB is an embedded columnar database engine and query execution runtime designed to handle analytical workloads on resource-constrained hardware. It is written in pure Python with **zero external dependencies**, allowing it to run out of the box on low-end virtual servers, Raspberry Pis, embedded devices, and developer workstations without compiling C extensions.

Traditional embedded databases like SQLite store data row-by-row. When you query 2 columns out of a 30-column table across 10 million rows, a row-oriented database still reads all 30 columns off the disk. MergenDB stores data column-by-column in compressed blocks, pruning unrequested columns from disk reads and skipping entire blocks via ZoneMap indexing.

---

## Key Features

- **Strictly Bounded Memory Footprint:** Streams data in configurable chunks (4,096–8,192 rows). Memory usage stays under 15–20 MB RAM regardless of whether your dataset is 100 MB or 100 GB.
- **Adaptive Columnar Encodings:** Automatically evaluates and applies the best encoding per block:
  - **Bit-Packing:** Packs 8 booleans into a single byte.
  - **Delta / Frame-of-Reference (FoR):** Compresses sequential IDs, integers, and timestamps.
  - **Dictionary Encoding:** Replaces repeated strings (status, city, category) with 1–2 byte integers.
  - **Run-Length Encoding (RLE):** Compresses contiguous identical values into `(count, value)` pairs.
  - **Secondary Zlib Compression:** Fast C-level streaming compression for cold data blocks.
- **ZoneMap Indexing:** Stores `min_value`, `max_value`, and `null_count` metadata per column chunk. If your query filters `WHERE age > 65` and a block's maximum age is 40, MergenDB skips reading that block entirely.
- **Robust SQL / phpMyAdmin Importer:** Line-by-line streaming parser for raw MySQL/phpMyAdmin SQL dumps with multiline statements, escaped characters, and schema autodetection.
- **Interactive REPL & Network Server:** Comes with a MySQL-like CLI shell and a built-in HTTP query server for remote queries from any language.
- **Zero Third-Party Dependencies:** Only uses Python standard library modules (`array`, `struct`, `zlib`, `csv`, `http.server`, `sqlite3`).

---

## Installation

```bash
pip install mergendb
```

Requires Python 3.8 or later.

---

## Quickstart (Python API)

### 1. Creating and Querying Tables

```python
from mergendb import MergenDB
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter

schema = Schema([
    ColumnDef("id", DataType.INT64),
    ColumnDef("city", DataType.STRING),
    ColumnDef("temp", DataType.FLOAT64),
    ColumnDef("active", DataType.BOOL)
])

# Write columnar data
with FileWriter("telemetry.mgdb", schema, block_size=4096) as writer:
    writer.write_rows([
        [1, "Istanbul", 24.5, True],
        [2, "Ankara", 18.2, False],
        [3, "Izmir", 28.0, True],
        [4, "Istanbul", 26.1, True],
    ])

# Query using standard SQL
result = MergenDB.query('SELECT city, temp FROM "telemetry.mgdb" WHERE temp > 20.0;')
print(result.display())
```

### 2. Pipeline Queries (MergenQL)

MergenDB also supports a pipe-delimited query syntax inspired by Unix pipes:

```python
query = '''
FROM "telemetry.mgdb"
| WHERE temp > 20.0 AND active == True
| COMPUTE temp_f = (temp * 1.8) + 32.0
| SELECT city, temp, temp_f
| SORT temp DESC
| LIMIT 5
'''

result = MergenDB.query(query)
print(result.display())
```

---

## Streaming Import & Export

MergenDB provides streaming importers and exporters that feature a real-time progress bar with throughput (rows/sec) and ETA:

### Import SQL Dumps (phpMyAdmin, mysqldump)

```bash
mergen
mergen> IMPORT SQL database_dump.sql mytable;
```

Or via Python:

```python
from mergendb.io.importer import DataImporter

# Streams line-by-line under 15 MB RAM, regardless of dump size (tested on 10M+ rows)
DataImporter.from_sql_dump("huge_dump.sql", "mytable.mgdb")
```

### Import SQLite Databases

```python
DataImporter.from_sqlite("legacy.sqlite3", "users.mgdb", table_name="users")
```

### Import CSV Files

```python
DataImporter.from_csv("logs.csv", "logs.mgdb")
```

### Export Tables to CSV, SQL, or JSONL

```text
mergen> EXPORT mytable.mgdb TO CSV "backup.csv";
mergen> EXPORT mytable.mgdb TO JSON "backup.jsonl";
mergen> EXPORT mytable.mgdb TO SQL "backup.sql";
```

---

## Command-Line Interface (REPL)

Launch the interactive shell:

```bash
mergen
```

```text
mergen> SHOW TABLES;
+------------------+------------+------------+
| Table Name       | Total Rows | Size (KB)  |
+------------------+------------+------------+
| users.mgdb       | 1,250,000  | 8,412.30   |
| logs.mgdb        | 5,400,000  | 24,190.50  |
+------------------+------------+------------+

mergen> USE users;
mergen> SELECT id, name, city WHERE city = 'Istanbul' LIMIT 10;
mergen> EXPLAIN SELECT id, name WHERE age > 60;
mergen> DESCRIBE users;
mergen> BENCHMARK users;
```

---

## HTTP Network Server

MergenDB includes an HTTP server that allows any application (Node.js, Go, PHP, Rust, C#) to execute queries over JSON:

```bash
# Start server on port 8765
mergendb-server --port 8765
```

Send a query using `curl`:

```bash
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, city, temp FROM \"telemetry.mgdb\" WHERE city = \"Istanbul\" LIMIT 5;"}'
```

Response:

```json
{
  "success": true,
  "columns": ["id", "city", "temp"],
  "rows": [
    [1, "Istanbul", 24.5],
    [4, "Istanbul", 26.1]
  ],
  "stats": {
    "execution_time_ms": 0.85,
    "rows_returned": 2,
    "blocks_scanned": 1,
    "blocks_skipped": 12,
    "bytes_read": 512
  }
}
```

---

## Benchmarks & Technical Characteristics

Benchmarked on an Intel i7 machine with 100,000 telemetry records (12 mixed numeric/string columns):

| Format | Storage Size | Space Saved | Disk I/O (2 Column Query) | Peak Memory |
| :--- | :--- | :--- | :--- | :--- |
| **JSON Lines (`.jsonl`)** | 19.5 MB | Baseline | 19.5 MB | Unbounded |
| **SQLite 3 (`.db`)** | 8.1 MB | 58.4% | 8.1 MB (reads full table) | Driver dependent |
| **MergenDB (`.mgdb`)** | **1.6 MB** | **91.5%** | **0.29 MB (pruned)** | **< 15 MB RAM** |

- **Exact Filter Throughput:** ~50,000,000 rows/sec (single core)
- **Substring (`LIKE '%term%'`) Throughput:** ~10,000,000 rows/sec (single core)
- **SQL Import Throughput:** ~70,000 rows/sec streaming parser on commodity hardware

---

## Running Tests

MergenDB includes a complete test suite covering columnar storage, compression encodings, SQL/SQLite/CSV importers, and the query planner:

```bash
python -m unittest discover tests
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Developed by [Uğur Türker Kebeci](https://github.com/ugurturkerkebeci).
