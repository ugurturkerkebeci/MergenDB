import os
import shutil
import unittest
import tempfile
import mergendb
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType

class TestHierarchy(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_and_subtable_lifecycle(self):
        # 1. Create a database "okul"
        db = mergendb.create_database("okul")
        self.assertEqual(db.name, "okul")
        self.assertTrue(os.path.exists("okul"))

        # 2. Create tables inside "okul": "ogretmenler" and "ogrenciler"
        teacher_schema = Schema([
            ColumnDef("id", DataType.INT32),
            ColumnDef("name", DataType.STRING),
            ColumnDef("brans", DataType.STRING)
        ])
        teachers = db.create_table("ogretmenler", teacher_schema)
        teachers.insert([
            {"id": 1, "name": "Ahmet Hoca", "brans": "Matematik"},
            {"id": 2, "name": "Fatma Hoca", "brans": "Fizik"}
        ])
        self.assertEqual(teachers.count(), 2)

        student_schema = Schema([
            ColumnDef("id", DataType.INT32),
            ColumnDef("student_name", DataType.STRING),
            ColumnDef("overall_score", DataType.FLOAT64)
        ])
        students = db.create_table("ogrenciler", student_schema)

        # 3. Direct values can be inserted into the main "ogrenciler" table
        students.insert([
            {"id": 101, "student_name": "Mert Yilmaz", "overall_score": 85.5},
            {"id": 102, "student_name": "Selin Demir", "overall_score": 92.0}
        ])
        self.assertEqual(students.count(), 2)

        # 4. Create nested sub-tables under "ogrenciler": "a_sinifi" and "b_sinifi"
        class_schema = Schema([
            ColumnDef("id", DataType.INT32),
            ColumnDef("student_name", DataType.STRING),
            ColumnDef("term_grade", DataType.INT32)
        ])
        class_a = students.create_subtable("a_sinifi", class_schema)
        class_b = students.create_subtable("b_sinifi", class_schema)

        # Verify on-disk paths
        self.assertTrue(os.path.exists(os.path.join("okul", "ogretmenler.mgdb")))
        self.assertTrue(os.path.exists(os.path.join("okul", "ogrenciler.mgdb")))
        self.assertTrue(os.path.exists(os.path.join("okul", "ogrenciler", "a_sinifi.mgdb")))
        self.assertTrue(os.path.exists(os.path.join("okul", "ogrenciler", "b_sinifi.mgdb")))

        # 5. Insert records into sub-tables
        class_a.insert([
            {"id": 201, "student_name": "Ali Veli", "term_grade": 95},
            {"id": 202, "student_name": "Ayse Kara", "term_grade": 98}
        ])
        class_b.insert([
            {"id": 203, "student_name": "Mehmet Can", "term_grade": 88}
        ])

        self.assertEqual(class_a.count(), 2)
        self.assertEqual(class_b.count(), 1)
        # Main table remains isolated with its own count
        self.assertEqual(students.count(), 2)

        # 6. Test subtable indexing via db["ogrenciler"]["a_sinifi"]
        self.assertEqual(db["ogrenciler"]["a_sinifi"].count(), 2)
        self.assertEqual(db["ogrenciler"].subtables(), ["a_sinifi", "b_sinifi"])

        # 7. Test listing tables in database
        tbl_names = db.tables()
        self.assertIn("ogretmenler", tbl_names)
        self.assertIn("ogrenciler", tbl_names)
        self.assertIn("ogrenciler.a_sinifi", tbl_names)
        self.assertIn("ogrenciler.b_sinifi", tbl_names)

        # 8. Test SQL queries across database and subtables
        res1 = db.sql("SELECT student_name, term_grade FROM ogrenciler.a_sinifi WHERE term_grade > 96")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0][0], "Ayse Kara")

        res2 = db.sql("SELECT student_name, term_grade FROM okul.ogrenciler.b_sinifi")
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0][0], "Mehmet Can")

        res_main = db.sql("SELECT student_name FROM ogrenciler")
        self.assertEqual(len(res_main), 2)

        # 9. Test SHOW DATABASES and SHOW TABLES
        dbs_res = mergendb.sql("SHOW DATABASES;")
        db_list = [r[0] for r in dbs_res]
        self.assertIn("okul", db_list)

        tbls_res = mergendb.sql("SHOW TABLES FROM okul;")
        tbl_names_sql = [r[0] for r in tbls_res]
        self.assertIn("ogretmenler", tbl_names_sql)
        self.assertIn("ogrenciler.a_sinifi", tbl_names_sql)

        # 10. Drop subtable
        db.drop_table("ogrenciler.b_sinifi")
        self.assertFalse(os.path.exists(os.path.join("okul", "ogrenciler", "b_sinifi.mgdb")))
        self.assertTrue(os.path.exists(os.path.join("okul", "ogrenciler", "a_sinifi.mgdb")))

        # 11. Drop database
        db.drop()
        self.assertFalse(os.path.exists("okul"))

if __name__ == "__main__":
    unittest.main()
