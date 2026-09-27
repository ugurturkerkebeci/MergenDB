import unittest
import os
import shutil
import tempfile
from mergendb.client import MergenDB
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType

class TestJoinsAndHaving(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.users_file = os.path.join(self.test_dir, "users.mgdb")
        self.orders_file = os.path.join(self.test_dir, "orders.mgdb")
        self.emp_file = os.path.join(self.test_dir, "employees.mgdb")

        # 1. Users Table
        users_schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
            ColumnDef("city", DataType.STRING),
            ColumnDef("age", DataType.INT32)
        ])
        users_tbl = MergenDB.create_table(self.users_file, users_schema)
        users_tbl.insert_many([
            [1, "Alice", "Istanbul", 28],
            [2, "Bob", "Ankara", 35],
            [3, "Charlie", "Izmir", 22],
            [4, "David", "Istanbul", 40],
            [5, "Eve", "Bursa", 30]  # Eve has no orders
        ])

        # 2. Orders Table
        orders_schema = Schema([
            ColumnDef("order_id", DataType.INT64),
            ColumnDef("user_id", DataType.INT64),
            ColumnDef("amount", DataType.FLOAT64),
            ColumnDef("item", DataType.STRING)
        ])
        orders_tbl = MergenDB.create_table(self.orders_file, orders_schema)
        orders_tbl.insert_many([
            [101, 1, 150.0, "Laptop Stand"],
            [102, 1, 45.0, "Mousepad"],
            [103, 2, 300.0, "Monitor"],
            [104, 3, 20.0, "USB Cable"],
            [105, 4, 1200.0, "Smartphone"],
            [106, 999, 50.0, "Orphan Item"]  # User 999 does not exist
        ])

        # 3. Employees Table for Multi-Column GROUP BY & HAVING
        emp_schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
            ColumnDef("department", DataType.STRING),
            ColumnDef("city", DataType.STRING),
            ColumnDef("salary", DataType.FLOAT64)
        ])
        emp_tbl = MergenDB.create_table(self.emp_file, emp_schema)
        emp_tbl.insert_many([
            [1, "Ali", "Engineering", "Istanbul", 80000.0],
            [2, "Ayse", "Engineering", "Istanbul", 90000.0],
            [3, "Mehmet", "Engineering", "Ankara", 75000.0],
            [4, "Fatma", "Marketing", "Istanbul", 60000.0],
            [5, "Can", "Marketing", "Istanbul", 65000.0],
            [6, "Zeynep", "Marketing", "Izmir", 55000.0],
            [7, "Burak", "Sales", "Ankara", 50000.0],
            [8, "Elif", "Sales", "Ankara", 52000.0]
        ])

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_pipeline_inner_join(self):
        # Join users and orders on id = user_id
        q = f'''
        FROM "{self.users_file}"
        | INNER JOIN "{self.orders_file}" ON id = user_id
        | SELECT name, item, amount
        | SORT amount DESC
        '''
        res = MergenDB.query(q)
        self.assertEqual(len(res), 5)
        # Top amount should be David's Smartphone (1200.0)
        self.assertEqual(res[0][0], "David")
        self.assertEqual(res[0][1], "Smartphone")
        self.assertEqual(res[0][2], 1200.0)

    def test_pipeline_left_join(self):
        # Eve (id=5) has no orders, should appear with NULL order columns
        q = f'''
        FROM "{self.users_file}"
        | LEFT JOIN "{self.orders_file}" ON id = user_id
        | SELECT id, name, amount
        | SORT id ASC
        '''
        res = MergenDB.query(q)
        # Alice has 2 orders, Bob 1, Charlie 1, David 1, Eve 1 = total 6 rows
        self.assertEqual(len(res), 6)
        eve_row = [r for r in res if r[1] == "Eve"][0]
        self.assertIsNone(eve_row[2])

    def test_pipeline_join_with_where(self):
        # Join with condition on joined column
        q = f'''
        FROM "{self.users_file}"
        | JOIN "{self.orders_file}" ON id = user_id
        | WHERE city = 'Istanbul' AND amount > 100
        | SELECT name, city, item, amount
        '''
        res = MergenDB.query(q)
        # Alice (Laptop Stand: 150) and David (Smartphone: 1200)
        self.assertEqual(len(res), 2)
        names = {r[0] for r in res}
        self.assertEqual(names, {"Alice", "David"})

    def test_multi_column_group_by_having(self):
        # GROUP BY department, city HAVING count > 1
        q = f'''
        FROM "{self.emp_file}"
        | AGGREGATE count(*) AS cnt, sum(salary) AS total_sal BY department, city
        | HAVING cnt > 1
        | SORT total_sal DESC
        '''
        res = MergenDB.query(q)
        # Groups with cnt > 1:
        # Engineering - Istanbul (Ali 80k, Ayse 90k -> total 170k, cnt 2)
        # Marketing - Istanbul (Fatma 60k, Can 65k -> total 125k, cnt 2)
        # Sales - Ankara (Burak 50k, Elif 52k -> total 102k, cnt 2)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0][0], "Engineering")
        self.assertEqual(res[0][1], "Istanbul")
        self.assertEqual(res[0][2], 2)
        self.assertEqual(res[0][3], 170000.0)

    def test_sql_inner_join(self):
        q = f'''
        SELECT users.name, orders.amount, orders.item
        FROM "{self.users_file}"
        INNER JOIN "{self.orders_file}" ON users.id = orders.user_id
        WHERE orders.amount >= 300
        ORDER BY orders.amount DESC
        '''
        res = MergenDB.query(q)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0][0], "David")
        self.assertEqual(res[0][1], 1200.0)
        self.assertEqual(res[1][0], "Bob")
        self.assertEqual(res[1][1], 300.0)

    def test_sql_left_join(self):
        q = f'''
        SELECT users.name, orders.amount
        FROM "{self.users_file}"
        LEFT JOIN "{self.orders_file}" ON users.id = orders.user_id
        WHERE users.id = 5
        '''
        res = MergenDB.query(q)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "Eve")
        self.assertIsNone(res[0][1])

    def test_sql_group_by_having(self):
        q = f'''
        SELECT department, city, count(*), sum(salary) AS total_sal
        FROM "{self.emp_file}"
        GROUP BY department, city
        HAVING sum(salary) > 110000
        ORDER BY total_sal DESC
        '''
        res = MergenDB.query(q)
        # Groups > 110k: Engineering-Istanbul (170k) and Marketing-Istanbul (125k)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0][0], "Engineering")
        self.assertEqual(res[0][3], 170000.0)
        self.assertEqual(res[1][0], "Marketing")
        self.assertEqual(res[1][3], 125000.0)

    def test_sql_having_with_alias_directly(self):
        q = f'''
        SELECT department, AVG(salary) AS avg_sal
        FROM "{self.emp_file}"
        GROUP BY department
        HAVING avg_sal >= 70000
        ORDER BY avg_sal DESC
        '''
        res = MergenDB.query(q)
        # Only Engineering (avg = (80+90+75)/3 = 81666.67)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "Engineering")
        self.assertAlmostEqual(res[0][1], 81666.67, delta=1.0)

if __name__ == "__main__":
    unittest.main()
