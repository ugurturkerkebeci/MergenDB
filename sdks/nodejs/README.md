<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="220" />
</p>

# MergenDB Node.js & TypeScript SDK

[![npm version](https://img.shields.io/npm/v/mergendb.svg?style=flat-square&logo=npm&logoColor=white)](https://www.npmjs.com/package/mergendb)
[![Socket npm Security Badge](https://badge.socket.dev/npm/package/mergendb)](https://badge.socket.dev/npm/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-0%20(Zero)-success.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)
[![Node.js Tests](https://img.shields.io/badge/tests-2000%2B%20passed-brightgreen.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Node.js and TypeScript client SDK for **MergenDB** — the ultra-compact, columnar embedded database engine engineered for high-throughput analytical SQL, edge computing, and strictly bounded memory environments.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

## Highlights

- **Sub-Second Columnar Execution:** Point lookups execute in **< 100ms on 100M+ rows**, and analytical queries scan at **~400M+ rows/second** without memory exhaustion or process crashes.
- **Selective Late Materialization:** Only matching rows decode dictionary values, accelerating sparse filters by up to **25x**.
- **Fault-Tolerant Streaming Ingestion:** Stream malformed or ragged CSV, JSONL, and SQL files directly into MergenDB at **> 5M rows/second** with zero crashes.
- **Zero External Dependencies:** Built strictly on the native Node.js runtime standard library (`http`, `https`, `url`, `fs`, `stream`). Zero third-party packages installed in your `node_modules`.
- **Pure Secure Driver:** Operates strictly over HTTP/HTTPS with zero shell execution and zero system subprocess vulnerabilities.
- **TypeScript First:** Complete typings, interfaces, and code completions included out of the box (`index.d.ts`).
- **Hierarchical Database Architecture:** Manage databases, tables, and nested sub-tables (`database.table.subtable`) with isolated namespaces and dot-notation SQL queries.
- **Zero-Memory Streaming Engine:** Stream multi-gigabyte CSV, JSON, JSONL, and SQL dumps directly to disk or network sockets in 64 KB blocks without memory exhaustion or heap crashes.
- **Dual Query Paradigm:** Execute full analytical SQL queries or use fluent document-style APIs (`find`, `findOne`, `search`, `insert`, `update`, `delete`, `upsert`).
- **Safe Parameterized SQL:** Tagged template literal `db.sql` prevents SQL injection with automatic escaping.
- **Strict Zero-Emoji Policy:** Clean, deterministic console logs and status indicators (`[+]`, `[-]`, `[*]`).

---

## Installation

Install via npm, yarn, or pnpm:

```bash
npm install mergendb
```

```bash
yarn add mergendb
```

```bash
pnpm add mergendb
```

---

## Quickstart

### 1. Connecting to MergenDB

Connect to a local or remote MergenDB instance:

```javascript
import { MergenDB, connect } from 'mergendb';

// Connect with default host (127.0.0.1:8765) and root credentials
const db = connect({
  host: '127.0.0.1',
  port: 8765,
  user: 'root',
  password: ''
});
```

### 2. Creating Tables & Ingesting Universal Data

```javascript
// Create a table for global IoT telemetry
const telemetry = await db.createTable('iot_telemetry', [
  { name: 'device_id', type: 'INT64' },
  { name: 'station_code', type: 'STRING' },
  { name: 'temperature', type: 'DOUBLE' },
  { name: 'humidity', type: 'DOUBLE' },
  { name: 'is_active', type: 'BOOLEAN' }
]);

// Insert universal records
await telemetry.insert([
  { device_id: 101, station_code: 'US-EAST-01', temperature: 21.4, humidity: 48.2, is_active: true },
  { device_id: 102, station_code: 'EU-WEST-02', temperature: 18.9, humidity: 55.0, is_active: true },
  { device_id: 103, station_code: 'AP-SOUTH-01', temperature: 31.2, humidity: 72.1, is_active: false }
]);
```

### 3. Analytical SQL & Tagged Template Queries

```javascript
// Safe parameterized SQL query using tagged template literal
const minTemp = 20.0;
const results = await db.sql`
  SELECT station_code, AVG(temperature) AS avg_temp
  FROM iot_telemetry
  WHERE temperature >= ${minTemp} AND is_active = true
  GROUP BY station_code
  ORDER BY avg_temp DESC;
`;

console.log(results.toObjects());
```

---

## Fluent Query Builder (`builder()` / `query()`)

Chain filter conditions, projections, sorting, and limits cleanly:

```javascript
const table = db.table('orders');

const highValueOrders = await table.query()
  .select('order_id', 'customer_id', 'total_amount', 'status')
  .where('total_amount >= 500.00')
  .filter({ status: 'completed' })
  .orderBy('total_amount DESC')
  .limit(25)
  .offset(0)
  .toObjects();

console.log(highValueOrders);
```

### Builder Shortcut Helpers

```javascript
// Extract a single column as a flat array without reading unused columns:
const customerIds = await table.query()
  .where("status = 'completed'")
  .pluck('customer_id');

// Retrieve first matching record:
const firstOrder = await table.query()
  .where("status = 'pending'")
  .first();

// Fast boolean existence check:
const hasOverdue = await table.query()
  .where("status = 'overdue'")
  .exists();
```

---

## Advanced Table Operations

### Upsert (Atomic Insert or Update)

Inserts new records or updates existing matching rows based on a unique primary key column:

```javascript
const inventory = db.table('inventory');

const result = await inventory.upsert([
  { sku: 'SKU-001', name: 'Standard Sensor Hub', stock: 150, price: 89.99 },
  { sku: 'SKU-002', name: 'Compact Gateway', stock: 45, price: 129.50 }
], 'sku');

console.log(`Inserted: ${result.inserted}, Updated: ${result.updated}`);
```

### Chunked Batch Insertion

Inserts massive row arrays in memory-safe chunks:

```javascript
const rows = Array.from({ length: 50000 }, (_, i) => ({
  id: i + 1,
  metric_name: 'cpu_usage',
  value: Math.random() * 100
}));

// Chunk into batches of 5,000 rows
const insertedCount = await table.batchInsert(rows, 5000);
```

### Column Plucking & Unique Values

```javascript
// Pluck single column as flat array:
const emails = await users.pluck('email');

// Pluck multiple columns as tuples:
const credentials = await users.pluck('id', 'email');

// Unique column values:
const regions = await users.distinct('region');
```

### Scalar Statistical Helpers

```javascript
const totalRevenue = await orders.sum('total_amount', "status = 'completed'");
const averageLatency = await telemetry.avg('temperature');
const minPrice = await products.min('price');
const maxPrice = await products.max('price');
```

---

## Hierarchical Databases & Sub-tables

Organize datasets into isolated containers and sub-tables:

```javascript
// 1. Create database container
const logistics = await db.createDatabase('logistics');

// 2. Create tables inside container
const shipments = await logistics.createTable('shipments', [
  { name: 'shipment_id', type: 'INT64' },
  { name: 'origin', type: 'STRING' },
  { name: 'destination', type: 'STRING' }
]);

// 3. Create nested sub-tables
const tracking = await shipments.createSubtable('tracking_events', [
  { name: 'event_id', type: 'INT64' },
  { name: 'checkpoint', type: 'STRING' },
  { name: 'timestamp', type: 'INT64' }
]);

// 4. Dot-notation SQL access
const res = await db.sql`
  SELECT * FROM "logistics.shipments.tracking_events"
  WHERE checkpoint = 'DEPARTED_FACILITY';
`;
```

---

## Zero-Memory Streaming Import & Export

Stream multi-gigabyte files directly to disk or network without memory exhaustion:

```javascript
const table = db.table('transactions');

// Export table to CSV
await table.exportToFile('transactions_backup.csv', 'csv');

// Export table to JSON Lines
await table.exportToFile('transactions_backup.jsonl', 'jsonl');

// Import CSV file into table
await table.importFile('new_transactions.csv', 'csv');
```

---

## Node.js CLI Runner

The `mergendb` package includes a zero-dependency CLI executable:

```bash
# Display help and usage
npx mergendb --help

# Start local server and open Mergen Studio in browser
npx mergendb studio 8765

# Execute SQL query against running server
npx mergendb query "SELECT COUNT(*) FROM iot_telemetry"

# Run system diagnostic benchmark
npx mergendb benchmark
```

---

## Complete API Reference

### `MergenDB` / `MergenClient`

| Method | Returns | Description |
| :--- | :--- | :--- |
| `sql\`query\`` | `Promise<QueryResult>` | Tagged template literal for SQL execution with automatic escaping. |
| `query(sqlQuery, options)` | `Promise<QueryResult>` | Executes raw SQL or pipeline query string. |
| `table(name, database?)` | `TableHandle` | Returns a table reference handle. |
| `createTable(name, cols, blockSize?)` | `Promise<TableHandle>` | Creates a new columnar table. |
| `listTables(database?)` | `Promise<TableInfo[]>` | Lists all tables in workspace or database. |
| `dropTable(name, database?)` | `Promise<Object>` | Permanently drops a table. |
| `database(name)` | `DatabaseHandle` | Returns a database container handle. |
| `createDatabase(name)` | `Promise<DatabaseHandle>` | Creates an isolated database container. |
| `listDatabases()` | `Promise<DatabaseInfo[]>` | Lists all discovered database containers. |
| `dropDatabase(name)` | `Promise<Object>` | Permanently drops a database container. |
| `status()` | `Promise<ServerStatus>` | Retrieves server diagnostics and hardware metrics. |
| `benchmark()` | `Promise<BenchmarkStats>` | Runs live columnar scan benchmark (rows/sec). |

### `TableHandle`

| Method | Returns | Description |
| :--- | :--- | :--- |
| `query()` / `builder()` | `TableQueryBuilder` | Starts fluent query builder. |
| `find(filters?, options?)` | `Promise<Object[]>` | Document-style search matching key-value criteria. |
| `findOne(filters?)` | `Promise<Object\|null>` | Returns first record matching criteria. |
| `first(where?)` | `Promise<Object\|null>` | Returns first record matching optional WHERE clause. |
| `last(where?)` | `Promise<Object\|null>` | Returns last record matching optional WHERE clause. |
| `take(count)` | `Promise<Object[]>` | Takes the first N records as objects. |
| `all(limit?)` | `Promise<Object[]>` | Retrieves all table records up to limit. |
| `where(condition, options?)` | `Promise<Object[]>` | Queries table using a raw SQL WHERE condition. |
| `select(...cols)` | `TableQueryBuilder` | Starts query builder with specified column projection. |
| `insert(data)` | `Promise<Object>` | Inserts single record or array of records. |
| `upsert(records, keyColumn?)` | `Promise<Object>` | Atomic upsert based on primary key column (default: `id`). |
| `batchInsert(records, batchSize?)` | `Promise<number>` | Inserts records in chunked batches. |
| `update(values, where)` | `Promise<number>` | Updates matching rows. |
| `delete(where)` | `Promise<number>` | Deletes matching rows. |
| `truncate()` | `Promise<number>` | Clears all rows while preserving schema. |
| `drop()` | `Promise<Object>` | Permanently deletes table. |
| `count(where?)` | `Promise<number>` | Returns total row count. |
| `exists(filters?)` | `Promise<boolean>` | O(1) early-exit check if matching record exists. |
| `pluck(...columns)` | `Promise<Array>` | Extracts column values as flat array or tuples. |
| `distinct(column, where?)` | `Promise<Array>` | Returns unique values for a column. |
| `sum(col, where?)` | `Promise<number>` | Sums numeric column. |
| `avg(col, where?)` | `Promise<number\|null>` | Calculates column average. |
| `min(col, where?)` | `Promise<any>` | Finds minimum column value. |
| `max(col, where?)` | `Promise<any>` | Finds maximum column value. |
| `exportToFile(file, format)` | `Promise<Object>` | Zero-memory streaming file export (`csv`, `json`, `jsonl`, `sql`). |
| `importFile(file, format)` | `Promise<Object>` | Zero-memory streaming file import (`csv`, `json`, `jsonl`, `sql`). |
| `subtable(name)` | `TableHandle` | Returns handle to nested sub-table. |
| `createSubtable(name, cols)` | `Promise<TableHandle>` | Creates nested sub-table. |

---

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
