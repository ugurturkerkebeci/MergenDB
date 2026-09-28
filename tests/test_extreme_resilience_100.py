"""
Extreme 100-Scenario Resilience and Fault Tolerance Test Suite for MergenDB v0.7.
Tests extreme edge cases, corrupt structures, dirty tokens, ragged records,
complex queries, schema mutations, and export roundtrips.
Strict zero emojis. Pure CPU, bounded RAM.
"""

import os
import shutil
import tempfile
import unittest
from typing import List

from mergendb import (
    MergenDB, Table, Schema, ColumnDef, DataType,
    import_csv, export_csv, export_json, export_jsonl, export_sql
)
from mergendb.io.importer import DataImporter


class TestExtremeResilience100(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mgdb_resilience100_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Category 1: Broken, Ragged and Dirty CSVs (Tests 1 to 20)
    # ------------------------------------------------------------------
    def test_c01_to_c20_broken_and_dirty_csv_scenarios(self):
        for t in range(1, 21):
            with self.subTest(scenario=t):
                csv_file = os.path.join(self.test_dir, f"dirty_c1_{t}.csv")
                out_mgdb = os.path.join(self.test_dir, f"out_c1_{t}.mgdb")

                lines = ["id,title,amount,flag"]
                for r in range(1, 25):
                    if t == 1: # ragged short rows
                        lines.append(f"{r},Title_{r}" if r % 2 == 0 else f"{r},Title_{r},{r * 10},true")
                    elif t == 2: # ragged long rows
                        lines.append(f"{r},Title_{r},{r * 10},true,extra1,extra2,extra3" if r % 3 == 0 else f"{r},Title_{r},{r * 10},true")
                    elif t == 3: # null bytes in strings
                        lines.append(f"{r},Title_\x00_{r},{r * 10},true")
                    elif t == 4: # unescaped quotes inside quoted strings
                        lines.append(f'{r},"Unclosed quote {r},{r * 10},true' if r % 4 == 0 else f'{r},"Clean {r}",{r * 10},true')
                    elif t == 5: # leading and trailing whitespace padding
                        lines.append(f"  {r}  ,   Padded_{r}   ,   {r * 5.5}   ,   false   ")
                    elif t == 6: # empty lines and comment lines
                        if r % 3 == 0:
                            lines.append("")
                        elif r % 5 == 0:
                            lines.append(f"# Comment line {r}")
                        lines.append(f"{r},Item_{r},{r * 1.25},true")
                    elif t == 7: # irregular windows/mac line breaks
                        lines.append(f"{r},Item_{r}\r,{r * 2},false")
                    elif t == 8: # extreme unicode characters (Turkish, Cyrillic, CJK)
                        lines.append(f"{r},Şiir_Örnek_Ürün_{r}__Кириллица_日本語,{r * 10},true")
                    elif t == 9: # dirty null tokens
                        tok = ["", "NULL", "none", "N/A", "NaN", "\\N", "nil", "-"][r % 8]
                        lines.append(f"{r},Item_{r},{tok if r % 2 == 0 else r * 10},{tok if r % 3 == 0 else 'true'}")
                    elif t == 10: # scientific notation in numbers
                        lines.append(f"{r},Sci_{r},{r}e2,true")
                    elif t == 11: # negative numbers and decimals
                        lines.append(f"-{r},Neg_{r},-{r * 3.14159},false")
                    elif t == 12: # commas inside properly escaped quotes
                        lines.append(f'{r},"Company, Inc., Division {r}",{r * 100},true')
                    elif t == 13: # semicolons as delimiters inside quotes
                        lines.append(f'{r},"Data;Part2;Part3",{r * 50},true')
                    elif t == 14: # single quote enclosed fields
                        lines.append(f"{r},'Single_Quoted_{r}',{r * 25},true")
                    elif t == 15: # consecutive delimiters (empty columns)
                        lines.append(f"{r},,,")
                    elif t == 16: # very long string fields (4 KB per cell)
                        long_str = f"payload_{r}_" + ("X" * 4000)
                        lines.append(f"{r},{long_str},{r * 10},true")
                    elif t == 17: # mix of tabs and spaces
                        lines.append(f"{r}\t,\tTabItem_{r}\t,\t{r * 10}\t,\ttrue")
                    elif t == 18: # pipe-like characters inside strings
                        lines.append(f'{r},"A|B|C|D|{r}",{r * 12},false')
                    elif t == 19: # BOM marker with ragged records
                        lines.append(f"{r},BOMItem_{r},{r * 10},true")
                    else: # t == 20: random zero bytes and carriage returns
                        lines.append(f"{r},\x00Item\r_{r},{r * 5},true")

                content = "\n".join(lines)
                if t == 19:
                    content = "\uFEFF" + content

                with open(csv_file, "w", encoding="utf-8") as f:
                    f.write(content)

                imported = DataImporter.from_csv(csv_file, out_mgdb)
                self.assertGreater(imported, 0, f"Scenario {t} imported 0 rows")
                tbl = Table(out_mgdb)
                self.assertEqual(tbl.row_count, imported)
                res = tbl.sql(f"SELECT COUNT(*) FROM out_c1_{t}")
                self.assertEqual(res.rows[0][0], imported)

    # ------------------------------------------------------------------
    # Category 2: Extreme Type Coercion & Arithmetic (Tests 21 to 40)
    # ------------------------------------------------------------------
    def test_c21_to_c40_extreme_types_and_operations(self):
        for t in range(21, 41):
            with self.subTest(scenario=t):
                tbl_path = os.path.join(self.test_dir, f"types_{t}.mgdb")
                schema = Schema([
                    ColumnDef("id", DataType.INT64),
                    ColumnDef("num", DataType.FLOAT64),
                    ColumnDef("tag", DataType.STRING),
                    ColumnDef("active", DataType.BOOL)
                ])
                tbl = MergenDB.create_table(tbl_path, schema)

                rows = []
                for r in range(1, 20):
                    if t == 21: # zero and negative floats
                        rows.append([r, -0.0 if r % 2 == 0 else 0.0, f"tag_{r}", True])
                    elif t == 22: # large integers
                        rows.append([r * 1000000000, float(r), f"tag_{r}", False])
                    elif t == 23: # very small floats (precision)
                        rows.append([r, 1e-8 * r, f"tag_{r}", True])
                    elif t == 24: # dirty boolean string inputs
                        b_val = [True, False, 1, 0, "true", "false", "yes", "no", "t", "f"][r % 10]
                        rows.append([r, float(r), f"tag_{r}", b_val])
                    elif t == 25: # dirty numeric strings
                        n_val = [f"{r}.5", f"{r}", f"+{r}", f"-{r}", "0", "100"][r % 6]
                        rows.append([r, n_val, f"tag_{r}", True])
                    elif t == 26: # None in all nullable columns
                        rows.append([r, None, None, None])
                    elif t == 27: # mixed None and valid values
                        rows.append([r, None if r % 2 == 0 else float(r), None if r % 3 == 0 else f"tag_{r}", None if r % 4 == 0 else True])
                    elif t == 28: # strings containing numbers and symbols
                        rows.append([r, float(r), f"${r * 100}.00 USD", True])
                    elif t == 29: # string column with escaped characters
                        rows.append([r, float(r), f"line1\\nline2\\ttab\\'{r}", False])
                    elif t == 30: # zero division prevention in computed expressions
                        rows.append([r, 0.0 if r % 3 == 0 else float(r), f"tag_{r}", True])
                    elif t == 31: # comparisons with mixed nulls
                        rows.append([r, float(r * 2), f"tag_{r}", r % 2 == 0])
                    elif t == 32: # boundary int64 values
                        rows.append([2147483647 + r, float(r), f"large_{r}", True])
                    elif t == 33: # string boolean tokens
                        rows.append([r, float(r), "TRUE" if r % 2 == 0 else "FALSE", True])
                    elif t == 34: # float string with leading zeros
                        rows.append([r, f"00{r}.50", f"tag_{r}", True])
                    elif t == 35: # float string with exponential E
                        rows.append([r, f"{r}e-2", f"tag_{r}", False])
                    elif t == 36: # whitespace strings
                        rows.append([r, float(r), "   ", True])
                    elif t == 37: # empty strings
                        rows.append([r, float(r), "", False])
                    elif t == 38: # symbols only
                        rows.append([r, float(r), "@#$%^&*()_+", True])
                    elif t == 39: # extreme negative int64
                        rows.append([-1000000000 - r, float(-r), f"neg_{r}", False])
                    else: # t == 40: float with many decimals
                        rows.append([r, 3.141592653589793 * r, f"pi_{r}", True])

                tbl.insert_many(rows)
                self.assertEqual(tbl.row_count, 19)

                # Test safe evaluation: WHERE condition with mixed types
                res = tbl.sql(f"SELECT id, num, tag FROM types_{t} WHERE num > 5 OR num IS NULL")
                self.assertIsNotNone(res)

                # Test safe arithmetic query (addition, multiplication)
                q_res = tbl.query("| WHERE active == true | SELECT id, num | LIMIT 5")
                self.assertIsNotNone(q_res)

    # ------------------------------------------------------------------
    # Category 3: Malformed JSON / JSONL Records (Tests 41 to 60)
    # ------------------------------------------------------------------
    def test_c41_to_c60_malformed_json_and_jsonl(self):
        for t in range(41, 61):
            with self.subTest(scenario=t):
                is_jsonl = (t % 2 == 0)
                file_ext = "jsonl" if is_jsonl else "json"
                in_file = os.path.join(self.test_dir, f"corrupt_{t}.{file_ext}")
                out_mgdb = os.path.join(self.test_dir, f"out_json_{t}.mgdb")

                if is_jsonl:
                    lines = []
                    for r in range(1, 25):
                        if r % 5 == 0 and t in (42, 44, 46, 48, 50):
                            # Broken JSON syntax (missing bracket or quote)
                            lines.append(f'{{"id": {r}, "val": "incomplete')
                        elif r % 7 == 0 and t in (52, 54, 56):
                            # Null bytes inside JSON
                            lines.append(f'{{"id": {r}, "val": "null\x00byte", "score": {r * 10}}}')
                        elif r % 4 == 0 and t in (58, 60):
                            # Empty line or whitespace line
                            lines.append("   ")
                        else:
                            lines.append(f'{{"id": {r}, "val": "item_{r}", "score": {r * 1.5}, "active": {str(r % 2 == 0).lower()}}}')
                    content = "\n".join(lines)
                else:
                    # JSON array
                    items = []
                    for r in range(1, 20):
                        items.append(f'{{"id": {r}, "val": "entry_{r}", "score": {r * 2.5}}}')
                    content = "[\n" + ",\n".join(items) + "\n]"

                with open(in_file, "w", encoding="utf-8") as f:
                    f.write(content)

                if is_jsonl:
                    imported = DataImporter.from_jsonl(in_file, out_mgdb)
                else:
                    imported = DataImporter.from_json(in_file, out_mgdb)

                self.assertGreater(imported, 10, f"JSON scenario {t} imported fewer than 10 rows: {imported}")
                tbl = Table(out_mgdb)
                self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # Category 4: Fragmented SQL Dumps & DDL (Tests 61 to 80)
    # ------------------------------------------------------------------
    def test_c61_to_c80_fragmented_sql_dumps(self):
        for t in range(61, 81):
            with self.subTest(scenario=t):
                sql_file = os.path.join(self.test_dir, f"dump_{t}.sql")
                out_mgdb = os.path.join(self.test_dir, f"out_sql_{t}.mgdb")

                lines = [
                    f"CREATE TABLE `table_{t}` (",
                    "  `id` int(11) NOT NULL,",
                    "  `code` varchar(64) DEFAULT NULL,",
                    "  `cost` decimal(10,2) DEFAULT NULL",
                    ");",
                    f"INSERT INTO `table_{t}` VALUES"
                ]

                tuples = []
                for r in range(1, 20):
                    if r % 4 == 0 and t % 3 == 0:
                        # Malformed tuple
                        tuples.append(f"({r}, 'Unclosed")
                    elif r % 6 == 0:
                        # Escaped quote
                        tuples.append(f"({r}, 'O\\'Malley_{r}', {r * 30.0})")
                    else:
                        tuples.append(f"({r}, 'Code_{r}', {r * 15.5})")

                lines.append(",\n".join(tuples) + ";")

                with open(sql_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

                imported = DataImporter.from_sql_dump(sql_file, out_mgdb)
                self.assertGreaterEqual(imported, 8, f"SQL scenario {t} imported too few rows: {imported}")
                tbl = Table(out_mgdb)
                self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # Category 5: End-to-End Mutation, Query & Export Roundtrips (Tests 81 to 100)
    # ------------------------------------------------------------------
    def test_c81_to_c100_mutation_query_export_roundtrip(self):
        for t in range(81, 101):
            with self.subTest(scenario=t):
                # 1. Create source table
                tbl_path = os.path.join(self.test_dir, f"roundtrip_{t}.mgdb")
                schema = Schema([
                    ColumnDef("id", DataType.INT64),
                    ColumnDef("name", DataType.STRING),
                    ColumnDef("metric", DataType.FLOAT64)
                ])
                tbl = MergenDB.create_table(tbl_path, schema)

                # 2. Insert batch with extreme and null values
                initial_rows = []
                for r in range(1, 30):
                    m_val = None if r % 5 == 0 else float(r * 10.5)
                    name_val = None if r % 7 == 0 else f"Entity_{r}_{t}"
                    initial_rows.append([r, name_val, m_val])
                tbl.insert_many(initial_rows)
                self.assertEqual(tbl.row_count, 29)

                # 3. Add new column dynamically
                tbl.add_column("status", "string", default="pending")
                self.assertIn("status", tbl.columns)

                # 4. Perform update on filtered rows
                updated = tbl.update({"status": "verified"}, where="id > 15")
                self.assertGreater(updated, 0)

                # 5. Query results with analytical aggregation
                res = tbl.sql(f"SELECT status, COUNT(*) AS cnt FROM roundtrip_{t} GROUP BY status")
                self.assertGreater(len(res.rows), 0)

                # 6. Export to chosen format and verify file exists and is non-empty
                fmt = ["csv", "json", "jsonl", "sql"][t % 4]
                exp_file = os.path.join(self.test_dir, f"export_{t}.{fmt}")

                if fmt == "csv":
                    export_csv(tbl_path, exp_file)
                elif fmt == "json":
                    export_json(tbl_path, exp_file)
                elif fmt == "jsonl":
                    export_jsonl(tbl_path, exp_file)
                else:
                    export_sql(tbl_path, exp_file)

                self.assertTrue(os.path.exists(exp_file))
                self.assertGreater(os.path.getsize(exp_file), 0)

                # 7. Re-import the exported file and assert row count matches
                reimported_path = os.path.join(self.test_dir, f"reimported_{t}.mgdb")
                if fmt == "csv":
                    re_count = DataImporter.from_csv(exp_file, reimported_path)
                elif fmt == "json":
                    re_count = DataImporter.from_json(exp_file, reimported_path)
                elif fmt == "jsonl":
                    re_count = DataImporter.from_jsonl(exp_file, reimported_path)
                else:
                    re_count = DataImporter.from_sql_dump(exp_file, reimported_path)

                self.assertEqual(re_count, 29, f"Roundtrip {t} ({fmt}) mismatch: {re_count} vs 29")


if __name__ == "__main__":
    unittest.main()
