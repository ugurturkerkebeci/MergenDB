import unittest
import os
import shutil
import tempfile
import sqlite3
import mergendb
from mergendb.io.importer import DataImporter

class TestImporter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.sqlite_file = os.path.join(self.test_dir, "legacy_sales.db").replace("\\", "/")
        self.sql_dump_file = os.path.join(self.test_dir, "dump.sql").replace("\\", "/")
        self.csv_file = os.path.join(self.test_dir, "customers.csv").replace("\\", "/")
        self.mgdb_sqlite = os.path.join(self.test_dir, "from_sqlite.mgdb").replace("\\", "/")
        self.mgdb_dump = os.path.join(self.test_dir, "from_dump.mgdb").replace("\\", "/")
        self.mgdb_csv = os.path.join(self.test_dir, "from_csv.mgdb").replace("\\", "/")

        # 1. Setup sample SQLite DB
        conn = sqlite3.connect(self.sqlite_file)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_name TEXT,
                amount REAL,
                status TEXT,
                is_shipped BOOLEAN
            );
        """)
        orders_data = [
            (i, f"Customer_{i % 20}", 50.0 + (i * 2.5), "DELIVERED" if i % 2 == 0 else "PENDING", i % 2 == 0)
            for i in range(500)
        ]
        cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders_data)
        conn.commit()
        conn.close()

        # 2. Setup sample SQL Dump
        with open(self.sql_dump_file, "w", encoding="utf-8") as f:
            f.write("""
            CREATE TABLE products (
                id INT,
                title VARCHAR(100),
                price DECIMAL(10,2),
                stock INT
            );
            INSERT INTO products VALUES (1, 'Laptop', 1200.50, 15);
            INSERT INTO products VALUES (2, 'Mouse', 25.00, 150);
            INSERT INTO products VALUES (3, 'Keyboard', 75.00, 80);
            """)

        # 3. Setup sample CSV
        with open(self.csv_file, "w", encoding="utf-8") as f:
            f.write("user_id,full_name,score,is_verified\n")
            for i in range(100):
                f.write(f"{i},User_{i},{85.5 + (i * 0.1)},true\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import_sqlite(self):
        tbl = mergendb.from_sqlite(self.sqlite_file, self.mgdb_sqlite, table_name="orders")
        self.assertEqual(tbl.row_count, 500)

        # Query the imported table
        res = mergendb.query(f"""
        FROM "{self.mgdb_sqlite}"
        | WHERE status == "DELIVERED"
        | AGGREGATE count(*) AS total_delivered, sum(amount) AS total_revenue
        """)
        self.assertEqual(len(res), 1)
        self.assertEqual(res.rows[0][0], 250)
        self.assertGreater(res.rows[0][1], 0)

    def test_import_sql_dump(self):
        tbl = mergendb.from_sql_dump(self.sql_dump_file, self.mgdb_dump)
        self.assertEqual(tbl.row_count, 3)

        res = mergendb.query(f"""
        FROM "{self.mgdb_dump}"
        | WHERE price > 50.0
        | SELECT title, price
        | SORT price DESC
        """)
        self.assertEqual(len(res), 2)
        self.assertEqual(res.rows[0][0], "Laptop")

    def test_import_csv(self):
        tbl = mergendb.from_csv(self.csv_file, self.mgdb_csv)
        self.assertEqual(tbl.row_count, 100)

        res = mergendb.query(f"""
        FROM "{self.mgdb_csv}"
        | WHERE score > 90.0
        | SELECT full_name, score
        """)
        self.assertGreater(len(res), 0)

    def test_import_sql_dump_complex_strings(self):
        complex_sql = os.path.join(self.test_dir, "complex.sql")
        complex_mgdb = os.path.join(self.test_dir, "complex.mgdb")
        with open(complex_sql, "w", encoding="utf-8") as f:
            f.write("""
            CREATE TABLE users (id INT, name VARCHAR(100), note VARCHAR(200));
            INSERT INTO users VALUES (1, 'Ahmet', 'Kadıköy (Merkez)');
            INSERT INTO users VALUES (2, 'O\\'Connor', 'Quotes and (brackets) test');
            """)
        tbl = mergendb.from_sql_dump(complex_sql, complex_mgdb)
        self.assertEqual(tbl.row_count, 2)
        res = mergendb.query(f'FROM "{complex_mgdb}" | SELECT name, note')
        self.assertEqual(res.rows[0][1], "Kadıköy (Merkez)")
        self.assertIn("O", res.rows[1][0])

if __name__ == "__main__":
    unittest.main()
