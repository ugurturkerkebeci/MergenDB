import unittest
import os
import shutil
import tempfile
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter
from mergendb.storage.reader import FileReader

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.test_dir, "test_table.mgdb")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_write_and_read_roundtrip(self):
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
            ColumnDef("age", DataType.INT32),
            ColumnDef("salary", DataType.FLOAT64),
            ColumnDef("is_active", DataType.BOOL)
        ])

        # Write 2500 rows with block size 500 -> Exactly 5 blocks
        with FileWriter(self.filepath, schema, block_size=500) as writer:
            for i in range(2500):
                writer.write_row({
                    "id": i,
                    "name": f"User_{i % 50}",
                    "age": 20 + (i // 100),  # Block 0: age 20-24, Block 1: 25-29, Block 2: 30-34, Block 3: 35-39, Block 4: 40-44
                    "salary": 5000.0 + (i * 1.5),
                    "is_active": (i % 2 == 0)
                })

        self.assertTrue(os.path.exists(self.filepath))

        with FileReader(self.filepath) as reader:
            self.assertEqual(reader.total_rows, 2500)
            self.assertEqual(len(reader.blocks), 5)
            self.assertEqual(reader.schema.column_names(), ["id", "name", "age", "salary", "is_active"])

            # 1. Full scan
            all_ids = []
            for batch, stats in reader.scan():
                all_ids.extend(batch.columns["id"])
            self.assertEqual(len(all_ids), 2500)
            self.assertEqual(all_ids[:5], [0, 1, 2, 3, 4])
            self.assertEqual(stats.blocks_scanned, 5)
            self.assertEqual(stats.blocks_skipped, 0)

            # 2. ZoneMap Pruning Test: age > 40
            # Only Block 4 has age > 40! Blocks 0, 1, 2, 3 must be SKIPPED!
            filtered_ids = []
            final_stats = None
            for batch, stats in reader.scan(predicates=[("age", ">", 40)]):
                filtered_ids.extend(batch.columns["id"])
                final_stats = stats

            self.assertIsNotNone(final_stats)
            self.assertEqual(final_stats.blocks_skipped, 4)  # 4 blocks skipped without reading!
            self.assertEqual(final_stats.blocks_scanned, 1)

            # 3. Column Pruning Test: Only read "name" and "salary"
            for batch, stats in reader.scan(columns=["name", "salary"]):
                self.assertIn("name", batch.columns)
                self.assertIn("salary", batch.columns)
                self.assertNotIn("id", batch.columns)
                self.assertNotIn("age", batch.columns)
                self.assertNotIn("is_active", batch.columns)

    def test_export_table_formats(self):
        from mergendb.cli.repl import MergenCLI
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
        ])
        with FileWriter(self.filepath, schema, block_size=100) as writer:
            for i in range(250):
                writer.write_row([i, f"Name_{i}"])

        cli = MergenCLI()
        # Test CSV export
        csv_out = os.path.join(self.test_dir, "out.csv")
        cli.export_table(self.filepath, "CSV", csv_out)
        self.assertTrue(os.path.exists(csv_out))
        self.assertGreater(os.path.getsize(csv_out), 0)

        # Test JSONL export
        jsonl_out = os.path.join(self.test_dir, "out.jsonl")
        cli.export_table(self.filepath, "JSON", jsonl_out)
        self.assertTrue(os.path.exists(jsonl_out))
        self.assertGreater(os.path.getsize(jsonl_out), 0)

        # Test SQL export
        sql_out = os.path.join(self.test_dir, "out.sql")
        cli.export_table(self.filepath, "SQL", sql_out)
        self.assertTrue(os.path.exists(sql_out))
        with open(sql_out, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("CREATE TABLE", content)
            self.assertIn("INSERT INTO", content)

if __name__ == "__main__":
    unittest.main()
