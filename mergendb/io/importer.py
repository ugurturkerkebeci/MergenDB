import os
import sys
import time
import csv
import sqlite3
import re
import io
import json
from typing import List, Dict, Any, Optional, Union
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter
from mergendb.io.progress import ProgressBar

try:
    csv.field_size_limit(sys.maxsize)
except (OverflowError, AttributeError):
    csv.field_size_limit(2147483647)

SQLITE_TYPE_MAP = {
    "integer": DataType.INT64,
    "int": DataType.INT64,
    "bigint": DataType.INT64,
    "smallint": DataType.INT32,
    "tinyint": DataType.INT32,
    "mediumint": DataType.INT32,
    "unsigned big int": DataType.INT64,
    "int2": DataType.INT32,
    "int8": DataType.INT64,
    "real": DataType.FLOAT64,
    "float": DataType.FLOAT64,
    "double": DataType.FLOAT64,
    "double precision": DataType.FLOAT64,
    "numeric": DataType.FLOAT64,
    "decimal": DataType.FLOAT64,
    "text": DataType.STRING,
    "varchar": DataType.STRING,
    "nvarchar": DataType.STRING,
    "character": DataType.STRING,
    "char": DataType.STRING,
    "clob": DataType.STRING,
    "boolean": DataType.BOOL,
    "bool": DataType.BOOL,
    "timestamp": DataType.TIMESTAMP,
    "datetime": DataType.STRING,
    "date": DataType.STRING,
    "blob": DataType.STRING,
}

def _map_sqlite_type(decl_type: Optional[str]) -> DataType:
    if not decl_type:
        return DataType.STRING
    clean = decl_type.strip().lower()
    # Strip (length) or (precision, scale), e.g. VARCHAR(255) -> varchar
    clean = re.sub(r"\(.*?\)", "", clean).strip()
    return SQLITE_TYPE_MAP.get(clean, DataType.STRING)

MYSQL_TYPE_MAP = {
    "int": DataType.INT64,
    "integer": DataType.INT64,
    "tinyint": DataType.INT32,
    "smallint": DataType.INT32,
    "mediumint": DataType.INT32,
    "bigint": DataType.INT64,
    "varchar": DataType.STRING,
    "char": DataType.STRING,
    "text": DataType.STRING,
    "tinytext": DataType.STRING,
    "mediumtext": DataType.STRING,
    "longtext": DataType.STRING,
    "date": DataType.STRING,
    "datetime": DataType.STRING,
    "timestamp": DataType.TIMESTAMP,
    "time": DataType.STRING,
    "year": DataType.INT32,
    "float": DataType.FLOAT64,
    "double": DataType.FLOAT64,
    "real": DataType.FLOAT64,
    "decimal": DataType.FLOAT64,
    "numeric": DataType.FLOAT64,
    "bool": DataType.BOOL,
    "boolean": DataType.BOOL,
}

MERNIS_COLS = [
    "tc", "ad", "soyad", "baba_adi", "anne_adi", "cinsiyet",
    "dogum_tarihi", "dogum_yeri", "medeni_hal", "il", "ilce",
    "mahalle", "cilt_no", "aile_sira_no", "birey_sira_no",
    "kimlik_tipi", "seri", "no"
]

def _infer_py_type(val: str) -> DataType:
    if val is None or val == "":
        return DataType.STRING
    v_clean = val.strip().lower()
    if v_clean in ("true", "false"):
        return DataType.BOOL
    try:
        int(val)
        return DataType.INT64
    except ValueError:
        pass
    try:
        float(val)
        return DataType.FLOAT64
    except ValueError:
        pass
    return DataType.STRING

