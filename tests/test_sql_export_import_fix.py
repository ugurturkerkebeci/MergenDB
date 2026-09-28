"""
Unit test verifying fix for partial export indentation bug and SQL dump import resilience.
"""
import os
import shutil
import tempfile
import unittest
from mergendb.client import Table, MergenDB
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.io.importer import DataImporter
from mergendb.cli.repl import main as repl_main

class TestExportImportResilience(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mgdb_path = os.path.join(self.tmpdir, "users.mgdb")
        self.sql_path = os.path.join(self.tmpdir, "users.sql")
        self.reimported_mgdb = os.path.join(self.tmpdir, "reimported.mgdb")

        # Create table with ID, TC, GSM
        schema = Schema([
            ColumnDef("ID", DataType.INT64),
            ColumnDef("TC", DataType.STRING),
            ColumnDef("GSM", DataType.STRING)
        ])
        t = Table.create(self.mgdb_path, schema)
        t.insert([
            {"ID": 1, "TC": "16813443088", "GSM": "5364761845"},
            {"ID": 2, "TC": "67315207012", "GSM": "5308776495"},
            {"ID": 3, "TC": "24242097482", "GSM": "5318701732"},
        ])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_sql_emits_one_tuple_per_row(self):
        t = Table(self.mgdb_path)
        t.export_sql(self.sql_path)

        with open(self.sql_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should only have 3 tuples, not 3*3 = 9 tuples
        self.assertEqual(content.count("(1, "), 1)
        self.assertEqual(content.count("(2, "), 1)
        self.assertEqual(content.count("(3, "), 1)
        self.assertNotIn("(1),\n", content)
        self.assertNotIn("(2),\n", content)

    def test_import_sql_recovers_complete_rows_from_corrupted_dump(self):
        # Construct a corrupted SQL dump with duplicate progressive sub-tuples like the user experienced
        corrupted_sql = """
CREATE TABLE IF NOT EXISTS `gsm` (
`ID` BIGINT,
`TC` TEXT,
`GSM` TEXT
);

INSERT INTO `gsm` VALUES
(1),
(1, '16813443088'),
(1, '16813443088', '5364761845'),
(2),
(2, '67315207012'),
(2, '67315207012', '5308776495'),
(3),
(3, '24242097482'),
(3, '24242097482', '5318701732');
"""
        corrupt_path = os.path.join(self.tmpdir, "corrupt.sql")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write(corrupted_sql)

        DataImporter.from_sql_dump(corrupt_path, self.reimported_mgdb)
        reimp = Table(self.reimported_mgdb)

        # Should import exactly 3 rows (not 9)
        self.assertEqual(reimp.row_count, 3)

        res = reimp.query("SELECT * FROM reimported ORDER BY ID ASC")
        rows = res.rows
        self.assertEqual(len(rows), 3)

        # Verify TC and GSM are NOT NULL
        self.assertEqual(rows[0][0], 1)
        self.assertEqual(rows[0][1], "16813443088")
        self.assertEqual(rows[0][2], "5364761845")

        self.assertEqual(rows[1][0], 2)
        self.assertEqual(rows[1][1], "67315207012")
        self.assertEqual(rows[1][2], "5308776495")

        self.assertEqual(rows[2][0], 3)
        self.assertEqual(rows[2][1], "24242097482")
        self.assertEqual(rows[2][2], "5318701732")

if __name__ == "__main__":
    unittest.main()
