import os
import csv
import sqlite3
import re
import io
from typing import List, Dict, Any, Optional, Union
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter

SQLITE_TYPE_MAP = {
    "integer": DataType.INT64,
    "int": DataType.INT64,
    "bigint": DataType.INT64,
    "smallint": DataType.INT32,
    "tinyint": DataType.INT32,
    "real": DataType.FLOAT64,
    "float": DataType.FLOAT64,
    "double": DataType.FLOAT64,
    "numeric": DataType.FLOAT64,
    "decimal": DataType.FLOAT64,
    "text": DataType.STRING,
    "varchar": DataType.STRING,
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
        block_size: int = 1024
    ) -> int:
        """
        Imports an entire SQLite table or SQL query result directly into a MergenDB (.mgdb) file.
        Streams rows in batches, keeping memory usage constant even for gigabyte-scale databases.
        """
        if not os.path.exists(sqlite_path):
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()

        try:
            if query:
                cursor.execute(query)
                # Infer schema from cursor.description
                columns = []
                for desc in cursor.description:
                    col_name = desc[0]
                    # Default to string/general if type not described
                    columns.append(ColumnDef(col_name, DataType.STRING))
                schema = Schema(columns)
            else:
                if not table_name:
                    # Pick first table if not provided
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                    tables = cursor.fetchall()
                    if not tables:
                        raise ValueError(f"No user tables found in SQLite database {sqlite_path}")
                    table_name = tables[0][0]

                # Inspect schema via PRAGMA table_info
                cursor.execute(f"PRAGMA table_info({table_name});")
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

                cursor.execute(f"SELECT * FROM {table_name}")

            total_imported = 0
            with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
                while True:
                    rows = cursor.fetchmany(block_size)
                    if not rows:
                        break
                    writer.write_rows(rows)
                    total_imported += len(rows)

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
        block_size: int = 2048
    ) -> int:
        """
        Pure streaming importer for SQL dumps of any size (1 GB, 50 GB, 500 GB).
        Streams line-by-line with constant O(1) memory (~15 MB RAM) to completely prevent OOM.
        Handles phpMyAdmin dumps, MySQL DDL, partial dumps, and raw tuple fragments.
        """
        # Resolve path
        if not os.path.exists(sql_dump_path):
            desktop_try = os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(sql_dump_path))
            if os.path.exists(desktop_try):
                sql_dump_path = desktop_try
            else:
                raise FileNotFoundError(f"SQL dump file not found: {sql_dump_path}")

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
                    m = re.match(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?[\w\d_]+`?\.)?`?([\w\d_]+)`?\s*\(", clean, re.IGNORECASE)
                    if m:
                        table_name = m.group(1)
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

        # Step 3: Stream rows line-by-line with constant memory
        total_imported = 0
        batch = []
        writer = None

        def _convert_row(raw_row, sch):
            converted = []
            for i, col_def in enumerate(sch.columns):
                val = raw_row[i] if i < len(raw_row) else None
                if val is None or val == "" or val == "NULL":
                    converted.append(None)
                elif col_def.data_type in (DataType.INT64, DataType.INT32):
                    try:
                        converted.append(int(val))
                    except ValueError:
                        converted.append(None)
                elif col_def.data_type == DataType.FLOAT64:
                    try:
                        converted.append(float(val))
                    except ValueError:
                        converted.append(None)
                elif col_def.data_type == DataType.BOOL:
                    converted.append(str(val).lower() in ("true", "1", "t"))
                else:
                    converted.append(str(val))
            return converted

        with open(sql_dump_path, "r", encoding=encoding, errors="replace", buffering=1024*1024) as f:
            try:
                inside_ddl = False
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("--") or s.startswith("/*") or s.startswith("SET ") or s.startswith("START ") or s.startswith("COMMIT") or s.startswith("LOCK ") or s.startswith("UNLOCK "):
                        continue

                    if inside_ddl:
                        if ";" in s or s.startswith("ENGINE=") or s.startswith(");"):
                            inside_ddl = False
                        continue

                    if s.upper().startswith("CREATE TABLE") or s.upper().startswith("ALTER TABLE") or s.upper().startswith("DROP TABLE"):
                        if not (";" in s and s.endswith(";")):
                            inside_ddl = True
                        continue

                    # Extract tuples from line
                    start_pos = 0
                    while True:
                        open_paren = s.find("(", start_pos)
                        if open_paren == -1:
                            break
                        close_paren = s.find(")", open_paren + 1)
                        if close_paren == -1:
                            break

                        tuple_str = s[open_paren + 1:close_paren]
                        start_pos = close_paren + 1

                        quote = "'" if "'" in tuple_str else '"'
                        reader = csv.reader(io.StringIO(tuple_str), delimiter=',', quotechar=quote, skipinitialspace=True)
                        try:
                            raw_row = [c.strip() for c in next(reader)]
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
                                    cnames = [f"col_{i+1}" for i in range(col_count)]
                                cols = []
                                for i, cn in enumerate(cnames):
                                    non_empty = [r[i] for r in batch if i < len(r) and r[i] is not None and str(r[i]).strip() != ""]
                                    dt = DataType.STRING
                                    if non_empty:
                                        if all(re.match(r'^-?\d+$', str(v).strip()) for v in non_empty[:50]):
                                            dt = DataType.INT64
                                        elif all(re.match(r'^-?\d+\.\d+$', str(v).strip()) for v in non_empty[:50]):
                                            dt = DataType.FLOAT64
                                    cols.append(ColumnDef(cn, dt))
                                schema = Schema(cols)
                                writer = FileWriter(output_mgdb_path, schema, block_size=block_size)
                                writer.__enter__()
                                conv_batch = [_convert_row(r, schema) for r in batch]
                                writer.write_rows(conv_batch)
                                total_imported += len(conv_batch)
                                batch = []
                            continue

                        if writer is None:
                            writer = FileWriter(output_mgdb_path, schema, block_size=block_size)
                            writer.__enter__()

                        batch.append(_convert_row(raw_row, schema))
                        if len(batch) >= block_size:
                            writer.write_rows(batch)
                            total_imported += len(batch)
                            batch = []

                if batch and writer:
                    writer.write_rows(batch)
                    total_imported += len(batch)

            finally:
                if writer:
                    writer.__exit__(None, None, None)

        return total_imported


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
        Imports CSV data with automatic type detection and streaming chunks.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Step 1: Infer schema by sampling first 50 rows
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f, delimiter=delimiter)
            first_row = next(reader, None)
            if not first_row:
                raise ValueError("Empty CSV file")

            col_names = [f"col_{i}" for i in range(len(first_row))]
            if has_header:
                col_names = [c.strip() for c in first_row]
                sample_rows = [next(reader, None) for _ in range(50)]
                sample_rows = [r for r in sample_rows if r]
            else:
                sample_rows = [first_row] + [next(reader, None) for _ in range(49)]
                sample_rows = [r for r in sample_rows if r]

            # Infer types per column
            col_types = []
            for col_idx in range(len(col_names)):
                types_found = set()
                for r in sample_rows:
                    if col_idx < len(r):
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
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f, delimiter=delimiter)
            if has_header:
                next(reader, None)

            with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
                batch = []
                for row in reader:
                    if not row or len(row) != len(columns):
                        continue
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
            # In DB-API 2.0, desc[1] is type_code. Default to STRING if mapping unknown.
            columns.append(ColumnDef(col_name, DataType.STRING))

        schema = Schema(columns)
        total_imported = 0

        with FileWriter(output_mgdb_path, schema, block_size=block_size) as writer:
            while True:
                rows = cursor.fetchmany(block_size)
                if not rows:
                    break
                writer.write_rows(rows)
                total_imported += len(rows)

        return total_imported
