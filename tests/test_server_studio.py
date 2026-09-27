import unittest
import threading
import http.client
import json
import time
import os
import shutil
import tempfile
from mergendb.client import MergenDB
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.server.server import ThreadingMergenServer, MergenRequestHandler

class TestServerStudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.orig_cwd = os.getcwd()
        os.chdir(cls.temp_dir)

        # Create a test table
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("name", DataType.STRING),
            ColumnDef("score", DataType.FLOAT64)
        ])
        tbl = MergenDB.create_table("studio_test.mgdb", schema)
        tbl.insert_many([
            [1, "Ada", 98.5],
            [2, "Alan", 95.0],
            [3, "Grace", 99.0],
        ])

        # Start server in background thread on dynamic port
        cls.server = ThreadingMergenServer(("127.0.0.1", 0), MergenRequestHandler)
        cls.host, cls.port = cls.server.server_address[:2]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        os.chdir(cls.orig_cwd)
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_json_root_endpoint(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request("GET", "/", headers={"Accept": "application/json"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertIn("application/json", resp.getheader("Content-Type"))
        data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(data["name"], "MergenDB Server")
        self.assertEqual(data["studio"], "/studio")
        conn.close()

    def test_studio_html_endpoint(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request("GET", "/studio")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertIn("text/html", resp.getheader("Content-Type"))
        html = resp.read().decode("utf-8")
        self.assertIn("MERGEN STUDIO", html)
        self.assertIn("queryEditor", html)
        self.assertIn("runQuery", html)
        conn.close()

    def test_browser_html_root_negotiation(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request("GET", "/", headers={"Accept": "text/html,application/xhtml+xml"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertIn("text/html", resp.getheader("Content-Type"))
        html = resp.read().decode("utf-8")
        self.assertIn("MERGEN STUDIO", html)
        conn.close()

    def test_tables_listing(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request("GET", "/tables")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertIn("tables", data)
        table_names = [t["table"] for t in data["tables"]]
        self.assertIn("studio_test.mgdb", table_names)
        conn.close()

    def test_query_post_endpoint(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        body = json.dumps({"query": "SELECT name, score FROM 'studio_test.mgdb' WHERE score >= 96;"})
        conn.request("POST", "/query", body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertEqual(data["columns"], ["name", "score"])
        self.assertEqual(len(data["rows"]), 2)  # Ada (98.5) and Grace (99.0)
        self.assertIn("stats", data)
        self.assertGreaterEqual(data["stats"]["execution_time_ms"], 0)
        conn.close()

    def test_query_post_error_handling(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        body = json.dumps({"query": "SELECT nonexistent FROM 'invalid_table.mgdb';"})
        conn.request("POST", "/query", body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 400)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertFalse(data["success"])
        self.assertIn("error", data)
        conn.close()

if __name__ == "__main__":
    unittest.main()
