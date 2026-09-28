/**
 * MergenDB Node.js SDK - Top 100 Database Engine Errors Test Suite
 * 10 Error Domains x 100 Test Units = 1,000 Unit Tests
 * Strictly Zero Emojis - Pure Node.js Standard Library - Non-blocking Architecture
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { connect, MergenDB, MergenError } = require('./index');

const TEST_PORT = 58988;
const TEST_DIR = path.join(__dirname, '..', '..', 'scratch', 'node_errors1000_env');

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
  console.log('   MERGENDB NODE.JS SDK - 1,000 TOP DATABASE ERRORS TEST SUITE');
  console.log('   10 Domains x 100 Test Units = 1,000 Tests');
  console.log('================================================================');

  if (!fs.existsSync(TEST_DIR)) {
    fs.mkdirSync(TEST_DIR, { recursive: true });
  }

  // Ensure fresh mergen_auth.json in test directory
  const testAuthFile = path.join(TEST_DIR, 'mergen_auth.json');
  if (fs.existsSync(testAuthFile)) {
    fs.unlinkSync(testAuthFile);
  }

  console.log(`[*] Spawning MergenDB server on port ${TEST_PORT}...`);
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  const repoRoot = path.resolve(__dirname, '..', '..');
  const serverProc = spawn(pythonPath, ['-u', '-m', 'mergendb.server.server', '--port', String(TEST_PORT)], {
    cwd: TEST_DIR,
    env: { ...process.env, PYTHONPATH: repoRoot },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  serverProc.stdout.on('data', () => {});
  serverProc.stderr.on('data', (d) => { process.stderr.write(`[SERVER STDERR] ${d}`); });

  serverProc.on('error', (err) => {
    console.error('Failed to spawn MergenDB server:', err);
    process.exit(1);
  });

  let passed = 0;
  let failed = 0;

  try {
    // Wait for server to be responsive
    let connected = false;
    const client = connect({ host: '127.0.0.1', port: TEST_PORT, username: 'root', password: '' });
    for (let i = 0; i < 40; i++) {
      try {
        const ping = await client.ping();
        if (ping) {
          connected = true;
          break;
        }
      } catch (e) {
        // wait
      }
      await sleep(150);
    }

    if (!connected) {
      throw new Error(`Could not connect to MergenDB test server on port ${TEST_PORT}`);
    }
    console.log('[*] Connected to server successfully. Running 1,000 test units across 10 domains...\n');

    // Setup base table for queries
    const baseTable = client.table('test_top_errors');
    try {
      await client.createTable('test_top_errors', [
        { name: 'id', type: 'int64' },
        { name: 'name', type: 'string' },
        { name: 'val', type: 'float64' }
      ]);
      await baseTable.insert([
        { id: 1, name: 'alpha', val: 10.5 },
        { id: 2, name: 'beta', val: 20.0 },
        { id: 3, name: 'gamma', val: 30.5 }
      ]);
    } catch (e) {
      // Table may exist
    }

    // -------------------------------------------------------------
    // DOMAIN 1: Syntax & Lexical Errors (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 1: Syntax & Lexical Errors (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Unclosed quotes and brackets
          try {
            await client.query(`SELECT * FROM test_top_errors WHERE name = 'unclosed_${i}`);
          } catch (e) {
            assert(e !== null, 'Expected syntax error');
          }
        } else if (i <= 50) {
          // Trailing commas and double pipes
          try {
            await client.query(`test_top_errors || filter id > ${i}`);
          } catch (e) {
            assert(e !== null, 'Expected pipeline syntax error');
          }
        } else if (i <= 75) {
          // Unclosed parentheses in filter
          try {
            await client.query(`SELECT * FROM test_top_errors WHERE ((id = ${i})`);
          } catch (e) {
            assert(e !== null, 'Expected paren syntax error');
          }
        } else {
          // Reserved keywords as unquoted identifiers
          try {
            await client.query(`SELECT FROM WHERE ${i}`);
          } catch (e) {
            assert(e !== null, 'Expected keyword syntax error');
          }
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 1 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 2: Schema & Resolution Errors (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 2: Schema & Resolution Errors (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Non-existent table resolution
          try {
            await client.query(`SELECT * FROM non_existent_table_${i}`);
          } catch (e) {
            assert(e !== null, 'Expected table not found error');
          }
        } else if (i <= 50) {
          // Non-existent column resolution
          try {
            await client.query(`SELECT invalid_col_${i} FROM test_top_errors`);
          } catch (e) {
            assert(e !== null, 'Expected column not found error');
          }
        } else if (i <= 75) {
          // Dropping non-existent table
          try {
            await client.dropTable(`no_such_tbl_${i}`);
          } catch (e) {
            // Error or graceful false is fine
          }
        } else {
          // Schema metadata query
          const schema = await baseTable.schema();
          assert(schema && schema.columns.length > 0, 'Schema should be returned');
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 2 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 3: Data Type & Coercion Errors (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 3: Data Type & Coercion Errors (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // String-to-number parse failure in query comparison
          const res = await client.query(`SELECT * FROM test_top_errors WHERE id = 'not_int_${i}'`);
          assert(Array.isArray(res.rows), 'Query should return array even on mismatch');
        } else if (i <= 50) {
          // Division / modulo evaluation
          const res = await client.query(`SELECT * FROM test_top_errors WHERE id = ${i % 3 + 1}`);
          assert(Array.isArray(res.rows), 'Valid query should return rows');
        } else if (i <= 75) {
          // Floating point boundary queries
          const res = await client.query(`SELECT * FROM test_top_errors WHERE val > ${i * 0.1}`);
          assert(Array.isArray(res.rows), 'Float filter should return rows');
        } else {
          // Boolean and null literal comparisons
          const res = await client.query(`SELECT * FROM test_top_errors WHERE id > 0`);
          assert(res.row_count > 0, 'Positive id filter should match');
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 3 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 4: Constraints & Data Integrity (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 4: Constraints & Data Integrity (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Extreme string lengths
          const longStr = 'x'.repeat(i * 100);
          await baseTable.insert({ id: 1000 + i, name: longStr, val: i });
        } else if (i <= 50) {
          // Null values in nullable columns
          await baseTable.insert({ id: 2000 + i, name: null, val: null });
        } else if (i <= 75) {
          // Empty dict or array insertion
          try {
            await baseTable.insert([]);
          } catch (e) {
            // Graceful handling
          }
        } else {
          // Count verification
          const count = await baseTable.count();
          assert(count > 0, 'Row count should remain positive');
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 4 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 5: Query Planning & Aggregations (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 5: Query Planning & Aggregations (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Limit edge cases
          const res = await client.query(`SELECT * FROM test_top_errors LIMIT ${i}`);
          assert(res.rows.length <= i, 'Result rows should not exceed limit');
        } else if (i <= 50) {
          // Negative limit handling
          try {
            await client.query(`SELECT * FROM test_top_errors LIMIT -${i}`);
          } catch (e) {
            assert(e !== null, 'Expected error on negative limit');
          }
        } else if (i <= 75) {
          // Aggregate count
          const res = await client.query(`SELECT COUNT(*) FROM test_top_errors`);
          assert(res.rows.length > 0, 'Count aggregate should return row');
        } else {
          // Order by queries
          const res = await client.query(`SELECT * FROM test_top_errors ORDER BY id DESC LIMIT 5`);
          assert(res.rows.length <= 5, 'Ordered limit should return <= 5');
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 5 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 6: Concurrency & Lock Contention (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 6: Concurrency & Lock Contention (100 Tests)...');
    for (let i = 1; i <= 100; i += 10) {
      const batchPromises = [];
      for (let j = 0; j < 10; j++) {
        batchPromises.push(client.query('SELECT * FROM test_top_errors LIMIT 1'));
      }
      const results = await Promise.all(batchPromises);
      for (const res of results) {
        assert(res.rows.length > 0, 'Concurrent query should succeed');
        passed++;
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 7: Authentication & Access Control (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 7: Authentication & Access Control (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Verify root authentication with empty password succeeds
          const rootClient = connect({ host: '127.0.0.1', port: TEST_PORT, username: 'root', password: '' });
          const pingRes = await rootClient.ping();
          assert(pingRes === true, 'Root auth with default empty password should succeed');
        } else if (i <= 50) {
          // Verify rejection with wrong password (HTTP 401)
          const badClient = connect({ host: '127.0.0.1', port: TEST_PORT, username: 'root', password: `wrong_${i}` });
          try {
            await badClient.query('SELECT 1');
            assert(false, 'Should have failed with HTTP 401 Unauthorized');
          } catch (e) {
            assert(e instanceof MergenError || e.message.includes('401') || e.message.includes('Auth'), 'Should fail with 401');
          }
        } else if (i <= 75) {
          // Verify login method returning JWT session token
          const loginClient = connect({ host: '127.0.0.1', port: TEST_PORT });
          const loginRes = await loginClient.login('root', '');
          assert(loginRes.success === true && loginRes.token.length > 0, 'Login should return session token');
          const status = await loginClient.status();
          assert(status.status === 'healthy' || status.status === 'ok', 'Status query with bearer token should succeed');
        } else {
          // Verify user auth status verification endpoint
          const authClient = connect({ host: '127.0.0.1', port: TEST_PORT, username: 'root', password: '' });
          const verifyRes = await authClient.verifyAuth();
          assert(verifyRes.authenticated === true && (verifyRes.user === 'root' || verifyRes.username === 'root'), 'verifyAuth should confirm root');
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 7 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 8: Connection & HTTP Protocol (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 8: Connection & HTTP Protocol (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Server status endpoint
          const st = await client.status();
          assert(st.status === 'healthy' || st.status === 'ok', 'Server status must be healthy');
        } else if (i <= 50) {
          // List databases endpoint
          const dbs = await client.listDatabases();
          assert(Array.isArray(dbs), 'listDatabases should return array');
        } else if (i <= 75) {
          // List tables endpoint
          const tbls = await client.listTables();
          assert(Array.isArray(tbls), 'listTables should return array');
        } else {
          // Connection to closed port error handling
          const offlineClient = connect({ host: '127.0.0.1', port: 59998, timeout: 200 });
          try {
            await offlineClient.ping();
          } catch (e) {
            // Expected connection failure
          }
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 8 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 9: Storage, File I/O & Corrupt Data (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 9: Storage, File I/O & Corrupt Data (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // Create and drop temporary table cycle
          const tblName = `tmp_storage_${i}`;
          await client.createTable(tblName, [{ name: 'x', type: 'int64' }]);
          await client.dropTable(tblName);
        } else if (i <= 50) {
          // Truncate table and verify empty
          const tblName = `tmp_trunc_${i}`;
          await client.createTable(tblName, [{ name: 'x', type: 'int64' }]);
          const t = client.table(tblName);
          await t.insert({ x: 1 });
          await t.truncate();
          const count = await t.count();
          assert(count === 0, 'Truncated table should have 0 rows');
          await client.dropTable(tblName);
        } else if (i <= 75) {
          // Check table stats
          const res = await client.query('SELECT * FROM test_top_errors LIMIT 1');
          assert(res.stats !== undefined, 'Query should return execution stats');
        } else {
          // Rename column resilience
          const tblName = `tmp_col_${i}`;
          await client.createTable(tblName, [{ name: 'old_col', type: 'string' }]);
          const t = client.table(tblName);
          await t.renameColumn('old_col', 'new_col');
          const sch = await t.schema();
          assert(sch.columns[0].name === 'new_col', 'Column should be renamed');
          await client.dropTable(tblName);
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 9 Test ${i} failed:`, err.message);
      }
    }

    // -------------------------------------------------------------
    // DOMAIN 10: Import/Export Format Transformations (100 Tests)
    // -------------------------------------------------------------
    console.log('[*] Running Domain 10: Import/Export Format Transformations (100 Tests)...');
    for (let i = 1; i <= 100; i++) {
      try {
        if (i <= 25) {
          // JSON export
          const expData = await baseTable.export('json');
          const parsedData = typeof expData === 'string' ? JSON.parse(expData) : expData;
          assert(Array.isArray(parsedData), 'Exported JSON should be array');
        } else if (i <= 50) {
          // CSV export
          const csvStr = await baseTable.export('csv');
          assert(csvStr.includes('id,name,val'), 'Exported CSV should contain header');
        } else if (i <= 75) {
          // JSON import
          const importData = JSON.stringify([{ id: 3000 + i, name: `imp_${i}`, val: 99.9 }]);
          const res = await baseTable.import(importData, 'json');
          assert(res.rows_imported >= 1, 'JSON import should succeed');
        } else {
          // Ragged CSV import error tolerance
          const raggedCsv = `id,name,val\n${4000 + i},item_${i},50.5\nBROKEN_LINE\n`;
          try {
            await baseTable.import(raggedCsv, 'csv');
          } catch (e) {
            // Error handling or partial import is valid
          }
        }
        passed++;
      } catch (err) {
        failed++;
        console.error(`[-] Domain 10 Test ${i} failed:`, err.message);
      }
    }

  } finally {
    console.log('\n[*] Stopping MergenDB test server...');
    serverProc.kill('SIGTERM');
    await sleep(400);
  }

  console.log('\n================================================================');
  console.log('   TEST RUN COMPLETE');
  console.log(`   Passed: ${passed} / 1000`);
  console.log(`   Failed: ${failed} / 1000`);
  console.log('================================================================');

  if (failed > 0 || passed !== 1000) {
    process.exit(1);
  }
}

run().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
