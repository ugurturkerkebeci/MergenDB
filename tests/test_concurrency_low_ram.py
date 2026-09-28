"""
Test concurrent multi-threaded read/write workloads and verify low RAM consumption.
Designed for low-resource environments (e.g., 500 MB RAM VPS, headless, zero GPU).
"""
import os
import shutil
import tempfile
import threading
import time
import tracemalloc
import unittest
from typing import List

from mergendb import MergenDB, Table, Schema, ColumnDef, DataType


class TestConcurrencyLowRam(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mgdb_concurr_")
        self.table_path = os.path.join(self.test_dir, "test_concurrent.mgdb")
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("worker_id", DataType.INT64),
            ColumnDef("payload", DataType.STRING),
            ColumnDef("score", DataType.FLOAT64),
        ])
        MergenDB.create_table(self.table_path, schema, block_size=1024)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_concurrent_readers_and_writers(self):
        """
        Runs multiple concurrent reader threads and multiple concurrent writer threads
        against a single table file. Verifies:
        1. No deadlocks or thread crashes.
        2. Data integrity preserved.
        3. Peak memory is strictly bounded (< 30 MB) via tracemalloc.
        """
        tracemalloc.start()
        tbl = Table(self.table_path)

        # Initial seed rows
        seed_rows = [[i, 0, f"seed_{i}", float(i * 1.5)] for i in range(100)]
        tbl.insert_many(seed_rows)

        num_writers = 3
        rows_per_writer = 150
        num_readers = 6
        reads_per_reader = 30

        writer_errors: List[Exception] = []
        reader_errors: List[Exception] = []

        def writer_task(wid: int):
            try:
                for chunk_idx in range(5):
                    batch = []
                    for r in range(rows_per_writer // 5):
                        rid = 1000 + (wid * 1000) + (chunk_idx * 30) + r
                        batch.append([rid, wid, f"item_{wid}_{chunk_idx}_{r}", float(rid * 0.1)])
                    tbl.insert_many(batch)
                    time.sleep(0.005)
            except Exception as e:
                writer_errors.append(e)

        def reader_task(rid: int):
            try:
                for _ in range(reads_per_reader):
                    # Test count and scan
                    total = tbl.count()
                    self.assertGreaterEqual(total, 100)
                    # Test MergenQL read query
                    res = tbl.query("| WHERE score >= 0 | SELECT id, score | LIMIT 10")
                    self.assertLessEqual(len(res.rows), 10)
                    time.sleep(0.003)
            except Exception as e:
                reader_errors.append(e)

        threads = []
        for i in range(num_writers):
            t = threading.Thread(target=writer_task, args=(i + 1,))
            threads.append(t)

        for i in range(num_readers):
            t = threading.Thread(target=reader_task, args=(i + 1,))
            threads.append(t)

        start_time = time.time()
        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=30.0)
            self.assertFalse(t.is_alive(), "A concurrent thread timed out or deadlocked")

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Check for errors in worker threads
        if writer_errors:
            self.fail(f"Writer threads encountered errors: {writer_errors}")
        if reader_errors:
            self.fail(f"Reader threads encountered errors: {reader_errors}")

        expected_total = 100 + (num_writers * rows_per_writer)
        final_count = tbl.count()
        self.assertEqual(final_count, expected_total, f"Expected {expected_total} rows, found {final_count}")

        # Peak memory in MB
        peak_mb = peak_mem / (1024 * 1024)
        # Should stay well under 30 MB (safe for 500 MB RAM VPS)
        self.assertLess(peak_mb, 30.0, f"Peak memory was {peak_mb:.2f} MB, exceeding 30 MB threshold")


if __name__ == "__main__":
    unittest.main()
