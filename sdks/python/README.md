<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="220" />
</p>

# MergenDB Python SDK & Core Engine (v1.0.0 Production Release)

[![PyPI version](https://img.shields.io/pypi/v/mergendb.svg?style=flat-square&logo=pypi&logoColor=white&cacheSeconds=300)](https://pypi.org/project/mergendb/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mergendb.svg?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/mergendb/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/mergendb.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mergendb/)
[![Socket PyPI Security Badge](https://badge.socket.dev/pypi/package/mergendb)](https://socket.dev/pypi/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-0%20(Zero)-success.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Python SDK and core embedded columnar database engine for **MergenDB** — engineered for unified **analytical SQL**, **sub-second 100M+ row columnar scans**, and **native AI-driven vector embedding similarity search**, all operating in strictly bounded memory (< 20 MB peak RAM).

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

## The v1.0.0 Milestone & Architectural Evolution

From our early v0.1 prototypes to the production v1.0.0 release, MergenDB was built to solve a fundamental contradiction in modern data engineering: *Why do embedded databases require gigabytes of dependencies (C++ compilers, LLVM, native runtimes) just to scan tabular data and query vector embeddings?*

MergenDB v1.0.0 unifies **columnar analytical OLAP** and **AI vector similarity search** into a single compact file (`.mgdb`) with zero external runtime dependencies.

### What We Achieved in v1.0.0:
1. **AI-Native Vector Operations:** Native `VECTOR` data type supporting float embeddings (128, 384, 768, 1536+ dimensions) stored in contiguous float32 buffers.
2. **SIMD-Grade Native Similarity:** Native computation of `COSINE_SIMILARITY`, `L2_DISTANCE` (Euclidean), `DOT_PRODUCT`, and `MANHATTAN_DISTANCE` directly inside SQL and pipeline queries without NumPy, PyTorch, or external C dependencies.
3. **Hybrid Search Pipeline:** Combine relational metadata filtering (`WHERE category = 'AI'`) with top-K vector nearest-neighbor search in sub-milliseconds via predicate pushdown.
4. **Sub-Second 100M+ Row Columnar Scans:** Point lookups execute in **< 100ms**, and analytical scans achieve **~400M+ rows/second** directly evaluating binary byte streams with zero-copy `mmap`.
5. **Selective Late Materialization:** Only matching rows decode dictionary values (`decode_dict_indices`), bypassing decompression of thousands of unneeded rows.
6. **Lazy Metadata Initialization (`LazyBlockList`):** Table opening overhead on multi-million row tables dropped to **0.0001 seconds**, deferring block parsing until individual blocks are accessed.
7. **Fault-Tolerant Ingestion (> 5M rows/s):** Robust parallel byte-range parser seamlessly processes ragged rows, escaped quotes, missing fields, null bytes (`\x00`), and diverse encodings.
8. **Strict Zero-Emoji Policy:** Clean, deterministic interface built with professional status tags (`[+]`, `[-]`, `[*]`, `[!]`).

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

## Comprehensive MergenQL & Python Usage Guide

MergenDB supports two synergistic querying interfaces: **Standard Analytical SQL** and the high-throughput **MergenQL Pipeline Syntax** (`| WHERE ... | COMPUTE ... | AGGREGATE ...`).

### 1. Embedded Local Analytics & Vector Hybrid Search

```python
import mergendb
from mergendb import Schema, ColumnDef, DataType, Table

# 1. Define schema with relational columns and an AI embedding vector column
schema = Schema([
    ColumnDef("doc_id", DataType.INT32),
    ColumnDef("title", DataType.STRING),
    ColumnDef("category", DataType.STRING),
    ColumnDef("embedding", DataType.VECTOR)
])

table = Table.create("knowledge_base.mgdb", schema, block_size=16384)

# 2. Insert records (embeddings can be float lists or tuples)
table.insert([
    {"doc_id": 1, "title": "Transformer Attention", "category": "AI", "embedding": [0.92, 0.12, 0.05]},
    {"doc_id": 2, "title": "Quantum Supremacy", "category": "Physics", "embedding": [0.81, 0.25, 0.10]},
    {"doc_id": 3, "title": "Neapolitan Pizza Dough", "category": "Cooking", "embedding": [0.05, 0.95, 0.12]},
    {"doc_id": 4, "title": "Reinforcement Learning", "category": "AI", "embedding": [0.89, 0.15, 0.02]}
])

# 3. High-Performance Hybrid Vector Search
# Filters by category first, then performs top-K cosine similarity ranking
results = table.vector_search(
    column="embedding",
    query_vector=[1.0, 0.0, 0.0],
    top_k=2,
    filter="category == 'AI'",
    metric="cosine"
)

results.show()
```

### 2. Analytical SQL with Vector Similarity Functions

You can seamlessly invoke vector similarity directly inside standard SQL:

```python
import mergendb

sql_query = """
SELECT doc_id, title, cosine_similarity(embedding, [1.0, 0.0, 0.0]) AS score
FROM knowledge_base
WHERE category = 'AI'
ORDER BY score DESC
LIMIT 5;
"""

res = mergendb.query(sql_query)
res.show()
```

### 3. MergenQL Direct Pipeline Syntax

When programmatic pipelines or custom computing stages are preferred, use the native MergenQL pipe syntax:

```python
pipe = """
FROM knowledge_base
| WHERE category == 'AI'
| COMPUTE score = cosine_similarity(embedding, [1.0, 0.0, 0.0])
| SORT score DESC
| LIMIT 5
"""

res = mergendb.query(pipe)
for row in res.to_dicts():
    print(f"[{row['doc_id']}] {row['title']} (Score: {row['score']:.4f})")
```

### 4. CLI (Command-Line Interface) Deep Dive

MergenDB comes with a robust CLI executable right out of the box (`mergendb` or `python -m mergendb`):

```bash
# 1. Inspect table metadata, compression stats, and block counts
mergendb info knowledge_base.mgdb

# 2. Execute an analytical SQL query from terminal
mergendb sql "SELECT title, category FROM knowledge_base.mgdb WHERE category = 'AI'"

# 3. Import multi-gigabyte CSV into columnar format at > 5,000,000 rows/second
mergendb import knowledge_base.mgdb raw_data.csv --delimiter "," --parallel

# 4. Stream table export to JSON, CSV, or SQL dump
mergendb export knowledge_base.mgdb --format json --output exported.json

# 5. Launch the high-concurrency headless HTTP/REST database server
mergendb server --port 8765 --host 0.0.0.0

# 6. Run complete hardware diagnostics and storage benchmark
mergendb benchmark
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
