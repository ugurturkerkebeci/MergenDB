import os
import unittest
import mergendb
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType


class TestMutations(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_mutation_db.mgdb"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

        # Create sample table with 5 rows
        self.tbl = mergendb.connect(self.test_file)
        self.sample_data = [
            {"id": 1, "name": "Alice", "balance": 100, "active": True},
            {"id": 2, "name": "Bob", "balance": 200, "active": False},
            {"id": 3, "name": "Charlie", "balance": 300, "active": True},
            {"id": 4, "name": "David", "balance": 400, "active": True},
            {"id": 5, "name": "Eve", "balance": 500, "active": False},
        ]
        self.tbl.insert(self.sample_data)

    def tearDown(self):
        for f in [self.test_file, self.test_file + ".tmp", "renamed_db.mgdb", "renamed_sql.mgdb"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def test_rename_column(self):
        self.tbl.rename_column("name", "full_name")
        self.assertIn("full_name", self.tbl.columns)
        self.assertNotIn("name", self.tbl.columns)

        # Verify data preserved
        rows = self.tbl.all()
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["full_name"], "Alice")
        self.assertEqual(rows[1]["full_name"], "Bob")

        # Test error conditions
        with self.assertRaises(KeyError):
            self.tbl.rename_column("non_existent", "xyz")
        with self.assertRaises(ValueError):
            self.tbl.rename_column("id", "balance")

    def test_drop_column(self):
        self.tbl.drop_column("active")
        self.assertNotIn("active", self.tbl.columns)
        self.assertIn("name", self.tbl.columns)
        self.assertEqual(len(self.tbl.all()), 5)

        with self.assertRaises(KeyError):
            self.tbl.drop_column("already_deleted")

    def test_add_column(self):
        self.tbl.add_column("country", "string", default="Turkey")
        self.assertIn("country", self.tbl.columns)

        rows = self.tbl.all()
        self.assertEqual(len(rows), 5)
        for r in rows:
            self.assertEqual(r["country"], "Turkey")

        # Add int column
        self.tbl.add_column("tier", DataType.INT64, default=1)
        rows2 = self.tbl.all()
        for r in rows2:
            self.assertEqual(r["tier"], 1)

        with self.assertRaises(ValueError):
            self.tbl.add_column("country", "string")

    def test_update_with_where(self):
        # Update balance for Charlie
        affected = self.tbl.update({"balance": 999}, where="name = 'Charlie'")
        self.assertEqual(affected, 1)

        charlie = self.tbl.find_one(name="Charlie")
        self.assertIsNotNone(charlie)
        self.assertEqual(charlie["balance"], 999)

        # Verify other rows unaffected
        alice = self.tbl.find_one(name="Alice")
        self.assertEqual(alice["balance"], 100)

    def test_update_all(self):
        affected = self.tbl.update({"active": False})
        self.assertEqual(affected, 5)

        for r in self.tbl.all():
            self.assertFalse(r["active"])

    def test_delete_with_where(self):
        affected = self.tbl.delete(where="balance > 300")
        self.assertEqual(affected, 2)  # David (400) and Eve (500)
        self.assertEqual(self.tbl.row_count, 3)

        remaining = [r["name"] for r in self.tbl.all()]
        self.assertEqual(remaining, ["Alice", "Bob", "Charlie"])

    def test_truncate(self):
        cnt = self.tbl.truncate()
        self.assertEqual(cnt, 5)
        self.assertEqual(self.tbl.row_count, 0)
        self.assertEqual(len(self.tbl.columns), 4)

    def test_drop_and_rename_table(self):
        renamed_path = "renamed_db.mgdb"
        self.tbl.rename(renamed_path)
        self.assertFalse(os.path.exists(self.test_file))
        self.assertTrue(os.path.exists(renamed_path))
        self.assertEqual(self.tbl.row_count, 5)

        dropped = self.tbl.drop()
        self.assertTrue(dropped)
        self.assertFalse(os.path.exists(renamed_path))

    def test_sql_mutations(self):
        # Test SQL UPDATE
        res_upd = self.tbl.sql(f"UPDATE {self.test_file} SET balance = 777 WHERE id = 1")
        self.assertEqual(res_upd.rows[0][0], 1)
        row1 = self.tbl.find_one(id=1)
        self.assertEqual(row1["balance"], 777)

        # Test SQL DELETE
        res_del = self.tbl.sql(f"DELETE FROM {self.test_file} WHERE id = 2")
        self.assertEqual(res_del.rows[0][0], 1)
        self.assertIsNone(self.tbl.find_one(id=2))
        self.assertEqual(self.tbl.row_count, 4)

        # Test SQL ALTER TABLE RENAME COLUMN
        self.tbl.sql(f"ALTER TABLE {self.test_file} RENAME COLUMN balance TO credits")
        self.assertIn("credits", self.tbl.columns)
        self.assertNotIn("balance", self.tbl.columns)

        # Test SQL ALTER TABLE ADD COLUMN
        self.tbl.sql(f"ALTER TABLE {self.test_file} ADD COLUMN rating FLOAT DEFAULT 4.5")
        self.assertIn("rating", self.tbl.columns)
        row = self.tbl.find_one(id=1)
        self.assertEqual(row["rating"], 4.5)

        # Test SQL ALTER TABLE DROP COLUMN
        self.tbl.sql(f"ALTER TABLE {self.test_file} DROP COLUMN rating")
        self.assertNotIn("rating", self.tbl.columns)

        # Test SQL TRUNCATE TABLE
        res_trunc = mergendb.sql(f"TRUNCATE TABLE {self.test_file}")
        self.assertEqual(self.tbl.row_count, 0)


if __name__ == "__main__":
    unittest.main()
