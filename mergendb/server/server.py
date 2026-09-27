import http.server
import socketserver
import json
import os
import time
import sys
import glob
from typing import Optional
from mergendb.client import MergenDB
from mergendb.storage.reader import FileReader

class MergenRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    High-performance, zero-dependency REST & Query API handler for MergenDB server.
    """

    def _send_response_json(self, status_code: int, data: dict):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path in ("", "/"):
            from mergendb import __version__
            self._send_response_json(200, {
                "name": "MergenDB Server",
                "version": __version__,
                "status": "online",
                "engine": "Lightning Columnar Engine",
                "docs": "/help"
            })
            return

        elif path == "/status" or path == "/health":
            files = glob.glob("*.mgdb")
            total_size = sum(os.path.getsize(f) for f in files)
            self._send_response_json(200, {
                "status": "healthy",
                "tables_count": len(files),
                "total_disk_bytes": total_size,
                "server_time": int(time.time()),
                "pid": os.getpid()
            })
            return

        elif path == "/tables":
            files = glob.glob("*.mgdb")
            tables = []
            for f in files:
                try:
                    sz = os.path.getsize(f)
                    with FileReader(f) as reader:
                        tables.append({
                            "table": f,
                            "rows": reader.total_rows,
                            "blocks": len(reader.blocks),
                            "bytes": sz,
                            "columns": [c.name for c in reader.schema.columns]
                        })
                except Exception:
                    pass
            self._send_response_json(200, {"tables": tables})
            return

        elif path == "/help":
            self._send_response_json(200, {
                "endpoints": {
                    "POST /query": "Execute MergenQL or SQL query. Body: {'query': '...'}",
                    "GET /tables": "List all tables with schema and size",
                    "GET /status": "Engine health and statistics",
                }
            })
            return

        else:
            self._send_response_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")

        if path == "/query":
            try:
                payload = json.loads(post_data) if post_data else {}
                query_text = payload.get("query", "").strip()
                if not query_text:
                    self._send_response_json(400, {"error": "Missing 'query' in request body"})
                    return

                t0 = time.perf_counter()
                result = MergenDB.query(query_text)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                response = {
                    "success": True,
                    "columns": result.column_names,
                    "rows": result.rows,
                    "stats": {
                        "execution_time_ms": round(elapsed_ms, 2),
                        "rows_returned": len(result.rows),
                        "blocks_scanned": result.stats.blocks_scanned if result.stats else 0,
                        "blocks_skipped": result.stats.blocks_skipped if result.stats else 0,
                        "bytes_read": result.stats.bytes_read if result.stats else 0
                    }
                }
                self._send_response_json(200, response)

            except Exception as e:
                self._send_response_json(400, {"success": False, "error": str(e)})
            return

        else:
            self._send_response_json(404, {"error": "Endpoint not found"})

    def log_message(self, format, *args):
        # Clean custom server logging
        sys.stdout.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

class ThreadingMergenServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port

def start_server(host: str = "0.0.0.0", port: int = 8765, data_dir: Optional[str] = None):
    if data_dir:
        os.chdir(data_dir)

    server = ThreadingMergenServer((host, port), MergenRequestHandler)
    print("=" * 70)
    print("   🏹 MERGENDB SERVER (MergenQL & SQL Network Engine)")
    print("=" * 70)
    print(f"  * Status        : RUNNING")
    print(f"  * Listening on  : http://{host}:{port}")
    print(f"  * Local Web API : http://localhost:{port}")
    print(f"  * Query Endpoint: POST http://localhost:{port}/query")
    print(f"  * Working Dir   : {os.getcwd()}")
    print("=" * 70)
    print(" Press Ctrl+C to stop the server.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMergenDB Server shutting down gracefully...")
        server.shutdown()
        server.server_close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MergenDB High-Performance Network Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    parser.add_argument("--dir", default=None, help="Directory containing .mgdb database files")
    args = parser.parse_args()
    start_server(host=args.host, port=args.port, data_dir=args.dir)

if __name__ == "__main__":
    main()
