<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="280" />
</p>

# MergenDB (v1.0.0 Production Release)

> **The Ultra-Compact, Zero-Dependency Embedded Columnar & Vector Database Engine for Python and Node.js**

[![PyPI version](https://img.shields.io/pypi/v/mergendb.svg?style=flat-square&logo=pypi&logoColor=white&cacheSeconds=300)](https://pypi.org/project/mergendb/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb.svg?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/mergendb.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![Socket PyPI Security Badge](https://badge.socket.dev/pypi/package/mergendb)](https://socket.dev/pypi/package/mergendb)
[![npm version](https://img.shields.io/npm/v/mergendb.svg?style=flat-square&logo=npm&logoColor=white&cacheSeconds=300)](https://www.npmjs.com/package/mergendb)
[![Socket npm Security Badge](https://badge.socket.dev/npm/package/mergendb)](https://badge.socket.dev/npm/package/mergendb)
[![Dependencies](https://img.shields.io/badge/Dependencies-0%20(Zero)-success.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![Tests Passing](https://img.shields.io/badge/Tests-4600%2B%20(100%25%20Passed)-brightgreen.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

## The v1.0.0 Milestone: AI-Native Analytical Evolution

MergenDB v1.0.0 marks a monumental milestone in embedded data engineering. Traditionally, developers have had to deploy separate databases for columnar analytics (e.g. DuckDB, ClickHouse) and separate engines for vector similarity search (e.g. Chroma, LanceDB, Pinecone). Furthermore, these engines rely on complex C++ compilation toolchains, LLVM, or massive multi-megabyte wheel packages.

**MergenDB v1.0.0 eliminates this complexity entirely.** It provides a **single-file (`.mgdb`), zero-external-dependency columnar database** that natively executes both **ultra-fast analytical SQL (GROUP BY, JOIN, AGGREGATE)** and **AI-driven vector embedding similarity search** in both Python and Node.js.

---

## Key Breakthroughs in v1.0.0

- **AI-Native `VECTOR` Type & SIMD Math:** Native storage and computing of float embeddings (128, 384, 768, 1536+ dimensions) with zero external libraries. Supports `COSINE_SIMILARITY`, `L2_DISTANCE` (Euclidean), `DOT_PRODUCT`, and `MANHATTAN_DISTANCE`.
- **Hybrid Relational + Vector Search:** Execute high-performance hybrid queries that combine SQL metadata filters with vector nearest-neighbor search in sub-milliseconds.
- **Sub-Second 100M+ Row Columnar Scans:** Point lookups execute in **< 100ms**, and analytical scans achieve **~400M+ rows/second** directly evaluating binary byte streams with zero-copy `mmap`.
- **Selective Late Materialization:** Only matching rows decode dictionary values (`decode_dict_indices`), bypassing decompression of thousands of unneeded rows.
- **Lazy Metadata Initialization (`LazyBlockList`):** Instant table opening (0.0001s) on multi-million row tables by deferring block metadata instantiation until requested.
- **Fault-Tolerant Streaming Ingestion (> 5M rows/s):** Robust parallel byte-range parser seamlessly processes ragged rows, escaped quotes, missing fields, null bytes (`\x00`), and diverse encodings.
- **Strictly Bounded Memory (< 20 MB RAM):** Data streams in configurable column blocks (1,024 to 65,536 rows). Peak memory never grows with database file size.
- **Hierarchical Database Architecture:** Manage databases, tables, and nested sub-tables (`database.table.subtable`) with isolated namespaces.
- **Zero External Dependencies:** Built purely on standard library primitives (`zlib`, `struct`, `mmap`, `json`, `sqlite3`, `http`).
- **Strict Zero-Emoji Policy:** Clean, professional interface built with deterministic status tags (`[+]`, `[-]`, `[*]`, `[!]`).

---

## SDKs & Extensions

| Package | Language / Environment | Registry | Description |
| :--- | :--- | :--- | :--- |
| **mergendb** | Python 3.8+ | [![PyPI](https://img.shields.io/pypi/v/mergendb.svg?style=flat-square&cacheSeconds=300)](https://pypi.org/project/mergendb/) | Embedded columnar engine, SQL executor, vector search & CLI |
| **mergendb** | Node.js / TypeScript | [![npm](https://img.shields.io/npm/v/mergendb.svg?style=flat-square&cacheSeconds=300)](https://www.npmjs.com/package/mergendb) | Zero-dependency Node.js client SDK with tagged template SQL |
| **mergendb-studio** | Web GUI Extension | [![PyPI](https://img.shields.io/pypi/v/mergendb-studio.svg?style=flat-square&cacheSeconds=300)](https://pypi.org/project/mergendb-studio/) | Interactive web management dashboard with purple theme |

---

## Comprehensive MergenQL & Usage Guide

### 1. Python: Embedded Analytics & Hybrid Vector Search

```python
import mergendb
from mergendb import Schema, ColumnDef, DataType, Table

# 1. Define schema with relational attributes and an AI embedding vector
schema = Schema([
    ColumnDef("doc_id", DataType.INT32),
    ColumnDef("title", DataType.STRING),
    ColumnDef("category", DataType.STRING),
    ColumnDef("embedding", DataType.VECTOR)
])

table = Table.create("knowledge_base.mgdb", schema)

# 2. Insert records
table.insert([
    {"doc_id": 1, "title": "Attention Is All You Need", "category": "AI", "embedding": [0.95, 0.1, 0.05]},
    {"doc_id": 2, "title": "General Relativity", "category": "Physics", "embedding": [0.82, 0.2, 0.15]},
    {"doc_id": 3, "title": "French Culinary Arts", "category": "Cooking", "embedding": [0.05, 0.9, 0.1]}
])

# 3. Hybrid Vector Search (Filter + Top-K Cosine Similarity)
results = table.vector_search(
    column="embedding",
    query_vector=[1.0, 0.0, 0.0],
    top_k=2,
    filter="category == 'AI'",
    metric="cosine"
)

results.show()
```

### 2. Analytical SQL with Vector Functions

```sql
SELECT title, category, cosine_similarity(embedding, [1.0, 0.0, 0.0]) AS score
FROM knowledge_base
WHERE category = 'AI'
ORDER BY score DESC
LIMIT 5;
```

In Python:
```python
res = mergendb.query("""
    SELECT title, cosine_similarity(embedding, [1.0, 0.0, 0.0]) AS score
    FROM knowledge_base
    ORDER BY score DESC
    LIMIT 3;
""")
res.show()
```

### 3. Node.js & TypeScript SDK

```typescript
import { MergenDB } from 'mergendb';

const db = new MergenDB({ host: '127.0.0.1', port: 8765, autoStart: true });
const table = db.table('knowledge_base');

// Native top-K vector search
const matches = await table.vectorSearch('embedding', [1.0, 0.0, 0.0], {
  topK: 2,
  filter: "category = 'AI'",
  metric: 'cosine'
});

for (const doc of matches) {
  console.log(`[+] Document: ${doc.title} (Score: ${doc.score.toFixed(4)})`);
}
```

### 4. CLI Command-Line Reference

The unified `mergendb` CLI provides comprehensive table inspection, query execution, and ingestion:

```bash
# Display table schema, row count, compression ratio, and block metadata
mergendb info knowledge_base.mgdb

# Execute analytical SQL directly from the terminal
mergendb sql "SELECT title, score FROM knowledge_base.mgdb WHERE score > 0.8"

# High-speed streaming CSV import (> 5M rows/second)
mergendb import knowledge_base.mgdb data.csv --delimiter "," --parallel

# Stream table export to JSON or CSV
mergendb export knowledge_base.mgdb --format json --output docs.json

# Launch the headless HTTP server with the new purple Studio Web UI
mergendb server --port 8765 --ui

# Run hardware profiler and memory benchmark
mergendb benchmark
```

---

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
