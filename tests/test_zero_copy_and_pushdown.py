import os
import unittest
import tempfile
import mmap
import mergendb
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter
from mergendb.storage.reader import FileReader

class TestZeroCopyAndPushdown(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.temp_dir, "test_pushdown.mgdb")

        # Create table with low cardinality column (status) to trigger dictionary encoding
        self.schema = Schema([
            ColumnDef("id", DataType.INT32),
            ColumnDef("name", DataType.STRING),
            ColumnDef("status", DataType.STRING),
            ColumnDef("score", DataType.FLOAT64)
        ])

        with FileWriter(self.filepath, self.schema, block_size=1000) as writer:
            statuses = ["ACTIVE", "PENDING", "FAILED", "SUSPENDED"]
            for i in range(2500):
                writer.write_row([
                    i + 1,
                    f"User_{i}",
                    statuses[i % len(statuses)],
                    float(i * 1.5)
                ])

    def tearDown(self):
        if os.path.exists(self.filepath):
            try:
                os.remove(self.filepath)
            except Exception:
                pass
        if os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except Exception:
                pass

    def test_mmap_reader_initialization_and_close(self):
        with FileReader(self.filepath) as reader:
            self.assertIsNotNone(reader._mmap)
            self.assertIsInstance(reader._mmap, mmap.mmap)
            # Verify read_chunk_bytes returns memoryview
            chunk_bytes = reader.read_chunk_bytes(0, 16)
            self.assertIsInstance(chunk_bytes, memoryview)
            self.assertEqual(len(chunk_bytes), 16)

        # After closing, _mmap must be closed and set to None
        self.assertIsNone(reader._mmap)
        self.assertTrue(reader._file.closed)

    def test_dict_predicate_pushdown_equality(self):
        tbl = mergendb.open(self.filepath)
        res = tbl.sql("SELECT id, status FROM test_pushdown WHERE status = 'ACTIVE';")
        # 2500 / 4 = 625 active rows
        self.assertEqual(len(res), 625)
        for r in res:
            self.assertEqual(r[1], "ACTIVE")

    def test_dict_predicate_pushdown_inequality(self):
        tbl = mergendb.open(self.filepath)
        res = tbl.sql("SELECT id, status FROM test_pushdown WHERE status != 'ACTIVE';")
        # 2500 - 625 = 1875 rows
        self.assertEqual(len(res), 1875)
        for r in res:
            self.assertNotEqual(r[1], "ACTIVE")

    def test_dict_predicate_pushdown_non_existent_value(self):
        tbl = mergendb.open(self.filepath)
        res = tbl.sql("SELECT id, status FROM test_pushdown WHERE status = 'DELETED';")
        # DELETED doesn't exist in any dictionary -> 0 rows returned instantly
        self.assertEqual(len(res), 0)

    def test_multi_condition_with_pushdown(self):
        tbl = mergendb.open(self.filepath)
        res = tbl.sql("SELECT id, status, score FROM test_pushdown WHERE status = 'PENDING' AND id <= 100;")
        # id <= 100 has 100 rows. PENDING is indices 1, 5, 9, ... 100 / 4 = 25
        self.assertEqual(len(res), 25)
        for r in res:
            self.assertEqual(r[1], "PENDING")
            self.assertLessEqual(r[0], 100)

if __name__ == "__main__":
    unittest.main()
