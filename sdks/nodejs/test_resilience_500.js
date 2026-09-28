/**
 * MergenDB Node.js SDK - 500 Extreme Resilience, Fault Tolerance & Non-Logical Data Test Suite.
 * Covers 500 distinct scenarios across:
 * - Scenarios 001 - 100: Broken, Ragged, Dirty, Scrambled CSVs
 * - Scenarios 101 - 200: Irregular, Broken, Ragged JSON & Streaming JSONL
 * - Scenarios 201 - 300: Fragmented SQL Dumps & Complex Analytical Queries
 * - Scenarios 301 - 400: Illogical Ordering, Schema Mutations & Updates
 * - Scenarios 401 - 500: End-to-End Export & Multi-Format Re-Import Roundtrips
 *
 * Strictly zero emojis. Pure Node.js standard library.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { connect } = require('./index');

const TEST_PORT = 58988;
const TEST_DIR = path.join(__dirname, '..', '..', 'scratch', 'node_resilience500_env');

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
  console.log('   MERGENDB NODE.JS SDK - 500 RESILIENCE & FAULT TOLERANCE TESTS');
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
    // Batch 1: Broken, Ragged, Dirty, Scrambled CSVs (Scenarios 1 - 100)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 1: Broken, Ragged, Dirty, Scrambled CSVs (Scenarios 1 - 100)...');
    for (let t = 1; t <= 100; t++) {
      const tblName = `node_csv_${t}.mgdb`;
      const lines = ['id,title,amount,flag'];
      const scrambledIds = [999, 12, -4, 55, 0, 780, 3, 42, 1000, 19, 8, 204, 33, 91, 15, 6, 77, 888, 2, 50];

      for (let i = 0; i < scrambledIds.length; i++) {
        const rid = scrambledIds[i];
        const mode = (t + i) % 15;

        if (mode === 0) {
          // Ragged short row
          lines.push(`${rid},Short_${i}`);
        } else if (mode === 1) {
          // Ragged long row
          lines.push(`${rid},Long_${i},${rid * 1.5},true,extra_col_A,extra_col_B`);
        } else if (mode === 2) {
          // Null bytes in string
          lines.push(`${rid},Title_\x00_Safe_${i},${rid * 2.0},true`);
        } else if (mode === 3) {
          // Irregular spaces and tabs
          lines.push(`  ${rid}  ,\t"Padded ${i}"\t,  ${rid * 3.14}  ,  false  `);
        } else if (mode === 4) {
          // Dirty null tokens
          const tok = ['', 'NULL', 'none', 'N/A', 'NaN', '\\N', 'nil', '-'][i % 8];
          lines.push(`${rid},Title_${i},${tok},${i % 2 === 0}`);
        } else if (mode === 5) {
          // Unicode Turkish, Cyrillic, Kanji
          lines.push(`${rid},"Veri_Örnek_${i}_Şiir_Москва_東京",${rid * 10},true`);
        } else if (mode === 6) {
          // Quoted commas and semicolons
          lines.push(`${rid},"Part, Subpart; Section: ${i}",${rid * 5.5},false`);
        } else if (mode === 7) {
          // Escaped quotes inside field
          lines.push(`${rid},"Quoted \\"Special\\" Item ${i}",${rid * 4},true`);
        } else if (mode === 8) {
          // Scientific notation and extreme floats
          lines.push(`${rid},Sci_${i},${rid}e2,true`);
        } else if (mode === 9) {
          // Empty line or comment
          lines.push('');
          lines.push(`# Comment row ${i}`);
          lines.push(`${rid},PostComment_${i},${rid * 1.2},false`);
        } else {
          // Standard valid row
          lines.push(`${rid},Standard_${i},${rid * 7.5},${i % 2 === 0}`);
        }
      }

      let content = lines.join('\n');
      if (t % 10 === 0) {
        content = '\uFEFF' + content; // UTF-8 BOM
      }

      const tbl = client.table(tblName);
      const res = await tbl.import(content, 'csv');
      assert(res.rows_imported >= 5, `CSV scenario ${t} imported fewer than 5 rows: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `CSV scenario ${t} count mismatch: ${count} vs ${res.rows_imported}`);
      passedTotal++;
    }
    console.log('    [+] Batch 1 (100/100 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 2: Irregular, Broken, Ragged JSON & Streaming JSONL (Scenarios 101 - 200)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 2: Irregular, Broken, Ragged JSON & JSONL (Scenarios 101 - 200)...');
    for (let t = 101; t <= 200; t++) {
      const isJsonl = (t % 2 === 0);
      const tblName = `node_json_${t}.mgdb`;
      const scrambledIds = [42, 100, 7, 0, 999, -5, 333, 12, 88, 15, 204, 55, 301, 8, 19, 44, 91, 105, 777, 2];
      let content = '';

      if (isJsonl) {
        const lines = [];
        for (let i = 0; i < scrambledIds.length; i++) {
          const rid = scrambledIds[i];
          if (i % 4 === 0 && t % 3 === 0) {
            // Malformed JSON line
            lines.push(`{"id": ${rid}, "name": "Broken_${i}`);
          } else if (i % 5 === 0 && t % 2 === 0) {
            // Null byte inside string
            lines.push(JSON.stringify({ id: rid, name: `null_\x00_${i}`, metric: rid * 1.5 }));
          } else if (i % 3 === 0 && t % 4 === 0) {
            // Whitespace or empty line
            lines.push('   ');
          } else {
            // Out of order keys
            lines.push(JSON.stringify({ metric: rid * 2.5, active: (i % 2 === 0), id: rid, name: `valid_${i}` }));
          }
        }
        content = lines.join('\n');
      } else {
        const arr = [];
        for (let i = 0; i < scrambledIds.length; i++) {
          const rid = scrambledIds[i];
          arr.push({
            id: rid,
            name: i % 4 === 0 ? null : `entity_${rid}`,
            metric: i % 3 === 0 ? null : (rid * 3.14)
          });
        }
        content = JSON.stringify(arr);
      }

      const tbl = client.table(tblName);
      const res = await tbl.import(content, isJsonl ? 'jsonl' : 'json');
      assert(res.rows_imported >= 5, `JSON scenario ${t} imported fewer than 5 rows: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `JSON scenario ${t} count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 2 (100/100 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 3: Fragmented SQL Dumps & Complex Queries (Scenarios 201 - 300)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 3: Fragmented SQL Dumps & Analytical Queries (Scenarios 201 - 300)...');
    for (let t = 201; t <= 300; t++) {
      const tblName = `node_sql_${t}.mgdb`;
      const lines = [
        `CREATE TABLE \`sql_entity_${t}\` (`,
        '  `id` bigint(20) NOT NULL,',
        '  `category` varchar(128) DEFAULT NULL,',
        '  `amount` decimal(12,2) DEFAULT NULL',
        ');',
        `INSERT INTO \`sql_entity_${t}\` VALUES`
      ];

      const ids = [500, 10, 250, 2, 90, 1, 800, 35, 777, 4, 120, 65, 300, 8, 44, 9, 600, 15, 888, 3];
      const categories = ['Electronics', 'Books', 'Fashion', 'Home', 'Automotive'];
      const tuples = [];

      for (let i = 0; i < ids.length; i++) {
        const rid = ids[i];
        const cat = categories[i % categories.length];
        if (i % 4 === 0 && t % 2 === 0) {
          // Broken syntax tuple
          tuples.push(`(${rid}, 'Incomplete`);
        } else if (i % 5 === 0) {
          // Escaped quote
          tuples.push(`(${rid}, 'O\\'Connor_${i}', ${rid * 15.5})`);
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
    console.log('    [+] Batch 3 (100/100 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 4: Illogical Ordering & Schema Mutations (Scenarios 301 - 400)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 4: Illogical Ordering & Schema Mutations (Scenarios 301 - 400)...');
    for (let t = 301; t <= 400; t++) {
      const tblName = `node_mut_${t}.mgdb`;
      const tbl = client.table(tblName);

      // Create table
      await client.createTable(tblName, [
        { name: 'id', type: 'INT64' },
        { name: 'tag', type: 'STRING' },
        { name: 'value', type: 'FLOAT64' }
      ]);

      // Illogical reverse insert with extreme negative numbers and nulls
      const batch = [];
      const ids = [1000, 50, -999, 12, 0, 450, -3, 88, 777, 1];
      for (let i = 0; i < ids.length; i++) {
        const rid = ids[i];
        batch.push({
          id: rid,
          tag: i % 3 === 0 ? null : `tag_${rid}_${t}`,
          value: i % 4 === 0 ? null : (rid * 2.5)
        });
      }
      await tbl.insert(batch);
      assert(await tbl.count() === 10, `Mutation scenario ${t} insert count mismatch`);

      // Add dynamic column
      const newCol = `dyn_${t % 50}`;
      await tbl.addColumn(newCol, 'string', 'fallback_init');
      const schema = await tbl.schema();
      assert(schema.columns.some(c => c.name === newCol), `Mutation scenario ${t} column addition failed`);

      // Update subset with condition
      await tbl.update({ value: 9999.99 }, 'id > 50');

      // Delete extreme negative IDs
      await tbl.delete('id < 0');
      const remaining = await tbl.count();
      assert(remaining === 8, `Mutation scenario ${t} post-delete count mismatch: ${remaining} vs 8`);
      passedTotal++;
    }
    console.log('    [+] Batch 4 (100/100 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 5: End-to-End Export & Multi-Format Roundtrips (Scenarios 401 - 500)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 5: End-to-End Export & Multi-Format Roundtrips (Scenarios 401 - 500)...');
    for (let t = 401; t <= 500; t++) {
      const tblName = `node_roundtrip_${t}.mgdb`;
      const tbl = client.table(tblName);

      // Create initial table
      await client.createTable(tblName, [
        { name: 'id', type: 'INT64' },
        { name: 'token', type: 'STRING' },
        { name: 'score', type: 'FLOAT64' }
      ]);

      const seed = [];
      const scrambled = [88, 3, 19, 0, 750, 42, 11, 999, 5, 120];
      for (let i = 0; i < scrambled.length; i++) {
        const rid = scrambled[i];
        seed.push({
          id: rid,
          token: `token_${rid}_${t}`,
          score: rid * 10.5
        });
      }
      await tbl.insert(seed);

      const fmt = ['csv', 'json', 'jsonl', 'sql'][t % 4];
      const expPath = path.join(TEST_DIR, `export_${t}.${fmt}`);
      await tbl.exportToFile(expPath, fmt);

      assert(fs.existsSync(expPath), `Export file missing for scenario ${t}`);
      assert(fs.statSync(expPath).size > 0, `Export file is empty for scenario ${t}`);

      // Re-import into fresh destination table
      const destTable = `node_dest_${t}.mgdb`;
      const dTable = client.table(destTable);
      await dTable.importFile(expPath, fmt);

      const reimported = await dTable.count();
      assert(reimported === 10, `Roundtrip scenario ${t} (${fmt}) mismatch: ${reimported} vs 10`);

      passedTotal++;
    }
    console.log('    [+] Batch 5 (100/100 scenarios): PASS');

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log('----------------------------------------------------------------');
    console.log(`   [SUCCESS] ALL ${passedTotal} / 500 RESILIENCE SCENARIOS PASSED IN ${duration}s!`);
    console.log('================================================================');

  } catch (err) {
    console.error('[-] Test failed with error:', err);
    process.exitCode = 1;
  } finally {
    serverProc.kill();
  }
}

run();
