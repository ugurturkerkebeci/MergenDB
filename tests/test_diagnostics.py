import unittest
import mergendb
from mergendb.testing.suite import run_diagnostics

class TestDiagnosticsAndBenchmarking(unittest.TestCase):
    def test_run_diagnostics_silent(self):
        res = run_diagnostics(verbose=False)
        self.assertTrue(res["success"])
        self.assertTrue(res["engine"]["passed"])
        self.assertTrue(res["server"]["passed"])
        self.assertGreater(res["hardware"]["ingest_rate"], 0)
        self.assertGreater(res["hardware"]["import_rate"], 0)
        self.assertGreater(res["hardware"]["export_rate"], 0)
        self.assertGreater(res["hardware"]["scan_rate"], 0)

    def test_mergendb_test_api(self):
        res = mergendb.test(verbose=False)
        self.assertTrue(res["success"])

    def test_mergendb_benchmark_api(self):
        res = mergendb.benchmark(verbose=False)
        self.assertTrue(res["success"])

if __name__ == "__main__":
    unittest.main()
