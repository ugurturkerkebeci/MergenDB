import os
import shutil
import tempfile
import unittest
import mergendb
from mergendb import Table, Schema, ColumnDef, DataType

class TestFriendlyAPI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "users.mgdb")

        # Create schema
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("adi", DataType.STRING),
            ColumnDef("bakiye", DataType.INT64),
            ColumnDef("sehir", DataType.STRING)
        ])
        self.table = mergendb.create_table(self.db_path, schema)

        # Insert test data
        self.table.insert([
            {"id": 1, "adi": "abdurrezzak", "bakiye": 30, "sehir": "Ankara"},
            {"id": 2, "adi": "mehmet", "bakiye": 50, "sehir": "İstanbul"},
            {"id": 3, "adi": "abdurrezzak", "bakiye": 100, "sehir": "İzmir"},
            {"id": 4, "adi": "ayse", "bakiye": 30, "sehir": "Ankara"},
        ])

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_connect_and_len(self):
        db = mergendb.connect(self.db_path)
        self.assertEqual(len(db), 4)
        self.assertEqual(db.count(), 4)
        self.assertEqual(db.columns, ["id", "adi", "bakiye", "sehir"])

    def test_find_kwargs(self):
        db = mergendb.connect(self.db_path)
        # Find where adi='abdurrezzak' AND bakiye=30
        res = db.find(adi="abdurrezzak", bakiye=30)
        self.assertEqual(len(res), 1)
        dicts = res.to_dicts()
        self.assertEqual(dicts[0]["id"], 1)
        self.assertEqual(dicts[0]["adi"], "abdurrezzak")
        self.assertEqual(dicts[0]["bakiye"], 30)

    def test_find_one(self):
        db = mergendb.connect(self.db_path)
        user = db.find_one(adi="abdurrezzak", bakiye=100)
        self.assertIsNotNone(user)
        self.assertEqual(user["id"], 3)
        self.assertEqual(user["sehir"], "İzmir")

        # Non-matching
        none_user = db.find_one(adi="non_existing")
        self.assertIsNone(none_user)

    def test_where_expression(self):
        db = mergendb.connect(self.db_path)
        res = db.where("bakiye >= 50 AND sehir != 'Ankara'")
        self.assertEqual(len(res), 2)

    def test_search_fulltext(self):
        db = mergendb.connect(self.db_path)
        res = db.search("rezza") # substring in 'abdurrezzak'
        self.assertEqual(len(res), 2)

    def test_select_fluent(self):
        db = mergendb.connect(self.db_path)
        res = db.select("adi", "bakiye", where="bakiye = 30", order_by="id DESC")
        self.assertEqual(len(res), 2)
        dicts = res.to_dicts()
        self.assertEqual(dicts[0]["id"] if "id" in dicts[0] else None, None) # only adi, bakiye
        self.assertEqual(dicts[0]["adi"], "ayse")
        self.assertEqual(dicts[1]["adi"], "abdurrezzak")

    def test_sql_direct(self):
        db = mergendb.connect(self.db_path)
        res = db.sql("SELECT * FROM users WHERE adi = 'abdurrezzak' AND bakiye = 30")
        self.assertEqual(len(res), 1)
        self.assertEqual(res.first[1], "abdurrezzak")

    def test_top_level_helpers(self):
        # mergendb.find
        res = mergendb.find(self.db_path, adi="ayse")
        self.assertEqual(len(res), 1)

        # mergendb.sql
        res_sql = mergendb.sql(f"SELECT adi, bakiye FROM '{self.db_path}' WHERE bakiye = 30")
        self.assertEqual(len(res_sql), 2)

if __name__ == "__main__":
    unittest.main()
