import http.server
import socketserver
import json
import os
import time
import sys
import glob
import urllib.parse
import csv
import io
import tempfile
import re
from typing import Optional, List, Dict, Any

from mergendb.client import MergenDB, Table
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.reader import FileReader
from mergendb.io.importer import DataImporter

class MergenRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    High-performance, zero-dependency REST, Studio Web UI, & Query API handler for MergenDB server.
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

    def _send_response_html(self, status_code: int, html: str):
        body = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_response_download(self, filename: str, content: bytes, mime_type: str):
        self.send_response(200)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = urllib.parse.parse_qs(parsed.query)
        accept = self.headers.get("Accept", "")

        if path in ("", "/"):
            if "text/html" in accept:
                from mergendb.server.studio_ui import STUDIO_HTML
                self._send_response_html(200, STUDIO_HTML)
                return

            from mergendb import __version__
            self._send_response_json(200, {
                "name": "MergenDB Server",
                "version": __version__,
                "status": "online",
                "engine": "Lightning Columnar Engine",
                "studio": "/studio",
                "docs": "/help"
            })
            return

        elif path == "/studio":
            from mergendb.server.studio_ui import STUDIO_HTML
            self._send_response_html(200, STUDIO_HTML)
            return

        elif path == "/status" or path == "/health":
            files = glob.glob("*.mgdb")
            total_size = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
            from mergendb import __version__
            from mergendb.testing.suite import _detect_os_name, _detect_cpu_model, _detect_total_ram_gb
            self._send_response_json(200, {
                "status": "healthy",
                "server": "MergenDB",
                "version": __version__,
                "engine_version": __version__,
                "tables_count": len(files),
                "total_disk_bytes": total_size,
                "server_time": int(time.time()),
                "pid": os.getpid(),
                "working_dir": os.getcwd(),
                "os": _detect_os_name(),
                "cpu": _detect_cpu_model(),
                "ram_gb": _detect_total_ram_gb(),
            })
            return

        elif path == "/tables":
            files = glob.glob("*.mgdb")
            tables = []
            for f in files:
                try:
                    sz = os.path.getsize(f)
                    with FileReader(f) as reader:
                        cols = []
                        for c in reader.schema.columns:
                            cols.append({
                                "name": c.name,
                                "type": c.data_type.name,
                                "nullable": getattr(c, "nullable", True)
                            })
                        tables.append({
                            "table": f,
                            "rows": reader.total_rows,
                            "blocks": len(reader.blocks),
                            "bytes": sz,
                            "columns": [c.name for c in reader.schema.columns],
                            "schema": cols
                        })
                except Exception:
                    pass
            self._send_response_json(200, {"tables": tables})
            return

        elif path == "/table_schema":
            table_name = params.get("table", [""])[0]
            if not table_name or not os.path.exists(table_name):
                self._send_response_json(404, {"error": f"Table '{table_name}' not found"})
                return

            try:
                sz = os.path.getsize(table_name)
                with FileReader(table_name) as reader:
                    cols = []
                    for c in reader.schema.columns:
                        cols.append({
                            "name": c.name,
                            "type": c.data_type.name,
                            "nullable": getattr(c, "nullable", True)
                        })
                    block_info = []
                    for i, blk in enumerate(reader.blocks):
                        total_comp = sum(c.compressed_bytes for c in blk.columns.values())
                        block_info.append({
                            "block_id": blk.block_id,
                            "row_count": blk.row_count,
                            "bytes": total_comp,
                        })
                    self._send_response_json(200, {
                        "table": table_name,
                        "rows": reader.total_rows,
                        "bytes": sz,
                        "blocks_count": len(reader.blocks),
                        "columns": cols,
                        "blocks": block_info
                    })
            except Exception as e:
                self._send_response_json(500, {"error": str(e)})
            return

        elif path == "/table_data":
            table_name = params.get("table", [""])[0]
            if not table_name or not os.path.exists(table_name):
                self._send_response_json(404, {"error": f"Table '{table_name}' not found"})
                return

            try:
                page = max(1, int(params.get("page", ["1"])[0]))
                limit = max(1, min(500, int(params.get("limit", ["50"])[0])))
                target_start = (page - 1) * limit
                target_end = target_start + limit

                with FileReader(table_name) as reader:
                    cols = [c.name for c in reader.schema.columns]
                    total_rows = reader.total_rows
                    rows = []
                    cur_idx = 0

                    for batch, _ in reader.scan():
                        b_count = batch.row_count
                        if cur_idx + b_count > target_start and cur_idx < target_end:
                            b_rows = [list(vals) for vals in zip(*(batch.columns[c] for c in cols))]
                            for r in b_rows:
                                if target_start <= cur_idx < target_end:
                                    rows.append(r)
                                cur_idx += 1
                                if cur_idx >= target_end:
                                    break
                        else:
                            cur_idx += b_count

                        if cur_idx >= target_end:
                            break

                self._send_response_json(200, {
                    "table": table_name,
                    "columns": cols,
                    "rows": rows,
                    "total_rows": total_rows,
                    "page": page,
                    "limit": limit
                })
            except Exception as e:
                self._send_response_json(500, {"error": str(e)})
            return

        elif path == "/export":
            table_name = params.get("table", [""])[0]
            fmt = params.get("format", ["csv"])[0].lower()
            if not table_name or not os.path.exists(table_name):
                self._send_response_json(404, {"error": f"Table '{table_name}' not found"})
                return

            try:
                base_name = os.path.splitext(os.path.basename(table_name))[0]
                with FileReader(table_name) as reader:
                    cols = [c.name for c in reader.schema.columns]

                    if fmt == "csv":
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        writer.writerow(cols)
                        for batch, _ in reader.scan():
                            b_rows = [list(vals) for vals in zip(*(batch.columns[c] for c in cols))]
                            for row in b_rows:
                                writer.writerow(row)
                        content = buf.getvalue().encode("utf-8")
                        self._send_response_download(f"{base_name}.csv", content, "text/csv")
                        return

                    elif fmt in ("json", "jsonl"):
                        if fmt == "jsonl":
                            lines = []
                            for batch, _ in reader.scan():
                                b_rows = [list(vals) for vals in zip(*(batch.columns[c] for c in cols))]
                                for row in b_rows:
                                    d = dict(zip(cols, row))
                                    lines.append(json.dumps(d, default=str))
                            content = ("\n".join(lines) + "\n").encode("utf-8")
                            self._send_response_download(f"{base_name}.jsonl", content, "application/x-ndjson")
                            return
                        else:
                            all_rows = []
                            for batch, _ in reader.scan():
                                b_rows = [list(vals) for vals in zip(*(batch.columns[c] for c in cols))]
                                for row in b_rows:
                                    all_rows.append(dict(zip(cols, row)))
                            content = json.dumps(all_rows, indent=2, default=str).encode("utf-8")
                            self._send_response_download(f"{base_name}.json", content, "application/json")
                            return

                    elif fmt == "sql":
                        lines = [f"-- MergenDB SQL Dump of table `{base_name}`", ""]
                        col_str = ", ".join(f"`{c}`" for c in cols)
                        for batch, _ in reader.scan():
                            b_rows = [list(vals) for vals in zip(*(batch.columns[c] for c in cols))]
                            for row in b_rows:
                                vals = []
                                for v in row:
                                    if v is None:
                                        vals.append("NULL")
                                    elif isinstance(v, (int, float)):
                                        vals.append(str(v))
                                    else:
                                        escaped = str(v).replace("'", "''")
                                        vals.append(f"'{escaped}'")
                                lines.append(f"INSERT INTO `{base_name}` ({col_str}) VALUES ({', '.join(vals)});")
                        content = "\n".join(lines).encode("utf-8")
                        self._send_response_download(f"{base_name}.sql", content, "application/sql")
                        return
                    else:
                        self._send_response_json(400, {"error": f"Unsupported export format '{fmt}'"})
            except Exception as e:
                self._send_response_json(500, {"error": str(e)})
            return

        elif path == "/help":
            self._send_response_json(200, {
                "endpoints": {
                    "GET /": "Server status or Mergen Studio Web UI (in browser)",
                    "GET /studio": "Mergen Studio Interactive Web Dashboard (phpMyAdmin style)",
                    "POST /query": "Execute MergenQL or SQL query. Body: {'query': '...', 'active_table': '...'}",
                    "GET /tables": "List all tables with schema and size",
                    "GET /table_schema": "Detailed schema, columns, block details. Query: ?table=...",
                    "GET /table_data": "Paginated table data. Query: ?table=...&page=1&limit=50",
                    "GET /export": "Download table export. Query: ?table=...&format=csv|json|sql",
                    "POST /import": "Import data into a table. Body: {'table': '...', 'format': 'csv', 'content': '...'}",
                    "POST /operation": "Table management: truncate, drop, rename, add_column",
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
                active_table = payload.get("active_table", "").strip()

                if not query_text:
                    self._send_response_json(400, {"error": "Missing 'query' in request body"})
                    return

                # If active_table provided and query is missing FROM clause, auto-inject active table
                if active_table and not re.search(r"\bFROM\b", query_text, re.IGNORECASE):
                    if query_text.upper().startswith("SELECT "):
                        query_text = f"{query_text} FROM '{active_table}'"

                t0 = time.perf_counter()
                result = MergenDB.query(query_text)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                response = {
                    "success": True,
                    "columns": result.column_names,
                    "rows": result.rows,
                    "row_count": len(result.rows),
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

        elif path == "/import":
            try:
                payload = json.loads(post_data) if post_data else {}
                target_table = payload.get("table", "").strip()
                fmt = payload.get("format", "csv").lower()
                content = payload.get("content", "")
                filepath = payload.get("filepath", "").strip()

                if not target_table:
                    self._send_response_json(400, {"error": "Missing 'table' in import request"})
                    return

                if not target_table.endswith(".mgdb"):
                    target_table += ".mgdb"

                t0 = time.perf_counter()
                total_imported = 0

                if filepath and os.path.exists(filepath):
                    source_file = filepath
                    clean_up_tmp = False
                elif content:
                    tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=f".{fmt}")
                    tmp.write(content)
                    tmp.close()
                    source_file = tmp.name
                    clean_up_tmp = True
                else:
                    self._send_response_json(400, {"error": "Neither 'content' nor 'filepath' provided for import."})
                    return

                try:
                    if fmt == "csv":
                        total_imported = DataImporter.from_csv(source_file, target_table)
                    elif fmt == "sql":
                        total_imported = DataImporter.from_sql_dump(source_file, target_table)
                    elif fmt in ("json", "jsonl"):
                        # Parse JSON/JSONL and insert
                        rows = []
                        with open(source_file, "r", encoding="utf-8", errors="replace") as jf:
                            first_char = jf.read(1)
                            jf.seek(0)
                            if first_char == "[":
                                data_arr = json.load(jf)
                                if isinstance(data_arr, list):
                                    rows = data_arr
                            else:
                                for line in jf:
                                    line = line.strip()
                                    if line:
                                        rows.append(json.loads(line))
                        tbl = Table(target_table)
                        tbl.insert(rows)
                        total_imported = len(rows)
                    else:
                        raise ValueError(f"Unsupported import format: {fmt}")
                finally:
                    if clean_up_tmp and os.path.exists(source_file):
                        try:
                            os.remove(source_file)
                        except Exception:
                            pass

                elapsed_ms = (time.perf_counter() - t0) * 1000
                self._send_response_json(200, {
                    "success": True,
                    "table": target_table,
                    "rows_imported": total_imported,
                    "execution_time_ms": round(elapsed_ms, 2)
                })

            except Exception as e:
                self._send_response_json(400, {"success": False, "error": str(e)})
            return

        elif path == "/operation":
            try:
                payload = json.loads(post_data) if post_data else {}
                action = (payload.get("action") or payload.get("op") or "").lower()
                target_table = (payload.get("table") or "").strip()

                if not target_table and action != "list":
                    self._send_response_json(400, {"error": "Missing 'table' in operation request"})
                    return

                t0 = time.perf_counter()

                if action == "truncate":
                    tbl = Table(target_table)
                    tbl.truncate()
                    msg = f"Table '{target_table}' truncated successfully."

                elif action == "drop":
                    tbl = Table(target_table)
                    tbl.drop()
                    msg = f"Table '{target_table}' dropped successfully."

                elif action == "rename":
                    new_table = (payload.get("new_table") or payload.get("new_name") or "").strip()
                    if not new_table:
                        self._send_response_json(400, {"error": "Missing 'new_table' in rename request"})
                        return
                    tbl = Table(target_table)
                    tbl.rename(new_table)
                    msg = f"Table renamed to '{new_table}' successfully."

                elif action == "add_column":
                    col_name = payload.get("name", "").strip()
                    col_type = payload.get("type", "STRING").strip().upper()
                    default_val = payload.get("default", None)
                    if not col_name:
                        self._send_response_json(400, {"error": "Missing 'name' for new column"})
                        return
                    dtype = getattr(DataType, col_type, DataType.STRING)
                    tbl = Table(target_table)
                    tbl.add_column(col_name, dtype, default=default_val)
                    msg = f"Column '{col_name}' ({col_type}) added successfully."

                elif action == "drop_column":
                    col_name = payload.get("name", "").strip()
                    if not col_name:
                        self._send_response_json(400, {"error": "Missing 'name' of column to drop"})
                        return
                    tbl = Table(target_table)
                    tbl.drop_column(col_name)
                    msg = f"Column '{col_name}' dropped successfully."

                elif action == "create_table":
                    cols_def = payload.get("columns", [])
                    if not cols_def:
                        self._send_response_json(400, {"error": "At least one column definition is required"})
                        return
                    column_defs = []
                    for c in cols_def:
                        c_name = c.get("name", "").strip()
                        c_type = c.get("type", "STRING").upper()
                        dtype = getattr(DataType, c_type, DataType.STRING)
                        column_defs.append(ColumnDef(c_name, dtype))
                    if not target_table.endswith(".mgdb"):
                        target_table += ".mgdb"
                    Table.create(target_table, Schema(column_defs))
                    msg = f"Table '{target_table}' created successfully."

                else:
                    self._send_response_json(400, {"error": f"Unknown operation action: '{action}'"})
                    return

                elapsed_ms = (time.perf_counter() - t0) * 1000
                self._send_response_json(200, {
                    "success": True,
                    "message": msg,
                    "execution_time_ms": round(elapsed_ms, 2)
                })

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
    print("   [+] MERGENDB SERVER (MergenQL & SQL Network Engine)")
    print("=" * 70)
    print(f"  * Status        : RUNNING")
    print(f"  * Listening on  : http://{host}:{port}")
    print(f"  * Mergen Studio : http://localhost:{port}/studio (Interactive Web UI)")
    print(f"  * REST Query API: POST http://localhost:{port}/query")
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
