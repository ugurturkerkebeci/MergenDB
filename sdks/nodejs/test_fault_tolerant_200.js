/**
 * Comprehensive 200-Combination Fault Tolerance Verification for MergenDB Node.js SDK.
 * Tests broken rows, dirty types, null bytes, ragged schemas, multi-encodings,
 * and malformed documents in CSV, JSONL, JSON, and SQL dumps.
 * Strictly zero emojis. Pure Node.js standard library.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { connect } = require('./index');

const TEST_PORT = 58988;
const TEST_DIR = path.join(__dirname, '..', '..', 'scratch', 'node_fault_test_env');

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
  console.log('   MERGENDB NODE.JS SDK - 200 COMBINATIONS FAULT TOLERANCE TEST');
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
      // quiet debug output
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
    // Batch 1: Ragged & Malformed CSV Combinations (1 - 40)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 1: Malformed and Ragged CSVs (Combinations 1 - 40)...');
    for (let i = 0; i < 40; i++) {
      const tblName = `ragged_${i}.mgdb`;
      const lines = ['id,name,value,active'];
      for (let r = 1; r <= 20; r++) {
        if (r % 3 === 0) {
          // Ragged: too few or too many columns
          if (i % 2 === 0) {
            lines.push(`${r},Partial`);
          } else {
            lines.push(`${r},Extra,100,true,surplus_col,extra_col`);
          }
        } else if (r % 5 === 0) {
          // Embedded null bytes
          lines.push(`${r},User_\x00${r},${r * 10},true`);
        } else if (r % 7 === 0) {
          // Extra blanks or strange separators
          lines.push(`  ${r}  ,  "Padded Name"  ,  ${r * 2.5}  ,  false  `);
        } else {
          lines.push(`${r},Name_${r},${r * 100},true`);
        }
      }
      const csvData = lines.join('\n');
      const tbl = client.table(tblName);
      const res = await tbl.import(csvData, 'csv');
      assert(res.rows_imported >= 15, `Batch 1 comb #${i + 1} imported fewer than 15 rows: ${res.rows_imported}`);
      const rowCount = await tbl.count();
      assert(rowCount === res.rows_imported, `Batch 1 comb #${i + 1} row count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 1 (40/40 combinations): PASS');

    // ------------------------------------------------------------------
    // Batch 2: Multi-Encoding and BOM CSV Combinations (41 - 80)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 2: Multi-Encoding and International Charsets (Combinations 41 - 80)...');
    for (let i = 0; i < 40; i++) {
      const tblName = `enc_${i}.mgdb`;
      const hasBOM = (i % 2 === 0);
      let content = hasBOM ? '\uFEFF' : '';
      content += 'id,user,city,score\n';
      const turkishCities = ['İstanbul', 'Ankara', 'İzmir', 'Eskişehir', 'Diyarbakır', 'Şanlıurfa', 'Gaziantep', 'Ağrı'];
      for (let r = 1; r <= 15; r++) {
        const city = turkishCities[(r + i) % turkishCities.length];
        content += `${r},Kullanıcı_${r},${city},${r * 10.5}\n`;
      }
      const tbl = client.table(tblName);
      const res = await tbl.import(content, 'csv');
      assert(res.rows_imported === 15, `Batch 2 comb #${i + 41} failed import count: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === 15, `Batch 2 comb #${i + 41} count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 2 (40/40 combinations): PASS');

    // ------------------------------------------------------------------
    // Batch 3: Dirty Type Tokens & Coercions (81 - 120)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 3: Dirty Null Tokens and Type Coercions (Combinations 81 - 120)...');
    const dirtyTokens = ['', 'NULL', 'null', 'None', 'none', 'N/A', 'NaN', 'nil', '-', '\\N'];
    for (let i = 0; i < 40; i++) {
      const tblName = `types_${i}.mgdb`;
      const lines = ['id,age,balance,verified,note'];
      for (let r = 1; r <= 20; r++) {
        const dToken = dirtyTokens[(r + i) % dirtyTokens.length];
        const ageVal = (r % 3 === 0) ? dToken : String(r * 3);
        const balVal = (r % 4 === 0) ? dToken : (r * 12.5).toFixed(2);
        const verVal = (r % 2 === 0) ? 'true' : (r % 5 === 0 ? dToken : 'false');
        lines.push(`${r},${ageVal},${balVal},${verVal},User_${r}`);
      }
      const tbl = client.table(tblName);
      const res = await tbl.import(lines.join('\n'), 'csv');
      assert(res.rows_imported === 20, `Batch 3 comb #${i + 81} lost rows: ${res.rows_imported}`);
      const count = await tbl.count();
      assert(count === 20, `Batch 3 comb #${i + 81} count mismatch: ${count}`);
      passedTotal++;
    }
    console.log('    [+] Batch 3 (40/40 combinations): PASS');

    // ------------------------------------------------------------------
    // Batch 4: Corrupted JSON / JSONL Records (121 - 160)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 4: Corrupted JSON and JSONL Records (Combinations 121 - 160)...');
    for (let i = 0; i < 40; i++) {
      const tblName = `json_broken_${i}.mgdb`;
      const isJsonl = (i % 2 === 0);
      let content = '';
      if (isJsonl) {
        const records = [];
        for (let r = 1; r <= 20; r++) {
          if (r % 4 === 0) {
            // Malformed JSON syntax
            records.push(`{"id": ${r}, "name": "Broken_${r}`);
          } else if (r % 7 === 0) {
            // Null bytes
            records.push(`{"id": ${r}, "name": "Null_\x00_${r}", "val": ${r * 5}}`);
          } else {
            records.push(JSON.stringify({ id: r, name: `Valid_${r}`, val: r * 10 }));
          }
        }
        content = records.join('\n');
      } else {
        // Standard JSON array with some invalid / dirty elements
        const arr = [];
        for (let r = 1; r <= 20; r++) {
          arr.push({
            id: r,
            name: (r % 5 === 0) ? null : `Entity_${r}`,
            score: (r % 3 === 0) ? 'N/A' : (r * 1.5),
            active: (r % 2 === 0)
          });
        }
        content = JSON.stringify(arr);
      }

      const tbl = client.table(tblName);
      const format = isJsonl ? 'jsonl' : 'json';
      const res = await tbl.import(content, format);
      const minExpected = isJsonl ? 14 : 20;
      assert(res.rows_imported >= minExpected, `Batch 4 comb #${i + 121} imported ${res.rows_imported}, expected >= ${minExpected}`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `Batch 4 comb #${i + 121} count mismatch`);
      passedTotal++;
    }
    console.log('    [+] Batch 4 (40/40 combinations): PASS');

    // ------------------------------------------------------------------
    // Batch 5: Fragmented and Corrupted SQL Dumps (161 - 200)
    // ------------------------------------------------------------------
    console.log('[*] Testing Batch 5: Fragmented SQL Dumps (Combinations 161 - 200)...');
    for (let i = 0; i < 40; i++) {
      const tblName = `sql_broken_${i}.mgdb`;
      const lines = [
        'CREATE TABLE `node_clients` (',
        '  `id` int(11) NOT NULL,',
        '  `name` varchar(100) DEFAULT NULL,',
        '  `balance` decimal(10,2) DEFAULT NULL',
        ');',
        'INSERT INTO `node_clients` VALUES'
      ];
      const tuples = [];
      for (let r = 1; r <= 15; r++) {
        if (r % 4 === 0) {
          // Broken syntax tuple
          tuples.push(`(${r}, 'Incomplete`);
        } else if (r % 6 === 0) {
          // Escaped quote
          tuples.push(`(${r}, 'D\\'Angelo', ${r * 80.0})`);
        } else {
          tuples.push(`(${r}, 'Client_${r}', ${r * 45.5})`);
        }
      }
      lines.push(tuples.join(',\n') + ';');
      const content = lines.join('\n');

      const tbl = client.table(tblName);
      const res = await tbl.import(content, 'sql');
      assert(res.rows_imported >= 7, `Batch 5 comb #${i + 161} imported ${res.rows_imported}, expected >= 7`);
      const count = await tbl.count();
      assert(count === res.rows_imported, `Batch 5 comb #${i + 161} count mismatch: ${count} vs ${res.rows_imported}`);
      passedTotal++;
    }
    console.log('    [+] Batch 5 (40/40 combinations): PASS');

    console.log('----------------------------------------------------------------');
    console.log(`   [SUCCESS] ALL ${passedTotal} / 200 FAULT TOLERANCE COMBINATIONS PASSED!`);
    console.log('================================================================');

  } catch (err) {
    console.error('[-] Test failed with error:', err);
    process.exitCode = 1;
  } finally {
    serverProc.kill();
  }
}

run();
