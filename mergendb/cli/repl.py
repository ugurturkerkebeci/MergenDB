import sys
import os
import glob
import time
import json
import csv
import re
from typing import Optional, List
from mergendb.client import MergenDB
from mergendb.core.types import DataType
from mergendb.storage.reader import FileReader
from mergendb.io.importer import DataImporter
from mergendb.io.progress import ProgressBar

BANNER = r"""
                _
               / \
              /   \
             / / \ \                   __  __                                _____  ____  
            / /   \ \                 |  \/  |                             |  __ \|  _ \ 
           / /  |  \ \                | \  / | ___ _ __ __ _  ___ _ __     | |  | | |_) |
          / /  / \  \ \               | |\/| |/ _ \ '__/ _` |/ _ \ '_ \    | |  | |  _ < 
         / /  /   \  \ \              | |  | |  __/ | | (_| |  __/ | | |   | |__| | |_) |
        / /  / /|\ \  \ \             |_|  |_|\___|_|  \__, |\___|_| |_|   |_____/|____/ 
       / /  / / | \ \  \ \                              __/ |                            
      / /__/_/  |  \_\__\ \                            |___/  v0.5.3 (Lightning Engine)
     /     \    |    /     \
    /_______\   |   /_______\         =[ MergenDB - Lightning Columnar Database      ]
             \  |  /           + -- --=[ 16 Adaptive Hardware Encodings (Up to 16x)  ]
              \ | /            + -- --=[ ZoneMap Zero-I/O Indexing (100M+ Rows Safe) ]
               \|/             + -- --=[ Network SQL/MergenQL Server on Port 8765    ]
                |              + -- --=[ Zero External Dependencies | Pure Speed     ]
                '              + -- --=[ Author: Ugur Turker Kebeci (@ugurturkerkebeci)

                   "Target Acquired. Zero Waste. Pure Speed."
    Type SQL or MergenQL commands ending with ';'. Type 'HELP;' for command list.
"""

HELP_TEXT = """
================================ MERGENDB COMMANDS ================================
Database & Table Management:
  SHOW TABLES;                                      - List all .mgdb tables with rows, size, blocks
  SHOW DATABASES;                                   - List databases / directories
  SHOW COLUMNS FROM <table>; (or DESC)              - Inspect columns, data types, nullability
  USE <table_name>;                                 - Set active table context
  CREATE TABLE <name> (col TYPE, ...);              - Create a new columnar table
  RENAME TABLE <old> TO <new>;                      - Rename a table
  TRUNCATE TABLE <table>; (or TRUNCATE;)            - Clear all rows in a table keeping schema
  DROP TABLE <table>; (or DROP;)                    - Delete a table permanently
  OPTIMIZE TABLE <table>;                           - Defragment and re-compress table blocks
  COUNT <table>;                                    - Instant O(1) total row count
  STATUS;                                           - Engine status, cache stats, and memory usage

Data & Schema Mutations (SQL):
  UPDATE <table> SET col1 = val1, ... [WHERE ...];  - Update matching rows in table
  DELETE FROM <table> [WHERE ...];                  - Delete matching rows from table
  ALTER TABLE <table> RENAME COLUMN <old> TO <new>; - Rename a column without data loss
  ALTER TABLE <table> DROP COLUMN <col>;            - Drop a column from table
  ALTER TABLE <table> ADD COLUMN <col> <type> [DEFAULT <val>]; - Add column with default
  (When inside 'USE <table>;', active table name is optional: UPDATE SET..., DELETE WHERE..., etc.)

Querying (MergenQL & SQL):
  FROM "table.mgdb" | WHERE ... | SELECT ...;      - Full pipeline query
  SELECT col1, col2 FROM <table> WHERE ...;        - Standard SQL query syntax
  EXPLAIN <query>;                                 - Display query optimization plan & pruning
  WHERE temp > 30 | SELECT col1, col2;             - Active table shortcut query (after USE)

Network & Server:
  SERVE [port];                                    - Start MergenQL TCP/HTTP server (default: 8765)

Data Ingestion & Export:
  IMPORT SQLITE <source.db> [tbl] <out.mgdb>;      - Ingest SQLite table
  IMPORT SQL <dump.sql> <out.mgdb>;                - Ingest MySQL / phpMyAdmin SQL dump
  IMPORT CSV <file.csv> <out.mgdb>;                - Ingest CSV file with auto-detect
  EXPORT <table.mgdb> TO CSV <output.csv>;         - Export to CSV
  EXPORT <table.mgdb> TO JSON <output.jsonl>;      - Export to JSON Lines
  EXPORT <table.mgdb> TO SQL <output.sql>;         - Export to SQL dump (DDL + INSERTs)

Diagnostics:
  BENCHMARK <table.mgdb>;                          - Run live speed & I/O benchmark
  INFO <table.mgdb>;                               - Compression ratio & block telemetry
  EXIT; (or QUIT;)                                 - Exit MergenDB CLI
===================================================================================
"""

