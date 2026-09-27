# MergenDB Node.js & TypeScript SDK

[![npm version](https://img.shields.io/badge/npm-v0.6.0-blue.svg)](https://www.npmjs.com/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Node.js and TypeScript client for **MergenDB** — the ultra-compact, columnar embedded database engine built for edge computing, local analytics, and memory-constrained workloads.

---

## ⚡ Features

- **Zero Runtime Dependencies:** Built purely on native Node.js standard library.
- **TypeScript First:** Complete typings, interfaces, and autocompletion out of the box.
- **SQL & Document-Style APIs:** Run analytical SQL or use fluent `.find()` / `.count()` syntax.
- **Tagged Template Literals (`db.sql`):** Safe parameter interpolation preventing SQL injection.
- **Analytical Metrics:** Direct visibility into query execution time, ZoneMap pruned blocks, and bytes read.
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

  // Check connection health
  const isHealthy = await db.ping();
  console.log('MergenDB connection status:', isHealthy ? 'ONLINE' : 'OFFLINE');

  // Analytical SQL Query
  const result = await db.query("SELECT country, COUNT(*), AVG(revenue) FROM sales GROUP BY country HAVING COUNT(*) > 10");
  console.log(`Executed in ${result.stats.execution_time_ms} ms`);
  console.table(result.rows);

  // Tagged template literal with automatic escaping
  const targetCountry = "TR";
  const users = await db.sql`SELECT id, name, balance FROM accounts WHERE country = ${targetCountry}`;
  console.log(`Found ${users.row_count} accounts`);

  // Document-style Table API
  const telemetry = db.table('telemetry.mgdb');
  const activeSensors = await telemetry.find({ status: 'ACTIVE' }, { limit: 10 });
  console.log('Active sensors:', activeSensors);
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
