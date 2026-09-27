import os
import json
import csv
import unittest
import tempfile
import shutil
from mergendb import MergenDB
from mergendb.cli.repl import MergenCLI

class TestExportFormats(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create a sample database.mgdb table
        self.tbl_path = os.path.join(self.temp_dir, "database.mgdb")
        from mergendb import Schema, ColumnDef, DataType
        import mergendb
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
            ColumnDef("score", DataType.FLOAT64),
            ColumnDef("active", DataType.BOOL)
        ])
        self.db = mergendb.create_table(self.tbl_path, schema, block_size=50)
        self.db.insert([
            {"id": 1, "name": "Alice", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 82.0, "active": False},
            {"id": 3, "name": "Charlie", "score": 88.5, "active": True},
        ])
        self.cli = MergenCLI()

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_database_to_json(self):
        self.cli.execute_command("EXPORT database TO JSON;")
        self.assertTrue(os.path.exists("database.json"), "database.json should exist")
        with open("database.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 3)
            self.assertEqual(data[0]["name"], "Alice")

    def test_export_database_to_csv(self):
        self.cli.execute_command("EXPORT database TO CSV;")
        self.assertTrue(os.path.exists("database.csv"), "database.csv should exist")
        with open("database.csv", "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
            self.assertEqual(len(rows), 4) # 1 header + 3 rows
            self.assertEqual(rows[0], ["id", "name", "score", "active"])

    def test_export_database_to_sql(self):
        self.cli.execute_command("EXPORT database TO SQL;")
        self.assertTrue(os.path.exists("database.sql"), "database.sql should exist")
        with open("database.sql", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("CREATE TABLE IF NOT EXISTS `database`", content)
            self.assertIn("INSERT INTO `database` VALUES", content)
            self.assertIn("'Alice'", content)

    def test_export_database_to_jsonl(self):
        self.cli.execute_command("EXPORT database TO JSONL;")
        self.assertTrue(os.path.exists("database.jsonl"), "database.jsonl should exist")
        with open("database.jsonl", "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[1]["name"], "Bob")

    def test_export_database_shorthand(self):
        # EXPORT database JSON;
        self.cli.execute_command("EXPORT database JSON;")
        self.assertTrue(os.path.exists("database.json"))

        # EXPORT database; (defaults to CSV)
        self.cli.execute_command("EXPORT database;")
        self.assertTrue(os.path.exists("database.csv"))

    def test_export_format_first_syntax(self):
        # EXPORT CSV database; -> MUST produce database.csv, NEVER an extensionless 'database' file
        self.cli.execute_command("EXPORT CSV database;")
        self.assertTrue(os.path.exists("database.csv"))
        self.assertFalse(os.path.exists("database"), "Should NOT create extensionless 'database' file!")

        # EXPORT JSON database;
        self.cli.execute_command("EXPORT JSON database;")
        self.assertTrue(os.path.exists("database.json"))

    def test_export_database_to_csv_database(self):
        # Even if user repeats table name as output or syntax: EXPORT database TO CSV database;
        self.cli.execute_command("EXPORT database TO CSV database;")
        self.assertTrue(os.path.exists("database.csv"))
        self.assertFalse(os.path.exists("database"), "Must NEVER create extensionless file")

    def test_export_custom_output_filename_without_ext(self):
        self.cli.execute_command("EXPORT database TO JSON my_custom_data;")
        self.assertTrue(os.path.exists("my_custom_data.json"), "Must append .json extension")

    def test_export_mismatched_extension_correction(self):
        # User specified format JSON, but typed .sql by mistake
        self.cli.execute_command("EXPORT database TO JSON my_dump.sql;")
        self.assertTrue(os.path.exists("my_dump.json"), "Must enforce format extension .json")

    def test_export_with_active_table(self):
        self.cli.execute_command("USE database;")
        self.cli.execute_command("EXPORT JSON;")
        self.assertTrue(os.path.exists("database.json"))

        self.cli.execute_command("EXPORT CSV;")
        self.assertTrue(os.path.exists("database.csv"))

        self.cli.execute_command("EXPORT custom.json;")
        self.assertTrue(os.path.exists("custom.json"))

    def test_python_api_export_ensures_extension(self):
        import mergendb
        tbl = mergendb.Table(self.tbl_path)
        # Calling export_csv with no extension
        tbl.export_csv("py_export")
        self.assertTrue(os.path.exists("py_export.csv"))

        # Calling export_json with no extension
        tbl.export_json("py_export_json")
        self.assertTrue(os.path.exists("py_export_json.json"))

        # Calling export without extension defaults to .csv
        tbl.export("py_export_def")
        self.assertTrue(os.path.exists("py_export_def.csv"))

if __name__ == "__main__":
    unittest.main()