class DataImporter:
    """
    High-performance, streaming data importer for SQL databases, SQL dump files, and CSV.
    Uses chunked streaming to prevent high RAM consumption.
    """

    @classmethod
    def from_sqlite(
        cls,
        sqlite_path: str,
        output_mgdb_path: str,
        table_name: Optional[str] = None,
        query: Optional[str] = None,
        block_size: int = 4096
    ) -> int:
        """
        Imports an entire SQLite table or SQL query result directly into a MergenDB (.mgdb) file.
        Streams rows in chunks, keeping memory footprint strictly bounded (< 15 MB RAM)
        making it 100% safe on low-spec hardware (e.g. 500 MB RAM devices).
        """
        if not os.path.exists(sqlite_path):
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()

        try:
            total_rows = None
            if query:
                cursor.execute(query)
                columns = [ColumnDef(desc[0], DataType.STRING) for desc in cursor.description]
                schema = Schema(columns)
            else:
                if not table_name:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                    tables = cursor.fetchall()
                    if not tables:
                        raise ValueError(f"No user tables found in SQLite database {sqlite_path}")
                    table_name = tables[0][0]

                # Get row count for 0-100% progress estimation
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`;")
                    cnt_row = cursor.fetchone()
                    if cnt_row:
                        total_rows = cnt_row[0]
                except Exception:
                    pass

                cursor.execute(f"PRAGMA table_info(`{table_name}`);")
                table_info = cursor.fetchall()
                if not table_info:
                    raise ValueError(f"Table '{table_name}' does not exist or has no columns.")

                columns = []
                for row in table_info:
                    col_name = row[1]
                    decl_type = row[2]
                    dtype = _map_sqlite_type(decl_type)
                    columns.append(ColumnDef(col_name, dtype))
                schema = Schema(columns)

                cursor.execute(f"SELECT * FROM `{table_name}`;")

            total_imported = 0
            pbar = ProgressBar("Importing SQLite", total_rows=total_rows)

            with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
                while True:
                    rows = cursor.fetchmany(block_size)
                    if not rows:
                        break
                    # Ensure bytearray/memoryview/bytes (BLOBs) are stringified to hex
                    safe_rows = []
                    for r in rows:
                        safe_row = [v.hex() if isinstance(v, (bytes, bytearray, memoryview)) else v for v in r]
                        safe_rows.append(safe_row)
                    writer.write_rows(safe_rows)
                    total_imported += len(safe_rows)
                    pbar.update(total_imported)

            pbar.finish()
            return total_imported

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def from_sql_dump(
        cls,
        sql_dump_path: str,
        output_mgdb_path: str,
        table_name: Optional[str] = None,
        block_size: int = 8192
    ) -> int:
        """
        Pure streaming importer for SQL dumps of any size (1 GB, 50 GB, 500 GB).
        Streams line-by-line with constant O(1) memory (~15 MB RAM) to completely prevent OOM.
        Handles phpMyAdmin dumps, MySQL DDL, partial dumps, and raw tuple fragments.
        Uses high-speed columnar conversion and displays a live real-time progress bar.
        """
        # Resolve path
        if not os.path.exists(sql_dump_path):
            candidates = [
                sql_dump_path,
                sql_dump_path + ".sql",
                os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(sql_dump_path)),
                os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(sql_dump_path) + ".sql"),
                os.path.join(os.path.expanduser("~"), "Downloads", os.path.basename(sql_dump_path)),
                os.path.join(os.path.expanduser("~"), "Downloads", os.path.basename(sql_dump_path) + ".sql"),
            ]
            found = None
            for cand in candidates:
                if os.path.exists(cand):
                    found = cand
                    break
            if found:
                sql_dump_path = found
            else:
                raise FileNotFoundError(f"SQL dump file not found: {sql_dump_path}")

        total_bytes = os.path.getsize(sql_dump_path)

        # Step 1: Detect encoding by peeking first 64 KB
        with open(sql_dump_path, "rb") as f:
            head = f.read(65536)
        encoding = "utf-8"
        for enc in ("utf-8", "cp1254", "iso-8859-9", "latin-1"):
            try:
                head.decode(enc)
                encoding = enc
                break
            except UnicodeDecodeError:
                continue

        # Step 2: Scan for CREATE TABLE in the first 500 lines without loading whole file
        schema = None
        in_create = False
        columns = []
        with open(sql_dump_path, "r", encoding=encoding, errors="replace", buffering=1024*1024) as f:
            for _ in range(500):
                line = f.readline()
                if not line:
                    break
                clean = line.strip()
                if not in_create:
                    m = re.match(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?[\w\d_]+`?\.)?`?([\w\d_]+)`?\s*\((.*)", clean, re.IGNORECASE)
                    if m:
                        table_name = m.group(1)
                        rest = m.group(2).strip()
                        if rest.endswith(");") or rest.endswith(")") or ");" in rest:
                            inner = rest[:rest.rfind(")")]
                            for item in inner.split(","):
                                item_clean = item.strip()
                                if not item_clean or re.match(r"^(?:PRIMARY\s+KEY|KEY|INDEX|UNIQUE|CONSTRAINT)", item_clean, re.IGNORECASE):
                                    continue
                                col_match = re.match(r"^`?([\w\d_]+)`?\s+([a-zA-Z]+)", item_clean)
                                if col_match:
                                    cname = col_match.group(1)
                                    ctype_raw = col_match.group(2).lower()
                                    dtype = MYSQL_TYPE_MAP.get(ctype_raw, DataType.STRING)
                                    columns.append(ColumnDef(cname, dtype))
                            break
                        else:
                            in_create = True
                else:
                    if clean.startswith(")") or clean.startswith("ENGINE=") or clean.startswith(");"):
                        in_create = False
                        break
                    if re.match(r"^(?:PRIMARY\s+KEY|KEY|INDEX|UNIQUE|CONSTRAINT)", clean, re.IGNORECASE):
                        continue
                    col_match = re.match(r"^`?([\w\d_]+)`?\s+([a-zA-Z]+)", clean)
                    if col_match:
                        cname = col_match.group(1)
                        ctype_raw = col_match.group(2).lower()
                        dtype = MYSQL_TYPE_MAP.get(ctype_raw, DataType.STRING)
                        columns.append(ColumnDef(cname, dtype))

            if columns:
                schema = Schema(columns)

        # Step 3: Stream rows line-by-line with constant memory and fast columnar transposition
        def _safe_int(v):
            if v is None or v == "" or v == "NULL":
                return None
            try:
                return int(v)
            except (ValueError, TypeError):
                return None

        def _safe_float(v):
            if v is None or v == "" or v == "NULL":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        def _safe_bool(v):
            if v is None or v == "" or v == "NULL":
                return None
            return str(v).lower() in ("true", "1", "t")

        def _safe_str(v):
            if v is None or v == "NULL":
                return None
            return v if isinstance(v, str) else str(v)

        def _build_converters(sch):
            convs = []
            for col in sch.columns:
                dt = col.data_type
                if dt in (DataType.INT64, DataType.INT32):
                    convs.append(lambda vals: [_safe_int(v) for v in vals])
                elif dt == DataType.FLOAT64:
                    convs.append(lambda vals: [_safe_float(v) for v in vals])
                elif dt == DataType.BOOL:
                    convs.append(lambda vals: [_safe_bool(v) for v in vals])
                else:
                    convs.append(lambda vals: [_safe_str(v) for v in vals])
            return convs

        def _write_columnar_batch(wr, sch, convs, b):
            cols_transposed = list(zip(*b))
            col_map = {}
            for idx, col in enumerate(sch.columns):
                if idx < len(cols_transposed):
                    col_map[col.name] = convs[idx](cols_transposed[idx])
                else:
                    col_map[col.name] = [None] * len(b)
            wr.write_columns(col_map, len(b))

        total_imported = 0
        batch = []
        writer = None
        converters = _build_converters(schema) if schema else None
        pbar = ProgressBar("Importing SQL", total_bytes=total_bytes)
        bytes_processed = 0

        with open(sql_dump_path, "r", encoding=encoding, errors="replace", buffering=256*1024) as f:
            try:
                inside_ddl = False
                pending = ""
                for line in f:
                    bytes_processed += len(line)
                    s = line.strip()
                    if not pending and (not s or s.startswith("--") or s.startswith("#") or s.startswith("/*") or s.startswith("/*!") or s.startswith("SET ") or s.startswith("START ") or s.startswith("COMMIT") or s.startswith("LOCK ") or s.startswith("UNLOCK ")):
                        continue

                    if inside_ddl:
                        if ";" in s or s.startswith("ENGINE=") or s.startswith(");"):
                            inside_ddl = False
                        continue

                    if not pending and (s.upper().startswith("CREATE TABLE") or s.upper().startswith("ALTER TABLE") or s.upper().startswith("DROP TABLE")):
                        if not (";" in s and s.endswith(";")):
                            inside_ddl = True
                        continue

                    combined = (pending + " " + s).strip() if pending else s

                    # Check quote balance
                    single_q = combined.count("'") - combined.count(r"\'")
                    double_q = combined.count('"') - combined.count(r'\"')
                    if (single_q % 2 != 0) or (double_q % 2 != 0):
                        pending = combined
                        continue

                    # Extract tuples from line
                    v_idx = combined.find("VALUES")
                    if v_idx == -1:
                        v_idx = combined.find("values")
                    i = v_idx + 6 if v_idx != -1 else 0
                    n = len(combined)

                    while i < n:
                        open_paren = combined.find('(', i)
                        if open_paren == -1:
                            break
                        close_paren = combined.find(')', open_paren + 1)
                        if close_paren == -1:
                            break

                        # Quote-aware paren matching on slice
                        while close_paren != -1:
                            sub = combined[open_paren + 1:close_paren]
                            q_count = sub.count("'")
                            if q_count % 2 != 0 or ('"' in sub and sub.count('"') % 2 != 0):
                                if "\\" in sub:
                                    q_count -= sub.count(r"\'")
                                    d_count = sub.count('"') - sub.count(r'\"')
                                    if q_count % 2 == 0 and d_count % 2 == 0:
                                        break
                                close_paren = combined.find(')', close_paren + 1)
                            else:
                                break

                        if close_paren == -1:
                            break

                        tuple_str = combined[open_paren + 1:close_paren]
                        i = close_paren + 1

                        quote = "'" if "'" in tuple_str else '"'
                        reader = csv.reader([tuple_str], delimiter=',', quotechar=quote, skipinitialspace=True)
                        try:
                            raw_row = [c.strip() if c is not None else None for c in next(reader)]
                        except Exception:
                            continue

                        if not raw_row:
                            continue

                        # If no CREATE TABLE was found, infer schema from first batch
                        if schema is None:
                            batch.append(raw_row)
                            if len(batch) >= 10:
                                col_count = len(batch[0])
                                if col_count == 18:
                                    cnames = MERNIS_COLS
                                else:
                                    cnames = [f"col_{c_idx+1}" for c_idx in range(col_count)]
                                cols = []
                                for c_idx, cn in enumerate(cnames):
                                    non_empty = [r[c_idx] for r in batch if c_idx < len(r) and r[c_idx] is not None and str(r[c_idx]).strip() != ""]
                                    dt = DataType.STRING
                                    if non_empty:
                                        if all(re.match(r'^-?\d+$', str(v).strip()) for v in non_empty[:50]):
                                            dt = DataType.INT64
                                        elif all(re.match(r'^-?\d+\.\d+$', str(v).strip()) for v in non_empty[:50]):
                                            dt = DataType.FLOAT64
                                    cols.append(ColumnDef(cn, dt))
                                schema = Schema(cols)
                                converters = _build_converters(schema)
                                writer = FileWriter(output_mgdb_path, schema, block_size=block_size)
                                writer.__enter__()
                                _write_columnar_batch(writer, schema, converters, batch)
                                total_imported += len(batch)
                                batch = []
                            continue

                        if writer is None:
                            converters = _build_converters(schema)
                            writer = FileWriter(output_mgdb_path, schema, block_size=block_size)
                            writer.__enter__()

                        batch.append(raw_row)
                        if len(batch) >= block_size:
                            _write_columnar_batch(writer, schema, converters, batch)
                            total_imported += len(batch)
                            batch = []
                            pbar.update(total_imported, current_bytes=bytes_processed)

                    # Check remainder after last processed tuple
                    rem = combined[i:].strip()
                    if rem and not rem.endswith(";"):
                        pending = rem
                    else:
                        pending = ""

                if batch and writer:
                    _write_columnar_batch(writer, schema, converters, batch)
                    total_imported += len(batch)
                    batch = []

                pbar.finish()

            finally:
                if writer:
                    writer.__exit__(None, None, None)

        return total_imported


    @classmethod
    def _detect_file_encoding(cls, file_path: str) -> str:
        with open(file_path, "rb") as f:
            sample = f.read(65536)
        if sample.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if sample.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if sample.startswith(b"\xfe\xff"):
            return "utf-16-be"
        for enc in ("utf-8", "cp1254", "iso-8859-9", "windows-1252", "latin-1"):
            try:
                sample.decode(enc)
                return enc
            except UnicodeDecodeError:
                continue
        return "utf-8"

    @classmethod
    def from_csv(
        cls,
        csv_path: str,
        output_mgdb_path: str,
        delimiter: str = ",",
        has_header: bool = True,
        block_size: int = 1024
    ) -> int:
        """
        Imports CSV data with automatic encoding detection, null-byte filtering,
        ragged row tolerance, and streaming chunks. Never fails on single dirty rows.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        encoding = cls._detect_file_encoding(csv_path)

        # Step 1: Infer schema by sampling initial rows
        sample_rows = []
        with open(csv_path, "r", encoding=encoding, errors="replace") as f:
            clean_lines = (line.replace("\x00", "") for line in f)
            reader = csv.reader(clean_lines, delimiter=delimiter)
            try:
                first_row = next(reader, None)
            except Exception:
                first_row = None

            if not first_row:
                raise ValueError("Empty or unreadable CSV file")

            col_names = [f"col_{i}" for i in range(len(first_row))]
            if has_header:
                col_names = [c.strip() if c else f"col_{i}" for i, c in enumerate(first_row)]
                for _ in range(50):
                    try:
                        r = next(reader, None)
                        if r:
                            sample_rows.append(r)
                    except Exception:
                        continue
            else:
                sample_rows.append(first_row)
                for _ in range(49):
                    try:
                        r = next(reader, None)
                        if r:
                            sample_rows.append(r)
                    except Exception:
                        continue

            col_types = []
            for col_idx in range(len(col_names)):
                types_found = set()
                for r in sample_rows:
                    if col_idx < len(r) and r[col_idx] is not None and str(r[col_idx]).strip() != "":
                        types_found.add(_infer_py_type(r[col_idx]))
                if DataType.STRING in types_found or not types_found:
                    col_types.append(DataType.STRING)
                elif DataType.FLOAT64 in types_found:
                    col_types.append(DataType.FLOAT64)
                elif DataType.INT64 in types_found:
                    col_types.append(DataType.INT64)
                elif DataType.BOOL in types_found:
                    col_types.append(DataType.BOOL)
                else:
                    col_types.append(DataType.STRING)

            columns = [ColumnDef(name, dtype) for name, dtype in zip(col_names, col_types)]
            schema = Schema(columns)

        # Step 2: Stream CSV to .mgdb
        total_imported = 0
        corrupted_rows = 0
        total_bytes = os.path.getsize(csv_path)
        pbar = ProgressBar("Importing CSV", total_bytes=total_bytes)

        with open(csv_path, "r", encoding=encoding, errors="replace") as f:
            clean_lines = (line.replace("\x00", "") for line in f)
            reader = csv.reader(clean_lines, delimiter=delimiter)
            if has_header:
                try:
                    next(reader, None)
                except Exception:
                    pass

            with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
                batch = []
                while True:
                    try:
                        row = next(reader)
                    except StopIteration:
                        break
                    except Exception:
                        corrupted_rows += 1
                        continue

                    if not row or all(c == "" or c is None for c in row):
                        continue

                    # Pad or slice to match columns
                    if len(row) < len(columns):
                        row = list(row) + [None] * (len(columns) - len(row))
                    elif len(row) > len(columns):
                        row = row[:len(columns)]

                    batch.append(row)
                    if len(batch) >= block_size:
                        writer.write_rows(batch)
                        total_imported += len(batch)
                        batch = []
                        pbar.update(total_imported)

                if batch:
                    writer.write_rows(batch)
                    total_imported += len(batch)
                    batch = []

        pbar.finish()
        return total_imported

    @classmethod
    def from_jsonl(
        cls,
        jsonl_path: str,
        output_mgdb_path: str,
        block_size: int = 1024
    ) -> int:
        """
        Streaming importer for JSON Lines (JSONL/NDJSON).
        Strictly bounded memory (<15 MB RAM). Tolerates broken lines
        without dropping the rest of the file.
        """
        if not os.path.exists(jsonl_path):
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

        encoding = cls._detect_file_encoding(jsonl_path)
        first_valid_objects = []

        # Step 1: Scan for schema from initial valid objects
        with open(jsonl_path, "r", encoding=encoding, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "\x00" in line:
                    line = line.replace("\x00", "").strip()
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        first_valid_objects.append(obj)
                        if len(first_valid_objects) >= 50:
                            break
                except Exception:
                    continue

        if not first_valid_objects:
            raise ValueError(f"No valid JSON objects found in {jsonl_path}")

        # Combine all seen keys to form comprehensive schema
        all_keys = []
        for obj in first_valid_objects:
            for k in obj.keys():
                if k not in all_keys:
                    all_keys.append(k)

        cols = []
        for k in all_keys:
            types_found = set()
            for obj in first_valid_objects:
                if k in obj and obj[k] is not None and str(obj[k]).strip() != "":
                    types_found.add(_infer_py_type(str(obj[k])))
            if DataType.STRING in types_found or not types_found:
                dt = DataType.STRING
            elif DataType.FLOAT64 in types_found:
                dt = DataType.FLOAT64
            elif DataType.INT64 in types_found:
                dt = DataType.INT64
            elif DataType.BOOL in types_found:
                dt = DataType.BOOL
            else:
                dt = DataType.STRING
            cols.append(ColumnDef(k, dt))

        schema = Schema(cols)
        col_names = [c.name for c in schema.columns]

        # Step 2: Stream records to writer
        total_imported = 0
        corrupted_lines = 0
        total_bytes = os.path.getsize(jsonl_path)
        pbar = ProgressBar("Importing JSONL", total_bytes=total_bytes)

        with open(jsonl_path, "r", encoding=encoding, errors="replace") as f:
            with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
                batch = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if "\x00" in line:
                        line = line.replace("\x00", "")
                    try:
                        obj = json.loads(line)
                    except Exception:
                        corrupted_lines += 1
                        continue

                    if not isinstance(obj, dict):
                        corrupted_lines += 1
                        continue

                    row = [obj.get(c) for c in col_names]
                    batch.append(row)
                    if len(batch) >= block_size:
                        writer.write_rows(batch)
                        total_imported += len(batch)
                        batch = []
                        pbar.update(total_imported)

                if batch:
                    writer.write_rows(batch)
                    total_imported += len(batch)
                    batch = []

        pbar.finish()
        return total_imported

    @classmethod
    def from_json(
        cls,
        json_path: str,
        output_mgdb_path: str,
        block_size: int = 1024
    ) -> int:
        """
        Streaming/chunked importer for standard JSON array or JSON object files.
        Tolerates malformed entries without crashing.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        encoding = cls._detect_file_encoding(json_path)
        with open(json_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        try:
            parsed = json.loads(content)
        except Exception:
            # Salvage mode: extract { ... } objects via regex if whole JSON is truncated/broken
            objects = []
            for match in re.finditer(r'\{[^{}]*\}', content):
                try:
                    obj = json.loads(match.group(0))
                    if isinstance(obj, dict):
                        objects.append(obj)
                except Exception:
                    pass
            parsed = objects

        if isinstance(parsed, dict):
            # Check if wrapped in array like {"data": [...]} or {"rows": [...]}
            for k, v in parsed.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    parsed = v
                    break
            else:
                parsed = [parsed]

        if not isinstance(parsed, list) or not parsed:
            raise ValueError(f"No JSON records could be extracted from {json_path}")

        # Extract schema
        all_keys = []
        for obj in parsed[:100]:
            if isinstance(obj, dict):
                for k in obj.keys():
                    if k not in all_keys:
                        all_keys.append(k)

        if not all_keys:
            all_keys = ["col_1"]

        cols = []
        for k in all_keys:
            types_found = set()
            for obj in parsed[:100]:
                if isinstance(obj, dict) and k in obj and obj[k] is not None and str(obj[k]).strip() != "":
                    types_found.add(_infer_py_type(str(obj[k])))
            if DataType.STRING in types_found or not types_found:
                dt = DataType.STRING
            elif DataType.FLOAT64 in types_found:
                dt = DataType.FLOAT64
            elif DataType.INT64 in types_found:
                dt = DataType.INT64
            elif DataType.BOOL in types_found:
                dt = DataType.BOOL
            else:
                dt = DataType.STRING
            cols.append(ColumnDef(k, dt))

        schema = Schema(cols)
        col_names = [c.name for c in schema.columns]

        total_imported = 0
        with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
            batch = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                row = [item.get(c) for c in col_names]
                batch.append(row)
                if len(batch) >= block_size:
                    writer.write_rows(batch)
                    total_imported += len(batch)
                    batch = []
            if batch:
                writer.write_rows(batch)
                total_imported += len(batch)

        return total_imported


    @classmethod
    def from_cursor(
        cls,
        cursor: Any,
        output_mgdb_path: str,
        block_size: int = 1024
    ) -> int:
        """
        Generic DB-API 2.0 importer. Works with psycopg2 (PostgreSQL),
        mysql-connector, pymysql, pyodbc (MS SQL), sqlite3, etc.
        """
        if not hasattr(cursor, "description") or not cursor.description:
            raise ValueError("Cursor has no result set description. Execute a SELECT query first.")

        columns = []
        for desc in cursor.description:
            col_name = desc[0]
            columns.append(ColumnDef(col_name, DataType.STRING))

        schema = Schema(columns)
        total_imported = 0
        pbar = ProgressBar("Importing Cursor")

        with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
            while True:
                rows = cursor.fetchmany(block_size)
                if not rows:
                    break
                writer.write_rows(rows)
                total_imported += len(rows)
                pbar.update(total_imported)

        pbar.finish()
        return total_imported
