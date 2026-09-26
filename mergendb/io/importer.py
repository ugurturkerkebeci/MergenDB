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
        block_size: int = 1024
    ) -> int:
        """
        Imports from a standard SQL dump file (.sql), including MySQL / phpMyAdmin dumps,
        raw tuple values dumps, and partial insert fragments.
        Automatically sanitizes MySQL-specific clauses and gracefully handles missing CREATE TABLE statements.
        """
        # Resolve path: current dir or Desktop if user typed filename without full path
        if not os.path.exists(sql_dump_path):
            desktop_try = os.path.join(os.path.expanduser("~"), "Desktop", os.path.basename(sql_dump_path))
            if os.path.exists(desktop_try):
                sql_dump_path = desktop_try
            else:
                raise FileNotFoundError(f"SQL dump file not found: {sql_dump_path}")

        # Read file with encoding fallback (UTF-8, Turkish CP1254, Latin-1)
        raw_bytes = None
        with open(sql_dump_path, "rb") as f:
            raw_bytes = f.read()

        script = None
        for enc in ("utf-8", "cp1254", "iso-8859-9", "latin-1"):
            try:
                script = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if script is None:
            script = raw_bytes.decode("utf-8", errors="replace")

        # Check if the script contains a CREATE TABLE statement
        has_create_table = bool(re.search(r'CREATE\s+TABLE', script, re.IGNORECASE))

        if has_create_table:
            try:
                # Sanitize MySQL / phpMyAdmin specific syntax for SQLite in-memory execution
                sanitized = re.sub(r'/\*![\s\S]*?\*/;?', '', script)
                sanitized = re.sub(r'/\*[\s\S]*?\*/;?', '', sanitized)
                sanitized = re.sub(r'--.*?\n', '\n', sanitized)
                sanitized = re.sub(r'ENGINE\s*=\s*[\w\d]+', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r'AUTO_INCREMENT\s*=\s*\d+', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r'DEFAULT\s+CHARSET\s*=\s*[\w\d]+', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r'COLLATE\s*=\s*[\w\d_]+', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r'LOCK\s+TABLES\s+[^;]+;', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r'UNLOCK\s+TABLES\s*;', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r',\s*(?:KEY|INDEX|UNIQUE KEY)\s*[\w\d_`]*\s*\([^)]+\)', '', sanitized, flags=re.IGNORECASE)
                sanitized = re.sub(r',\s*CONSTRAINT\s*[\w\d_`]*\s*FOREIGN KEY\s*\([^)]+\)\s*REFERENCES\s*[^)]+\)', '', sanitized, flags=re.IGNORECASE)

                conn = sqlite3.connect(":memory:")
                conn.executescript(sanitized)
                cursor = conn.cursor()
                try:
                    if not table_name:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                        tables = cursor.fetchall()
                        if tables:
                            table_name = tables[0][0]
                    if table_name:
                        cursor.execute(f"PRAGMA table_info({table_name});")
                        table_info = cursor.fetchall()
                        columns = [ColumnDef(row[1], _map_sqlite_type(row[2])) for row in table_info]
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
            except Exception:
                # Fallback to native raw tuple parser
                pass

        # Native Direct Tuple & Values Parser (Handles partial dumps like medeni.sql, raw VALUES fragments, etc.)
        return cls._import_raw_tuples(script, output_mgdb_path, block_size=block_size)

    @classmethod
    def _import_raw_tuples(
        cls,
        text: str,
        output_mgdb_path: str,
        block_size: int = 1024
    ) -> int:
        pattern = re.compile(r'\(([\s\S]*?)\)(?:,|\s*;)', re.DOTALL)

        batch = []
        schema = None
        writer = None
        total_imported = 0

        # Turkish Mernis / Medeni standard 18-column names
        MERNIS_COLS = [
            "tc", "ad", "soyad", "baba_adi", "anne_adi", "cinsiyet",
            "dogum_tarihi", "dogum_yeri", "medeni_hal", "il", "ilce",
            "mahalle", "cilt_no", "aile_sira_no", "birey_sira_no",
            "kimlik_tipi", "seri", "no"
        ]

        def _infer_schema(sample_rows):
            col_count = len(sample_rows[0])
            if col_count == 18:
                col_names = MERNIS_COLS
            else:
                col_names = [f"col_{i+1}" for i in range(col_count)]

            columns = []
            for i, col_name in enumerate(col_names):
                non_empty = [r[i] for r in sample_rows if i < len(r) and r[i] is not None and str(r[i]).strip() != ""]
                dtype = DataType.STRING
                if non_empty:
                    if all(re.match(r'^-?\d+$', str(v).strip()) for v in non_empty[:50]):
                        dtype = DataType.INT64
                    elif all(re.match(r'^-?\d+\.\d+$', str(v).strip()) for v in non_empty[:50]):
                        dtype = DataType.FLOAT64
                    elif all(str(v).lower() in ('true', 'false', '0', '1') for v in non_empty[:50]):
                        dtype = DataType.BOOL
                columns.append(ColumnDef(col_name, dtype))
            return Schema(columns)

        def _convert_row(raw_row, sch):
            converted = []
            for i, col_def in enumerate(sch.columns):
                val = raw_row[i] if i < len(raw_row) else None
                if val is None or val == "":
                    converted.append(None)
                elif col_def.data_type == DataType.INT64:
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

        try:
            for m in pattern.finditer(text):
                raw_tuple = m.group(1).strip()
                raw_tuple = raw_tuple.replace('\r\n', ' ').replace('\n', ' ')
                reader = csv.reader(io.StringIO(raw_tuple), delimiter=',', quotechar='"', skipinitialspace=True)
                try:
                    row = [c.strip() for c in next(reader)]
                except Exception:
                    continue

                if not row:
                    continue

                batch.append(row)

                if schema is None and len(batch) >= 10:
                    schema = _infer_schema(batch)
                    writer = FileWriter(output_mgdb_path, schema, block_size=block_size)
                    writer.__enter__()

                if schema and len(batch) >= block_size:
                    converted_rows = [_convert_row(r, schema) for r in batch]
                    writer.write_rows(converted_rows)
                    total_imported += len(converted_rows)
                    batch = []

            # Flush remaining batch
            if batch:
                if schema is None:
                    schema = _infer_schema(batch)
                    writer = FileWriter(output_mgdb_path, schema, block_size=block_size)
                    writer.__enter__()
                converted_rows = [_convert_row(r, schema) for r in batch]
                writer.write_rows(converted_rows)
                total_imported += len(converted_rows)

            return total_imported
        finally:
            if writer:
                writer.__exit__(None, None, None)

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
