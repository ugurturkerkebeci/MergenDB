import os
import csv
import sqlite3
import re
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
        Imports from a standard SQL dump file (.sql) containing CREATE TABLE and INSERT statements.
        Loads into a temporary in-memory SQLite sandbox and writes to .mgdb.
        """
        if not os.path.exists(sql_dump_path):
            raise FileNotFoundError(f"SQL dump file not found: {sql_dump_path}")

        conn = sqlite3.connect(":memory:")
        with open(sql_dump_path, "r", encoding="utf-8", errors="replace") as f:
            script = f.read()

        conn.executescript(script)
        cursor = conn.cursor()

        try:
            if not table_name:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = cursor.fetchall()
                if not tables:
                    raise ValueError(f"No tables found in SQL dump: {sql_dump_path}")
                table_name = tables[0][0]

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
