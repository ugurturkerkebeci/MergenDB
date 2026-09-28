/**
 * Extreme 100-Scenario Resilience and Fault Tolerance Test Suite for MergenDB Node.js SDK v0.7.
 * Tests broken rows, dirty types, null bytes, ragged schemas, multi-encodings,
 * complex mutations, analytical queries, and export roundtrips.
 * Strictly zero emojis. Pure Node.js standard library.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { connect } = require('./index');

const TEST_PORT = 58999;
const TEST_DIR = path.join(__dirname, '..', '..', 'scratch', 'node_resilience100_env');

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
  console.log('   MERGENDB NODE.JS SDK - 100 EXTREME RESILIENCE SCENARIOS');
  console.log('================================================================');

  if (!fs.existsSync(TEST_DIR)) {
    fs.mkdirSync(TEST_DIR, { recursive: true });
  }

  // 1. Spawn MergenDB server
  console.log(`[*] Spawning MergenDB server on port ${TEST_PORT}...`);
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  const repoRoot = path.resolve(__dirname, '..', '..');
  const serverProc = spawn(pythonPath, ['-u', '-m', 'mergendb.server.server', '--port', String(TEST_PORT)], {
    cwd: TEST_DIR,
    env: { ...process.env, PYTHONPATH: repoRoot },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  serverProc.stderr.on('data', (d) => {
    const msg = d.toString();
    if (!msg.includes('HTTP/1.1')) {
      // quiet debug
    }
  });

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

  try {
    // ------------------------------------------------------------------
    // Batch 1: Broken, Ragged and Dirty CSVs (Scenarios 1 - 20)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 1: Broken, Ragged and Dirty CSVs (Scenarios 1 - 20)...');
    for (let t = 1; t <= 20; t++) {
      const tblName = `node_c1_${t}.mgdb`;
      const lines = ['id,title,amount,flag'];
      for (let r = 1; r <= 20; r++) {
        if (t === 1) { // ragged short lines
          lines.push(r % 2 === 0 ? `${r},Short_${r}` : `${r},Clean_${r},${r * 10},true`);
        } else if (t === 2) { // ragged long lines
          lines.push(r % 3 === 0 ? `${r},Long_${r},${r * 10},true,extra1,extra2` : `${r},Clean_${r},${r * 10},true`);
        } else if (t === 3) { // null bytes
          lines.push(`${r},User_\x00_${r},${r * 5},true`);
        } else if (t === 4) { // whitespace padding
          lines.push(`  ${r}  ,  "Padded ${r}"  ,  ${r * 2.5}  ,  false  `);
        } else if (t === 5) { // empty and comment lines
          if (r % 3 === 0) lines.push('');
          if (r % 5 === 0) lines.push(`# Comment ${r}`);
          lines.push(`${r},Item_${r},${r * 1.5},true`);
        } else if (t === 6) { // carriage returns
          lines.push(`${r},Item_${r}\r,${r * 3},false`);
        } else if (t === 7) { // extreme unicode (Turkish, Russian, Japanese)
          lines.push(`${r},Şiir_Örnek_${r}_Москва_東京,${r * 10},true`);
        } else if (t === 8) { // dirty null tokens
          const tok = ['', 'NULL', 'none', 'N/A', 'NaN', '\\N', 'nil', '-'][r % 8];
          lines.push(`${r},Item_${r},${r % 2 === 0 ? tok : r * 10},true`);
        } else if (t === 9) { // scientific notation
          lines.push(`${r},Sci_${r},${r}e3,true`);
        } else if (t === 10) { // negative numbers
          lines.push(`-${r},Neg_${r},-${r * 5.25},false`);
        } else if (t === 11) { // quotes with commas
          lines.push(`${r},"Part, Division ${r}",${r * 100},true`);
        } else if (t === 12) { // semicolons inside quotes
          lines.push(`${r},"Segment;A;B;${r}",${r * 20},true`);
        } else if (t === 13) { // single quotes
          lines.push(`${r},'Single_${r}',${r * 15},true`);
        } else if (t === 14) { // empty fields
          lines.push(`${r},,,`);
        } else if (t === 15) { // long fields (2 KB)
          lines.push(`${r},${'Y'.repeat(2000)},${r * 10},true`);
        } else if (t === 16) { // tabs
          lines.push(`${r}\t,\tTab_${r}\t,\t${r * 10}\t,\ttrue`);
        } else if (t === 17) { // pipes inside quotes
          lines.push(`${r},"X|Y|Z|${r}",${r * 10},false`);
        } else if (t === 18) { // BOM marker
          lines.push(`${r},BOM_${r},${r * 10},true`);
        } else if (t === 19) { // boolean token variations
          const bTok = ['true', 'false', '1', '0', 'yes', 'no'][r % 6];
          lines.push(`${r},Bool_${r},${r * 10},${bTok}`);
        } else { // t === 20: null bytes and irregular returns
          lines.push(`${r},\x00Item_${r}\r,${r * 5},true`);
        }
      }

      let content = lines.join('\n');
      if (t === 18) content = '\uFEFF' + content;

      const tbl = client.table(tblName);
      const res = await tbl.import(content, 'csv');
      assert(res.rows_imported >= 10, `Batch 1 scenario ${t} imported fewer than 10 rows: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `Batch 1 scenario ${t} count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 1 (20/20 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 2: Extreme Schema & Mutations (Scenarios 21 - 40)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 2: Schema Mutations & Complex Insertions (Scenarios 21 - 40)...');
    for (let t = 21; t <= 40; t++) {
      const tblName = `node_c2_${t}.mgdb`;
      const tbl = client.table(tblName);

      // Create with schema
      await client.createTable(tblName, [
        { name: 'id', type: 'INT64' },
        { name: 'val', type: 'FLOAT64' },
        { name: 'label', type: 'STRING' },
        { name: 'active', type: 'BOOL' }
      ]);

      // Insert irregular objects
      const batch = [];
      for (let r = 1; r <= 15; r++) {
        batch.push({
          id: r,
          val: r % 4 === 0 ? null : (r * 3.5),
          label: r % 3 === 0 ? null : `Label_${r}_${t}`,
          active: r % 2 === 0
        });
      }
      await tbl.insert(batch);
      assert(await tbl.count() === 15, `Scenario ${t} insert count mismatch`);

      // Add column
      await tbl.addColumn(`extra_${t}`, 'string', 'default_val');
      const schema = await tbl.schema();
      assert(schema.columns.some(c => c.name === `extra_${t}`), `Scenario ${t} column addition failed`);

      // Update rows
      await tbl.update({ active: false }, 'id > 10');

      // Delete subset
      await tbl.delete('id = 1');
      assert(await tbl.count() === 14, `Scenario ${t} post-delete count mismatch`);

      passedTotal++;
    }
    console.log('    [+] Batch 2 (20/20 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 3: Malformed JSON & JSONL Streams (Scenarios 41 - 60)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 3: Malformed JSON and JSONL Streams (Scenarios 41 - 60)...');
    for (let t = 41; t <= 60; t++) {
      const isJsonl = (t % 2 === 0);
      const tblName = `node_c3_${t}.mgdb`;
      let content = '';

      if (isJsonl) {
        const lines = [];
        for (let r = 1; r <= 20; r++) {
          if (r % 5 === 0 && t in [42, 44, 46, 48]) {
            lines.push(`{"id": ${r}, "name": "corrupt`);
          } else if (r % 7 === 0) {
            lines.push(`{"id": ${r}, "name": "null_\x00_${r}", "score": ${r * 10}}`);
          } else {
            lines.push(JSON.stringify({ id: r, name: `valid_${r}`, score: r * 2.5 }));
          }
        }
        content = lines.join('\n');
      } else {
        const arr = [];
        for (let r = 1; r <= 15; r++) {
          arr.push({ id: r, name: `entity_${r}`, score: r % 3 === 0 ? null : (r * 1.5) });
        }
        content = JSON.stringify(arr);
      }

      const tbl = client.table(tblName);
      const res = await tbl.import(content, isJsonl ? 'jsonl' : 'json');
      assert(res.rows_imported >= 10, `Batch 3 scenario ${t} imported fewer than 10 rows: ${res.rows_imported}`);
      assert(await tbl.count() === res.rows_imported, `Batch 3 scenario ${t} count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 3 (20/20 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 4: Fragmented SQL Dumps & Complex Queries (Scenarios 61 - 80)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 4: Fragmented SQL Dumps & Analytical Queries (Scenarios 61 - 80)...');
    for (let t = 61; t <= 80; t++) {
      const tblName = `node_c4_${t}.mgdb`;
      const lines = [
        `CREATE TABLE \`sql_test_${t}\` (`,
        '  `id` int(11) NOT NULL,',
        '  `region` varchar(32) DEFAULT NULL,',
        '  `sales` decimal(10,2) DEFAULT NULL',
        ');',
        `INSERT INTO \`sql_test_${t}\` VALUES`
      ];

      const regions = ['North', 'South', 'East', 'West'];
      const tuples = [];
      for (let r = 1; r <= 16; r++) {
        if (r % 4 === 0 && t % 2 === 0) {
          tuples.push(`(${r}, 'Incomplete`);
        } else if (r % 6 === 0) {
          tuples.push(`(${r}, 'O\\'Brian', ${r * 50.0})`);
        } else {
          tuples.push(`(${r}, '${regions[r % 4]}', ${r * 25.5})`);
        }
      }
      lines.push(tuples.join(',\n') + ';');

      const tbl = client.table(tblName);
      const res = await tbl.import(lines.join('\n'), 'sql');
      assert(res.rows_imported >= 8, `Batch 4 scenario ${t} imported fewer than 8 rows: ${res.rows_imported}`);

      // Analytical query with GROUP BY
      const queryRes = await client.query(
        `SELECT region, COUNT(*) AS count_total FROM ${tblName} GROUP BY region`
      );
      assert(queryRes.rows.length > 0, `Batch 4 scenario ${t} query failed`);

      passedTotal++;
    }
    console.log('    [+] Batch 4 (20/20 scenarios): PASS');

    // ------------------------------------------------------------------
    // Batch 5: End-to-End Export & Re-Import Roundtrips (Scenarios 81 - 100)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 5: End-to-End Export & Re-import Roundtrips (Scenarios 81 - 100)...');
    for (let t = 81; t <= 100; t++) {
      const tblName = `node_c5_${t}.mgdb`;
      const tbl = client.table(tblName);

      // Seed table
      await client.createTable(tblName, [
        { name: 'id', type: 'INT64' },
        { name: 'tag', type: 'STRING' },
        { name: 'rating', type: 'FLOAT64' }
      ]);

      const seed = [];
      for (let r = 1; r <= 20; r++) {
        seed.push({ id: r, tag: `tag_${r}_${t}`, rating: r * 4.5 });
      }
      await tbl.insert(seed);

      const fmt = ['csv', 'json', 'jsonl', 'sql'][t % 4];
      const expPath = path.join(TEST_DIR, `exp_roundtrip_${t}.${fmt}`);
      await tbl.exportToFile(expPath, fmt);

      assert(fs.existsSync(expPath), `Export file not created for scenario ${t}`);
      assert(fs.statSync(expPath).size > 0, `Export file is empty for scenario ${t}`);

      // Re-import into a new table
      const reimportTable = `reimport_${t}.mgdb`;
      const rTbl = client.table(reimportTable);
      await rTbl.importFile(expPath, fmt);

      const reimportedCount = await rTbl.count();
      assert(reimportedCount === 20, `Roundtrip ${t} (${fmt}) mismatch: ${reimportedCount} vs 20`);

      passedTotal++;
    }
    console.log('    [+] Batch 5 (20/20 scenarios): PASS');

    console.log('----------------------------------------------------------------');
    console.log(`   [SUCCESS] ALL ${passedTotal} / 100 EXTREME RESILIENCE SCENARIOS PASSED!`);
    console.log('================================================================');

  } catch (err) {
    console.error('[-] Test failed with error:', err);
    process.exitCode = 1;
  } finally {
    serverProc.kill();
  }
}

run();
