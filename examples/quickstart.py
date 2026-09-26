import os
import sys

# Ensure mergendb package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import mergendb

def main():
    db_file = "quickstart_users.mgdb"

    # 1. Define schema
    schema = mergendb.Schema([
        mergendb.ColumnDef("id", mergendb.DataType.INT64),
        mergendb.ColumnDef("name", mergendb.DataType.STRING),
        mergendb.ColumnDef("age", mergendb.DataType.INT32),
        mergendb.ColumnDef("country", mergendb.DataType.STRING),
        mergendb.ColumnDef("salary", mergendb.DataType.FLOAT64),
        mergendb.ColumnDef("is_active", mergendb.DataType.BOOL)
    ])

    print("--- 1. Creating Table ---")
    table = mergendb.create_table(db_file, schema, block_size=100)

    # 2. Insert records
    print("--- 2. Inserting Data ---")
    data = [
        {"id": 1, "name": "Alice", "age": 28, "country": "TR", "salary": 75000.0, "is_active": True},
        {"id": 2, "name": "Bob", "age": 34, "country": "DE", "salary": 82000.0, "is_active": True},
        {"id": 3, "name": "Charlie", "age": 22, "country": "TR", "salary": 52000.0, "is_active": False},
        {"id": 4, "name": "Diana", "age": 41, "country": "US", "salary": 115000.0, "is_active": True},
        {"id": 5, "name": "Emre", "age": 29, "country": "TR", "salary": 91000.0, "is_active": True},
        {"id": 6, "name": "Fatma", "age": 36, "country": "TR", "salary": 96000.0, "is_active": True},
    ]
    table.insert_many(data)
    print(f"Table created with {table.row_count} rows.")

    # 3. Query using MergenQL Pipeline Syntax
    print("\n--- 3. Running MergenQL Pipeline Query ---")
    query_str = f"""
    FROM "{db_file}"
    | WHERE country == "TR" AND is_active == true
    | COMPUTE bonus = salary * 0.15
    | SELECT name, age, salary, bonus
    | SORT salary DESC
    """
    print("Executing Query:\n", query_str.strip())
    print("\nResult:")
    result = mergendb.query(query_str)
    print(result.display())

    # 4. Aggregation Query
    print("\n--- 4. Running Aggregation Query ---")
    agg_query = f"""
    FROM "{db_file}"
    | AGGREGATE count(*) AS user_count, avg(salary) AS avg_salary, max(age) AS max_age BY country
    | SORT user_count DESC
    """
    print(mergendb.query(agg_query).display())

    # Cleanup
    if os.path.exists(db_file):
        os.remove(db_file)

if __name__ == "__main__":
    main()
