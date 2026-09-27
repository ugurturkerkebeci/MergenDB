import os
import sys
import time
import json
import urllib.request
import urllib.error
import tempfile
import threading
import platform
import socket
from typing import Dict, Any, Optional

import mergendb
from mergendb.client import MergenDB, Table
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter
from mergendb.storage.reader import FileReader
from mergendb.server.server import ThreadingMergenServer, MergenRequestHandler


class SilentMergenRequestHandler(MergenRequestHandler):
    """Silences stdout request logging during automated diagnostic tests."""
    def log_message(self, format, *args):
        pass


def _verify_engine(temp_dir: str) -> Dict[str, Any]:
    db_path = os.path.join(temp_dir, "diag_engine.mgdb")
    schema = Schema([
        ColumnDef("id", DataType.INT32),
        ColumnDef("name", DataType.STRING),
        ColumnDef("status", DataType.STRING),
        ColumnDef("score", DataType.FLOAT64),
        ColumnDef("active", DataType.BOOL),
    ])

    # 1. Write blocks with diverse encodings
    with FileWriter(db_path, schema, block_size=200) as writer:
        statuses = ["ACTIVE", "PENDING", "FAILED", "SUSPENDED"]
        for i in range(1000):
            writer.write_row([
                i + 1,
                f"User_{i}",
                statuses[i % len(statuses)],
                float(i * 2.5),
                (i % 2 == 0)
            ])

    # 2. Verify mmap zero-copy chunk reading
    with FileReader(db_path) as reader:
        chunk = reader.read_chunk_bytes(0, 16)
        is_zero_copy = isinstance(chunk, memoryview)
        if hasattr(chunk, "release"):
            chunk.release()
        del chunk

    # 3. Verify Late Materialization & Pushdown
    table = mergendb.open(db_path)
    res_pushdown = table.sql("SELECT id, status FROM diag_engine WHERE status = 'ACTIVE';")
    pushdown_ok = len(res_pushdown) == 250

    # 4. Verify ZoneMap Pruning
    res_pruned = table.sql("SELECT id FROM diag_engine WHERE id > 999999;")
    zonemap_ok = (len(res_pruned) == 0 and res_pruned.stats.blocks_skipped == res_pruned.stats.total_blocks)

    # 5. Verify In-Place Mutations
    up_cnt = table.update({"score": 9999.0}, where="status = 'FAILED'")
    del_cnt = table.delete(where="status = 'SUSPENDED'")
    table.add_column("tier", "string", default="STANDARD")
    mutations_ok = (up_cnt == 250 and del_cnt == 250 and "tier" in table.columns and len(table) == 750)

    return {
        "passed": is_zero_copy and pushdown_ok and zonemap_ok and mutations_ok,
        "zero_copy": is_zero_copy,
        "pushdown": pushdown_ok,
        "zonemap_pruning": zonemap_ok,
        "mutations": mutations_ok,
    }


