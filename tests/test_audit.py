import unittest
import os
import tempfile
import shutil
import json
import time

import mergendb
from mergendb.client import MergenDB
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.reader import FileReader
from mergendb.storage.writer import FileWriter

class TestSystemAudit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unicode_and_null_handling(self):
        unicode_db = os.path.join(self.temp_dir, "unicode.mgdb")
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
            ColumnDef("city", DataType.STRING),
            ColumnDef("rating", DataType.FLOAT64),
            ColumnDef("is_active", DataType.BOOL)
        ])
        tbl = MergenDB.create_table(unicode_db, schema, block_size=3)
        sample_data = [
            [1, "Uğur Türker Kebeci", "İstanbul", 9.8, True],
            [2, "Çınar Şahin", "İzmir", None, False],
            [3, "Özlem Dağ", "Ankara", 8.5, None],
            [4, "Gökçe Yıldız (Star)", "Antalya", 9.2, True],
            [5, "NULL User", None, None, False],
            [6, "Ahmet Çalık", "Konya", 7.0, True]
        ]
        tbl.insert_many(sample_data, block_size=3)
        res = tbl.sql("SELECT name, city FROM unicode WHERE city = 'İstanbul'")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][0], "Uğur Türker Kebeci")
        res_sub = tbl.sql("SELECT name FROM unicode WHERE name LIKE '%(Star)%'")
        self.assertEqual(len(res_sub), 1)
        self.assertIn("Gökçe", res_sub[0][0])

    def test_bloom_filter_zero_io_skip(self):
        bloom_db = os.path.join(self.temp_dir, "bloom.mgdb")
        b_schema = Schema([
            ColumnDef("guid", DataType.STRING),
            ColumnDef("val", DataType.INT64)
        ])
        with FileWriter(bloom_db, b_schema, block_size=50) as w:
            for i in range(500):
                w.write_row([f"uuid-{i:04d}", i])

        with FileReader(bloom_db) as reader:
            batches = list(reader.scan(predicates=[("guid", "==", "uuid-0250")]))
            self.assertEqual(reader.last_scan_stats.blocks_scanned, 1)
            self.assertEqual(reader.last_scan_stats.blocks_skipped, 9)

    def test_zonemap_range_pruning(self):
        bloom_db = os.path.join(self.temp_dir, "bloom_zm.mgdb")
        b_schema = Schema([
            ColumnDef("guid", DataType.STRING),
            ColumnDef("val", DataType.INT64)
        ])
        with FileWriter(bloom_db, b_schema, block_size=50) as w:
            for i in range(500):
                w.write_row([f"uuid-{i:04d}", i])

        with FileReader(bloom_db) as reader:
            batches = list(reader.scan(predicates=[("val", ">", 400)]))
            self.assertGreaterEqual(reader.last_scan_stats.blocks_skipped, 7)

    def test_hash_join_and_having(self):
        t_users = os.path.join(self.temp_dir, "j_users.mgdb")
        t_orders = os.path.join(self.temp_dir, "j_orders.mgdb")

        u_tbl = MergenDB.create_table(t_users, Schema([ColumnDef("uid", DataType.INT64), ColumnDef("uname", DataType.STRING)]))
        u_tbl.insert_many([[1, "Alice"], [2, "Bob"], [3, "Charlie"]])

        o_tbl = MergenDB.create_table(t_orders, Schema([ColumnDef("oid", DataType.INT64), ColumnDef("user_id", DataType.INT64), ColumnDef("price", DataType.FLOAT64)]))
        o_tbl.insert_many([[101, 1, 50.0], [102, 1, 75.0], [103, 2, 200.0]])

        # INNER JOIN
        res_inner = MergenDB.query(f'FROM "{t_users}" | INNER JOIN "{t_orders}" ON uid = user_id | SELECT uname, price')
        self.assertEqual(len(res_inner), 3)

        # LEFT JOIN
        res_left = MergenDB.query(f'FROM "{t_users}" | LEFT JOIN "{t_orders}" ON uid = user_id | SELECT uname, price')
        self.assertEqual(len(res_left), 4)
        charlie_price = [r[1] for r in res_left if r[0] == "Charlie"][0]
        self.assertIsNone(charlie_price)

    def test_mutations_and_alter(self):
        t_mut = os.path.join(self.temp_dir, "mut.mgdb")
        m_tbl = MergenDB.create_table(t_mut, Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("val", DataType.INT64)
        ]))
        m_tbl.insert_many([[1, 10], [2, 20], [3, 30]])
        m_tbl.update({"val": 99}, where="id = 2")
        self.assertEqual(m_tbl.first("id = 2")["val"], 99)
        m_tbl.delete(where="id = 1")
        self.assertEqual(len(m_tbl.all()), 2)
        m_tbl.add_column("bonus", "FLOAT64", default=5.5)
        self.assertEqual(m_tbl.first()["bonus"], 5.5)
        m_tbl.rename_column("bonus", "extra_bonus")
        self.assertIn("extra_bonus", m_tbl.first())
        m_tbl.truncate()
        self.assertEqual(len(m_tbl.all()), 0)

if __name__ == "__main__":
    unittest.main()
