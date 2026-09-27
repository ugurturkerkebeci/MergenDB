import os
import unittest
import tempfile
import shutil
import mergendb
from mergendb import Schema, ColumnDef, DataType
from mergendb.storage.reader import FileReader

class TestParallelScan(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tbl_path = os.path.join(self.temp_dir, "multi_block.mgdb")

        # Create schema
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("dept", DataType.STRING),
            ColumnDef("salary", DataType.INT64),
            ColumnDef("active", DataType.BOOL)
        ])

        # Write 2,000 rows with block_size=100 -> exactly 20 blocks
        table = mergendb.create_table(self.tbl_path, schema, block_size=100)
        rows = []
        for i in range(2000):
            dept = "Engineering" if i % 3 == 0 else ("Sales" if i % 3 == 1 else "Support")
            rows.append({
                "id": i,
                "dept": dept,
                "salary": 30000 + (i * 10),
                "active": (i % 2 == 0)
            })
        table.insert(rows, block_size=100)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sequential_vs_parallel_scan_parity(self):
        with FileReader(self.tbl_path) as reader:
            self.assertEqual(len(reader.blocks), 20)

            # 1. Sequential scan
            seq_rows = []
            for batch, stats in reader.scan(parallel=False):
                for row in zip(*(batch.columns[c] for c in ["id", "dept", "salary", "active"])):
                    seq_rows.append(row)

            # 2. Parallel multi-threaded scan
            par_rows = []
            for batch, stats in reader.scan(parallel=True, max_workers=4):
                for row in zip(*(batch.columns[c] for c in ["id", "dept", "salary", "active"])):
                    par_rows.append(row)

            self.assertEqual(len(seq_rows), 2000)
            self.assertEqual(len(par_rows), 2000)
            self.assertEqual(seq_rows, par_rows, "Parallel scan must preserve exact block and row ordering")

    def test_parallel_scan_with_filters(self):
        # Query with WHERE filter across 20 blocks using MergenDB query
        res_seq = mergendb.query(f'FROM "{self.tbl_path}" | WHERE dept = "Engineering" AND salary > 40000 | SELECT id, dept, salary')
        res_all = mergendb.query(f'FROM "{self.tbl_path}" | WHERE salary < 31000 | SELECT id, dept')

        self.assertTrue(len(res_seq.rows) > 0)
        for r in res_seq.rows:
            self.assertEqual(r[1], "Engineering")
            self.assertGreater(r[2], 40000)

        self.assertEqual(len(res_all.rows), 100) # 0 to 99 have salary < 31000

    def test_parallel_scan_zonemap_pruning(self):
        # Filter that matches only 1 block: id >= 1900
        with FileReader(self.tbl_path) as reader:
            matching_rows = 0
            scanned_blocks = 0
            for batch, stats in reader.scan(
                columns=["id"],
                predicates=[("id", ">=", 1900)],
                parallel=True,
                max_workers=4
            ):
                matching_rows += batch.row_count
                scanned_blocks = stats.blocks_scanned

            self.assertGreater(stats.blocks_skipped, 15, "ZoneMap must prune majority of blocks in parallel scan")

if __name__ == "__main__":
    unittest.main()