class MergenCLI:
    def __init__(self):
        self.active_table: Optional[str] = None

    def _resolve_table_path(self, name: str) -> str:
        name = name.strip().strip('"').strip("'")
        if not name.endswith(".mgdb"):
            name = name + ".mgdb"
        return name

    def show_tables(self):
        files = glob.glob("*.mgdb")
        if not files:
            print("\n(No .mgdb tables found in current directory)\n")
            return

        print("\n+--------------------------------+------------+--------------+-----------+")
        print("| Table Name                     | Rows       | Disk Size    | Blocks    |")
        print("+--------------------------------+------------+--------------+-----------+")
        for f in files:
            try:
                sz = os.path.getsize(f)
                with FileReader(f) as reader:
                    rows = reader.total_rows
                    blocks = len(reader.blocks)
                size_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"
                print(f"| {f.ljust(30)} | {str(f'{rows:,}').rjust(10)} | {size_str.rjust(12)} | {str(blocks).rjust(9)} |")
            except Exception:
                print(f"| {f.ljust(30)} | {'CORRUPT'.center(10)} | {'-'.center(12)} | {'-'.center(9)} |")
        print("+--------------------------------+------------+--------------+-----------+\n")

    def show_databases(self):
        cwd = os.getcwd()
        dirs = [d for d in os.listdir(cwd) if os.path.isdir(d) and not d.startswith(".")]
        print(f"\nCurrent Directory: {cwd}")
        print("+--------------------------------+")
        print("| Database / Directory           |")
        print("+--------------------------------+")
        print(f"| {os.path.basename(cwd).ljust(30)} | (Current)")
        for d in dirs:
            print(f"| {d.ljust(30)} |")
        print("+--------------------------------+\n")

    def describe_table(self, table_name: str):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return

        with FileReader(filepath) as reader:
            print(f"\nTable: {filepath} ({reader.total_rows:,} rows, {len(reader.blocks)} blocks)")
            print("+---------------------------+----------------+----------+")
            print("| Column                    | Type           | Nullable |")
            print("+---------------------------+----------------+----------+")
            for col in reader.schema.columns:
                print(f"| {col.name.ljust(25)} | {col.data_type.name.ljust(14)} | {str(col.nullable).ljust(8)} |")
            print("+---------------------------+----------------+----------+\n")

    def count_table(self, table_name: str):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return
        with FileReader(filepath) as reader:
            print(f"\n{filepath}: {reader.total_rows:,} rows.\n")

    def truncate_table(self, table_name: str):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return
        with FileReader(filepath) as reader:
            schema = reader.schema
        MergenDB.create_table(filepath, schema)
        print(f"Table '{filepath}' truncated. (0 rows)\n")

    def rename_table(self, old_name: str, new_name: str):
        old_path = self._resolve_table_path(old_name)
        new_path = self._resolve_table_path(new_name)
        if not os.path.exists(old_path):
            print(f"Error: Table '{old_path}' not found.")
            return
        os.rename(old_path, new_path)
        if self.active_table == old_path:
            self.active_table = new_path
        print(f"Table renamed from '{old_path}' to '{new_path}'.\n")

    def optimize_table(self, table_name: str):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return
        print(f"Optimizing blocks for '{filepath}'...")
        t0 = time.perf_counter()
        tbl = MergenDB.open_table(filepath)
        tbl.insert_many([], block_size=2048) # triggers re-flushing & block consolidation
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"Table '{filepath}' optimized in {elapsed:.2f} ms.\n")

    def explain_query(self, query_str: str):
        from mergendb.query.lexer import Lexer
        from mergendb.query.parser import Parser
        from mergendb.query.planner import QueryPlanner
        from mergendb.query.ast_nodes import QueryPlan

        tokens = Lexer(query_str).tokenize()
        plan = Parser(tokens).parse()

        if not isinstance(plan, QueryPlan):
            print("EXPLAIN only supports SELECT / FROM queries.")
            return

        pushdowns = QueryPlanner.extract_pushdown_predicates(plan.where_expr)
        needed_cols = QueryPlanner.collect_required_columns(plan)

        print("\n--- MergenQL Query Plan ---")
        print(f"  Source Table       : {plan.table_source}")
        print(f"  Pushdown Predicates: {pushdowns if pushdowns else '(None - Full block scan)'}")
        print(f"  Columns to Read    : {needed_cols if needed_cols else '(All Columns)'}")
        print(f"  Computed Columns   : {[c.target_column for c in plan.computes] if plan.computes else '(None)'}")
        print(f"  Aggregation        : {[a.alias for a in plan.aggregate.aggregations] if plan.aggregate else '(None)'}")
        print(f"  Sort               : {plan.sort.column + (' DESC' if plan.sort.descending else ' ASC') if plan.sort else '(None)'}")
        print(f"  Limit              : {plan.limit if plan.limit is not None else '(None)'}\n")

    def show_info(self, table_name: str):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return

        sz = os.path.getsize(filepath)
        with FileReader(filepath) as reader:
            u_bytes = sum(c.uncompressed_bytes for b in reader.blocks for c in b.columns.values())
            c_bytes = sum(c.compressed_bytes for b in reader.blocks for c in b.columns.values())
            ratio = (u_bytes / c_bytes) if c_bytes > 0 else 1.0
            saved = ((1.0 - c_bytes / u_bytes) * 100.0) if u_bytes > 0 else 0.0

            print(f"\n--- Storage Telemetry: {filepath} ---")
            print(f"Total Rows        : {reader.total_rows:,}")
            print(f"Total Blocks      : {len(reader.blocks)}")
            print(f"On-Disk Size      : {sz / 1024:.2f} KB ({sz:,} bytes)")
            print(f"Raw Uncompressed  : {u_bytes / 1024:.2f} KB")
            print(f"Compressed Data   : {c_bytes / 1024:.2f} KB")
            print(f"Compression Ratio : {ratio:.2f}x (Saved {saved:.1f}% space)\n")

    def export_table(self, table_name: str, fmt: str, out_file: Optional[str]):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return

        fmt = fmt.upper()
        if fmt == "CVS":
            fmt = "CSV"

        if not out_file:
            base = os.path.splitext(filepath)[0]
            if fmt == "CSV":
                out_file = f"{base}.csv"
            elif fmt == "SQL":
                out_file = f"{base}.sql"
            elif fmt == "JSON":
                out_file = f"{base}.json"
            elif fmt == "JSONL":
                out_file = f"{base}.jsonl"
            else:
                out_file = f"{base}.csv"

        with FileReader(filepath) as reader:
            total_rows = reader.total_rows
            col_names = reader.schema.column_names()
            pbar = ProgressBar(f"Exporting to {fmt}", total_rows=total_rows)
            exported = 0

            if fmt == "CSV":
                with open(out_file, "w", newline="", encoding="utf-8", buffering=256*1024) as f:
                    writer = csv.writer(f)
                    writer.writerow(col_names)
                    for batch, _ in reader.scan():
                        cols = batch.columns
                        writer.writerows(zip(*(cols[c] for c in col_names)))
                        exported += batch.row_count
                        pbar.update(exported)

            elif fmt == "SQL":
                with open(out_file, "w", encoding="utf-8", buffering=256*1024) as f:
                    clean_tbl = os.path.splitext(os.path.basename(filepath))[0]
                    col_defs = []
                    for c in reader.schema.columns:
                        tname = "TEXT"
                        if c.data_type in (DataType.INT64, DataType.INT32):
                            tname = "BIGINT"
                        elif c.data_type == DataType.FLOAT64:
                            tname = "DOUBLE"
                        elif c.data_type == DataType.BOOL:
                            tname = "BOOLEAN"
                        col_defs.append(f"  `{c.name}` {tname}")
                    f.write(f"CREATE TABLE IF NOT EXISTS `{clean_tbl}` (\n" + ",\n".join(col_defs) + "\n);\n\n")

                    chunk_size = 1000
                    chunk = []
                    for batch, _ in reader.scan():
                        cols = batch.columns
                        for row_vals in zip(*(cols[c] for c in col_names)):
                            formatted = []
                            for val in row_vals:
                                if val is None:
                                    formatted.append("NULL")
                                elif isinstance(val, (int, float)):
                                    formatted.append(str(val))
                                elif isinstance(val, bool):
                                    formatted.append("1" if val else "0")
                                else:
                                    esc = str(val).replace("\\", "\\\\").replace("'", "''")
                                    formatted.append(f"'{esc}'")
                            chunk.append("(" + ", ".join(formatted) + ")")
                            if len(chunk) >= chunk_size:
                                f.write(f"INSERT INTO `{clean_tbl}` VALUES\n" + ",\n".join(chunk) + ";\n")
                                chunk = []
                        exported += batch.row_count
                        pbar.update(exported)
                    if chunk:
                        f.write(f"INSERT INTO `{clean_tbl}` VALUES\n" + ",\n".join(chunk) + ";\n")

            elif fmt == "JSON":
                with open(out_file, "w", encoding="utf-8", buffering=256*1024) as f:
                    f.write("[\n")
                    first = True
                    for batch, _ in reader.scan():
                        cols = batch.columns
                        for row in zip(*(cols[c] for c in col_names)):
                            record_str = json.dumps(dict(zip(col_names, row)))
                            if not first:
                                f.write(",\n  " + record_str)
                            else:
                                f.write("  " + record_str)
                                first = False
                        exported += batch.row_count
                        pbar.update(exported)
                    f.write("\n]\n")

            else:  # JSONL
                with open(out_file, "w", encoding="utf-8", buffering=256*1024) as f:
                    for batch, _ in reader.scan():
                        cols = batch.columns
                        lines = [json.dumps(dict(zip(col_names, row))) + "\n" for row in zip(*(cols[c] for c in col_names))]
                        f.writelines(lines)
                        exported += batch.row_count
                        pbar.update(exported)

            pbar.finish(f"[+] Successfully exported {exported:,} rows to '{out_file}'!")

    def benchmark_table(self, table_name: str):
        filepath = self._resolve_table_path(table_name)
        if not os.path.exists(filepath):
            print(f"Error: Table '{filepath}' not found.")
            return

        with FileReader(filepath) as reader:
            first_col = reader.schema.columns[0].name
            num_rows = reader.total_rows

        print(f"\nBenchmarking '{filepath}' ({num_rows:,} rows)...")
        t0 = time.perf_counter()
        res1 = MergenDB.query(f'FROM "{filepath}" | AGGREGATE count(*) AS cnt')
        ms1 = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        res2 = MergenDB.query(f'FROM "{filepath}" | SELECT {first_col} | LIMIT 100')
        ms2 = (time.perf_counter() - t0) * 1000

        throughput = (num_rows / (ms1/1000.0)) if ms1 > 0 else 0
        print(f"  * Aggregation scan : {ms1:.2f} ms")
        print(f"  * Column prune scan: {ms2:.2f} ms")
        print(f"  * Throughput       : {throughput:,.0f} rows/sec\n")

    def execute_command(self, raw_cmd: str):
        cmd = raw_cmd.strip().rstrip(";")
        if not cmd:
            return

        parts = cmd.split()
        keyword = parts[0].upper()

        if keyword in ("EXIT", "QUIT", "\\Q"):
            print("Görüşmek üzere!")
            sys.exit(0)

        elif keyword == "HELP":
            print(HELP_TEXT)

        elif keyword == "SERVE":
            port = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 8765
            from mergendb.server.server import start_server
            start_server(port=port)

        elif keyword in ("SHOW", "LIST"):
            if len(parts) == 1:
                print("Available SHOW commands: SHOW TABLES;, SHOW DATABASES;, SHOW COLUMNS [FROM <table>];\n")
                return
            sub = parts[1].upper()
            if sub in ("TABLES", "TABLE"):
                self.show_tables()
            elif sub in ("DATABASES", "DATABASE"):
                self.show_databases()
            elif sub in ("COLUMNS", "COLUMN", "FIELDS", "FIELD"):
                if len(parts) >= 4 and parts[2].upper() == "FROM":
                    self.describe_table(parts[3])
                elif len(parts) == 3:
                    self.describe_table(parts[2])
                elif self.active_table:
                    self.describe_table(self.active_table)
                else:
                    print("Error: No active table context. Use 'SHOW COLUMNS FROM <table>;' or 'USE <table_name>;'.\n")
            else:
                print(f"Unknown SHOW command: {cmd}\nAvailable: SHOW TABLES;, SHOW DATABASES;, SHOW COLUMNS [FROM <table>];\n")

        elif keyword in ("DESCRIBE", "DESC"):
            tbl = parts[1] if len(parts) > 1 else self.active_table
            if tbl:
                self.describe_table(tbl)
            else:
                print("Error: Specify a table name or use 'USE <table_name>;'.\n")

        elif keyword == "COUNT" and len(parts) > 1:
            self.count_table(parts[1])

        elif keyword == "TRUNCATE":
            if len(parts) == 1 and self.active_table:
                self.truncate_table(self.active_table)
            elif len(parts) >= 2 and parts[1].upper() != "TABLE":
                self.truncate_table(parts[1])
            elif len(parts) >= 3 and parts[1].upper() == "TABLE":
                self.truncate_table(parts[2])
            else:
                print("Error: Specify a table name or use 'USE <table_name>;'.\n")

        elif keyword == "DROP":
            if len(parts) == 1 and self.active_table:
                tbl = self.active_table
                if os.path.exists(tbl):
                    os.remove(tbl)
                self.active_table = None
                print(f"Table '{tbl}' dropped successfully.\n")
            elif len(parts) == 2 and parts[1].upper() != "TABLE":
                tbl = self._resolve_table_path(parts[1])
                if os.path.exists(tbl):
                    os.remove(tbl)
                    if self.active_table == tbl:
                        self.active_table = None
                    print(f"Table '{tbl}' dropped successfully.\n")
                else:
                    print(f"Table '{tbl}' not found.\n")
            elif len(parts) >= 3 and parts[1].upper() == "TABLE":
                tbl = self._resolve_table_path(parts[2])
                if os.path.exists(tbl):
                    os.remove(tbl)
                    if self.active_table == tbl:
                        self.active_table = None
                    print(f"Table '{tbl}' dropped successfully.\n")
                else:
                    print(f"Table '{tbl}' not found.\n")
            else:
                print("Error: Specify a table name or use 'USE <table_name>;'.\n")

        elif keyword == "UPDATE":
            query_str = cmd
            if re.match(r"^UPDATE\s+SET\b", query_str, re.IGNORECASE):
                if not self.active_table:
                    print("Error: No active table selected. Use 'USE <table_name>;' or 'UPDATE <table> SET ...'.\n")
                    return
                query_str = f'UPDATE "{self.active_table}" ' + query_str[7:]
            try:
                res = MergenDB.query(query_str, show_progress=True)
                print(res.display())
            except Exception as e:
                print(f"Error: {e}")

        elif keyword == "DELETE":
            query_str = cmd
            del_m = re.match(r"^DELETE(?:\s+WHERE\s+(.+))?$", query_str, re.IGNORECASE)
            if del_m:
                if not self.active_table:
                    print("Error: No active table selected. Use 'USE <table_name>;' or 'DELETE FROM <table> ...'.\n")
                    return
                wh = del_m.group(1)
                query_str = f'DELETE FROM "{self.active_table}"' + (f" WHERE {wh}" if wh else "")
            try:
                res = MergenDB.query(query_str, show_progress=True)
                print(res.display())
            except Exception as e:
                print(f"Error: {e}")

        elif keyword == "ALTER":
            try:
                res = MergenDB.query(cmd, show_progress=True)
                print(res.display())
            except Exception as e:
                print(f"Error: {e}")

        elif keyword in ("RENAME", "DROP", "ADD") and len(parts) > 1 and parts[1].upper() == "COLUMN":
            if not self.active_table:
                print(f"Error: No active table selected. Use 'USE <table_name>;' or 'ALTER TABLE <table> {cmd};'.\n")
                return
            alter_cmd = f'ALTER TABLE "{self.active_table}" {cmd}'
            try:
                res = MergenDB.query(alter_cmd, show_progress=True)
                print(res.display())
            except Exception as e:
                print(f"Error: {e}")

        elif keyword == "RENAME" and len(parts) >= 5 and parts[1].upper() == "TABLE" and parts[3].upper() == "TO":
            self.rename_table(parts[2], parts[4])

        elif keyword == "OPTIMIZE" and len(parts) >= 3 and parts[1].upper() == "TABLE":
            self.optimize_table(parts[2])

        elif keyword == "EXPLAIN":
            query_part = cmd[7:].strip()
            if query_part.upper().startswith("SELECT ") and "FROM " in query_part.upper():
                query_part = self._convert_sql_to_pipeline(query_part)
            self.explain_query(query_part)

        elif keyword == "USE" and len(parts) > 1:
            tbl = self._resolve_table_path(parts[1])
            if os.path.exists(tbl):
                self.active_table = tbl
                print(f"Database/Table context set to: {tbl}")
            else:
                print(f"Error: Table '{tbl}' does not exist.")

        elif keyword == "INFO" and len(parts) > 1:
            self.show_info(parts[1])

        elif keyword == "BENCHMARK" and len(parts) > 1:
            self.benchmark_table(parts[1])

        elif keyword == "EXPORT":
            rem = parts[1:]
            if not rem:
                if self.active_table:
                    print("Usage: EXPORT <SQL|CSV|JSON|JSONL> [output_file]; or EXPORT TO <SQL|CSV|JSON>;\n")
                else:
                    print("Usage: EXPORT <table.mgdb> TO <SQL|CSV|JSON|JSONL> [output_file];\n")
                return

            tbl = None
            fmt = "CSV"
            out = None

            if rem[0].upper() == "TO":
                if not self.active_table:
                    print("Error: No active table selected. Use 'USE <table_name>;' or 'EXPORT <table> TO ...'.\n")
                    return
                tbl = self.active_table
                fmt = rem[1].upper() if len(rem) > 1 else "CSV"
                out = rem[2] if len(rem) > 2 else None

            elif rem[0].upper() in ("SQL", "CSV", "CVS", "JSON", "JSONL"):
                if not self.active_table:
                    print("Error: No active table selected. Use 'USE <table_name>;' or 'EXPORT <table> TO ...'.\n")
                    return
                tbl = self.active_table
                fmt = rem[0].upper()
                out = rem[1] if len(rem) > 1 else None

            elif any(rem[0].lower().endswith(ext) for ext in (".sql", ".csv", ".json", ".jsonl")):
                if not self.active_table:
                    print("Error: No active table selected. Use 'USE <table_name>;' or specify table: 'EXPORT <table> <file>'.\n")
                    return
                tbl = self.active_table
                out = rem[0]
                ext = os.path.splitext(out)[1].lower().lstrip(".")
                fmt = ext.upper()

            else:
                tbl = rem[0]
                rest = rem[1:]
                if rest and rest[0].upper() == "TO":
                    rest = rest[1:]

                if not rest:
                    fmt = "SQL"
                    out = None
                elif rest[0].upper() in ("SQL", "CSV", "CVS", "JSON", "JSONL"):
                    fmt = rest[0].upper()
                    out = rest[1] if len(rest) > 1 else None
                elif any(rest[0].lower().endswith(ext) for ext in (".sql", ".csv", ".json", ".jsonl")):
                    out = rest[0]
                    ext = os.path.splitext(out)[1].lower().lstrip(".")
                    fmt = ext.upper()
                else:
                    fmt = rest[0].upper()
                    out = rest[1] if len(rest) > 1 else None

            if fmt == "CVS":
                fmt = "CSV"

            self.export_table(tbl, fmt, out)

        elif keyword == "IMPORT" and len(parts) >= 4:
            sub = parts[1].upper()
            t0 = time.perf_counter()
            if sub == "SQLITE":
                src = parts[2]
                if len(parts) == 4:
                    out = self._resolve_table_path(parts[3])
                    tbl = None
                else:
                    tbl = parts[3]
                    out = self._resolve_table_path(parts[4])
                cnt = DataImporter.from_sqlite(src, out, table_name=tbl)
                print(f"Imported {cnt:,} rows from SQLite into '{out}' in {(time.perf_counter()-t0)*1000:.2f} ms.")
            elif sub == "SQL":
                src = parts[2]
                out = self._resolve_table_path(parts[3])
                cnt = DataImporter.from_sql_dump(src, out)
                self.active_table = out
                print(f"[*] Active table context automatically switched to: '{out}'\n")
            elif sub == "CSV":
                src = parts[2]
                out = self._resolve_table_path(parts[3])
                cnt = DataImporter.from_csv(src, out)
                self.active_table = out
                print(f"Imported {cnt:,} rows from CSV into '{out}' in {(time.perf_counter()-t0)*1000:.2f} ms.\n")
            else:
                print(f"Unknown import format: {sub}. Use SQLITE, SQL, or CSV.")

        elif keyword == "STATUS":
            files = glob.glob("*.mgdb")
            total_size = sum(os.path.getsize(f) for f in files)
            print("\n--- MergenDB Engine Status ---")
            print(f"Active Table Context : {self.active_table or '(None)'}")
            print(f"Local Tables Count   : {len(files)}")
            print(f"Total Local Data Size: {total_size / 1024:.2f} KB")
            print(f"Engine Version       : 0.5.3 (Lightning Columnar Engine)")
            print(f"Process PID          : {os.getpid()}\n")

        else:
            # Query Execution (MergenQL or SQL)
            query_str = cmd
            if query_str.upper().startswith("SELECT ") and "FROM " not in query_str.upper() and self.active_table:
                sel_m = re.match(r"^SELECT\s+(.+?)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$", query_str, re.IGNORECASE)
                if sel_m:
                    cols, where_clause, order_by, limit_val = sel_m.groups()
                    sql_synth = f"SELECT {cols} FROM {self.active_table}"
                    if where_clause: sql_synth += f" WHERE {where_clause}"
                    if order_by: sql_synth += f" ORDER BY {order_by}"
                    if limit_val: sql_synth += f" LIMIT {limit_val}"
                    query_str = self._convert_sql_to_pipeline(sql_synth)

            elif (query_str.startswith("|") or query_str.upper().startswith("WHERE ") or query_str.upper().startswith("SELECT ")) and "FROM" not in query_str.upper():
                if not self.active_table:
                    print("Error: No active table selected. Use 'USE <table_name>;' or specify 'FROM \"table.mgdb\"'.")
                    return
                if not query_str.startswith("|"):
                    query_str = "| " + query_str
                query_str = f'FROM "{self.active_table}"\n' + query_str

            if query_str.upper().startswith("SELECT ") and "FROM " in query_str.upper():
                query_str = self._convert_sql_to_pipeline(query_str)

            try:
                result = MergenDB.query(query_str, show_progress=True)
                print(result.display())
            except Exception as e:
                print(f"Error: {e}")

    def _convert_sql_to_pipeline(self, sql: str) -> str:
        """Translates basic standard SQL 'SELECT ... FROM ... WHERE ...' into MergenQL pipeline."""
        m = re.match(r"SELECT\s+(.+?)\s+FROM\s+([^\s;]+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$", sql, re.IGNORECASE)
        if not m:
            return sql

        cols, tbl, where_clause, order_by, limit_val = m.groups()
        tbl = self._resolve_table_path(tbl)
        pipe = [f'FROM "{tbl}"']

        if where_clause:
            pipe.append(f"| WHERE {where_clause}")
        if cols.strip() != "*":
            pipe.append(f"| SELECT {cols.strip()}")
        if order_by:
            parts = order_by.strip().split()
            col = parts[0]
            desc = "DESC" if len(parts) > 1 and parts[1].upper() == "DESC" else "ASC"
            pipe.append(f"| SORT {col} {desc}")
        if limit_val:
            pipe.append(f"| LIMIT {limit_val}")

        return "\n".join(pipe)

    def run(self):
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        print(BANNER)
        buffer = []

        while True:
            try:
                table_prompt = f"[{os.path.basename(self.active_table)}]" if self.active_table else ""
                prompt = f"mergen{table_prompt}> " if not buffer else "      ...> "
                line = input(prompt)

                stripped = line.strip()

                if not buffer and stripped.startswith("."):
                    sub = stripped[1:].upper()
                    if sub in ("HELP", "?"): self.execute_command("HELP;")
                    elif sub in ("TABLES", "SHOW TABLES"): self.show_tables()
                    elif sub in ("EXIT", "QUIT", "Q"): sys.exit(0)
                    elif sub.startswith("DESC "): self.execute_command(f"DESC {stripped[5:]};")
                    elif sub.startswith("INFO "): self.execute_command(f"INFO {stripped[5:]};")
                    else: print(f"Unknown shortcut: {stripped}. Type HELP; for commands.")
                    continue

                buffer.append(line)

                if stripped.endswith(";"):
                    full_cmd = "\n".join(buffer)
                    buffer = []
                    try:
                        self.execute_command(full_cmd)
                    except Exception as e:
                        print(f"Error: {e}")

            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break

def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("serve", "server"):
        port = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8765
        from mergendb.server.server import start_server
        start_server(port=port)
    else:
        cli = MergenCLI()
        cli.run()

if __name__ == "__main__":
    main()
