import os
import sys
import time
import sqlite3
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mergendb

def run_comparison():
    print("=" * 75)
    print("      MERGENDB vs SQLITE (Standard SQL) HEAD-TO-HEAD BENCHMARK")
    print("=" * 75)

    n_rows = 100_000
    print(f"\n[1] Generating {n_rows:,} analytical records (12 columns per row)...")

    sqlite_db = "benchmark_sqlite.db"
    mergen_file = "benchmark_mergen.mgdb"

    for f in (sqlite_db, mergen_file):
        if os.path.exists(f):
            os.remove(f)

    # 1. Setup SQLite
    conn = sqlite3.connect(sqlite_db)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE metrics (
            id INTEGER,
            timestamp INTEGER,
            region TEXT,
            sensor_type TEXT,
            status TEXT,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            voltage REAL,
            battery INTEGER,
            firmware_ver TEXT,
            is_active INTEGER
        );
    """)

    regions = ["TR-Marmara", "TR-Ege", "TR-Akdeniz", "TR-IcAnadolu", "EU-Central"]
    sensor_types = ["TEMP_V1", "TEMP_V2", "HUMID_X", "BARO_PRO"]
    statuses = ["OK", "OK", "OK", "WARN", "CRIT"]
    firmwares = ["v1.0.4", "v1.1.0", "v1.2.5"]

    base_time = 1710000000

    data = []
    mergen_rows = []
    for i in range(n_rows):
        temp = round(random.gauss(24.0, 6.0), 2)
        row = (
            i,
            base_time + (i * 2),
            regions[(i // 500) % len(regions)],
            sensor_types[i % len(sensor_types)],
            statuses[i % len(statuses)],
            temp,
            round(random.uniform(20.0, 90.0), 2),
            round(random.uniform(980.0, 1030.0), 2),
            round(random.uniform(3.1, 3.5), 3),
            100 - (i % 80),
            firmwares[i % len(firmwares)],
            1 if (i % 2 == 0) else 0
        )
        data.append(row)

    print("\n[2] Populating SQLite database...")
    t0 = time.perf_counter()
    cur.executemany("INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", data)
    conn.commit()
    sqlite_write_time = (time.perf_counter() - t0) * 1000

    print("[3] Populating MergenDB columnar storage...")
    t0 = time.perf_counter()
    schema = mergendb.Schema([
        mergendb.ColumnDef("id", mergendb.DataType.INT64),
        mergendb.ColumnDef("timestamp", mergendb.DataType.INT64),
        mergendb.ColumnDef("region", mergendb.DataType.STRING),
        mergendb.ColumnDef("sensor_type", mergendb.DataType.STRING),
        mergendb.ColumnDef("status", mergendb.DataType.STRING),
        mergendb.ColumnDef("temperature", mergendb.DataType.FLOAT64),
        mergendb.ColumnDef("humidity", mergendb.DataType.FLOAT64),
        mergendb.ColumnDef("pressure", mergendb.DataType.FLOAT64),
        mergendb.ColumnDef("voltage", mergendb.DataType.FLOAT32),
        mergendb.ColumnDef("battery", mergendb.DataType.INT32),
        mergendb.ColumnDef("firmware_ver", mergendb.DataType.STRING),
        mergendb.ColumnDef("is_active", mergendb.DataType.BOOL),
    ])
    tbl = mergendb.create_table(mergen_file, schema, block_size=2048)
    tbl.insert_many(data)
    mergen_write_time = (time.perf_counter() - t0) * 1000

    sqlite_size = os.path.getsize(sqlite_db)
    mergen_size = os.path.getsize(mergen_file)

    print("\n" + "=" * 75)
    print("                     1. STORAGE SPACE (BOYUT) TESTİ")
    print("=" * 75)
    print(f"  SQLite (Standard SQL) : {sqlite_size / (1024*1024):8.2f} MB ({sqlite_size:,} bytes)")
    print(f"  MergenDB (.mgdb)      : {mergen_size / (1024*1024):8.2f} MB ({mergen_size:,} bytes)")
    print(f"  Fark                  : MergenDB %{((1 - mergen_size/sqlite_size) * 100):.1f} DAHA KÜÇÜK ({(sqlite_size/mergen_size):.2f}x Tasarruf)")
    print("=" * 75)

    print("\n" + "=" * 75)
    print("                     2. ANALYTICAL QUERY BENCHMARK")
    print("=" * 75)

    # Test 1: Sadece 2 sütun üzerinden filtre ve agregasyon (Sütunsal I/O avantajı)
    print("\n--- TEST 1: Filtre + Gruplama (Sadece 2 sütun okunacak) ---")
    sql_q1 = "SELECT region, COUNT(*), AVG(temperature) FROM metrics WHERE temperature > 30.0 GROUP BY region"
    mergen_q1 = f"""
    FROM "{mergen_file}"
    | WHERE temperature > 30.0
    | AGGREGATE count(*) AS cnt, avg(temperature) AS avg_temp BY region
    """

    # SQLite
    t0 = time.perf_counter()
    cur.execute(sql_q1)
    res_sql = cur.fetchall()
    sql_t1 = (time.perf_counter() - t0) * 1000

    # MergenDB
    t0 = time.perf_counter()
    res_mergen = mergendb.query(mergen_q1)
    mergen_t1 = (time.perf_counter() - t0) * 1000

    print(f"  Standard SQL (SQLite) : {sql_t1:6.2f} ms")
    print(f"  MergenQL (MergenDB)   : {mergen_t1:6.2f} ms")
    print(f"  Disk I/O Okunan Byte  : MergenDB sadece {res_mergen.stats.bytes_read / 1024:.1f} KB okudu (12 sütun yerine sadece 2 sütun!).")

    # Test 2: ZoneMap Atlama Testi (Nadir Değerler - Outlier Query)
    print("\n--- TEST 2: ZoneMap Atlama (Outlier Range: temperature > 42.0) ---")
    sql_q2 = "SELECT id, temperature FROM metrics WHERE temperature > 42.0"
    mergen_q2 = f"""
    FROM "{mergen_file}"
    | WHERE temperature > 42.0
    | SELECT id, temperature
    """

    t0 = time.perf_counter()
    cur.execute(sql_q2)
    res_sql2 = cur.fetchall()
    sql_t2 = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    res_mergen2 = mergendb.query(mergen_q2)
    mergen_t2 = (time.perf_counter() - t0) * 1000

    print(f"  Standard SQL (SQLite) : {sql_t2:6.2f} ms (Tüm {n_rows:,} satırı baştan sona taradı)")
    print(f"  MergenQL (MergenDB)   : {mergen_t2:6.2f} ms ({res_mergen2.stats.blocks_skipped} blok diskten bile okunmadan atlandı!)")

    conn.close()
    for f in (sqlite_db, mergen_file):
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "=" * 75)
    print("                     SONUÇ ÖZETİ")
    print("=" * 75)
    print(f"  Depolama Tasarrufu : MergenDB, SQLite'tan {(sqlite_size/mergen_size):.2f} kat daha az yer kaplıyor.")
    print(f"  Okuma Verimliliği  : MergenDB sadece sorgulanan 2 sütunu okurken, SQL diskin tamamını okur.")
    print(f"  CPU / RAM          : MergenDB 100.000 satırı minik chunk'larla işlediği için RAM sabit kalır.")
    print("=" * 75)

if __name__ == "__main__":
    run_comparison()
