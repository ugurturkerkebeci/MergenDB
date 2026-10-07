/**
 * Automated test suite for MergenDB Node.js SDK
 * Spawns a background MergenDB server and verifies all client operations end-to-end.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { connect, MergenDB } = require('./index');

const TEST_PORT = 58976;
const TEST_DIR = path.join(__dirname, '..', '..', 'scratch', 'node_test_env');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function run() {
  console.log('================================================================');
  console.log('   [+] MERGENDB NODE.JS SDK END-TO-END VERIFICATION SUITE');
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

  serverProc.stderr.on('data', (d) => {
    const msg = d.toString();
    if (!msg.includes('HTTP/1.1')) {
      console.error('[Server Stderr]:', msg.trim());
    }
  });

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
  console.log('    [+] Server connection established: PASS');

  try {
    // 2. Status / Hardware diagnostics check
    const status = await client.status();
    console.log(`    [+] Server Diagnostics (/status): PASS (${status.server || 'MergenDB'} v${status.version || status.engine_version}, CPU: ${status.cpu || status.cpu_model || 'Detected'})`);

    // 3. Create table
    const tableName = 'test_sensors.mgdb';
    console.log(`[*] Creating table '${tableName}'...`);
    await client.createTable(tableName, [
      { name: 'id', type: 'INT64' },
      { name: 'sensor', type: 'STRING' },
      { name: 'temperature', type: 'FLOAT64' },
      { name: 'active', type: 'BOOL' }
    ]);
    console.log('    [+] Table Creation: PASS');

    // 4. Import CSV data
    const csvContent = "id,sensor,temperature,active\n1,TEMP-01,23.5,True\n2,TEMP-02,24.1,True\n3,TEMP-03,28.9,False\n4,TEMP-01,23.8,True\n";
    const sensorTable = client.table(tableName);
    console.log('[*] Importing CSV test data...');
    const importRes = await sensorTable.import(csvContent, 'csv');
    console.log(`    [+] CSV Import: PASS (${importRes.rows_imported} rows imported)`);

    // 5. Inspect Schema
    const schema = await sensorTable.schema();
    if (schema.columns.length !== 4) {
      throw new Error(`Expected 4 columns, got ${schema.columns.length}`);
    }
    console.log('    [+] Table Schema Inspection: PASS');

    // 6. Paginated Data Fetch
    const pageData = await sensorTable.data(1, 10);
    if (pageData.rows.length !== 4) {
      throw new Error(`Expected 4 rows in page, got ${pageData.rows.length}`);
    }
    console.log('    [+] Table Data Pagination: PASS');

    // 7. SQL Query Execution
    const sqlRes = await client.query(`SELECT sensor, COUNT(*), AVG(temperature) FROM test_sensors GROUP BY sensor`);
    if (!sqlRes.rows || sqlRes.rows.length === 0) {
      throw new Error('Expected aggregated rows from query');
    }
    console.log(`    [+] Analytical SQL & GROUP BY: PASS (${sqlRes.rows.length} group results in ${sqlRes.stats.execution_time_ms}ms)`);

    // 8. Tagged Template SQL
    const targetSensor = 'TEMP-01';
    const tagRes = await client.sql`SELECT id, sensor, temperature FROM test_sensors WHERE sensor = ${targetSensor}`;
    if (tagRes.row_count !== 2) {
      throw new Error(`Expected 2 rows for ${targetSensor}, got ${tagRes.row_count}`);
    }
    console.log('    [+] Tagged Template Literal (client.sql``): PASS');

    // 9. Fluent Document-Style API (find & findOne)
    const activeSensors = await sensorTable.find({ active: true });
    if (activeSensors.length !== 3) {
      throw new Error(`Expected 3 active sensors, got ${activeSensors.length}`);
    }
    const singleSensor = await sensorTable.findOne({ id: 2 });
    if (!singleSensor || singleSensor.sensor !== 'TEMP-02') {
      throw new Error('findOne did not return correct sensor');
    }
    console.log('    [+] Fluent Table find() & findOne(): PASS');

    // 10. Direct Object Insert
    await sensorTable.insert({ id: 5, sensor: 'TEMP-05', temperature: 29.5, active: true });
    const countAfterInsert = await sensorTable.count();
    if (countAfterInsert !== 5) {
      throw new Error(`Expected 5 rows after insert, got ${countAfterInsert}`);
    }
    console.log('    [+] Direct Object insert(): PASS');

    // 11. Full-text Substring Search
    const searchMatches = await sensorTable.search('05');
    if (searchMatches.length !== 1 || searchMatches[0].sensor !== 'TEMP-05') {
      throw new Error('search() did not find matching sensor');
    }
    console.log('    [+] Full-text search(): PASS');

    // 12. Update Records
    await sensorTable.update({ temperature: 31.0 }, "sensor = 'TEMP-05'");
    const updatedRecord = await sensorTable.findOne({ sensor: 'TEMP-05' });
    if (!updatedRecord || updatedRecord.temperature !== 31.0) {
      throw new Error('update() did not update record properly');
    }
    console.log('    [+] Table update(): PASS');

    // 13. Delete Records
    await sensorTable.delete("sensor = 'TEMP-05'");
    const countAfterDelete = await sensorTable.count();
    if (countAfterDelete !== 4) {
      throw new Error(`Expected 4 rows after delete, got ${countAfterDelete}`);
    }
    console.log('    [+] Table delete(): PASS');

    // 14. Schema Alterations (Add, Rename, Drop Column)
    await sensorTable.addColumn('battery_pct', 'FLOAT64', 100.0);
    const schemaWithBattery = await sensorTable.schema();
    if (!schemaWithBattery.columns.some(c => c.name === 'battery_pct')) {
      throw new Error('addColumn() failed');
    }
    console.log('    [+] Table addColumn(): PASS');

    await sensorTable.renameColumn('battery_pct', 'battery_level');
    const schemaRenamed = await sensorTable.schema();
    if (!schemaRenamed.columns.some(c => c.name === 'battery_level')) {
      throw new Error('renameColumn() failed');
    }
    console.log('    [+] Table renameColumn(): PASS');

    await sensorTable.dropColumn('battery_level');
    const schemaDropped = await sensorTable.schema();
    if (schemaDropped.columns.some(c => c.name === 'battery_level')) {
      throw new Error('dropColumn() failed');
    }
    console.log('    [+] Table dropColumn(): PASS');

    // 15. Live Hardware Benchmark via Node.js
    const benchData = await client.benchmark();
    if (!benchData || !benchData.benchmark || !benchData.benchmark.scan_rate) {
      throw new Error('benchmark() did not return hardware scan rate');
    }
    console.log(`    [+] Live Hardware Benchmark (client.benchmark()): PASS (Scan: ${benchData.benchmark.scan_rate.toLocaleString()} rows/s)`);

    // 16. Table Export (JSON & CSV)
    const exportedJson = await sensorTable.export('json');
    const parsedJson = typeof exportedJson === 'string' ? JSON.parse(exportedJson) : exportedJson;
    if (!Array.isArray(parsedJson) || parsedJson.length !== 4) {
      throw new Error('Exported JSON format invalid');
    }
    console.log('    [+] Table Data Export (JSON): PASS');

    // 16b. Streaming Export to File & Streaming Import from File
    const streamExportPath = path.join(TEST_DIR, 'streamed_sensors.csv');
    await sensorTable.exportToFile(streamExportPath, 'csv');
    if (!fs.existsSync(streamExportPath) || fs.statSync(streamExportPath).size === 0) {
      throw new Error('exportToFile() failed or produced empty file');
    }
    console.log('    [+] Zero-Memory Streaming exportToFile(): PASS');

    const streamImportTable = client.table('stream_imported.mgdb');
    await client.createTable('stream_imported.mgdb', [
      { name: 'id', type: 'INT64' },
      { name: 'sensor', type: 'STRING' },
      { name: 'temperature', type: 'FLOAT64' },
      { name: 'active', type: 'BOOL' }
    ]);
    const streamImportRes = await streamImportTable.importFile(streamExportPath, 'csv');
    if (!streamImportRes.success || streamImportRes.rows_imported !== 4) {
      throw new Error(`importFile() failed: ${JSON.stringify(streamImportRes)}`);
    }
    console.log('    [+] Zero-Memory Streaming importFile(): PASS');
    await streamImportTable.drop();

    // 17. Advanced Table & QueryBuilder Operations
    console.log('[*] Testing Advanced Table & QueryBuilder methods in Node.js...');
    const firstSensor = await sensorTable.first();
    const lastSensor = await sensorTable.last();
    const takeTwo = await sensorTable.take(2);
    const existsTemp1 = await sensorTable.exists({ sensor: 'TEMP-01' });
    const existsBogus = await sensorTable.exists({ sensor: 'NON_EXISTENT' });
    const distinctSensors = await sensorTable.distinct('sensor');
    const pluckedTemps = await sensorTable.pluck('temperature');
    const tempSum = await sensorTable.sum('temperature');
    const tempAvg = await sensorTable.avg('temperature');
    const tempMin = await sensorTable.min('temperature');
    const tempMax = await sensorTable.max('temperature');

    if (!firstSensor || !lastSensor || takeTwo.length !== 2 || !existsTemp1 || existsBogus) {
      throw new Error('first/last/take/exists assertions failed');
    }
    if (distinctSensors.length < 2 || pluckedTemps.length !== 4) {
      throw new Error('distinct/pluck assertions failed');
    }
    if (typeof tempSum !== 'number' || tempSum <= 0 || typeof tempAvg !== 'number') {
      throw new Error('numeric aggregations (sum/avg) failed');
    }

    // Upsert testing
    const upRes = await sensorTable.upsert([
      { id: 1, sensor: 'TEMP-01-CALIBRATED', temperature: 24.5, active: true },
      { id: 99, sensor: 'TEMP-99', temperature: 19.0, active: false }
    ], 'id');
    if (upRes.inserted !== 1 || upRes.updated !== 1) {
      throw new Error(`upsert() expected 1 inserted and 1 updated, got ${JSON.stringify(upRes)}`);
    }

    // QueryBuilder chaining
    const qbRes = await sensorTable.builder()
      .select('id', 'sensor', 'temperature')
      .where('temperature >= 20')
      .orderBy('temperature DESC')
      .limit(3)
      .toObjects();
    if (!Array.isArray(qbRes) || qbRes.length === 0) {
      throw new Error('TableQueryBuilder chaining failed');
    }
    console.log('    [+] Advanced APIs (first, last, take, exists, distinct, pluck, upsert, stats, QueryBuilder): PASS');

    // 18. Database & Sub-table Hierarchy Tests
    console.log('[*] Testing Database container and sub-table hierarchy in Node.js...');
    await client.createDatabase('okul_node');
    const dbsList = await client.listDatabases();
    if (!dbsList.some(d => d.name === 'okul_node')) {
      throw new Error('Database okul_node not found in listDatabases()');
    }
    const okulDb = client.database('okul_node');
    await okulDb.createTable('ogrenciler', [
      { name: 'id', type: 'INT64' },
      { name: 'name', type: 'STRING' }
    ]);
    const ogrencilerTable = okulDb.table('ogrenciler');
    await ogrencilerTable.insert([
      { id: 1, name: 'Ali' },
      { id: 2, name: 'Veli' }
    ]);
    // Create nested sub-table: okul_node.ogrenciler.a_sinifi
    await ogrencilerTable.createSubtable('a_sinifi', [
      { name: 'student_id', type: 'INT64' },
      { name: 'grade', type: 'STRING' }
    ]);
    const aSinifiTable = ogrencilerTable.subtable('a_sinifi');
    await aSinifiTable.insert([
      { student_id: 1, grade: 'A+' }
    ]);
    const aSinifiRows = await aSinifiTable.find();
    if (aSinifiRows.length !== 1 || aSinifiRows[0].grade !== 'A+') {
      throw new Error('Sub-table query failed');
    }
    console.log('    [+] Database & Nested Sub-table Hierarchy: PASS');
    await okulDb.drop();

    // 17. Truncate Table
    await sensorTable.truncate();
    const countAfterTruncate = await sensorTable.count();
    if (countAfterTruncate !== 0) {
      throw new Error(`Expected 0 rows after truncate, got ${countAfterTruncate}`);
    }
    console.log('    [+] Table Truncate Operation: PASS');

    // 18. Drop Table
    await sensorTable.drop();
    const tablesList = await client.listTables();
    const stillExists = tablesList.some(t => t.name === tableName);
    if (stillExists) {
      throw new Error('Table still exists after drop');
    }
    console.log('    [+] Table Drop Operation: PASS');

    console.log('----------------------------------------------------------------');
    console.log('   [SUCCESS] ALL NODE.JS SDK TESTS PASSED WITH 0 ERRORS!');
    console.log('================================================================');
  } finally {
    // Terminate server process cleanly
    serverProc.kill();
  }
}

run().catch((err) => {
  console.error('\n[-] Node.js SDK Test Failed:', err);
  process.exit(1);
});
