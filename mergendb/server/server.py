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

from mergendb.client import (
    MergenDB, Table, Database, resolve_table_path, scan_tables_in_dir, list_databases
)
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.reader import FileReader
from mergendb.io.importer import DataImporter
from mergendb.io.exporter import DataExporter

class MergenRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    High-performance, zero-dependency REST, Studio Web UI, & Query API handler for MergenDB server.
    """
    protocol_version = "HTTP/1.1"

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

    def _send_response_streaming_download(self, filename: str, mime_type: str, chunk_generator):
        """
        Streams file download directly to client using standard HTTP streaming.
        Strict zero-RAM footprint (< 15 MB) regardless of table size.
        Writes raw payload bytes without chunk framing headers so exported files are never corrupted.
        """
        self.send_response(200)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "close")
        self.end_headers()

        for chunk in chunk_generator:
            if chunk:
                self.wfile.write(chunk)
                self.wfile.flush()

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

        elif path == "/logo" or path == "/logo.png":
            candidates = [
                os.path.join(os.path.dirname(__file__), "..", "..", "docs", "images", "logo.png"),
                os.path.join(os.getcwd(), "docs", "images", "logo.png"),
            ]
            for p in candidates:
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self._send_response_json(404, {"error": "Logo not found"})
            return

        elif path == "/status" or path == "/health":
            files = glob.glob("*.mgdb")
            total_size = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
            from mergendb import __version__
            from mergendb.testing.suite import _detect_os_name, _detect_cpu_model, _detect_total_ram_gb
            res_obj = {
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
            }
            if params.get("benchmark", ["0"])[0] in ("1", "true"):
                import tempfile
                from mergendb.testing.suite import _profile_hardware
                with tempfile.TemporaryDirectory() as tmp_bench:
                    res_obj["benchmark"] = _profile_hardware(tmp_bench, verbose=False)

            self._send_response_json(200, res_obj)
            return

        elif path == "/databases":
            dbs = list_databases()
            self._send_response_json(200, {
                "databases": dbs,
                "active_database": getattr(MergenDB, "active_database", "default")
            })
            return

        elif path == "/query":
            q = params.get("q", params.get("query", [""]))[0]
            tbl = params.get("table", params.get("active_table", [""]))[0]
            db_name = params.get("database", [""])[0]
            self._execute_query(q, tbl, db_name)
            return

        elif path == "/tables":
            db_name = params.get("database", [""])[0]
            if db_name:
                db_obj = Database(db_name)
                tables = db_obj.list_tables()
            else:
                tables = []
                for db_meta in list_databases():
                    db_tables = scan_tables_in_dir(db_meta["path"], db_name=db_meta["name"])
                    tables.extend(db_tables)
            self._send_response_json(200, {
                "tables": tables,
                "active_database": getattr(MergenDB, "active_database", "default")
            })
            return

        elif path == "/table_schema":
            raw_tbl = params.get("table", [""])[0]
            explicit_path = params.get("path", [""])[0]
            db_name = params.get("database", [""])[0] or getattr(MergenDB, "active_database", "default")
            if explicit_path and os.path.isfile(explicit_path):
                table_name = explicit_path
            else:
                table_name = resolve_table_path(raw_tbl, active_db=db_name)
            if not table_name or not os.path.exists(table_name):
                self._send_response_json(404, {"error": f"Table '{raw_tbl}' not found"})
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
            raw_tbl = params.get("table", [""])[0]
            explicit_path = params.get("path", [""])[0]
            db_name = params.get("database", [""])[0] or getattr(MergenDB, "active_database", "default")
            if explicit_path and os.path.isfile(explicit_path):
                table_name = explicit_path
            else:
                table_name = resolve_table_path(raw_tbl, active_db=db_name)
            if not table_name or not os.path.exists(table_name):
                self._send_response_json(404, {"error": f"Table '{raw_tbl}' not found"})
                return

            try:
                page = max(1, int(params.get("page", ["1"])[0]))
                limit = max(1, min(500, int(params.get("limit", ["50"])[0])))
                sort_col = params.get("sort_col", [""])[0]
                sort_dir = params.get("sort_dir", ["asc"])[0].lower()
                target_start = (page - 1) * limit
                target_end = target_start + limit

                with FileReader(table_name) as reader:
                    cols = [c.name for c in reader.schema.columns]
                    total_rows = reader.total_rows

                    if sort_col and sort_col in cols:
                        all_rows = []
                        for batch, _ in reader.scan():
                            b_rows = [list(vals) for vals in zip(*(batch.columns[c] for c in cols))]
                            all_rows.extend(b_rows)
                        col_idx = cols.index(sort_col)
                        all_rows.sort(
                            key=lambda r: (r[col_idx] is None, str(r[col_idx]) if not isinstance(r[col_idx], (int, float)) else r[col_idx]),
                            reverse=(sort_dir == "desc")
                        )
                        rows = all_rows[target_start:target_end]
                    else:
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
            raw_tbl = params.get("table", [""])[0]
            explicit_path = params.get("path", [""])[0]
            fmt = params.get("format", ["csv"])[0].lower()
            db_name = params.get("database", [""])[0] or getattr(MergenDB, "active_database", "default")
            if explicit_path and os.path.isfile(explicit_path):
                table_name = explicit_path
            else:
                table_name = resolve_table_path(raw_tbl, active_db=db_name)
            if not table_name or not os.path.exists(table_name):
                self._send_response_json(404, {"error": f"Table '{raw_tbl}' not found"})
                return

            try:
                base_name = os.path.splitext(os.path.basename(table_name))[0]
                mime_map = {
                    "csv": "text/csv",
                    "json": "application/json",
                    "jsonl": "application/x-ndjson",
                    "sql": "application/sql"
                }
                if fmt not in mime_map:
                    self._send_response_json(400, {"error": f"Unsupported export format '{fmt}'"})
                    return

                mime_type = mime_map[fmt]
                filename = f"{base_name}.{fmt}"
                chunks = DataExporter.stream_chunks(table_name, fmt=fmt)
                self._send_response_streaming_download(filename, mime_type, chunks)
                return
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

    def _execute_query(self, query_text: str, active_table: str = "", active_database: str = ""):
        query_text = (query_text or "").strip()
        active_table = (active_table or "").strip()
        act_db = active_database or getattr(MergenDB, "active_database", "default")

        if not query_text:
            self._send_response_json(400, {"success": False, "error": "Missing 'query' parameter"})
            return

        # If active_table provided and query is missing FROM clause, auto-inject active table
        if active_table and not re.search(r"\bFROM\b", query_text, re.IGNORECASE):
            if query_text.upper().startswith("SELECT "):
                query_text = f"{query_text} FROM '{active_table}'"

        try:
            t0 = time.perf_counter()
            result = MergenDB.query(query_text, active_db=act_db)
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

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        params = urllib.parse.parse_qs(parsed_url.query)
        content_length = int(self.headers.get("Content-Length", 0))

        if path in ("/import_stream", "/import_file"):
            raw_tbl = params.get("table", [""])[0]
            explicit_path = params.get("path", [""])[0]
            fmt = params.get("format", ["csv"])[0].lower()
            db_name = params.get("database", [""])[0] or getattr(MergenDB, "active_database", "default")

            if not raw_tbl and not explicit_path:
                self._send_response_json(400, {"error": "Missing 'table' parameter"})
                return

            if explicit_path and os.path.isfile(explicit_path):
                target_table = explicit_path
            else:
                target_table = resolve_table_path(raw_tbl, active_db=db_name, for_create=True)
            t0 = time.perf_counter()

            # Stream direct from socket to temp file in 64KB chunks (strictly bounded RAM)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}")
            bytes_left = content_length
            chunk_size = 64 * 1024
            try:
                while bytes_left > 0:
                    n = min(chunk_size, bytes_left)
                    chunk = self.rfile.read(n)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    bytes_left -= len(chunk)
            finally:
                tmp.close()

            source_file = tmp.name
            try:
                if fmt == "csv":
                    total_imported = DataImporter.from_csv(source_file, target_table)
                elif fmt == "sql":
                    total_imported = DataImporter.from_sql_dump(source_file, target_table)
                elif fmt in ("json", "jsonl"):
                    total_imported = 0
                    tbl = Table(target_table)
                    with open(source_file, "r", encoding="utf-8", errors="replace") as jf:
                        first_char = jf.read(1)
                        jf.seek(0)
                        if first_char == "[":
                            data_arr = json.load(jf)
                            if isinstance(data_arr, list):
                                tbl.insert(data_arr)
                                total_imported = len(data_arr)
                        else:
                            batch = []
                            for line in jf:
                                line = line.strip()
                                if line:
                                    batch.append(json.loads(line))
                                    if len(batch) >= 1000:
                                        tbl.insert(batch)
                                        total_imported += len(batch)
                                        batch = []
                            if batch:
                                tbl.insert(batch)
                                total_imported += len(batch)
                else:
                    raise ValueError(f"Unsupported import format: {fmt}")

                elapsed_ms = (time.perf_counter() - t0) * 1000
                self._send_response_json(200, {
                    "success": True,
                    "table": target_table,
                    "rows_imported": total_imported,
                    "execution_time_ms": round(elapsed_ms, 2)
                })
            except Exception as e:
                self._send_response_json(400, {"success": False, "error": str(e)})
            finally:
                if os.path.exists(source_file):
                    try:
                        os.remove(source_file)
                    except Exception:
                        pass
            return

        post_data = self.rfile.read(content_length).decode("utf-8")

        if path == "/database":
            try:
                payload = json.loads(post_data) if post_data else {}
                action = payload.get("action", "create").lower()
                name = payload.get("name", "").strip()
                if not name:
                    self._send_response_json(400, {"error": "Missing database 'name'"})
                    return
                if action == "create":
                    Database.create(name)
                    msg = f"Database '{name}' created."
                elif action == "drop":
                    Database(name).drop()
                    msg = f"Database '{name}' dropped."
                elif action == "use":
                    MergenDB.active_database = name
                    msg = f"Active database set to '{name}'."
                else:
                    self._send_response_json(400, {"error": f"Unknown database action: '{action}'"})
                    return
                self._send_response_json(200, {"success": True, "message": msg, "database": name})
            except Exception as e:
                self._send_response_json(400, {"error": str(e)})
            return

        elif path == "/query":
            try:
                payload = json.loads(post_data) if post_data else {}
            except Exception:
                payload = {}
            query_text = payload.get("query", payload.get("q", "")).strip()
            active_table = payload.get("active_table", payload.get("table", "")).strip()
            active_db = payload.get("database", "").strip()
            self._execute_query(query_text, active_table, active_db)
            return

        elif path == "/import":
            try:
                payload = json.loads(post_data) if post_data else {}
                target_table = payload.get("table", "").strip()
                explicit_path = payload.get("path", "").strip()
                db_name = payload.get("database", "").strip() or getattr(MergenDB, "active_database", "default")
                fmt = payload.get("format", "csv").lower()
                content = payload.get("content", "")
                filepath = payload.get("filepath", "").strip()

                if not target_table and not explicit_path:
                    self._send_response_json(400, {"error": "Missing 'table' in import request"})
                    return

                if explicit_path and os.path.isfile(explicit_path):
                    target_table = explicit_path
                else:
                    target_table = resolve_table_path(target_table, active_db=db_name, for_create=True)

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
                db_name = payload.get("database", "").strip() or getattr(MergenDB, "active_database", "default")

                if action in ("create_database", "drop_database", "use_database"):
                    d_name = payload.get("name", target_table).strip()
                    if not d_name:
                        self._send_response_json(400, {"error": "Missing database name"})
                        return
                    if action == "create_database":
                        Database.create(d_name)
                        msg = f"Database '{d_name}' created."
                    elif action == "drop_database":
                        Database(d_name).drop()
                        msg = f"Database '{d_name}' dropped."
                    elif action == "use_database":
                        MergenDB.active_database = d_name
                        msg = f"Active database set to '{d_name}'."
                    self._send_response_json(200, {"success": True, "message": msg, "database": d_name})
                    return

                if not target_table and action not in ("create_table", "create_subtable", "list"):
                    self._send_response_json(400, {"error": "Missing 'table' in operation request"})
                    return

                t0 = time.perf_counter()

                if action in ("create_table", "create_subtable"):
                    cols_def = payload.get("columns", [])
                    parent_table = payload.get("parent_table", "").strip()
                    if parent_table and not target_table.startswith(parent_table + "."):
                        table_ident = f"{parent_table}.{target_table}"
                    else:
                        table_ident = target_table

                    if not cols_def:
                        self._send_response_json(400, {"error": "At least one column definition is required"})
                        return
                    column_defs = []
                    for c in cols_def:
                        c_name = c.get("name", "").strip()
                        c_type = c.get("type", "STRING").upper()
                        dtype = getattr(DataType, c_type, DataType.STRING)
                        column_defs.append(ColumnDef(c_name, dtype))

                    resolved = resolve_table_path(table_ident, active_db=db_name, for_create=True)
                    Table.create(resolved, Schema(column_defs))
                    msg = f"Table '{table_ident}' created successfully."

                else:
                    explicit_path = (payload.get("path") or "").strip()
                    if explicit_path and os.path.isfile(explicit_path):
                        resolved_table = explicit_path
                    else:
                        resolved_table = resolve_table_path(target_table, active_db=db_name)
                    if not os.path.exists(resolved_table) and action != "insert":
                        self._send_response_json(404, {"error": f"Table '{target_table}' not found"})
                        return

                    tbl = Table(resolved_table)

                    if action == "truncate":
                        tbl.truncate()
                        msg = f"Table '{target_table}' truncated successfully."

                    elif action == "drop":
                        tbl.drop()
                        msg = f"Table '{target_table}' dropped successfully."

                    elif action == "rename":
                        new_table = (payload.get("new_table") or payload.get("new_name") or "").strip()
                        if not new_table:
                            self._send_response_json(400, {"error": "Missing 'new_table' in rename request"})
                            return
                        new_resolved = resolve_table_path(new_table, active_db=db_name, for_create=True)
                        tbl.rename(new_resolved)
                        msg = f"Table renamed to '{new_table}' successfully."

                    elif action == "add_column":
                        col_name = payload.get("name", "").strip()
                        col_type = payload.get("type", "STRING").strip().upper()
                        default_val = payload.get("default", None)
                        if not col_name:
                            self._send_response_json(400, {"error": "Missing 'name' for new column"})
                            return
                        dtype = getattr(DataType, col_type, DataType.STRING)
                        tbl.add_column(col_name, dtype, default=default_val)
                        msg = f"Column '{col_name}' ({col_type}) added successfully."

                    elif action == "drop_column":
                        col_name = payload.get("name", "").strip()
                        if not col_name:
                            self._send_response_json(400, {"error": "Missing 'name' of column to drop"})
                            return
                        tbl.drop_column(col_name)
                        msg = f"Column '{col_name}' dropped successfully."

                    elif action == "rename_column":
                        old_col = payload.get("old_name", "").strip()
                        new_col = payload.get("new_name", "").strip()
                        if not old_col or not new_col:
                            self._send_response_json(400, {"error": "Missing old_name or new_name in rename_column"})
                            return
                        tbl.rename_column(old_col, new_col)
                        msg = f"Column '{old_col}' renamed to '{new_col}' successfully."

                    elif action == "insert":
                        row_data = payload.get("row") or payload.get("data")
                        if not row_data:
                            self._send_response_json(400, {"error": "Missing 'row' data for insert"})
                            return
                        if isinstance(row_data, dict):
                            tbl.insert([row_data])
                        elif isinstance(row_data, list):
                            tbl.insert(row_data)
                        msg = f"Inserted record into '{target_table}' successfully."

                    elif action in ("delete", "delete_row"):
                        where_cond = payload.get("where", "").strip()
                        if not where_cond:
                            self._send_response_json(400, {"error": "Missing 'where' condition for delete"})
                            return
                        del_count = tbl.delete(where=where_cond)
                        msg = f"Deleted {del_count} row(s) from '{target_table}'."

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