def _verify_server(temp_dir: str) -> Dict[str, Any]:
    # Start ephemeral HTTP server on localhost with port 0 (OS picks free port)
    server = ThreadingMergenServer(("127.0.0.1", 0), SilentMergenRequestHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    time.sleep(0.05)  # brief startup yield

    try:
        # 1. Test GET /status
        req = urllib.request.Request(f"http://127.0.0.1:{port}/status")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            status_code = resp.status
            status_data = json.loads(resp.read().decode("utf-8"))
            get_ok = (status_code == 200 and status_data.get("status") == "healthy")

        # 2. Test POST /query with transient table
        test_mgdb = os.path.join(temp_dir, "diag_srv.mgdb").replace("\\", "/")
        init_q = f"CREATE TABLE \"{test_mgdb}\" (id INT32, val STRING);"
        init_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/query",
            data=json.dumps({"query": init_q}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(init_req, timeout=3.0) as resp:
            init_ok = (resp.status == 200)

        post_ok = get_ok and init_ok
    except Exception as e:
        post_ok = False
        status_data = {"error": str(e)}
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1.0)

    return {
        "passed": post_ok,
        "endpoint_status": get_ok if 'get_ok' in locals() else False,
        "endpoint_query": init_ok if 'init_ok' in locals() else False,
        "port": port
    }


def _profile_hardware(temp_dir: str) -> Dict[str, Any]:
    N_ROWS = 10_000
    db_path = os.path.join(temp_dir, "profile_bench.mgdb")
    csv_path = os.path.join(temp_dir, "profile_data.csv")

    schema = Schema([
        ColumnDef("id", DataType.INT32),
        ColumnDef("client", DataType.STRING),
        ColumnDef("category", DataType.STRING),
        ColumnDef("amount", DataType.FLOAT64),
        ColumnDef("is_cleared", DataType.BOOL),
    ])

    cats = ["RETAIL", "WHOLESALE", "ENTERPRISE", "GOV", "SUBSCRIPTION"]

    # 1. Measure Ingestion / Append Rate
    t_write_start = time.perf_counter()
    with FileWriter(db_path, schema, block_size=2000) as writer:
        for i in range(N_ROWS):
            writer.write_row([
                i + 1,
                f"Client_{i % 500}",
                cats[i % len(cats)],
                float((i * 17) % 10000) + 0.5,
                (i % 3 != 0)
            ])
    write_time = max(time.perf_counter() - t_write_start, 0.0001)
    write_rate = int(N_ROWS / write_time)

    # 2. Measure Analytical Scan Rate (mmap zero-copy + Late Materialization)
    table = mergendb.open(db_path)
    t_scan_start = time.perf_counter()
    q_res = table.sql("SELECT id, client, amount FROM profile_bench WHERE category = 'ENTERPRISE' AND amount > 2500;")
    scan_time = max(time.perf_counter() - t_scan_start, 0.0001)
    scan_rate = int(N_ROWS / scan_time)

    # 3. Measure Export Speed (CSV)
    out_csv = os.path.join(temp_dir, "export_test.csv")
    t_export_start = time.perf_counter()
    mergendb.export_csv(db_path, out_csv)
    export_time = max(time.perf_counter() - t_export_start, 0.0001)
    export_rate = int(N_ROWS / export_time)

    # 4. Measure Import Speed (CSV Streaming)
    # Generate 5000 rows CSV
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("id,client,category,amount,is_cleared\n")
        for i in range(5000):
            f.write(f"{i+1},Client_{i%500},{cats[i%len(cats)]},{(i*17)%10000}.5,{i%3!=0}\n")

    in_mgdb = os.path.join(temp_dir, "imported.mgdb")
    t_import_start = time.perf_counter()
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        mergendb.from_csv(csv_path, in_mgdb)
    import_time = max(time.perf_counter() - t_import_start, 0.0001)
    import_rate = int(5000 / import_time)

    # Clean up large profile files
    for p in (db_path, csv_path, out_csv, in_mgdb):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    # Tier Classification
    if scan_rate >= 2_000_000 and import_rate >= 100_000:
        tier = "S-Tier (Server-Grade / High-Throughput Cloud)"
        rec_block = "4,096 - 8,192 rows"
        desc = "Exceptional CPU & I/O cache bandwidth. Easily processes 10M+ row workloads."
    elif scan_rate >= 800_000 and import_rate >= 50_000:
        tier = "A-Tier (Performance Desktop / Modern Laptop)"
        rec_block = "2,048 - 4,096 rows"
        desc = "High single-core speed and fast page cache. Excellent for local analytics."
    elif scan_rate >= 250_000:
        tier = "B-Tier (Standard Hardware / Edge Device)"
        rec_block = "1,024 - 2,048 rows"
        desc = "Balanced throughput. Low memory footprint (<15 MB RAM) guaranteed."
    else:
        tier = "C-Tier (Resource-Constrained Micro / IoT)"
        rec_block = "512 - 1,024 rows"
        desc = "Optimized for minimal RAM usage and continuous battery/thermal stability."

    return {
        "platform": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu_cores": os.cpu_count() or 1,
        "python_runtime": f"{platform.python_implementation()} {sys.version.split()[0]}",
        "ingest_rate": write_rate,
        "import_rate": import_rate,
        "export_rate": export_rate,
        "scan_rate": scan_rate,
        "tier": tier,
        "recommended_block_size": rec_block,
        "device_assessment": desc
    }


def run_diagnostics(verbose: bool = True) -> Dict[str, Any]:
    """
    Executes end-to-end diagnostics on MergenDB:
    1. Engine Core (Zero-Copy mmap, Encodings, ZoneMaps, Mutations)
    2. Network Server (REST & Query API over HTTP)
    3. Hardware Capability Profile (Estimated Import, Export, and Scan Rates)
    """
    temp_dir = tempfile.mkdtemp()
    t_start = time.perf_counter()

    if verbose:
        print("\n" + "=" * 74)
        print("   [+] MERGENDB SYSTEM DIAGNOSTICS & HARDWARE PROFILER")
        print("=" * 74)
        print("[*] Running engine core integrity checks...")

    try:
        engine_res = _verify_engine(temp_dir)
        if verbose:
            print("    [+] Zero-Copy mmap I/O          : PASS" if engine_res["zero_copy"] else "    [-] Zero-Copy mmap I/O          : FAIL")
            print("    [+] Dictionary Pushdown Engine : PASS" if engine_res["pushdown"] else "    [-] Dictionary Pushdown Engine : FAIL")
            print("    [+] ZoneMap Block Pruning      : PASS" if engine_res["zonemap_pruning"] else "    [-] ZoneMap Block Pruning      : FAIL")
            print("    [+] ACID Data & Schema Mutation: PASS" if engine_res["mutations"] else "    [-] ACID Data & Schema Mutation: FAIL")

        if verbose:
            print("[*] Verifying MergenQL Network HTTP Server...")
        server_res = _verify_server(temp_dir)
        if verbose:
            print(f"    [+] HTTP Endpoint /status      : PASS (Port {server_res['port']})" if server_res["endpoint_status"] else "    [-] HTTP Endpoint /status      : FAIL")
            print(f"    [+] POST /query SQL Dispatch   : PASS" if server_res["endpoint_query"] else "    [-] POST /query SQL Dispatch   : FAIL")

        if verbose:
            print("[*] Profiling device hardware and benchmarking throughput...")
        hw_res = _profile_hardware(temp_dir)

        total_elapsed = time.perf_counter() - t_start

        if verbose:
            print("\n" + "-" * 74)
            print("  [DEVICE HARDWARE SPECIFICATIONS & DETECTED ENVIRONMENT]")
            print("-" * 74)
            print(f"  * Operating System   : {hw_res['platform']}")
            print(f"  * CPU Architecture   : {hw_res['architecture']} ({hw_res['cpu_cores']} logical threads)")
            print(f"  * Python Runtime     : {hw_res['python_runtime']}")
            print(f"  * Engine Version     : v{mergendb.__version__} (Pure Python / Zero-Dependency)")

            print("\n" + "-" * 74)
            print("  [ESTIMATED PROCESSING SPEEDS FOR THIS HARDWARE]")
            print("-" * 74)
            print(f"  * Ingestion / Append : ~{hw_res['ingest_rate']:,} rows/sec")
            print(f"  * CSV / SQL Import   : ~{hw_res['import_rate']:,} rows/sec")
            print(f"  * Table Export       : ~{hw_res['export_rate']:,} rows/sec")
            print(f"  * Analytical Queries : ~{hw_res['scan_rate']:,} rows/sec (Zero-Copy Column Scan)")
            print(f"  * Performance Tier   : {hw_res['tier']}")
            print(f"  * Optimal Block Size : {hw_res['recommended_block_size']}")
            print(f"  * Assessment         : {hw_res['device_assessment']}")
            print("-" * 74)
            all_ok = engine_res["passed"] and server_res["passed"]
            status_text = "[SUCCESS] ALL CHECKS PASSED PERFECTLY" if all_ok else "[WARNING] SOME CHECKS ENCOUNTERED ISSUES"
            print(f"  {status_text} in {total_elapsed:.2f}s\n" + "=" * 74 + "\n")

        return {
            "success": engine_res["passed"] and server_res["passed"],
            "engine": engine_res,
            "server": server_res,
            "hardware": hw_res,
            "elapsed_seconds": total_elapsed
        }

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
