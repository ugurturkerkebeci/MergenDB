/**
 * MergenDB Node.js & JavaScript Quickstart Guide
 * ===============================================
 * Demonstrates connecting to MergenDB, creating/opening tables, inserting rows,
 * querying with SQL, document-style find/findOne, updating, and deleting records.
 *
 * Requirements:
 *   npm install mergendb
 *
 * Run directly:
 *   node examples/javascript_quickstart.js
 */

const path = require('path');
const fs = require('fs');

// In local projects, use: const { connect } = require('mergendb');
let mergendb;
try {
  mergendb = require('../sdks/nodejs');
} catch (e) {
  mergendb = require('mergendb');
}

async function main() {
  console.log("=== 1. Connecting to MergenDB ===");
  // Connects to local or remote MergenDB server.
  // Set autoStart: true to automatically spawn the background server if not already running!
  const client = mergendb.connect({
    host: '127.0.0.1',
    port: 8765,
    user: 'root',
    password: '',
    autoStart: true
  });

  const status = await client.status();
  console.log(`Connected successfully to MergenDB server (Platform: ${status.platform}, Threads: ${status.cpu_threads})`);

  // Target table
  const tableName = 'app_users.mgdb';
  const table = client.table(tableName);

  console.log("\n=== 2. Inserting Records (CRUD: Create) ===");
  // Automatically infers columnar schema and compresses on the fly
  await table.insert([
    { id: 1, name: "Alice", role: "admin", department: "Engineering", salary: 95000, is_active: true },
    { id: 2, name: "Bob", role: "user", department: "Design", salary: 78000, is_active: true },
    { id: 3, name: "Charlie", role: "user", department: "Engineering", salary: 88000, is_active: false },
    { id: 4, name: "Diana", role: "manager", department: "Product", salary: 110000, is_active: true },
    { id: 5, name: "Emre", role: "user", department: "Engineering", salary: 92000, is_active: true }
  ]);
  console.log(`Inserted rows into '${tableName}'`);

  console.log("\n=== 3. Querying with Standard SQL (CRUD: Read) ===");
  // Execute full analytical SQL queries
  const sqlResult = await client.query(
    `SELECT name, department, salary FROM ${tableName} WHERE salary >= 85000 ORDER BY salary DESC;`
  );
  console.log(`Query completed in ${sqlResult.stats.execution_time_ms.toFixed(2)} ms. Returned ${sqlResult.rows.length} rows:`);
  console.table(sqlResult.rows);

  // Safe tagged template literal with automatic escaping
  const targetDepartment = "Engineering";
  const safeResult = await client.sql`SELECT name, salary FROM ${tableName} WHERE department = ${targetDepartment} AND is_active = true`;
  console.log(`Active ${targetDepartment} team members:`, safeResult.rows);

  console.log("\n=== 4. Document-Style find() and findOne() ===");
  // Quick document lookup without writing SQL
  const user = await table.findOne({ name: "Alice" });
  console.log("Found Alice:", user);

  // Find all active engineers
  const engineers = await table.find({ department: "Engineering", is_active: true });
  console.log(`Found ${engineers.length} active engineers`);

  console.log("\n=== 5. Updating Records (CRUD: Update) ===");
  // Update via fluent API
  const updateRes = await table.update(
    { salary: 105000, role: "lead_engineer" },
    "name = 'Alice'"
  );
  console.log(`Updated records for Alice`);

  // Or update via SQL statement
  await client.query(`UPDATE ${tableName} SET salary = 99000 WHERE department = 'Engineering' AND name != 'Alice';`);
  const updatedAlice = await table.findOne({ name: "Alice" });
  console.log("Alice's updated record:", updatedAlice);

  console.log("\n=== 6. Deleting Records (CRUD: Delete) ===");
  // Delete matching rows
  const deleteRes = await table.delete("is_active = false");
  console.log(`Deleted inactive user(s)`);

  console.log("\n=== 7. Analytical Aggregations (GROUP BY, COUNT, AVG) ===");
  const aggResult = await client.query(
    `SELECT department, COUNT(*), AVG(salary) FROM ${tableName} GROUP BY department;`
  );
  console.table(aggResult.rows);

  // Cleanup demo table
  try {
    await table.drop();
    console.log(`Cleaned up '${tableName}'.`);
  } catch (err) {}

  console.log("\nDone! JavaScript quickstart completed successfully.");
}

main().catch(console.error);
