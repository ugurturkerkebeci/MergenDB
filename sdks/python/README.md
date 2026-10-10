<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="220" />
</p>

# MergenDB Python SDK & Core Engine

[![PyPI version](https://img.shields.io/pypi/v/mergendb.svg?style=flat-square&logo=pypi&logoColor=white&cacheSeconds=300)](https://pypi.org/project/mergendb/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb.svg?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![Socket PyPI Security Badge](https://badge.socket.dev/pypi/package/mergendb)](https://socket.dev/pypi/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-0%20(Zero)-success.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Python SDK and core embedded columnar database engine for **MergenDB** — engineered for high-throughput analytical SQL, sub-second 100M+ row table scans, edge computing, and strictly bounded memory environments (< 20 MB peak RAM).

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

## Highlights

- **Sub-Second 100M+ Row Columnar Scans:** Point lookups execute in **< 100ms**, and analytical scans execute at **~400M+ rows/second** directly evaluating binary byte streams with zero-copy `mmap`.
- **Lazy Metadata Initialization (`LazyBlockList`):** Table opening overhead on multi-million row tables dropped to **0.0001 seconds**, deferring block parsing until individual blocks are accessed.
- **Selective Late Materialization:** Only matching rows decode dictionary values (`decode_dict_indices`), bypassing decompression of thousands of unneeded rows.
- **Fault-Tolerant Streaming Ingestion (> 5M rows/s):** Robust parallel byte-range parser seamlessly processes ragged rows, escaped quotes, missing fields, null bytes (`\x00`), and diverse encodings.
- **Zero External Dependencies:** Built purely on standard library primitives (`zlib`, `struct`, `mmap`, `json`, `sqlite3`, `http`). Zero third-party packages required.
- **Strictly Bounded Memory (< 20 MB RAM):** Data streams in configurable column blocks (1,024 to 65,536 rows). Peak memory never grows with database file size.
- **Hierarchical Database Architecture:** Manage databases, tables, and nested sub-tables (`database.table.subtable`) with isolated namespaces.
- **Dual Query Paradigm:** Execute full analytical SQL queries or use fluent document-style APIs (`find`, `find_one`, `search`, `insert`, `update`, `delete`, `upsert`).
- **Strict Zero-Emoji Policy:** Clean, professional interface built with deterministic status tags (`[+]`, `[-]`, `[*]`, `[!]`).

---

## Installation

```bash
pip install --upgrade mergendb
```

To include the optional web dashboard extension:

```bash
pip install --upgrade "mergendb[studio]"
```

---

## Quickstart

### 1. Embedded Local Analytics (Universal IoT Telemetry Example)

```python
import mergendb

# Connect to local table (auto-created if absent)
telemetry = mergendb.connect("iot_telemetry.mgdb")

# Define schema if empty
if telemetry.row_count == 0:
    telemetry.create_schema([
        ("device_id", "INT64"),
        ("station_code", "STRING"),
        ("temperature", "DOUBLE"),
        ("humidity", "DOUBLE"),
        ("is_active", "BOOLEAN")
    ])

# Insert records
telemetry.insert([
    {"device_id": 101, "station_code": "US-EAST-01", "temperature": 21.4, "humidity": 48.2, "is_active": True},
    {"device_id": 102, "station_code": "EU-WEST-02", "temperature": 18.9, "humidity": 55.0, "is_active": True},
    {"device_id": 103, "station_code": "AP-SOUTH-01", "temperature": 31.2, "humidity": 72.1, "is_active": False}
])

# Execute Analytical SQL
res = telemetry.sql("""
    SELECT station_code, AVG(temperature) AS avg_temp, MAX(humidity) AS max_hum
    FROM iot_telemetry
    WHERE is_active = true
    GROUP BY station_code
""")

res.show()
```

### 2. High-Speed Fault-Tolerant Streaming CSV Ingestion

```python
import mergendb

# Ingest multi-gigabyte CSV into columnar format at > 5,000,000 rows/second
rows_imported = mergendb.from_csv(
    csv_path="huge_dataset.csv",
    output_mgdb_path="analytics.mgdb",
    delimiter=",",
    has_header=True,
    block_size=65536,
    parallel=True
)

print(f"[+] Successfully imported {rows_imported:,} rows!")
```

### 3. Remote Server Connection

```python
import mergendb

# Connect to a remote MergenDB network server
client = mergendb.RemoteClient("http://localhost:8765", username="root", password="")

# Run query over HTTP
res = client.query("SELECT * FROM 'analytics.mgdb' WHERE temperature > 25.0 LIMIT 10")
for row in res.to_dicts():
    print(row)
```

---

## Hardware Profiling & Diagnostics

Run the integrated system diagnostics and hardware profiler directly from Python:

```python
import mergendb

# Run full diagnostics and hardware throughput benchmark
mergendb.benchmark()
```

---

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
