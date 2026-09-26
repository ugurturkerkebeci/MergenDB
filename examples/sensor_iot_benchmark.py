import os
import time
import json
import csv
import random
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mergendb

def run_benchmark():
    print("=" * 70)
    print("      MERGENDB COMPRESSION & PERFORMANCE BENCHMARK")
    print("=" * 70)

    num_rows = 50_000
    print(f"\n[1] Generating {num_rows:,} realistic IoT sensor records...")

    mgdb_file = "iot_telemetry.mgdb"
    json_file = "iot_telemetry.jsonl"
    csv_file = "iot_telemetry.csv"

    # Schema
    schema = mergendb.Schema([
        mergendb.ColumnDef("timestamp", mergendb.DataType.INT64),
        mergendb.ColumnDef("device_id", mergendb.DataType.STRING),
        mergendb.ColumnDef("building", mergendb.DataType.STRING),
        mergendb.ColumnDef("room", mergendb.DataType.STRING),
        mergendb.ColumnDef("temperature", mergendb.DataType.FLOAT64),
        mergendb.ColumnDef("humidity", mergendb.DataType.FLOAT64),
        mergendb.ColumnDef("voltage", mergendb.DataType.FLOAT32),
        mergendb.ColumnDef("status", mergendb.DataType.STRING),
        mergendb.ColumnDef("is_alert", mergendb.DataType.BOOL)
    ])

    buildings = ["HQ-Tower", "Warehouse-A", "Warehouse-B", "DataCenter-1"]
    rooms = ["ServerRoom", "Office-101", "Lab-2", "Storage-Main", "HVAC-Plant"]
    statuses = ["HEALTHY", "WARNING", "STANDBY", "CRITICAL"]

    base_time = 1710000000

    rows = []
    for i in range(num_rows):
        temp = round(random.gauss(23.0, 5.0), 2)
        rows.append({
            "timestamp": base_time + (i * 5),
            "device_id": f"device_{i % 50:03d}",
            "building": buildings[(i // 500) % len(buildings)],
            "room": rooms[i % len(rooms)],
            "temperature": temp,
            "humidity": round(random.uniform(30.0, 75.0), 2),
            "voltage": round(random.uniform(3.2, 3.4), 3),
            "status": "CRITICAL" if temp > 35.0 else random.choice(statuses),
            "is_alert": temp > 35.0
        })

    # 1. Write MergenDB
    print("\n[2] Writing to MergenDB (.mgdb) columnar storage...")
    t0 = time.perf_counter()
    table = mergendb.create_table(mgdb_file, schema, block_size=2000)
    table.insert_many(rows)
    mgdb_write_time = (time.perf_counter() - t0) * 1000

    # 2. Write CSV
    print("[3] Writing to Standard CSV (.csv)...")
    t0 = time.perf_counter()
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[c.name for c in schema.columns])
        writer.writeheader()
        writer.writerows(rows)
    csv_write_time = (time.perf_counter() - t0) * 1000

    # 3. Write JSONL
    print("[4] Writing to JSON Lines (.jsonl)...")
    t0 = time.perf_counter()
    with open(json_file, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    json_write_time = (time.perf_counter() - t0) * 1000

    # Storage Comparison
    mgdb_size = os.path.getsize(mgdb_file)
    csv_size = os.path.getsize(csv_file)
    json_size = os.path.getsize(json_file)

    print("\n" + "=" * 70)
    print("                   STORAGE FOOTPRINT COMPARISON")
    print("=" * 70)
    print(f"  Format         | File Size (KB)  | Ratio vs JSON | Space Saved")
    print(f"  ---------------|-----------------|---------------|------------")
    print(f"  JSON Lines     | {json_size / 1024:12.1f} KB |         1.00x |       0.0 %")
    print(f"  Standard CSV   | {csv_size / 1024:12.1f} KB | {(json_size / csv_size):12.2f}x | {(1.0 - csv_size / json_size) * 100:9.1f} %")
    print(f"  MergenDB (.mgdb)| {mgdb_size / 1024:12.1f} KB | {(json_size / mgdb_size):12.2f}x | {(1.0 - mgdb_size / json_size) * 100:9.1f} %")
    print("=" * 70)

    # Query Performance: Filter + Aggregation
    print("\n[5] Executing Analytical MergenQL Query:")
    query_str = f"""
    FROM "{mgdb_file}"
    | WHERE temperature > 32.0 AND is_alert == true
    | AGGREGATE count(*) AS alert_count, avg(temperature) AS avg_temp, max(temperature) AS max_temp BY building
    | SORT alert_count DESC
    """
    print(query_str.strip())
    print("-" * 70)

    t0 = time.perf_counter()
    result = mergendb.query(query_str)
    query_time = (time.perf_counter() - t0) * 1000

    print(result.display())

    # Cleanup temporary test files
    for fpath in (mgdb_file, json_file, csv_file):
        if os.path.exists(fpath):
            os.remove(fpath)

    print("\nBenchmark successfully finished!")

if __name__ == "__main__":
    run_benchmark()
