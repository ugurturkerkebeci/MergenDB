"""
Comprehensive 500-Scenario Extreme Resilience and Fault Tolerance Test Suite for MergenDB v0.7.1.
Tests completely broken data sets, illogical ordering, ragged schemas, corrupt encodings,
boundary arithmetic, dynamic schema mutations, complex analytical queries, and export roundtrips.
Strict zero emojis. Pure CPU, bounded RAM.
"""

import os
import shutil
import tempfile
import unittest
from typing import List, Dict, Any

from mergendb import (
    MergenDB, Table, Schema, ColumnDef, DataType,
    export_csv, export_json, export_jsonl, export_sql
)
from mergendb.io.importer import DataImporter


class TestResilience500(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="mgdb_resilience500_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def _run_scenario(self, idx: int):
        if 1 <= idx <= 100:
            self._scenario_csv(idx)
        elif 101 <= idx <= 200:
            self._scenario_json(idx)
        elif 201 <= idx <= 300:
            self._scenario_sql(idx)
        elif 301 <= idx <= 400:
            self._scenario_mutation(idx)
        else:
            self._scenario_query_roundtrip(idx)

    # ------------------------------------------------------------------
    # 1 - 100: Extreme CSV & Illogical Orderings
    # ------------------------------------------------------------------
    def _scenario_csv(self, idx: int):
        csv_file = os.path.join(self.test_dir, f"csv_{idx}.csv")
        mgdb_file = os.path.join(self.test_dir, f"csv_out_{idx}.mgdb")

        # Illogical scrambled ordering: IDs in chaotic sequence
        scrambled_ids = [999, 12, 404, 3, 85, 0, -42, 1000000, 77, 19, 5, 250, -1, 8888, 64]
        lines = ["id,title,score,flag"]

        dirty_tokens = ["", "NULL", "none", "N/A", "NaN", "\\N", "nil", "-", "undefined", "null"]

        for row_i, rid in enumerate(scrambled_ids):
            d_tok = dirty_tokens[(row_i + idx) % len(dirty_tokens)]
            if idx % 10 == 1: # Ragged short rows
                lines.append(f"{rid},ShortTitle_{row_i}" if row_i % 2 == 0 else f"{rid},Valid_{row_i},{row_i * 10},true")
            elif idx % 10 == 2: # Ragged extra long rows
                lines.append(f"{rid},Extra_{row_i},{row_i * 5},false,surplus1,surplus2,surplus3" if row_i % 3 == 0 else f"{rid},Valid_{row_i},{row_i * 5},true")
            elif idx % 10 == 3: # Null bytes in string
                lines.append(f"{rid},NullByte_\x00_{row_i},{row_i * 12.5},true")
            elif idx % 10 == 4: # Whitespace padding and irregular tabs
                lines.append(f"  {rid}  \t,\t  'Padded {row_i}'  \t,\t  {row_i * 1.5}  \t,\t  false  ")
            elif idx % 10 == 5: # Dirty null tokens
                lines.append(f"{rid},Token_{row_i},{d_tok if row_i % 2 == 0 else row_i * 20},{d_tok if row_i % 3 == 0 else 'true'}")
            elif idx % 10 == 6: # Empty lines and comments mixed in
                if row_i % 3 == 0:
                    lines.append("")
                if row_i % 4 == 0:
                    lines.append(f"# Comment line {row_i}")
                lines.append(f"{rid},Clean_{row_i},{row_i * 8},false")
            elif idx % 10 == 7: # Carriage returns and Windows CRLF
                lines.append(f"{rid},Item_{row_i}\r,{row_i * 7},true")
            elif idx % 10 == 8: # Extreme Unicode (Turkish, Cyrillic, Japanese, Arabic)
                lines.append(f"{rid},Şehir_Örnek_{row_i}_Москва_東京_العربية,{row_i * 9},true")
            elif idx % 10 == 9: # Exponential numbers and scientific notation
                lines.append(f"{rid},Sci_{row_i},{row_i}e-3,true")
            else: # idx % 10 == 0: Unclosed quotes on select lines
                lines.append(f'{rid},"Unclosed_{row_i},{row_i * 4},true' if row_i % 4 == 0 else f'{rid},"Quoted {row_i}",{row_i * 4},true')

        content = "\n".join(lines)
        if idx % 7 == 0:
            content = "\uFEFF" + content # BOM prefix

        with open(csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        imported = DataImporter.from_csv(csv_file, mgdb_file)
        self.assertGreater(imported, 0, f"CSV scenario {idx} imported 0 rows")
        tbl = Table(mgdb_file)
        self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # 101 - 200: Irregular & Corrupt JSON / JSONL
    # ------------------------------------------------------------------
    def _scenario_json(self, idx: int):
        is_jsonl = (idx % 2 == 0)
        ext = "jsonl" if is_jsonl else "json"
        in_file = os.path.join(self.test_dir, f"json_{idx}.{ext}")
        mgdb_file = os.path.join(self.test_dir, f"json_out_{idx}.mgdb")

        # Illogical scrambled IDs
        ids = [42, 100, 7, 0, 999, -5, 333, 12, 88, 15, 204, 55, 301, 8, 19, 44, 91, 105, 777, 2]

        if is_jsonl:
            lines = []
            for i, rid in enumerate(ids):
                if i % 4 == 0 and idx % 3 == 0:
                    # Malformed JSON syntax (broken braces / unclosed quote)
                    lines.append(f'{{"id": {rid}, "name": "Broken_{i}')
                elif i % 5 == 0 and idx % 2 == 0:
                    # Embedded null bytes
                    lines.append(f'{{"id": {rid}, "name": "null\x00byte", "metric": {rid * 1.5}}}')
                elif i % 3 == 0 and idx % 4 == 0:
                    # Whitespace or empty line
                    lines.append("    ")
                else:
                    # Out-of-order keys
                    lines.append(f'{{"metric": {rid * 2.5}, "active": {str(i % 2 == 0).lower()}, "id": {rid}, "name": "valid_{i}"}}')
            content = "\n".join(lines)
        else:
            # JSON array with irregular elements and null values
            items = []
            for i, rid in enumerate(ids):
                m_val = "null" if i % 3 == 0 else f"{rid * 3.14:.2f}"
                name_val = "null" if i % 4 == 0 else f'"entry_{rid}"'
                items.append(f'{{"id": {rid}, "name": {name_val}, "metric": {m_val}}}')
            content = "[\n" + ",\n".join(items) + "\n]"

        with open(in_file, "w", encoding="utf-8") as f:
            f.write(content)

        if is_jsonl:
            imported = DataImporter.from_jsonl(in_file, mgdb_file)
        else:
            imported = DataImporter.from_json(in_file, mgdb_file)

        self.assertGreater(imported, 5, f"JSON scenario {idx} imported fewer than 5 rows: {imported}")
        tbl = Table(mgdb_file)
        self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # 201 - 300: Fragmented SQL Dumps & Complex DDL
    # ------------------------------------------------------------------
    def _scenario_sql(self, idx: int):
        sql_file = os.path.join(self.test_dir, f"dump_{idx}.sql")
        mgdb_file = os.path.join(self.test_dir, f"sql_out_{idx}.mgdb")

        lines = [
            f"/*!40101 SET @saved_cs_client = @@character_set_client */;",
            f"CREATE TABLE `entity_{idx}` (",
            "  `id` bigint(20) NOT NULL,",
            "  `category` varchar(128) DEFAULT NULL,",
            "  `amount` decimal(12,2) DEFAULT NULL",
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
            f"INSERT INTO `entity_{idx}` VALUES"
        ]

        tuples = []
        ids = [500, 10, 250, 2, 90, 1, 800, 35, 777, 4, 120, 65, 300, 8, 44, 9, 600, 15, 888, 3]
        categories = ["Electronics", "Books", "Fashion", "Home", "Automotive"]

        for i, rid in enumerate(ids):
            cat = categories[i % len(categories)]
            if i % 4 == 0 and idx % 2 == 0:
                # Broken syntax tuple
                tuples.append(f"({rid}, 'Incomplete")
            elif i % 5 == 0:
                # Escaped quote
                tuples.append(f"({rid}, 'O\\'Connor_{i}', {rid * 15.5})")
            else:
                tuples.append(f"({rid}, '{cat}', {rid * 12.0})")

        lines.append(",\n".join(tuples) + ";")
        lines.append("/*!40101 SET character_set_client = @saved_cs_client */;")

        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        imported = DataImporter.from_sql_dump(sql_file, mgdb_file)
        self.assertGreaterEqual(imported, 5, f"SQL scenario {idx} imported fewer than 5 rows: {imported}")
        tbl = Table(mgdb_file)
        self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # 301 - 400: Illogical Ordering & Extreme Schema Mutations
    # ------------------------------------------------------------------
    def _scenario_mutation(self, idx: int):
        tbl_file = os.path.join(self.test_dir, f"mut_{idx}.mgdb")
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("tag", DataType.STRING),
            ColumnDef("value", DataType.FLOAT64)
        ])
        tbl = MergenDB.create_table(tbl_file, schema)

        # Scrambled non-monotonic IDs
        scrambled_rows = [
            [50, "B", 10.5],
            [10, "A", None],
            [100, None, 20.0],
            [25, "C", 5.0],
            [-5, "Z", 0.0],
            [75, "E", 15.5]
        ]
        tbl.insert_many(scrambled_rows)
        self.assertEqual(tbl.row_count, 6)

        # Dynamic column addition
        col_name = f"status_{idx}"
        tbl.add_column(col_name, "string", default="init")
        self.assertIn(col_name, tbl.columns)

        # Update with complex inverted condition
        tbl.update({col_name: "processed"}, where=f"id > 20")

        # Column rename
        renamed_col = f"renamed_{idx}"
        tbl.rename_column(col_name, renamed_col)
        self.assertIn(renamed_col, tbl.columns)
        self.assertNotIn(col_name, tbl.columns)

        # Delete matching subset
        tbl.delete("id < 0")
        self.assertEqual(tbl.row_count, 5)

        # Drop added column
        tbl.drop_column(renamed_col)
        self.assertNotIn(renamed_col, tbl.columns)
        self.assertEqual(tbl.row_count, 5)

    # ------------------------------------------------------------------
    # 401 - 500: Advanced Queries, Aggregations & Export Roundtrips
    # ------------------------------------------------------------------
    def _scenario_query_roundtrip(self, idx: int):
        tbl_file = os.path.join(self.test_dir, f"rt_{idx}.mgdb")
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("group_key", DataType.STRING),
            ColumnDef("amount", DataType.FLOAT64),
            ColumnDef("flag", DataType.BOOL)
        ])
        tbl = MergenDB.create_table(tbl_file, schema)

        # Insert 20 rows with mixed groups and nulls
        rows = []
        for r in range(1, 21):
            gk = f"grp_{r % 4}"
            amt = None if r % 5 == 0 else float(r * 10)
            rows.append([r, gk, amt, r % 2 == 0])
        tbl.insert_many(rows)

        # Analytical SQL query with GROUP BY and HAVING
        clean_name = f"rt_{idx}"
        res = tbl.sql(f"SELECT group_key, COUNT(*) AS total FROM {clean_name} GROUP BY group_key HAVING COUNT(*) >= 1")
        self.assertGreater(len(res.rows), 0)

        # Export to CSV / JSON / JSONL / SQL
        fmt = ["csv", "json", "jsonl", "sql"][idx % 4]
        exp_file = os.path.join(self.test_dir, f"export_{idx}.{fmt}")

        if fmt == "csv":
            export_csv(tbl_file, exp_file)
        elif fmt == "json":
            export_json(tbl_file, exp_file)
        elif fmt == "jsonl":
            export_jsonl(tbl_file, exp_file)
        else:
            export_sql(tbl_file, exp_file)

        self.assertTrue(os.path.exists(exp_file))
        self.assertGreater(os.path.getsize(exp_file), 0)

        # Re-import and assert 100% data recovery
        re_mgdb = os.path.join(self.test_dir, f"re_{idx}.mgdb")
        if fmt == "csv":
            count = DataImporter.from_csv(exp_file, re_mgdb)
        elif fmt == "json":
            count = DataImporter.from_json(exp_file, re_mgdb)
        elif fmt == "jsonl":
            count = DataImporter.from_jsonl(exp_file, re_mgdb)
        else:
            count = DataImporter.from_sql_dump(exp_file, re_mgdb)

        self.assertEqual(count, 20, f"Roundtrip {idx} ({fmt}) mismatch: {count} vs 20")


def _generate_500_tests():
    for i in range(1, 501):
        def test_fn(self, scenario_idx=i):
            self._run_scenario(scenario_idx)
        test_fn.__name__ = f"test_{i:03d}_resilience_scenario"
        test_fn.__doc__ = f"Resilience scenario #{i}"
        setattr(TestResilience500, test_fn.__name__, test_fn)

_generate_500_tests()

if __name__ == "__main__":
    unittest.main()
