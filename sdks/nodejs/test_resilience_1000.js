/**
 * MergenDB Node.js SDK - 1000 Heavy Resilience, Fault-Tolerance & Complex Edge Case Test Suite.
 * Covers 1000 distinct scenarios across:
 * - Scenarios 0001 - 0200: Complex, Irregular, Corrupted Encodings & Ragged CSV/TSV/PSV
 * - Scenarios 0201 - 0400: Malformed, Broken, Ragged Schemas & Deeply Nested JSON/JSONL
 * - Scenarios 0401 - 0600: Fragmented SQL Dumps, DDL Edge Cases & Complex Group/Filter Queries
 * - Scenarios 0601 - 0800: Illogical Ordering, High-Churn Dynamic Schema Mutations & Updates
 * - Scenarios 0801 - 1000: End-to-End Multi-Format Cross Roundtrips & Zero-Length Boundaries
 *
 * Strictly zero emojis. Pure Node.js standard library.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { connect } = require('./index');

const TEST_PORT = 58977;
const TEST_DIR = path.join(__dirname, '..', '..', 'scratch', 'node_resilience1000_env');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error('Assertion failed: ' + message);
  }
}

async function run() {
  console.log('================================================================');
  console.log('   MERGENDB NODE.JS SDK - 1000 RESILIENCE & FAULT TOLERANCE TESTS');
  console.log('================================================================');

  if (!fs.existsSync(TEST_DIR)) {
    fs.mkdirSync(TEST_DIR, { recursive: true });
  }

  // 1. Spawn MergenDB server in scratch directory
  console.log(`[*] Spawning MergenDB server on port ${TEST_PORT}...`);
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  const repoRoot = path.resolve(__dirname, '..', '..');
  const serverProc = spawn(pythonPath, ['-u', '-m', 'mergendb.server.server', '--port', String(TEST_PORT)], {
    cwd: TEST_DIR,
    env: { ...process.env, PYTHONPATH: repoRoot },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  serverProc.stdout.on('data', () => {}); // Drain stdout pipe buffer to prevent OS deadlock
  serverProc.stderr.on('data', () => {});

  serverProc.on('error', (err) => {
    console.error('Failed to spawn MergenDB server:', err);
    process.exit(1);
  });

  // Wait for server to bind
  let connected = false;
  const client = connect(`http://127.0.0.1:${TEST_PORT}`);

  for (let attempt = 0; attempt < 30; attempt++) {
    await sleep(200);
    const alive = await client.ping();
    if (alive) {
      connected = true;
      break;
    }
  }

  if (!connected) {
    console.error('[-] Error: MergenDB server did not respond within 6 seconds.');
    serverProc.kill();
    process.exit(1);
  }
  console.log('    [+] Server connection established.');

  let passedTotal = 0;
  const startTime = Date.now();

  try {
    // ------------------------------------------------------------------
    // Batch 1: Complex, Irregular, Corrupted Encodings & Ragged CSV (1 - 200)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 1: Complex, Irregular & Ragged CSVs (Scenarios 1 - 200)...');
    for (let t = 1; t <= 200; t++) {
      const tblName = `node_csv1000_${t}.mgdb`;
      const delimiter = [',', '\t', ';', '|'][t % 4];
      const headers = ['id', 'code_name', 'score', 'is_verified', 'extra_notes'];
      const lines = [headers.join(delimiter)];

      const scrambledIds = [999999, -500, 0, 42, 123456789, -1, 77, 314, 8, 2048, 55, -99, 100, 3, 7777];
      const nullTokens = ['', 'NULL', 'none', 'N/A', 'NaN', '\\N', 'nil', '-', 'None', 'undefined', '#N/A'];

      for (let i = 0; i < scrambledIds.length; i++) {
        const rid = scrambledIds[i];
        const mode = (t + i) % 18;

        if (mode === 0) {
          lines.push(`${rid}${delimiter}ShortRow_${i}`);
        } else if (mode === 1) {
          lines.push([rid, `Long_${i}`, rid * 1.5, 'true', 'extra1', 'extra2', 'extra3'].join(delimiter));
        } else if (mode === 2) {
          lines.push([rid, `Safe\x00Null_${i}`, rid * 2.0, 'true', 'notes'].join(delimiter));
        } else if (mode === 3) {
          lines.push(`  ${rid}  ${delimiter}  "Padded ${i}"  ${delimiter}  ${rid * 3.14}  ${delimiter}  false  ${delimiter}  "note"  `);
        } else if (mode === 4) {
          const tok = nullTokens[i % nullTokens.length];
          lines.push([rid, `Token_${i}`, tok, (i % 2 === 0).toString(), ''].join(delimiter));
        } else if (mode === 5) {
          lines.push([rid, `Şiir_Örnek_${i}_Москва_東京_العربية_clean`, rid * 10, 'true', 'unicode'].join(delimiter));
        } else if (mode === 6) {
          lines.push([rid, `""Quoted""_${i}`, rid * 4.2, 'false', `Note with "quotes" ${i}`].join(delimiter));
        } else if (mode === 7) {
          lines.push([rid, `Sci_${i}`, `${rid}e-4`, 'true', 'exp'].join(delimiter));
        } else if (mode === 8) {
          lines.push('');
          lines.push(`# Comment line ${i}`);
          lines.push([rid, `PostComment_${i}`, rid * 0.5, 'false', 'ok'].join(delimiter));
        } else if (mode === 9) {
          lines.push(headers.join(delimiter));
          lines.push([rid, `PostHeader_${i}`, rid * 1.1, 'true', 'repeated'].join(delimiter));
        } else if (mode === 10) {
          lines.push([rid, `Ctrl_${i}\r\v`, rid * 7.7, 'false', 'control'].join(delimiter));
        } else {
          lines.push([rid, `Valid_${i}`, rid * 5.0, (i % 2 === 0).toString(), `normal_note_${i}`].join(delimiter));
        }
      }

      let content = lines.join('\n');
      if (t % 5 === 0) {
        content = '\uFEFF' + content; // UTF-8 BOM
      }

      const tbl = client.table(tblName);
      const res = await tbl.import(content, 'csv');
      assert(res.rows_imported >= 3, `CSV scenario ${t} imported fewer than 3 rows: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `CSV scenario ${t} count mismatch: ${count} vs ${res.rows_imported}`);
      passedTotal++;
    }
    console.log('    [+] Batch 1 (200/200 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 2: Malformed, Broken, Ragged Schemas & JSON (201 - 400)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 2: Irregular, Broken & Ragged JSON/JSONL (Scenarios 201 - 400)...');
    for (let t = 201; t <= 400; t++) {
      const isJsonl = (t % 2 === 0);
      const tblName = `node_json1000_${t}.mgdb`;
      const scrambledIds = [42, 100, 7, 0, 999, -5, 333, 12, 88, 15, 204, 55, 301, 8, 19, 44, 91, 105, 777, 2];
      let content = '';

      if (isJsonl) {
        const lines = [];
        for (let i = 0; i < scrambledIds.length; i++) {
          const rid = scrambledIds[i];
          const mode = (t + i) % 10;
          if (mode === 0) {
            lines.push(`{"id": ${rid}, "name": "Broken_${i}`);
          } else if (mode === 1) {
            lines.push(JSON.stringify({ id: rid, name: { nested: { key: `deep_${i}` } }, metric: rid * 1.5 }));
          } else if (mode === 2) {
            lines.push(JSON.stringify({ id: rid, name: `null\x00safe_${i}`, metric: rid * 2.2 }));
          } else if (mode === 3) {
            lines.push(JSON.stringify({ record_id: rid, title: `drift_${i}`, score: rid * 3.3, flag: true }));
          } else if (mode === 4) {
            lines.push('     ');
          } else if (mode === 5) {
            lines.push(`// Comment line ${i}`);
          } else {
            lines.push(JSON.stringify({
              metric: i % 4 === 0 ? null : (rid * 4.4),
              active: (i % 2 === 0),
              id: rid,
              name: i % 3 === 0 ? null : `entity_${rid}`
            }));
          }
        }
        content = lines.join('\n');
      } else {
        const items = [];
        for (let i = 0; i < scrambledIds.length; i++) {
          const rid = scrambledIds[i];
          if (i % 5 === 0 && t % 3 === 0) {
            items.push({ id: rid, name: `complex_${rid}`, metric: rid * 2.5, tags: ['a', 'b', i] });
          } else {
            items.push({
              id: rid,
              name: i % 4 === 0 ? null : `entry_${rid}`,
              metric: i % 3 === 0 ? null : (rid * 3.14)
            });
          }
        }
        content = JSON.stringify(items);
      }

      const tbl = client.table(tblName);
      const res = await tbl.import(content, isJsonl ? 'jsonl' : 'json');
      assert(res.rows_imported >= 3, `JSON scenario ${t} imported fewer than 3 rows: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `JSON scenario ${t} count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 2 (200/200 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 3: Fragmented SQL Dumps & Complex Queries (401 - 600)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 3: Fragmented SQL Dumps & Analytical Queries (Scenarios 401 - 600)...');
    for (let t = 401; t <= 600; t++) {
      const tblName = `node_sql1000_${t}.mgdb`;
      const lines = [
        `CREATE TABLE \`sql_entity_${t}\` (`,
        '  `id` bigint(20) NOT NULL AUTO_INCREMENT,',
        '  `category` varchar(128) DEFAULT NULL,',
        '  `amount` decimal(12,2) DEFAULT NULL,',
        '  PRIMARY KEY (`id`)',
        ');',
        `INSERT INTO \`sql_entity_${t}\` VALUES`
      ];

      const ids = [500, 10, 250, 2, 90, 1, 800, 35, 777, 4, 120, 65, 300, 8, 44, 9, 600, 15, 888, 3];
      const categories = ['Electronics', 'Books', 'Fashion', 'Home', 'Automotive', 'Industrial', 'Health'];
      const tuples = [];

      for (let i = 0; i < ids.length; i++) {
        const rid = ids[i];
        const cat = categories[i % categories.length];
        if (i % 4 === 0 && t % 2 === 0) {
          tuples.push(`(${rid}, 'Incomplete`);
        } else if (i % 5 === 0) {
          tuples.push(`(${rid}, 'O\\'Connor_${i}', ${rid * 15.5})`);
        } else if (i % 7 === 0) {
          tuples.push(`(${rid}, NULL, NULL)`);
        } else {
          tuples.push(`(${rid}, '${cat}', ${rid * 12.0})`);
        }
      }
      lines.push(tuples.join(',\n') + ';');

      const tbl = client.table(tblName);
      const res = await tbl.import(lines.join('\n'), 'sql');
      assert(res.rows_imported >= 5, `SQL scenario ${t} imported fewer than 5 rows: ${res.rows_imported}`);

      // Analytical query with GROUP BY
      const queryRes = await client.query(
        `SELECT category, COUNT(*) AS total_count FROM ${tblName} GROUP BY category`
      );
      assert(queryRes.rows.length > 0, `SQL scenario ${t} query failed`);
      passedTotal++;
    }
    console.log('    [+] Batch 3 (200/200 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 4: Illogical Ordering & Schema Mutations (601 - 800)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 4: Illogical Ordering & Schema Mutations (Scenarios 601 - 800)...');
    for (let t = 601; t <= 800; t++) {
      const tblName = `node_mut1000_${t}.mgdb`;
      const tbl = client.table(tblName);

      // Create table
      await client.createTable(tblName, [
        { name: 'id', type: 'INT64' },
        { name: 'tag', type: 'STRING' },
        { name: 'value', type: 'FLOAT64' }
      ]);

      // Illogical reverse insert with negative IDs and nulls
      const batch = [];
      const ids = [10000, 50, -9999, 12, 0, 450, -3, 88, 777, 1, -12345, 999];
      for (let i = 0; i < ids.length; i++) {
        const rid = ids[i];
        batch.push({
          id: rid,
          tag: i % 3 === 0 ? null : `tag_${rid}_${t}`,
          value: i % 4 === 0 ? null : (rid * 2.5)
        });
      }
      await tbl.insert(batch);
      assert(await tbl.count() === 12, `Mutation scenario ${t} insert count mismatch`);

      // Add dynamic column
      const newCol = `metric_${t % 100}`;
      await tbl.addColumn(newCol, 'string', 'init_val');
      const schema = await tbl.schema();
      assert(schema.columns.some(c => c.name === newCol), `Mutation scenario ${t} column addition failed`);

      // Update subset with condition
      await tbl.update({ value: 8888.88 }, 'id > 100');

      // Delete negative IDs
      await tbl.delete('id < 0');
      const remaining = await tbl.count();
      assert(remaining === 9, `Mutation scenario ${t} post-delete count mismatch: ${remaining} vs 9`);
      passedTotal++;
    }
    console.log('    [+] Batch 4 (200/200 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 5: End-to-End Export & Multi-Format Roundtrips (801 - 1000)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 5: Multi-Format Cross Roundtrips (Scenarios 801 - 1000)...');
    for (let t = 801; t <= 1000; t++) {
      const tblName = `node_roundtrip1000_${t}.mgdb`;
      const tbl = client.table(tblName);

      // Create initial table
      await client.createTable(tblName, [
        { name: 'id', type: 'INT64' },
        { name: 'name', type: 'STRING' },
        { name: 'rating', type: 'FLOAT64' },
        { name: 'active', type: 'BOOL' }
      ]);

      const fmt = ['csv', 'json', 'jsonl', 'sql'][t % 4];

      if (t % 50 === 0) {
        // Zero-row empty table export/import roundtrip
        const expPath = path.join(TEST_DIR, `empty_exp1000_${t}.${fmt}`);
        await tbl.exportToFile(expPath, fmt);
        assert(fs.existsSync(expPath), `Empty export file missing for scenario ${t}`);

        const destTable = `node_empty_dest1000_${t}.mgdb`;
        const dTable = client.table(destTable);
        await dTable.importFile(expPath, fmt);
        const reimported = await dTable.count();
        assert(reimported === 0, `Empty roundtrip scenario ${t} mismatch: ${reimported} vs 0`);
        passedTotal++;
        continue;
      }

      const seed = [];
      const scrambled = [55, 1, 999, 12, 4, 300, 77, 8, 120, 2];
      for (let i = 0; i < scrambled.length; i++) {
        const rid = scrambled[i];
        seed.push({
          id: rid,
          name: `user_${rid}_${t}`,
          rating: rid * 1.5,
          active: (rid % 2 === 0)
        });
      }
      await tbl.insert(seed);

      const expPath = path.join(TEST_DIR, `exp1000_${t}.${fmt}`);
      await tbl.exportToFile(expPath, fmt);

      assert(fs.existsSync(expPath), `Export file missing for scenario ${t}`);
      assert(fs.statSync(expPath).size > 0, `Export file is empty for scenario ${t}`);

      // Re-import into fresh destination table
      const destTable = `node_dest1000_${t}.mgdb`;
      const dTable = client.table(destTable);
      await dTable.importFile(expPath, fmt);

      const reimported = await dTable.count();
      assert(reimported === 10, `Roundtrip scenario ${t} (${fmt}) mismatch: ${reimported} vs 10`);

      passedTotal++;
    }
    console.log('    [+] Batch 5 (200/200 scenarios): PASS');

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log('----------------------------------------------------------------');
    console.log(`   [SUCCESS] ALL ${passedTotal} / 1000 RESILIENCE SCENARIOS PASSED IN ${duration}s!`);
    console.log('================================================================');

  } catch (err) {
    console.error('[-] Test failed with error:', err);
    process.exitCode = 1;
  } finally {
    serverProc.kill();
  }
}

run();
