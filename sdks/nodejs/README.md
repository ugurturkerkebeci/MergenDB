<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="220" />
</p>

# MergenDB Node.js & TypeScript SDK

[![npm version](https://img.shields.io/badge/npm-v0.8.1-blue.svg)](https://www.npmjs.com/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://github.com/ugurturkerkebeci/MergenDB)
[![Node.js Tests](https://img.shields.io/badge/tests-2000%2B%20passed-brightgreen.svg)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Node.js and TypeScript client SDK for **MergenDB** — the ultra-compact, columnar embedded database engine built for edge computing, local analytical SQL, and memory-constrained workloads.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

## Highlights

- **Vectorized Predicate Pushdown (v0.8.0+):** Point lookups and scalar filters (`WHERE TOKEN = "12345678901"`) execute in **~1 second on 100M+ rows** without memory exhaustion or file size bloat.
- **Zero External Dependencies:** Built purely on native Node.js standard library (`http`, `https`, `url`, `child_process`, `fs`, `stream`). Zero third-party packages installed in your runtime.
- **Hierarchical Database Architecture:** Manage databases, tables, and nested sub-tables (`database.table.subtable`) with isolated namespaces and dot-notation SQL queries.
- **Zero-Memory Streaming File Engine:** Pipe multi-gigabyte CSV, JSON, JSONL, and SQL dumps directly to disk or server in 64 KB blocks without memory exhaustion or process crashes.
- **Auto-Start Server (`autoStart: true`):** Spawns and manages the local background MergenDB server transparently if it is not already running.
- **TypeScript First:** Complete typings, interfaces, and code completions included out of the box.
- **Dual Query Paradigm:** Execute full analytical SQL or use fluent document-style APIs (`find`, `findOne`, `search`, `insert`, `update`, `delete`).
- **Safe Parameterized SQL:** Tagged template literal `db.sql` prevents SQL injection with automatic escaping.
- **Live Hardware Telemetry:** Access CPU model, thread topology, and columnar scan benchmarks exceeding 1,000,000 rows/second.

---

## Installation

```bash
npm install mergendb
```

---

## Simple Database CRUD Quickstart

Connecting to a database, inserting data, querying with SQL or document methods, updating, and deleting:

```javascript
const { connect } = require('mergendb');

async function main() {
  // 1. Connect to MergenDB (autoStart spawns local background server automatically)
  const db = connect({
    autoStart: true,
    port: 8765,
    user: 'root',
    password: ''
  });

  const users = db.table('users.mgdb');

  // 2. Insert Records (Create) - schema inferred and compressed automatically
  await users.insert([
    { id: 1, name: 'Alice', department: 'Engineering', salary: 95000, active: true },
    { id: 2, name: 'Bob', department: 'Research', salary: 82000, active: true },
    { id: 3, name: 'Charlie', department: 'Engineering', salary: 102000, active: false },
    { id: 4, name: 'Diana', department: 'Design', salary: 88000, active: true }
  ]);
  console.log('Inserted rows into users.mgdb');

  // 3. Query with Standard SQL (Read)
  const result = await db.query(
    "SELECT name, department, salary FROM users.mgdb WHERE salary >= 85000 ORDER BY salary DESC;"
  );
  console.table(result.rows);

  // Safe tagged template literal with automatic escaping:
  const dept = 'Engineering';
  const eng = await db.sql`SELECT name, salary FROM users.mgdb WHERE department = ${dept} AND active = true`;
  console.log('Active Engineers:', eng.rows);

  // 4. Document-Style find() & findOne()
  const alice = await users.findOne({ name: 'Alice' });
  console.log('Found Alice:', alice);

  const activeStaff = await users.find({ active: true });
  console.log(`Found ${activeStaff.length} active staff members`);

  // 5. Update Records (Update)
  await users.update({ salary: 110000 }, "name = 'Alice'");
  // Or via SQL:
  await db.query("UPDATE users.mgdb SET salary = salary + 3000 WHERE department = 'Engineering';");

  // 6. Delete Records (Delete)
  await users.delete("active = false");
  // Or via SQL:
  await db.query("DELETE FROM users.mgdb WHERE name = 'Bob';");

  // 7. Columnar Analytical Aggregations
  const stats = await db.query(
    "SELECT department, COUNT(*), AVG(salary) FROM users.mgdb GROUP BY department;"
  );
  console.table(stats.rows);
}

main().catch(console.error);
```

### 1. Zero-Setup Auto-Start Connection

```javascript
const { connect } = require('mergendb');

async function main() {
  // Spawns and connects to the background MergenDB engine automatically
  // Default authentication: user 'root' with empty password
  const db = connect({ 
    autoStart: true, 
    port: 8765,
    user: 'root',
    password: ''
  });

  // Verify server health and hardware specifications
  const status = await db.status();
  console.log(`Connected to MergenDB v${status.version} (${status.cpu_threads} CPU threads)`);

  // Insert records into a table (auto-infers schema)
  const users = db.table('users.mgdb');
  await users.insert([
    { id: 1, name: 'Alice', department: 'Engineering', salary: 95000 },
    { id: 2, name: 'Bob', department: 'Research', salary: 88000 },
    { id: 3, name: 'Charlie', department: 'Engineering', salary: 102000 }
  ]);

  // Execute analytical SQL with columnar filtering and aggregation
  const queryResult = await db.query(
    "SELECT department, COUNT(*), AVG(salary) FROM users.mgdb GROUP BY department"
  );
  console.log(`Query completed in ${queryResult.stats.execution_time_ms} ms`);
  console.table(queryResult.rows);

  // Tagged template literal with automatic SQL escaping
  const targetName = 'Alice';
  const match = await db.sql`SELECT * FROM users.mgdb WHERE name = ${targetName}`;
  console.log('User found:', match.rows[0]);
}

main().catch(console.error);
```

---

## Hierarchical Database Containers & Nested Sub-tables

MergenDB provides structured hierarchy: **Databases -> Tables -> Nested Sub-tables**.

```javascript
const { connect } = require('mergendb');

async function hierarchicalExample() {
  const client = connect({ host: '127.0.0.1', port: 8765 });

  // 1. Create and manage databases
  await client.createDatabase('enterprise');
  const dbs = await client.listDatabases();
  console.log('Databases:', dbs);

  const enterpriseDb = client.database('enterprise');

  // 2. Create tables inside the database
  await enterpriseDb.createTable('employees', [
    { name: 'employee_id', type: 'INT' },
    { name: 'full_name', type: 'TEXT' },
    { name: 'department', type: 'TEXT' }
  ]);

  const employeesTable = enterpriseDb.table('employees');
  await employeesTable.insert([
    { employee_id: 101, full_name: 'Alice Johnson', department: 'Engineering' },
    { employee_id: 102, full_name: 'Bob Smith', department: 'Research' }
  ]);

  // 3. Create nested sub-tables (e.g. division-specific teams under employees)
  await employeesTable.createSubtable('engineering', [
    { name: 'employee_id', type: 'INT' },
    { name: 'team', type: 'TEXT' },
    { name: 'code_score', type: 'FLOAT' }
  ]);

  const engineeringTable = employeesTable.subtable('engineering');
  await engineeringTable.insert([
    { employee_id: 101, team: 'Infrastructure', code_score: 98.5 }
  ]);

  // List all sub-tables under employees
  const subtables = await employeesTable.listSubtables();
  console.log('Sub-tables under employees:', subtables);

  // 4. Query nested sub-tables using dot notation
  const res = await client.query('SELECT * FROM enterprise.employees.engineering');
  console.table(res.rows);
}

hierarchicalExample().catch(console.error);
```

---

## Zero-Memory Streaming File Import & Export

Large dataset exports and imports operate via pure Node.js streams. Data is processed in 64 KB chunks without buffering entire tables into V8 heap memory, completely preventing out-of-memory errors and browser crashes.

```javascript
const { connect } = require('mergendb');
const path = require('path');

async function streamingExample() {
  const db = connect('http://localhost:8765');
  const table = db.table('analytics_events.mgdb');

  const exportPath = path.join(__dirname, 'events_dump.csv');
  const importPath = path.join(__dirname, 'new_records.csv');

  // Export table directly to disk via HTTP chunked stream
  console.log('Starting stream export...');
  await table.exportToFile(exportPath, 'csv');
  console.log('Export written successfully to', exportPath);

  // Import file directly via raw socket streaming (64 KB chunks)
  console.log('Starting stream import...');
  const importResult = await table.importFile(importPath, 'csv');
  console.log(`Imported ${importResult.rows_imported} rows in ${importResult.execution_time_ms} ms`);
}

streamingExample().catch(console.error);
```

---

## Complete API Reference

### Connection & Client

```typescript
import { connect, MergenDB } from 'mergendb';

const client = connect({
  host: '127.0.0.1',
  port: 8765,
  activeTable: 'users.mgdb',
  timeout: 30000,
  autoStart: true
});

// Ping server
const isAlive: boolean = await client.ping();

// Hardware and runtime metrics
const sys = await client.status();

// Columnar benchmark
const bench = await client.benchmark();
```

### Database Management

```typescript
// Create database
await client.createDatabase('analytics');

// List databases with sizes and table counts
const dbList = await client.listDatabases();

// Get database handle
const analytics = client.database('analytics');

// List tables in database
const tables = await analytics.listTables();

// Drop database
await client.dropDatabase('analytics');
```

### Table Operations

```typescript
const table = client.table('sensor_data.mgdb');

// Schema inspection
const schema = await table.schema();

// Paginated data retrieval
const page1 = await table.data(1, 50);

// Key-value search
const results = await table.find({ status: 'active' }, { limit: 100 });

// Full-text substring search across all columns
const matched = await table.search('temperature_alert');

// Record count with optional filter
const count = await table.count({ status: 'active' });

// Insert single or batch records
await table.insert([{ timestamp: 1710000000, reading: 42.1 }]);

// Column schema alterations
await table.addColumn('location', 'TEXT', 'Room 1');
await table.renameColumn('reading', 'sensor_value');
await table.dropColumn('location');

// In-place updates and deletions
await table.update({ sensor_value: 45.0 }, "timestamp = 1710000000");
await table.delete("sensor_value < 10.0");

// Truncate and drop
await table.truncate();
await table.drop();
```

### Analytical SQL Queries

```typescript
const result = await client.query(
  "SELECT region, COUNT(*), SUM(sales) FROM transactions GROUP BY region HAVING SUM(sales) > 50000 ORDER BY SUM(sales) DESC"
);

console.log(result.columns);                // Column headers
console.log(result.rows);                   // Matrix rows
console.log(result.stats.execution_time_ms); // Query execution duration
console.log(result.stats.blocks_pruned);     // Blocks skipped via ZoneMaps & Bloom filters
console.log(result.stats.bytes_read);        // Total raw bytes scanned
```

---

## Web Studio & CLI Runner
 
MergenDB core is headless and lightweight. MergenDB Studio is available as an optional extension package:

```bash
# Launch headless server
npx mergendb serve 8765

# Launch Web Studio (auto-installs mergendb-studio if not present)
npx mergendb studio 8765
```

The Web Studio provides:
- Hierarchical database, table, and sub-table navigation tree with expand/collapse states.
- Zero-memory streaming file import and export dialogs with live byte-level progress bars.
- Interactive SQL console with syntax feedback and query timer.
- Dynamic pagination and in-place row editing.
- Full multi-language support (English, German, Turkish).

---

## License

MIT License. Copyright (c) 2026 Uğur Türker Kebeci.
