<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/logo.png" alt="MergenDB Logo" width="220" />
</p>

# MergenDB Node.js & TypeScript SDK (v1.0.0 Production Release)

[![npm version](https://img.shields.io/npm/v/mergendb.svg?style=flat-square&logo=npm&logoColor=white&cacheSeconds=300)](https://www.npmjs.com/package/mergendb)
[![Socket npm Security Badge](https://badge.socket.dev/npm/package/mergendb)](https://badge.socket.dev/npm/package/mergendb)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-0%20(Zero)-success.svg?style=flat-square)](https://github.com/ugurturkerkebeci/MergenDB)

The official **zero-dependency** Node.js and TypeScript client SDK for **MergenDB** — engineered for high-throughput columnar analytics, embedded edge backends, and unified **AI vector embedding similarity search**.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

## The v1.0.0 Milestone & Architectural Evolution

MergenDB Node.js SDK v1.0.0 is built to bring enterprise-grade analytical SQL and neural vector search into the JavaScript/TypeScript ecosystem without pulling in heavy native bindings, node-gyp builds, or gigabytes of external binaries.

### What We Achieved in v1.0.0:
1. **AI-Native Vector Operations:** Seamlessly store and query `VECTOR` columns with JavaScript `Array<number>` or `Float32Array`.
2. **Native Vector Search Method (`table.vectorSearch`):** Execute nearest-neighbor searches using Cosine, Euclidean (L2), Dot Product, or Manhattan distance.
3. **Sub-Millisecond Hybrid Queries:** Combine relational filters (`filter: "category = 'AI'"`) with vector similarity in a single network round-trip.
4. **Zero External Runtime Dependencies:** Built strictly on Node.js core modules (`http`, `https`, `fs`, `path`, `url`). Zero `node_modules` required in production.
5. **Tagged Template Literal SQL (`db.sql`):** Safe, parameterized analytical SQL queries with intuitive template strings.
6. **Zero-Memory Streaming I/O:** Stream multi-gigabyte CSV, JSON, and SQL dumps directly to disk or network sockets with bounded memory buffers.
7. **Strict Zero-Emoji Policy:** Clean, professional terminal interface built with deterministic status tags (`[+]`, `[-]`, `[*]`, `[!]`).

---

## Installation

```bash
npm install mergendb
```

Or using yarn / pnpm:

```bash
yarn add mergendb
# or
pnpm add mergendb
```

---

## Comprehensive MergenQL & Node.js Usage Guide

### 1. Connection & Local Auto-Start

```typescript
import { MergenDB } from 'mergendb';

// Connect to MergenDB server (or automatically spawn local headless daemon)
const db = new MergenDB({
  host: '127.0.0.1',
  port: 8765,
  autoStart: true // auto-spawns background database daemon if not running
});

await db.ping();
console.log('[+] Connected to MergenDB v1.0.0');
```

### 2. Creating Tables with Vector & Relational Columns

```typescript
const telemetry = db.table('iot_knowledge_base');

await telemetry.create([
  { name: 'doc_id', type: 'INT32' },
  { name: 'title', type: 'STRING' },
  { name: 'category', type: 'STRING' },
  { name: 'embedding', type: 'VECTOR' }
]);

// Insert documents with float vectors
await telemetry.insert([
  { doc_id: 1, title: 'Attention Is All You Need', category: 'AI', embedding: [0.95, 0.1, 0.05] },
  { doc_id: 2, title: 'General Relativity', category: 'Physics', embedding: [0.82, 0.2, 0.15] },
  { doc_id: 3, title: 'French Culinary Arts', category: 'Cooking', embedding: [0.05, 0.9, 0.1] }
]);
```

### 3. Native Vector Similarity Search

Perform top-K nearest-neighbor similarity searches using the intuitive `vectorSearch` API:

```typescript
const results = await telemetry.vectorSearch('embedding', [1.0, 0.0, 0.0], {
  topK: 2,
  filter: "category = 'AI'",
  metric: 'cosine' // 'cosine', 'l2', 'dot', 'manhattan'
});

for (const row of results) {
  console.log(`[+] Document: ${row.title} | Score: ${row.score.toFixed(4)}`);
}
```

### 4. Tagged Template SQL with Vector Similarity

Execute standard SQL with native mathematical vector functions directly in Node.js:

```typescript
const minScore = 0.8;
const targetVector = [1.0, 0.0, 0.0];

const queryRes = await db.sql`
  SELECT doc_id, title, cosine_similarity(embedding, ${targetVector}) AS score
  FROM iot_knowledge_base
  WHERE category = 'AI'
  ORDER BY score DESC
  LIMIT 5;
`;

console.log(queryRes.toObjects());
```

### 5. CLI Usage in Node.js Projects

The Node.js package includes a global and local CLI runner (`mergendb` or `npx mergendb`):

```bash
# Check database server health
npx mergendb status

# Run SQL query from terminal
npx mergendb query "SELECT title, score FROM iot_knowledge_base"

# Benchmark hardware and scan throughput
npx mergendb benchmark
```

---

## TypeScript Definitions

Full TypeScript definitions are bundled in the package (`index.d.ts`), providing complete autocompletion and type inference for `TableHandle`, `DatabaseHandle`, `QueryResult`, and query builder interfaces.

---

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE) for details.
