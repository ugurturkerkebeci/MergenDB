# MergenDB Node.js & TypeScript SDK

[![npm version](https://img.shields.io/badge/npm-v0.6.1-blue.svg)](https://www.npmjs.com/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Node.js and TypeScript client for **MergenDB** — the ultra-compact, columnar embedded database engine built for edge computing, local analytics, and memory-constrained workloads.

---

## ⚡ Features

- **Zero Runtime Dependencies:** Built purely on native Node.js standard library (`http`, `url`, `child_process`).
- **TypeScript First:** Complete typings, interfaces, and autocompletion out of the box.
- **100% Feature Parity with Python CLI:** Insert, query, search, update, delete, schema alteration, and benchmarks.
- **SQL & Document-Style APIs:** Run analytical SQL or use fluent `.find()` / `.findOne()` / `.search()` syntax.
- **Tagged Template Literals (`db.sql`):** Safe parameter interpolation preventing SQL injection.
- **Live Hardware Profiling:** Direct access to `db.benchmark()` scanning over 1,000,000+ rows/sec.
- **Full phpMyAdmin Studio Operations:** Truncate, Drop, Rename, Import, and Export directly from JS/TS.

---

## 📦 Installation

```bash
npm install mergendb
```

---

## 🚀 Quick Start

### 1. Start the MergenDB Server

```bash
mergen serve 8765
```

### 2. Connect from Node.js (JavaScript / TypeScript)

```javascript
const { connect } = require('mergendb');
// Or with ESM / TypeScript:
// import { connect } from 'mergendb';

async function main() {
  // Connect to local or remote MergenDB server
  const db = connect('http://localhost:8765');

  // Check connection health & CPU specs
  const isHealthy = await db.ping();
  const status = await db.status();
  console.log(`Connected to MergenDB ${status.version} on ${status.system?.cpu || 'system'}`);

  // Insert records directly (auto-inferred schema)
  const users = db.table('users.mgdb');
  await users.insert([
    { id: 1, name: 'Alice', role: 'admin', balance: 1500 },
    { id: 2, name: 'Bob', role: 'engineer', balance: 2400 }
  ]);

  // Full-text substring search across all columns
  const searchResults = await users.search('Ali');
  console.log('Search matches:', searchResults.rows);

  // Update records
  await users.update({ balance: 1750 }, "name = 'Alice'");

  // Delete records
  await users.delete("balance < 1000");

  // Schema alterations
  await users.addColumn('last_login', 'TIMESTAMP');
  await users.renameColumn('role', 'user_role');

  // Analytical SQL Query
  const result = await db.query("SELECT user_role, COUNT(*), AVG(balance) FROM users GROUP BY user_role");
  console.log(`Executed in ${result.stats.execution_time_ms} ms`);
  console.table(result.rows);

  // Tagged template literal with automatic escaping
  const targetId = 1;
  const user = await db.sql`SELECT * FROM users WHERE id = ${targetId}`;
  console.log('User found:', user.rows[0]);

  // Live hardware benchmark
  const bench = await db.benchmark();
  console.log(`Hardware Scan Throughput: ${bench.scan_throughput}`);
}

main().catch(console.error);
```

---

## 📖 API Reference

### Connection

```typescript
const db = connect({
  host: '127.0.0.1',
  port: 8765,
  activeTable: 'analytics.mgdb',
  timeout: 30000 // ms
});
```

### Table CRUD & Search Operations

```typescript
const table = db.table('users.mgdb');

// Insert rows
await table.insert([{ id: 1, name: 'Charlie', balance: 500 }]);

// Key-value filtering
const active = await table.find({ role: 'admin' }, { limit: 10, offset: 0 });

// Full-text search
const matches = await table.search('engineering');

// In-place updates
await table.update({ balance: 600 }, "id = 1");

// Deletion
await table.delete("id = 1");

// Schema alterations
await table.addColumn('country', 'TEXT', 'TR');
await table.renameColumn('country', 'nation');
await table.dropColumn('nation');

// Administrative
await table.truncate();
await table.drop();
```

### Analytical SQL Execution

```typescript
const res = await db.query("SELECT * FROM logs WHERE severity = 'ERROR'");

console.log(res.columns);               // ['timestamp', 'severity', 'message']
console.log(res.rows);                  // [[1695840000, 'ERROR', 'Disk full'], ...]
console.log(res.stats.execution_time_ms); // 0.42 ms
console.log(res.stats.blocks_pruned);    // 8 (Skipped via ZoneMaps & Bloom filter)
```

### Fluent Table Operations

```typescript
const table = db.table('users');

// Inspect schema
const schema = await table.schema();
console.log(schema.columns);

// Paginated data view
const page1 = await table.data(1, 25);

// Count records
const totalAdmins = await table.count({ role: 'admin' });

// Export data
const csvData = await table.export('csv');
const jsonData = await table.export('json');

// Administrative actions
await table.truncate(); // Clear records
await table.drop();     // Delete .mgdb file
```

---

## 📄 License

MIT © [Uğur Türker Kebeci](https://github.com/ugurturkerkebeci)
