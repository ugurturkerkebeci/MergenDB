"""
MergenDB Python Quickstart Guide
================================
Demonstrates how to connect to a database, create tables, insert rows,
query with SQL or Pythonic find(), update records, and delete records.

Run directly:
    python examples/python_quickstart.py
"""

import os
import mergendb

def main():
    db_file = "my_database.mgdb"

    # Cleanup any previous run
    if os.path.exists(db_file):
        os.remove(db_file)

    print("=== 1. Connecting / Opening Database ===")
    # Connect to an embedded table file (auto-creates if it doesn't exist)
    table = mergendb.connect(db_file)
    print(f"Connected to: {table.filepath}")

    print("\n=== 2. Inserting Records (CRUD: Create) ===")
    # Insert multiple documents directly. Schema and types are automatically inferred!
    table.insert([
        {"id": 1, "username": "alice", "email": "alice@mergendb.io", "role": "admin", "age": 28, "balance": 1500.50},
        {"id": 2, "username": "bob", "email": "bob@mergendb.io", "role": "user", "age": 34, "balance": 820.00},
        {"id": 3, "username": "charlie", "email": "charlie@mergendb.io", "role": "user", "age": 22, "balance": 450.25},
        {"id": 4, "username": "diana", "email": "diana@mergendb.io", "role": "moderator", "age": 31, "balance": 2100.00},
        {"id": 5, "username": "emre", "email": "emre@mergendb.io", "role": "user", "age": 29, "balance": 990.00},
    ])
    print(f"Total rows inserted: {table.row_count}")
    print(f"Columns: {table.columns}")

    print("\n=== 3. Querying with Standard SQL (CRUD: Read) ===")
    # Execute full SQL query with WHERE, ORDER BY, and LIMIT
    result = table.sql("SELECT username, role, balance FROM my_database WHERE balance > 800 ORDER BY balance DESC;")
    result.show()

    # Convert query results directly to a list of Python dictionaries
    records = result.to_dicts()
    print("Fetched records as dicts:", records)

    print("\n=== 4. Querying with Pythonic find() & find_one() ===")
    # Quick key-value lookup without writing SQL strings
    user = table.find_one(username="alice")
    print(f"Found user: {user['username']} | Role: {user['role']} | Balance: ${user['balance']}")

    # Find multiple matching rows
    standard_users = table.find(role="user")
    print(f"Found {len(standard_users)} users with role='user'")

    print("\n=== 5. Updating Records (CRUD: Update) ===")
    # Update via Pythonic dictionary API
    updated_count = table.update({"balance": 2500.00, "role": "senior_admin"}, where="username = 'alice'")
    print(f"Updated {updated_count} row(s) using table.update()")

    # Or update via standard SQL statement
    mergendb.sql(f"UPDATE \"{db_file}\" SET balance = balance + 100 WHERE role = 'user';")

    # Verify updated values
    updated_alice = table.find_one(username="alice")
    print(f"Alice after update: Role={updated_alice['role']}, Balance=${updated_alice['balance']}")

    print("\n=== 6. Deleting Records (CRUD: Delete) ===")
    # Delete matching rows
    deleted_count = table.delete(where="age < 25")
    print(f"Deleted {deleted_count} user(s) under 25 years old")
    print(f"Remaining total rows: {table.row_count}")

    # Or delete via standard SQL
    mergendb.sql(f"DELETE FROM \"{db_file}\" WHERE username = 'bob';")
    print(f"Remaining after SQL delete: {table.row_count}")

    print("\n=== 7. High-Performance Columnar Aggregations ===")
    # Fast analytical aggregation (COUNT, AVG, SUM, MIN, MAX)
    summary = table.sql("SELECT role, COUNT(*), AVG(balance) FROM my_database GROUP BY role;")
    summary.show()

    # Clean up
    if os.path.exists(db_file):
        os.remove(db_file)
    print("Done! Demo completed successfully.")

if __name__ == "__main__":
    main()
