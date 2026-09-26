import sys
import os
import time
from mergendb.client import MergenDB
from mergendb.storage.reader import FileReader

BANNER = r"""
  __  __                               _____  ____  
 |  \/  |                             |  __ \|  _ \ 
 | \  / | ___ _ __ __ _  ___ _ __     | |  | | |_) |
 | |\/| |/ _ \ '__/ _` |/ _ \ '_ \    | |  | |  _ < 
 | |  | |  __/ | | (_| |  __/ | | |   | |__| | |_) |
 |_|  |_|\___|_|  \__, |\___|_| |_|   |_____/|____/ 
                   __/ |                            
                  |___/   v0.1.0 (Edge Columnar Engine)

 Type your MergenQL pipeline query ending with ';' or type '.help' for commands.
"""

HELP_TEXT = """
Commands:
  .help                                      - Show this help menu
  .schema <file.mgdb>                        - Display table schema and block metadata
  .info <file.mgdb>                          - Show compression ratio & block stats
  .import sqlite <source.db> [tbl] <out.mgdb>- Convert SQLite database/table to MergenDB
  .import sql <dump.sql> <out.mgdb>          - Import SQL dump file into MergenDB
  .import csv <source.csv> <out.mgdb>        - Import CSV file into MergenDB
  .exit / .quit                              - Exit the REPL

Example Query:
  FROM "sensors.mgdb"
  | WHERE temperature > 35.0 AND room == "kitchen"
  | COMPUTE temp_f = (temperature * 1.8) + 32.0
  | SELECT room, temperature, temp_f
  | SORT temperature DESC
  | LIMIT 10;
"""

def handle_import(args: list):
    if len(args) < 3:
        print("Usage: .import <sqlite|sql|csv> <source_file> [options] <out.mgdb>")
        return

    subcmd = args[1].lower()
    from mergendb.io.importer import DataImporter

    try:
        t0 = time.perf_counter()
        if subcmd == "sqlite":
            if len(args) == 4:
                src, tbl, out = args[2], args[3], args[4] if len(args) > 4 else None
            src = args[2]
            if len(args) == 4:
                out = args[3]
                tbl = None
            else:
                tbl = args[3]
                out = args[4]
            count = DataImporter.from_sqlite(src, out, table_name=tbl)
            print(f"Successfully imported {count:,} rows from SQLite into {out} in {(time.perf_counter()-t0)*1000:.2f}ms")
        elif subcmd == "sql":
            src = args[2]
            out = args[3]
            count = DataImporter.from_sql_dump(src, out)
            print(f"Successfully imported {count:,} rows from SQL dump into {out} in {(time.perf_counter()-t0)*1000:.2f}ms")
        elif subcmd == "csv":
            src = args[2]
            out = args[3]
            count = DataImporter.from_csv(src, out)
            print(f"Successfully imported {count:,} rows from CSV into {out} in {(time.perf_counter()-t0)*1000:.2f}ms")
        else:
            print(f"Unknown import type '{subcmd}'. Choose sqlite, sql, or csv.")
    except Exception as e:
        print(f"Import failed: {e}")

def print_schema(filepath: str):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    with FileReader(filepath) as reader:
        print(f"\nTable: {filepath}")
        print(f"Total Rows: {reader.total_rows:,} | Blocks: {len(reader.blocks)}")
        print("\nColumns:")
        for col in reader.schema.columns:
            print(f"  - {col.name.ljust(20)} : {col.data_type.name}")
        print()

def print_info(filepath: str):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    file_size = os.path.getsize(filepath)
    with FileReader(filepath) as reader:
        total_uncompressed = 0
        total_compressed = 0
        for b in reader.blocks:
            for c in b.columns.values():
                total_uncompressed += c.uncompressed_bytes
                total_compressed += c.compressed_bytes

        ratio = (total_uncompressed / total_compressed) if total_compressed > 0 else 1.0
        saved_pct = ((1.0 - (total_compressed / total_uncompressed)) * 100.0) if total_uncompressed > 0 else 0.0

        print(f"\n--- Storage Footprint: {filepath} ---")
        print(f"Total Rows           : {reader.total_rows:,}")
        print(f"Total Blocks         : {len(reader.blocks)}")
        print(f"File Size on Disk    : {file_size / 1024:.2f} KB ({file_size:,} bytes)")
        print(f"Raw Uncompressed     : {total_uncompressed / 1024:.2f} KB")
        print(f"Compressed Data      : {total_compressed / 1024:.2f} KB")
        print(f"Compression Ratio    : {ratio:.2f}x (Saved {saved_pct:.1f}% space)")
        print()

def main():
    print(BANNER)
    buffer = []

    while True:
        try:
            prompt = "mergen> " if not buffer else "    ...> "
            line = input(prompt)

            stripped = line.strip()

            if not buffer and stripped.startswith("."):
                parts = stripped.split()
                cmd = parts[0].lower()
                if cmd in (".exit", ".quit"):
                    print("Görüşmek üzere!")
                    break
                elif cmd == ".help":
                    print(HELP_TEXT)
                elif cmd == ".schema" and len(parts) > 1:
                    print_schema(parts[1])
                elif cmd == ".info" and len(parts) > 1:
                    print_info(parts[1])
                elif cmd == ".import":
                    handle_import(parts)
                else:
                    print(f"Unknown command or missing argument: {stripped}")
                continue

            buffer.append(line)

            # Query ends with semicolon
            if stripped.endswith(";"):
                query_str = "\n".join(buffer).rstrip(";")
                buffer = []
                try:
                    result = MergenDB.query(query_str)
                    print(result.display())
                except Exception as e:
                    print(f"Error: {e}")
                print()

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()
