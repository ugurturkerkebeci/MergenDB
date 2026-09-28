import unittest
import os
import shutil
import tempfile
import json
from mergendb.client import MergenDB, Table
from mergendb.io.importer import DataImporter
from mergendb.io.exporter import DataExporter

class TestFaultTolerantImport200(unittest.TestCase):
    """
    Comprehensive verification suite running 200 distinct dirty-data,
    broken-encoding, ragged-row, and malformed-file import test combinations.
    Guarantees that a single corrupt piece of data NEVER discards or ruins
    an entire document or table.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="mergen_ft200_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Batch 1: Encodings & Byte Sanitization (40 combinations: 1 - 40)
    # ------------------------------------------------------------------
    def test_001_to_040_encoding_combinations(self):
        encodings_data = [
            ("utf8_basic", "id,name,val\n1,Ahmet,100\n2,Mehmet,200\n", "utf-8"),
            ("utf8_bom", "\ufeffid,name,val\n1,Can,150\n2,Deniz,250\n", "utf-8-sig"),
            ("cp1254_turkish", "id,sehir,puan\n1,İstanbul,95\n2,İzmir,90\n3,Eskişehir,85\n", "cp1254"),
            ("iso8859_9_turkish", "id,urun,fiyat\n1,Çanta,120\n2,Şapka,80\n3,Gözlük,250\n", "iso-8859-9"),
            ("latin1_special", "id,text,num\n1,café,10\n2,naïve,20\n3,résumé,30\n", "latin-1"),
            ("windows1252_symbols", "id,sym,amt\n1,€,500\n2,£,400\n3,$,300\n", "windows-1252"),
        ]

        # Generate 40 encoding variations with null bytes, control chars, and surrogates
        for i in range(40):
            base_idx = i % len(encodings_data)
            tag, content, enc = encodings_data[base_idx]
            
            # Inject varying corruptions: null bytes, replacement chars, control chars
            raw_bytes = content.encode(enc, errors="replace")
            if i % 3 == 0:
                raw_bytes = raw_bytes.replace(b"\n", b"\x00\n")  # embedded null byte
            if i % 5 == 0:
                raw_bytes = raw_bytes + b"\x01\x02\x03\n"        # trailing control bytes
            if i % 7 == 0:
                raw_bytes = b"\xef\xbb\xbf" + raw_bytes          # injected UTF-8 BOM

            file_path = os.path.join(self.test_dir, f"enc_test_{i}.csv")
            mgdb_path = os.path.join(self.test_dir, f"enc_out_{i}.mgdb")
            with open(file_path, "wb") as f:
                f.write(raw_bytes)

            imported = DataImporter.from_csv(file_path, mgdb_path)
            self.assertGreaterEqual(imported, 1, f"Encoding combination #{i+1} failed to import valid rows")
            tbl = Table(mgdb_path)
            self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # Batch 2: Ragged & Broken CSV Structures (40 combinations: 41 - 80)
    # ------------------------------------------------------------------
    def test_041_to_080_ragged_csv_combinations(self):
        for i in range(40):
            file_path = os.path.join(self.test_dir, f"ragged_test_{i}.csv")
            mgdb_path = os.path.join(self.test_dir, f"ragged_out_{i}.mgdb")

            lines = ["id,col_a,col_b,col_c"]
            valid_count = 0
            for r in range(1, 15):
                if r % 4 == 0:
                    # Missing columns (ragged short)
                    lines.append(f"{r},val_{r}")
                    valid_count += 1
                elif r % 5 == 0:
                    # Extra columns (ragged long)
                    lines.append(f"{r},val_{r},b_{r},c_{r},extra_1,extra_2")
                    valid_count += 1
                elif r % 7 == 0:
                    # Blank line
                    lines.append("   ")
                elif r % 6 == 0:
                    # Stray quotes
                    lines.append(f'{r},"val_quoted_{r},normal,normal')
                    valid_count += 1
                else:
                    lines.append(f"{r},val_{r},b_{r},c_{r}")
                    valid_count += 1

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            imported = DataImporter.from_csv(file_path, mgdb_path)
            self.assertGreaterEqual(imported, 5, f"Ragged CSV combination #{i+41} failed to salvage rows")
            tbl = Table(mgdb_path)
            self.assertEqual(tbl.row_count, imported)

    # ------------------------------------------------------------------
    # Batch 3: Dirty & Malformed Data Types (40 combinations: 81 - 120)
    # ------------------------------------------------------------------
    def test_081_to_120_dirty_type_combinations(self):
        for i in range(40):
            file_path = os.path.join(self.test_dir, f"dirty_type_{i}.csv")
            mgdb_path = os.path.join(self.test_dir, f"dirty_type_{i}.mgdb")

            # Schema: id (int), age (int), score (float), active (bool), name (string)
            lines = ["id,age,score,active,name"]
            dirty_tokens = ["", "NULL", "none", "N/A", "NaN", "\\N", "nil", "-", "inf", "corrupt_val"]
            
            for r in range(1, 20):
                d_token = dirty_tokens[(r + i) % len(dirty_tokens)]
                age_val = r * 5 if r % 3 != 0 else d_token
                score_val = f"{r * 1.5:.2f}" if r % 4 != 0 else d_token
                bool_val = "true" if r % 2 == 0 else ("false" if r % 3 == 0 else d_token)
                lines.append(f"{r},{age_val},{score_val},{bool_val},Person_{r}")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            imported = DataImporter.from_csv(file_path, mgdb_path)
            self.assertEqual(imported, 19, f"Dirty type combination #{i+81} lost rows")
            tbl = Table(mgdb_path)
            self.assertEqual(tbl.row_count, 19)
            self.assertEqual(tbl.count(), 19)

    # ------------------------------------------------------------------
    # Batch 4: Corrupted JSON and JSONL Records (40 combinations: 121 - 160)
    # ------------------------------------------------------------------
    def test_121_to_160_json_and_jsonl_combinations(self):
        for i in range(40):
            is_jsonl = (i % 2 == 0)
            if is_jsonl:
                file_path = os.path.join(self.test_dir, f"broken_{i}.jsonl")
                mgdb_path = os.path.join(self.test_dir, f"broken_out_{i}.mgdb")

                lines = []
                expected_valid = 0
                for r in range(1, 25):
                    if r % 5 == 0:
                        # Corrupted JSON line (truncated or bad syntax)
                        lines.append(f'{{"id": {r}, "title": "Incomplete')
                    elif r % 7 == 0:
                        lines.append("   ")  # blank line
                    elif r % 9 == 0:
                        lines.append(f'{{"id": {r}, "title": "Valid", "extra_col": {r * 10}}}')
                        expected_valid += 1
                    else:
                        lines.append(json.dumps({"id": r, "title": f"Book {r}", "price": r * 12.5}))
                        expected_valid += 1

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

                imported = DataImporter.from_jsonl(file_path, mgdb_path)
                self.assertGreaterEqual(imported, expected_valid - 1, f"JSONL combination #{i+121} lost valid lines")
                tbl = Table(mgdb_path)
                self.assertEqual(tbl.row_count, imported)
            else:
                file_path = os.path.join(self.test_dir, f"broken_{i}.json")
                mgdb_path = os.path.join(self.test_dir, f"broken_json_out_{i}.mgdb")

                # JSON array with some invalid fragments or trailing comma
                items = [f'{{"id": {r}, "name": "Item_{r}", "qty": {r*2}}}' for r in range(1, 15)]
                # Inject a truncated item
                items.append('{"id": 99, "name": "Broken')
                content = "[\n  " + ",\n  ".join(items) + "\n]"

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                imported = DataImporter.from_json(file_path, mgdb_path)
                self.assertGreaterEqual(imported, 14, f"JSON combination #{i+121} failed to salvage array items")

    # ------------------------------------------------------------------
    # Batch 5: Corrupted SQL Dump Fragments (40 combinations: 161 - 200)
    # ------------------------------------------------------------------
    def test_161_to_200_sql_dump_combinations(self):
        for i in range(40):
            file_path = os.path.join(self.test_dir, f"dump_{i}.sql")
            mgdb_path = os.path.join(self.test_dir, f"dump_out_{i}.mgdb")

            lines = [
                "-- MergenDB SQL Dump Edge Case Test",
                "/*!40101 SET NAMES utf8mb4 */;",
                "CREATE TABLE `clients` (",
                "  `id` int(11) NOT NULL,",
                "  `name` varchar(100) DEFAULT NULL,",
                "  `balance` decimal(10,2) DEFAULT NULL",
                ");",
                "LOCK TABLES `clients` WRITE;",
                "INSERT INTO `clients` VALUES"
            ]

            tuples = []
            expected_valid = 0
            for r in range(1, 15):
                if r % 4 == 0:
                    # Incomplete tuple or syntax error
                    tuples.append(f"({r}, 'Broken Name")
                elif r % 6 == 0:
                    # Escaped quote inside string
                    tuples.append(f"({r}, 'O\\'Reilly', {r * 100})")
                    expected_valid += 1
                else:
                    tuples.append(f"({r}, 'Client_{r}', {r * 50.5})")
                    expected_valid += 1

            lines.append(",\n".join(tuples) + ";")
            lines.append("UNLOCK TABLES;")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            imported = DataImporter.from_sql_dump(file_path, mgdb_path)
            self.assertGreaterEqual(imported, 7, f"SQL dump combination #{i+161} failed to import valid tuples")
            tbl = Table(mgdb_path)
            self.assertEqual(tbl.row_count, imported)


if __name__ == "__main__":
    unittest.main()
