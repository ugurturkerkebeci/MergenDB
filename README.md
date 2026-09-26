<p align="center">
  <img src="https://raw.githubusercontent.com/ugurturkerkebeci/MergenDB/main/docs/images/banner.jpg" alt="MergenDB Banner" width="100%" />
</p>

# 🏹 MergenDB

<p align="center">
  <a href="https://pypi.org/project/mergendb/"><img src="https://img.shields.io/pypi/v/mergendb.svg?color=blue&style=for-the-badge" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/mergendb/"><img src="https://img.shields.io/pypi/pyversions/mergendb.svg?color=blue&style=for-the-badge" alt="Python Versions" /></a>
  <a href="https://github.com/ugurturkerkebeci/MergenDB/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License: MIT" /></a>
  <a href="https://github.com/ugurturkerkebeci"><img src="https://img.shields.io/badge/Author-Uğur%20Türker%20Kebeci-orange.svg?style=for-the-badge" alt="Author" /></a>
  <img src="https://img.shields.io/badge/Compression-Up%20to%2016x-brightgreen.svg?style=for-the-badge" alt="Compression" />
</p>

> **"Big Data on Small Hardware"**  
> **MergenDB** is an ultra-compact, columnar, embedded database engine and custom query language (**MergenQL**) designed to run analytical workloads on resource-constrained systems (Raspberry Pi, IoT gateways, low-end VPS, and edge devices) with maximum compression, zero memory exhaustion, and blazingly fast execution.
>
> 👨‍💻 **Author & Lead Developer:** **Uğur Türker Kebeci** ([@ugurturkerkebeci](https://github.com/ugurturkerkebeci))

Named after **Mergen**, the ancient Turkic deity of wisdom, precision, and archery—who never misses his target.

---

## 📦 Installation

Install MergenDB directly from PyPI:

```bash
pip install mergendb
```

*(MergenDB has **zero external dependencies** for its core engine—runs out of the box on Python 3.8+!)*

---

## ⚡ Core Philosophy & Architecture

Traditional databases (MySQL, PostgreSQL, SQLite) store data in a **row-oriented** layout. If a table has 40 columns and you only query `temperature` and `room`, row-oriented engines must read all 40 columns from disk, wasting massive I/O bandwidth and RAM.

**MergenDB** redesigns storage from the silicon up:

```text
  [ Raw Input Records (SQL / CSV / JSON / Dicts) ]
                        │
                        ▼
       [ Vector Chunker (1024 - 4096 rows) ]
                        │
                        ▼
       [ Columnar Vertical Partitioning ]
                        │
  ┌─────────────────────┴──────────────────────┐
  │         Adaptive Compression Engine         │
  │  • Bit-Packing      (8 Bools / Byte)       │
  │  • Frame-of-Ref/Delta (Timestamps & IDs)   │
  │  • Dictionary       (Repeated Strings)     │
  │  • Run-Length (RLE) (Sequential Duplicates)│
  └─────────────────────┬──────────────────────┘
                        │
                        ▼
   [ ZoneMap Indices (Min / Max per Chunk) ]
                        │
                        ▼
      [ .mgdb Columnar Binary Disk Storage ]
```

### 1. 🗜️ Adaptive Hardware-Level Encodings
* **Bit-Packing:** 8 boolean values are packed into a single byte (**8x compression**).
* **Delta / Frame-of-Reference (FoR):** Art arda gelen ID'ler veya zaman damgalarında farklar saklanır (8-byte tamsayı yerine 1-2 byte).
* **Dictionary Encoding:** Tekrar eden metinler (status, category, city) 1-2 byte'lık ID tablolarına eşlenir.
* **Run-Length Encoding (RLE):** Art arda gelen aynı değerler tek bir sayaçla saklanır.
* **Adaptive Selection:** MergenDB her blokta en az yer kaplayan algoritmayı otomatik olarak tespit edip seçer.

### 2. 🎯 ZoneMap Indexing (Zero I/O Block Pruning)
Her veri bloğu minik bir `min_val` ve `max_val` üstverisi taşır. Eğer sorgunuz `WHERE temperature > 40` ise ve bloğun tavanı `35` ise, **MergenDB o bloğu diskten bile okumadan atlar**.

### 3. ✂️ Column Pruning
Tabloda 50 sütun olsa bile sorgunuz 2 sütun istediyse, kalan 48 sütun diskten **hiç okunmaz**. Disk I/O darboğazı %90+ oranında yok edilir.

### 4. 🌊 Vectorized & Chunked Streaming (Zero OOM)
Veriler 2048'lik dilimler (chunk) halinde boru hattından akar. **109 Milyonluk dev bir veritabanı bile 512 MB RAM'li küçük bir cihazda belleği patlatmadan (Out Of Memory olmadan) işlenir.**

---

## 📊 Benchmark: MergenDB vs SQLite vs JSON

Tested on **100,000 analytical telemetry records** (12 columns per row):

| Depolama Formatı | Disk Boyutu | Boyut Oranı | Alan Tasarrufu | Disk I/O Okuma |
| :--- | :--- | :--- | :--- | :--- |
| **JSON Lines (`.jsonl`)** | ~ 19.5 MB | 1.00x | %0.0 | ~ 19.5 MB |
| **Standard SQL (SQLite)** | 8.11 MB | 2.40x | %58.4 | 8.11 MB (Tüm tablo) |
| **MergenDB (`.mgdb`)** | **1.65 MB** | **11.80x** | **%91.5** | **0.29 MB (Sadece 2 sütun!)** |

> 🚀 **Sonuç:** MergenDB SQLite'tan **5 kat**, JSON'dan **12 kat daha küçüktür**. Analitik sorgularda diski **27 kat daha az** yorar!

---

## 📖 MergenQL & Komut Başvuru Kılavuzu (Cheat Sheet)

MergenDB'nin özgün sorgu dili **MergenQL**, verinin mantıksal olarak soldan sağa aktığı boru hattı (`|`) mimarisine dayanır.

### 1. Boru Hattı Aşamaları (Pipeline Stages)

| Komut | Açıklama | Örnek |
| :--- | :--- | :--- |
| `FROM` | Kaynak `.mgdb` dosyasını belirtir. | `FROM "telemetry.mgdb"` |
| `WHERE` | Satırları filtreler (ZoneMap uyumludur). | `\| WHERE temp > 30.0 AND room == "Lab"` |
| `COMPUTE` | Yeni hesaplanmış sütun üretir. | `\| COMPUTE temp_f = (temp * 1.8) + 32.0` |
| `SELECT` | Yansıtılacak sütunları seçer (Column Pruning). | `\| SELECT device_id, temp, temp_f` |
| `AGGREGATE` | Özet fonksiyonları çalıştırır. | `\| AGGREGATE avg(temp) AS ortalama BY room` |
| `SORT` | Sıralama yapar (`ASC` veya `DESC`). | `\| SORT ortalama DESC` |
| `LIMIT` | Sonuç satır sayısını sınırlar. | `\| LIMIT 10` |

### 2. Desteklenen Filtreleme Operatörleri (`WHERE`)
* **Karşılaştırma:** `==`, `=`, `!=`, `<>`, `<`, `<=`, `>`, `>=`
* **Mantıksal:** `AND`, `OR`
* **Metin Arama:** `LIKE` *(SQL `%` ve `_` joker karakterlerini destekler)*  
  *Örnek:* `| WHERE room LIKE "kit%"` veya `| WHERE email LIKE "%@gmail.com"`

### 3. Agregasyon Fonksiyonları (`AGGREGATE`)
* `count(*)` veya `count(col)`: Satır adedi
* `sum(col)`: Toplam
* `avg(col)`: Aritmetik ortalama
* `min(col)`: En küçük değer
* `max(col)`: En büyük değer
* `median(col)`: Medyan (ortanca) değer
* `stddev(col)`: Standart sapma

---

## 📥 SQL, SQLite & CSV İçe / Dışa Aktarma (High-Performance Import & Export)

MergenDB, gigabaytlarca veriyi (1 GB, 50 GB, 500 GB) dönüştürürken **canlı 0-100% ilerleme çubuğu** sunar ve **500 MB RAM'e sahip en mütevazı cihazlarda bile** asla belleği tüketmez (O(1) memory, tepe bellek < 20 MB RAM).

```text
[*] Importing SQL: 4,500,000 / 9,376,881 rows [============>-----------]  48.0% | 285,400 rows/s | ETA: 17s
[+] Successfully imported 9,376,881 rows in 32.80s (285,880 rows/s)!
```

### 1. phpMyAdmin veya MySQL Dump Dosyalarını Aktarma (`.sql`)
phpMyAdmin, mysqldump veya Adminer'den dışa aktarılan `.sql` dosyalarını tek hamlede içe aktarın:
* **Çok Satırlı (Multiline) Kayıtlar:** phpMyAdmin'in satırlara böldüğü INSERT ifadelerini ve metin içindeki satır sonlarını eksiksiz birleştirir.
* **Tırnak Duyarlı (Quote-Aware) Parite:** Parantez içeren metinleri (`'Kadıköy (Merkez)'`) ve kaçış karakterlerini (`\'`, `\"`) hatasız işler.
* **Otomatik Temizleme:** MySQL'e özel `ENGINE=InnoDB`, `AUTO_INCREMENT`, `LOCK TABLES`, `/*!...` ve `#` yorum satırları otomatik filtrelenir.

```python
import mergendb

table = mergendb.from_sql_dump("phpmyadmin_dump.sql", "database.mgdb")
print(f"Toplam {table.row_count:,} satır MergenDB'ye aktarıldı!")
```

### 2. SQLite Veritabanlarını Aktarma (`.db`, `.sqlite`)
Tüm SQLite veri tiplerini (INTEGER, REAL, TEXT, BLOB/Binary, DATETIME, TIMESTAMP) otomatik dönüştürür.
```python
table = mergendb.from_sqlite("legacy.db", "orders.mgdb", table_name="orders")
```

### 3. CSV Dosyalarını Otomatik Tip Algılama ile Aktarma
```python
table = mergendb.from_csv("sensor_data.csv", "sensor_data.mgdb")
```

### 4. Canlı DB-API 2.0 (PostgreSQL, MySQL, Oracle, MSSQL) Bağlantılarından Çekme
```python
import pymysql
from mergendb.io.importer import DataImporter

conn = pymysql.connect(host="localhost", user="root", password="", database="eticaret")
cur = conn.cursor()
cur.execute("SELECT * FROM siparisler")

DataImporter.from_cursor(cur, output_mgdb_path="siparisler.mgdb")
```

### 5. Dışa Aktarma (Export: CSV, JSONL, SQL Dump)
MergenDB tablolarını canlı yüzde ve hız çubuğuyla saniyeler içinde dışa aktarabilirsiniz:
```sql
EXPORT orders.mgdb TO CSV "orders_export.csv";
EXPORT orders.mgdb TO JSON "orders_export.jsonl";
EXPORT orders.mgdb TO SQL "orders_backup.sql";
```
*(SQL dışa aktarımı, hem `CREATE TABLE` DDL şemasını hem de 500'lük gruplar halinde optimize edilmiş standart `INSERT INTO` ifadelerini otomatik üretir).*

---

## 💻 İnteraktif Terminal Kabuğu (REPL CLI) & SQL Desteği

MergenDB, terminalden tek bir komutla açılan, tıpkı MySQL CLI gibi zengin komut setine sahip bir REPL kabuğu içerir:

```bash
# Terminalden anında başlatın:
mergen
# veya:
python -m mergendb.cli.repl
```

```text
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
      / /__/_/  |  \_\__\ \                            |___/  v0.4.4 (Lightning Engine)
     /     \    |    /     \
    /_______\   |   /_______\         =[ MergenDB - Lightning Columnar Database      ]
             \  |  /           + -- --=[ 16 Adaptive Hardware Encodings (Up to 16x)  ]
              \ | /            + -- --=[ ZoneMap Zero-I/O Indexing (100M+ Rows Safe) ]
               \|/             + -- --=[ Network SQL/MergenQL Server on Port 8765    ]
                |              + -- --=[ Zero External Dependencies | Pure Speed     ]
                '              + -- --=[ Author: Ugur Turker Kebeci (@ugurturkerkebeci)

                   "Target Acquired. Zero Waste. Pure Speed."
    Type SQL or MergenQL commands ending with ';'. Type 'HELP;' for command list.
```

### 🛠️ MySQL Benzeri Veritabanı Yönetim Komutları

| Komut | Açıklama |
| :--- | :--- |
| `SHOW TABLES;` | Mevcut dizindeki tüm `.mgdb` tablolarını, satır sayılarını ve boyutlarını listeler. |
| `SHOW DATABASES;` | Veritabanı dizinlerini listeler. |
| `DESCRIBE <table>;` (veya `DESC`) | Tablonun sütunlarını, veri tiplerini ve null durumlarını gösterir. |
| `USE <tablo>;` | Aktif tablo bağlamını belirler. Artık sorgularda tablo adı yazmadan sorgulayabilirsiniz. |
| `COUNT <tablo>;` | Tablodaki toplam kayıt sayısını disk bloklarını taramadan anında O(1) sürede döner. |
| `TRUNCATE TABLE <tablo>;` | Tablo şemasını koruyarak tüm satırları sıfırlar. |
| `RENAME TABLE <eski> TO <yeni>;` | Tabloyu yeniden adlandırır. |
| `OPTIMIZE TABLE <tablo>;` | Veri bloklarını yeniden sıkıştırır ve birleştirir. |
| `EXPLAIN <sorgu>;` | Sorgunun çalıştırma planını, taranacak ve atlanacak blok sayılarını gösterir. |
| `IMPORT SQL <dosya.sql> <tablo.mgdb>;` | phpMyAdmin / MySQL dump dosyasını canlı ilerleme çubuğuyla içe aktarır. |
| `IMPORT SQLITE <dosya.db> [tablo] <cikti.mgdb>;` | SQLite veritabanını canlı sayaçla MergenDB'ye dönüştürür. |
| `IMPORT CSV <dosya.csv> <tablo.mgdb>;` | CSV dosyasını otomatik tip tespitiyle içe aktarır. |
| `EXPORT <table> TO CSV <dosya.csv>;` | Tabloyu CSV formatında dışa aktarır. |
| `EXPORT <table> TO JSON <dosya.jsonl>;` | Tabloyu JSON Lines formatında dışa aktarır. |
| `EXPORT <table> TO SQL <dosya.sql>;` | Tabloyu tam şemalı SQL dump olarak dışa aktarır. |
| `SERVE [port];` | CLI içinden doğrudan arka planda MergenQL Ağ Sunucusunu başlatır. |
| `BENCHMARK <tablo>;` | Tablo üzerinde canlı I/O ve sorgu okuma hız testi yapar. |
| `INFO <tablo>;` | Tablonun sıkıştırma oranını ve ZoneMap telemetrisini raporlar. |

---

## 🌐 MergenDB Network Server (MySQL/PostgreSQL Tarzı Ağ Sunucusu)

MergenDB yalnızca gömülü (embedded) bir kütüphane değil, aynı zamanda uzaktan REST & JSON üzerinden sorgu çalıştırabileceğiniz bir **Veritabanı Sunucusudur**.

### Sunucuyu Başlatma

```bash
# Bağımsız sunucuyu 8765 portunda başlatın:
mergendb-server --port 8765

# Veya Python içerisinden:
mergendb serve 8765
```

```text
======================================================================
   🏹 MERGENDB SERVER (MergenQL & SQL Network Engine)
======================================================================
  * Status        : RUNNING
  * Listening on  : http://0.0.0.0:8765
  * Local Web API : http://localhost:8765
  * Query Endpoint: POST http://localhost:8765/query
  * Working Dir   : /data/db
======================================================================
```

### Uzaktan Sorgu Gönderme (HTTP & cURL)

Herhangi bir dilden (Python, Node.js, Go, PHP, C# vb.) standart HTTP POST isteğiyle MergenQL veya SQL sorguları çalıştırabilirsiniz:

```bash
curl -X POST http://localhost:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT user_id, email, city FROM users WHERE city == \"Istanbul\" LIMIT 10;"}'
```

**JSON Yanıtı:**
```json
{
  "success": true,
  "columns": ["user_id", "email", "city"],
  "rows": [
    [1001, "ugur@example.com", "Istanbul"],
    [1042, "ali@example.com", "Istanbul"]
  ],
  "stats": {
    "execution_time_ms": 1.45,
    "rows_returned": 2,
    "blocks_scanned": 1,
    "blocks_skipped": 48,
    "bytes_read": 1024
  }
}
```

---

## 🧪 Test Paketini Çalıştırma

```bash
python -m unittest discover tests
```
*(Tüm 18 birim testi sıfır hata ile geçmektedir).*

---

## 👨‍💻 Yazar & İletişim

* **Geliştirici:** Uğur Türker Kebeci
* **GitHub:** [@ugurturkerkebeci](https://github.com/ugurturkerkebeci)
* **Proje Deposu:** [https://github.com/ugurturkerkebeci/MergenDB](https://github.com/ugurturkerkebeci/MergenDB)
* **PyPI:** [https://pypi.org/project/mergendb/](https://pypi.org/project/mergendb/)

## 📄 Lisans
Bu proje **MIT Lisansı** ile lisanslanmıştır. Açık kaynak dünyasına ve düşük donanımlı sistemlerde büyük veri analitiğine katkı sağlamak amacıyla geliştirilmiştir.
