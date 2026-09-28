import os
import re
import csv
import json
import time
import builtins
import threading
from typing import List, Dict, Any, Union, Optional
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType, cast_value
from mergendb.storage.writer import FileWriter
from mergendb.storage.reader import FileReader
from mergendb.storage.lock import TableLockManager, safe_atomic_replace
from mergendb.query.engine import QueryEngine, QueryResult, ExecutionStats, ExpressionEvaluator
from mergendb.query.parser import Parser
from mergendb.query.lexer import Lexer
from mergendb.query.ast_nodes import QueryPlan, CreateTableNode, InsertNode



def _parse_set_clause(clause: str) -> Dict[str, Any]:
    items = []
    current = []
    in_quote = False
    quote_char = None
    for ch in clause:
        if ch in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = ch
            elif quote_char == ch:
                in_quote = False
                quote_char = None
        if ch == ',' and not in_quote:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        items.append("".join(current).strip())

    result = {}
    for item in items:
        if "=" not in item:
            raise SyntaxError(f"Invalid SET expression: '{item}'. Expected 'column = value'")
        col, val = item.split("=", 1)
        col = col.strip().strip("'\"`")
        val = val.strip()
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            parsed_val = val[1:-1].replace("''", "'")
        elif val.upper() == "NULL":
            parsed_val = None
        elif val.upper() == "TRUE":
            parsed_val = True
        elif val.upper() == "FALSE":
            parsed_val = False
        else:
            try:
                parsed_val = float(val) if "." in val else int(val)
            except ValueError:
                parsed_val = val
        result[col] = parsed_val
    return result


SYSTEM_IGNORED_DIRS = {
    'node_modules', '__pycache__', 'dist', 'build', '.git', '.gemini',
    'mergendb.egg-info', 'venv', '.venv', 'env', 'docs', 'sdks', 'mergendb',
    'tests', 'scratch', '.idea', '.vscode'
}


def resolve_table_path(table_name: str, active_db: Optional[str] = None, for_create: bool = False, base_dir: str = ".") -> str:
    """
    Resolves a logical table or sub-table identifier to its concrete on-disk .mgdb file path.
    Supports:
    - Direct paths: "sensors.mgdb", "school/students.mgdb", absolute paths
    - Dot notation: "school.students", "school.students.class_a"
    - Database-scoped names: "students", "students.class_a" (when active_db="school")
    """
    raw = str(table_name).strip().strip("'\"`")
    if not raw:
        return raw

    raw = raw.replace("\\", "/")

    # 1. Exact existing file match
    if os.path.isfile(raw):
        return os.path.normpath(raw)
    if os.path.isfile(raw + ".mgdb"):
        return os.path.normpath(raw + ".mgdb")

    cand_base = os.path.join(base_dir, raw)
    if os.path.isfile(cand_base):
        return os.path.normpath(cand_base)
    if os.path.isfile(cand_base + ".mgdb"):
        return os.path.normpath(cand_base + ".mgdb")

    clean_raw = raw[:-5] if raw.endswith(".mgdb") else raw

    # 2. Check inside active_db if specified
    if active_db and active_db != "default":
        db_folder = os.path.join(base_dir, active_db)

        cand_in_db = os.path.join(db_folder, raw)
        if os.path.isfile(cand_in_db):
            return os.path.normpath(cand_in_db)
        if os.path.isfile(cand_in_db + ".mgdb"):
            return os.path.normpath(cand_in_db + ".mgdb")

        cand_clean_in_db = os.path.join(db_folder, clean_raw)
        if os.path.isfile(cand_clean_in_db + ".mgdb"):
            return os.path.normpath(cand_clean_in_db + ".mgdb")

        # Strip active_db prefix if table_name started with active_db
        clean_tbl = clean_raw
        if clean_tbl.startswith(active_db + "."):
            clean_tbl = clean_tbl[len(active_db) + 1:]
        elif clean_tbl.startswith(active_db + "/"):
            clean_tbl = clean_tbl[len(active_db) + 1:]

        if "." in clean_tbl:
            parts = clean_tbl.split(".")
            # Nested: school/students/class_a.mgdb
            cand_nested = os.path.join(db_folder, *parts) + ".mgdb"
            if os.path.isfile(cand_nested):
                return os.path.normpath(cand_nested)
            # Flat: school/students.class_a.mgdb
            cand_flat = os.path.join(db_folder, ".".join(parts)) + ".mgdb"
            if os.path.isfile(cand_flat):
                return os.path.normpath(cand_flat)
        else:
            cand_file = os.path.join(db_folder, f"{clean_tbl}.mgdb")
            if os.path.isfile(cand_file):
                return os.path.normpath(cand_file)

    # 3. Dot-notation resolution across all databases (e.g. "school.students" or "school.students.class_a")
    if "." in clean_raw:
        parts = clean_raw.split(".")
        first_db = parts[0]
        rest = parts[1:]
        cand_db = os.path.join(base_dir, first_db)
        if os.path.isdir(cand_db):
            if len(rest) == 1:
                cand = os.path.join(cand_db, f"{rest[0]}.mgdb")
                if os.path.isfile(cand):
                    return os.path.normpath(cand)
            cand_nested = os.path.join(cand_db, *rest) + ".mgdb"
            if os.path.isfile(cand_nested):
                return os.path.normpath(cand_nested)
            cand_flat = os.path.join(cand_db, ".".join(rest)) + ".mgdb"
            if os.path.isfile(cand_flat):
                return os.path.normpath(cand_flat)

        cand_root_nested = os.path.join(base_dir, *parts) + ".mgdb"
        if os.path.isfile(cand_root_nested):
            return os.path.normpath(cand_root_nested)
        cand_root_flat = os.path.join(base_dir, ".".join(parts)) + ".mgdb"
        if os.path.isfile(cand_root_flat):
            return os.path.normpath(cand_root_flat)

    # 4. Handle creation path
    if for_create:
        clean = clean_raw
        if active_db and active_db != "default":
            db_dir = os.path.join(base_dir, active_db)
            os.makedirs(db_dir, exist_ok=True)
            if clean.startswith(active_db + "."):
                clean = clean[len(active_db) + 1:]
            if "." in clean:
                parts = clean.split(".")
                sub_dir = os.path.join(db_dir, *parts[:-1])
                os.makedirs(sub_dir, exist_ok=True)
                return os.path.normpath(os.path.join(sub_dir, f"{parts[-1]}.mgdb"))
            return os.path.normpath(os.path.join(db_dir, f"{clean}.mgdb"))
        else:
            if "." in clean:
                parts = clean.split(".")
                if os.path.isdir(os.path.join(base_dir, parts[0])) or os.path.isfile(os.path.join(base_dir, f"{parts[0]}.mgdb")):
                    sub_dir = os.path.join(base_dir, *parts[:-1])
                    os.makedirs(sub_dir, exist_ok=True)
                    return os.path.normpath(os.path.join(sub_dir, f"{parts[-1]}.mgdb"))
            return os.path.normpath(os.path.join(base_dir, f"{clean}.mgdb"))

    # 5. Default fallback
    clean_name = raw[:-5] if raw.endswith(".mgdb") else raw
    if active_db and active_db != "default":
        return os.path.normpath(os.path.join(base_dir, active_db, f"{clean_name}.mgdb"))
    return os.path.normpath(os.path.join(base_dir, f"{clean_name}.mgdb"))


def scan_tables_in_dir(dir_path: str, db_name: str = "default") -> List[Dict[str, Any]]:
    """Recursively scans a directory for all .mgdb tables and nested sub-tables."""
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return []

    tables_map: Dict[str, Dict[str, Any]] = {}
    dir_path = os.path.abspath(dir_path)

    # For default database, only descend into subdirectories that correspond to an existing root table
    allowed_root_subdirs = set()
    if db_name == "default":
        for item in os.listdir(dir_path):
            if item.endswith(".mgdb") and os.path.isfile(os.path.join(dir_path, item)):
                tbl_stem = item[:-5]
                if os.path.isdir(os.path.join(dir_path, tbl_stem)):
                    allowed_root_subdirs.add(tbl_stem)

    for root, dirs, files in os.walk(dir_path):
        if db_name == "default" and root == dir_path:
            dirs[:] = [d for d in dirs if d in allowed_root_subdirs]
        else:
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SYSTEM_IGNORED_DIRS]

        rel_root = os.path.relpath(root, dir_path)
        if rel_root == ".":
            parent_parts = []
        else:
            parent_parts = rel_root.replace("\\", "/").split("/")

        for f in files:
            if not f.endswith(".mgdb"):
                continue
            f_path = os.path.join(root, f)
            t_name = f[:-5]
            if parent_parts:
                full_name = ".".join(parent_parts + [t_name])
                parent_table = ".".join(parent_parts)
                table_type = "subtable"
            elif "." in t_name:
                parts = t_name.split(".")
                full_name = t_name
                parent_table = ".".join(parts[:-1])
                t_name = parts[-1]
                table_type = "subtable"
            else:
                full_name = t_name
                parent_table = None
                table_type = "table"

            rows = 0
            cols = []
            blocks_cnt = 0
            sz = 0
            try:
                sz = os.path.getsize(f_path)
                with FileReader(f_path) as reader:
                    rows = reader.total_rows
                    blocks_cnt = len(reader.blocks)
                    for c in reader.schema.columns:
                        cols.append({
                            "name": c.name,
                            "type": c.data_type.name,
                            "nullable": getattr(c, "nullable", True)
                        })
            except Exception:
                pass

            tables_map[full_name] = {
                "name": t_name,
                "table": f"{t_name}.mgdb" if table_type == "table" else f"{full_name}.mgdb",
                "full_name": full_name,
                "database": db_name,
                "path": os.path.normpath(f_path),
                "type": table_type,
                "parent": parent_table,
                "rows": rows,
                "bytes": sz,
                "blocks": blocks_cnt,
                "columns": [c["name"] for c in cols],
                "schema": cols,
                "subtables": []
            }

    # Link subtables into parent entries
    for full_name, info in list(tables_map.items()):
        parent = info.get("parent")
        if parent:
            if parent in tables_map:
                if info["name"] not in tables_map[parent]["subtables"]:
                    tables_map[parent]["subtables"].append(info["name"])
            else:
                parent_path = os.path.join(dir_path, *parent.split("."))
                tables_map[parent] = {
                    "name": parent.split(".")[-1],
                    "full_name": parent,
                    "database": db_name,
                    "path": os.path.normpath(parent_path),
                    "type": "collection",
                    "parent": ".".join(parent.split(".")[:-1]) if "." in parent else None,
                    "rows": 0,
                    "bytes": 0,
                    "blocks": 0,
                    "columns": [],
                    "schema": [],
                    "subtables": [info["name"]]
                }

    return sorted(tables_map.values(), key=lambda t: t["full_name"])


def list_databases(base_dir: str = ".") -> List[Dict[str, Any]]:
    """Discovers all databases (subdirectories and root default) in the workspace."""
    base_dir = os.path.abspath(base_dir)
    databases = []

    # 1. Default database (root *.mgdb files)
    try:
        root_mgdbs = [f for f in os.listdir(base_dir) if f.endswith(".mgdb") and os.path.isfile(os.path.join(base_dir, f))]
        root_total_bytes = sum(os.path.getsize(os.path.join(base_dir, f)) for f in root_mgdbs)
    except Exception:
        root_mgdbs = []
        root_total_bytes = 0

    databases.append({
        "name": "default",
        "path": base_dir,
        "tables_count": len(root_mgdbs),
        "total_bytes": root_total_bytes
    })

    # 2. Subdirectory databases
    try:
        entries = sorted(os.listdir(base_dir))
    except Exception:
        entries = []

    for entry in entries:
        full_entry = os.path.join(base_dir, entry)
        if not os.path.isdir(full_entry) or entry.startswith(".") or entry in SYSTEM_IGNORED_DIRS:
            continue

        db_tables = scan_tables_in_dir(full_entry, db_name=entry)
        total_sz = sum(t["bytes"] for t in db_tables)
        databases.append({
            "name": entry,
            "path": full_entry,
            "tables_count": len([t for t in db_tables if t["type"] != "collection"]),
            "total_bytes": total_sz
        })

    return databases


class Table:
    """
    Represents a MergenDB columnar table file.
    Provides intuitive, Pythonic data manipulation and querying methods.
    """

    def __init__(self, filepath: str):
        filepath = filepath.strip().strip("'\"`")
        if not filepath.endswith(".mgdb") and not os.path.exists(filepath):
            filepath += ".mgdb"
        self.filepath = filepath

    @classmethod
    def create(cls, filepath: str, schema: Schema, block_size: int = 1024) -> 'Table':
        """Creates a new empty table with the given schema."""
        MergenDB.create_table(filepath, schema, block_size=block_size)
        return cls(filepath)

    @property
    def schema(self) -> Schema:
        with FileReader(self.filepath) as reader:
            return reader.schema

    @property
    def columns(self) -> List[str]:
        """Returns list of column names in the table."""
        return self.schema.column_names()

    @property
    def row_count(self) -> int:
        """Returns the total number of rows stored in the table."""
        with FileReader(self.filepath) as reader:
            return reader.total_rows

    def __len__(self) -> int:
        return self.row_count

    def __repr__(self) -> str:
        exists = os.path.exists(self.filepath)
        rows = self.row_count if exists else 0
        return f"<MergenDB.Table '{self.filepath}' rows={rows:,}>"

    def count(self) -> int:
        """Returns total row count."""
        return self.row_count

    @property
    def subtables_dir(self) -> str:
        """Directory path where subtables of this table are located."""
        base_path = self.filepath[:-5] if self.filepath.endswith(".mgdb") else self.filepath
        return base_path

    def create_subtable(self, name: str, schema: Union[Schema, List[ColumnDef]], block_size: int = 1024) -> 'Table':
        """
        Creates a nested sub-table under this table.
        Example:
            employees = db.table("employees")
            engineering = employees.create_subtable("engineering", schema)
        """
        if isinstance(schema, list):
            schema = Schema(schema)
        os.makedirs(self.subtables_dir, exist_ok=True)
        sub_path = os.path.join(self.subtables_dir, f"{name}.mgdb")
        return MergenDB.create_table(sub_path, schema, block_size=block_size)

    def subtable(self, name: str) -> 'Table':
        """Returns an existing nested sub-table."""
        sub_path = os.path.join(self.subtables_dir, f"{name}.mgdb")
        if not os.path.exists(sub_path) and os.path.exists(os.path.join(self.subtables_dir, name)):
            return Table(os.path.join(self.subtables_dir, name))
        return Table(sub_path)

    def __getitem__(self, name: str) -> 'Table':
        """Direct indexing for nested sub-tables: table['a_sinifi']."""
        return self.subtable(name)

    def subtables(self) -> List[str]:
        """Returns list of sub-table names under this table."""
        s_dir = self.subtables_dir
        if not os.path.exists(s_dir) or not os.path.isdir(s_dir):
            return []
        res = []
        for item in sorted(os.listdir(s_dir)):
            if item.endswith(".mgdb"):
                res.append(item[:-5])
            elif os.path.isdir(os.path.join(s_dir, item)):
                res.append(item)
        return res

    def list_subtables(self) -> List[Dict[str, Any]]:
        """Returns rich metadata list for all sub-tables."""
        s_dir = self.subtables_dir
        if not os.path.exists(s_dir) or not os.path.isdir(s_dir):
            return []
        db_name = os.path.basename(os.path.dirname(os.path.abspath(self.filepath)))
        return scan_tables_in_dir(s_dir, db_name=db_name)

    def insert(self, data: Union[Dict[str, Any], List[Dict[str, Any]], List[List[Any]]], block_size: int = 1024):
        """
        Inserts row(s) into the table. Accepts:
        - A single dictionary: {'name': 'Alice', 'balance': 50}
        - A list of dictionaries: [{'name': 'Alice'}, {'name': 'Bob'}]
        - A list of row value lists: [['Alice', 50], ['Bob', 70]]
        If the table file does not exist yet and dicts are provided, schema is automatically inferred!
        """
        if not os.path.exists(self.filepath):
            if isinstance(data, dict):
                sample = data
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                sample = data[0]
            else:
                raise FileNotFoundError(f"Table file '{self.filepath}' does not exist. Call create_table or insert dicts to auto-create.")

            # Infer schema from sample dict
            cols = []
            for k, v in sample.items():
                if isinstance(v, bool):
                    dt = DataType.BOOL
                elif isinstance(v, int):
                    dt = DataType.INT64
                elif isinstance(v, float):
                    dt = DataType.FLOAT64
                else:
                    dt = DataType.STRING
                cols.append(ColumnDef(k, dt))
            MergenDB.create_table(self.filepath, Schema(cols), block_size=block_size)

        if isinstance(data, dict):
            col_names = self.columns
            row = [data.get(c) for c in col_names]
            self.insert_many([row], block_size=block_size)
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            col_names = self.columns
            rows = [[d.get(c) for c in col_names] for d in data]
            self.insert_many(rows, block_size=block_size)
        elif isinstance(data, list):
            self.insert_many(data, block_size=block_size)
        else:
            raise TypeError("Data to insert must be a dict, list of dicts, or list of row lists.")

    def insert_many(self, rows: List[Any], block_size: int = 1024):
        """
        Appends rows to the table with streaming block preservation and concurrency write lock.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' does not exist. Call create_table first.")

        with TableLockManager.get_lock(self.filepath).write():
            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            try:
                with FileReader(self.filepath) as reader:
                    schema = reader.schema
                    with FileWriter(temp_path, schema, block_size=block_size) as writer:
                        for batch, _ in reader.scan():
                            writer.write_columns(batch.columns, batch.row_count)
                        writer.write_rows(rows)

                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

    def rename_column(self, old_name: str, new_name: str) -> "Table":
        """
        Renames an existing column in the table schema and data.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        with TableLockManager.get_lock(self.filepath).write():
            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            try:
                with FileReader(self.filepath) as reader:
                    schema = reader.schema
                    if not schema.has_column(old_name):
                        raise KeyError(f"Column '{old_name}' not found in table schema.")
                    if schema.has_column(new_name):
                        raise ValueError(f"Column '{new_name}' already exists in table schema.")

                    new_columns = [
                        ColumnDef(new_name, c.data_type, c.nullable) if c.name == old_name else c
                        for c in schema.columns
                    ]
                    new_schema = Schema(new_columns)

                    with FileWriter(temp_path, new_schema) as writer:
                        for batch, _ in reader.scan():
                            cols = dict(batch.columns)
                            cols[new_name] = cols.pop(old_name)
                            writer.write_columns(cols, batch.row_count)

                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        return self


    def drop_column(self, column_name: str) -> "Table":
        """
        Permanently drops a column from the table schema and data.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        with TableLockManager.get_lock(self.filepath).write():
            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            try:
                with FileReader(self.filepath) as reader:
                    schema = reader.schema
                    if not schema.has_column(column_name):
                        raise KeyError(f"Column '{column_name}' not found in table schema.")
                    if len(schema.columns) <= 1:
                        raise ValueError("Cannot drop the only column in the table.")

                    new_columns = [c for c in schema.columns if c.name != column_name]
                    new_schema = Schema(new_columns)

                    with FileWriter(temp_path, new_schema) as writer:
                        for batch, _ in reader.scan():
                            cols = dict(batch.columns)
                            cols.pop(column_name, None)
                            writer.write_columns(cols, batch.row_count)

                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        return self

    def add_column(self, column_name: str, data_type: Union[DataType, str], default: Any = None, nullable: bool = True) -> "Table":
        """
        Adds a new column with a default value to the table.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        dt_map = {
            "int": DataType.INT32,
            "int32": DataType.INT32,
            "int64": DataType.INT64,
            "bigint": DataType.INT64,
            "float": DataType.FLOAT64,
            "float32": DataType.FLOAT32,
            "float64": DataType.FLOAT64,
            "double": DataType.FLOAT64,
            "string": DataType.STRING,
            "text": DataType.STRING,
            "bool": DataType.BOOL,
            "boolean": DataType.BOOL,
            "timestamp": DataType.TIMESTAMP,
        }
        if isinstance(data_type, str):
            dt_key = data_type.strip().lower()
            if dt_key not in dt_map:
                raise ValueError(f"Unknown data type '{data_type}'. Valid: {list(dt_map.keys())}")
            dt = dt_map[dt_key]
        else:
            dt = data_type

        with TableLockManager.get_lock(self.filepath).write():
            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            try:
                with FileReader(self.filepath) as reader:
                    schema = reader.schema
                    if schema.has_column(column_name):
                        raise ValueError(f"Column '{column_name}' already exists in table schema.")

                    new_columns = list(schema.columns) + [ColumnDef(column_name, dt, nullable)]
                    new_schema = Schema(new_columns)
                    cast_default = cast_value(default, dt)

                    with FileWriter(temp_path, new_schema) as writer:
                        for batch, _ in reader.scan():
                            cols = dict(batch.columns)
                            cols[column_name] = [cast_default] * batch.row_count
                            writer.write_columns(cols, batch.row_count)

                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        return self


    def update(self, set_values: Dict[str, Any], where: Optional[str] = None) -> int:
        """
        Updates matching rows in the table.
        set_values: dictionary of {column_name: new_value}
        where: optional filter condition (e.g. "id = 5 AND active = true")
        Returns total number of rows updated.
        """
        if not set_values:
            return 0
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        with TableLockManager.get_lock(self.filepath).write():
            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            updated_count = 0
            try:
                with FileReader(self.filepath) as reader:
                    schema = reader.schema
                    col_map = {c.name: c for c in schema.columns}
                    for col in set_values:
                        if col not in col_map:
                            raise KeyError(f"Column '{col}' does not exist in table schema.")

                    casted_updates = {
                        col: cast_value(val, col_map[col].data_type)
                        for col, val in set_values.items()
                    }

                    where_expr = None
                    if where and where.strip():
                        tokens = Lexer(where).tokenize()
                        where_expr = Parser(tokens)._parse_expression()
                        QueryEngine._coerce_expr_literals(where_expr, schema)

                    with FileWriter(temp_path, schema) as writer:
                        for batch, _ in reader.scan():
                            cols = dict(batch.columns)
                            count = batch.row_count

                            if where_expr is not None:
                                mask = ExpressionEvaluator.evaluate(where_expr, cols, count)
                                matches = [i for i, m in enumerate(mask) if m]
                                if matches:
                                    for col_name, new_val in casted_updates.items():
                                        col_list = list(cols[col_name])
                                        for idx in matches:
                                            col_list[idx] = new_val
                                        cols[col_name] = col_list
                                    updated_count += len(matches)
                            else:
                                for col_name, new_val in casted_updates.items():
                                    cols[col_name] = [new_val] * count
                                updated_count += count

                            writer.write_columns(cols, count)

                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        return updated_count

    def delete(self, where: Optional[str] = None) -> int:
        """
        Deletes matching rows from the table.
        where: optional filter condition. If omitted or None, truncates all rows.
        Returns total number of rows deleted.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        if where is None or not where.strip():
            return self.truncate()

        with TableLockManager.get_lock(self.filepath).write():
            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            deleted_count = 0
            try:
                with FileReader(self.filepath) as reader:
                    schema = reader.schema
                    tokens = Lexer(where).tokenize()
                    where_expr = Parser(tokens)._parse_expression()
                    QueryEngine._coerce_expr_literals(where_expr, schema)

                    with FileWriter(temp_path, schema) as writer:
                        for batch, _ in reader.scan():
                            cols = dict(batch.columns)
                            count = batch.row_count
                            mask = ExpressionEvaluator.evaluate(where_expr, cols, count)
                            match_count = sum(1 for m in mask if m)

                            if match_count == 0:
                                writer.write_columns(cols, count)
                            elif match_count == count:
                                deleted_count += match_count
                            else:
                                filtered = {c: [v for v, m in zip(vals, mask) if not m] for c, vals in cols.items()}
                                deleted_count += match_count
                                writer.write_columns(filtered, count - match_count)

                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        return deleted_count

    def truncate(self) -> int:
        """
        Removes all rows from the table while preserving schema.
        Returns number of rows removed.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")
        with TableLockManager.get_lock(self.filepath).write():
            with FileReader(self.filepath) as reader:
                schema = reader.schema
                total = reader.total_rows

            temp_path = f"{self.filepath}.tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}"
            try:
                with FileWriter(temp_path, schema) as writer:
                    pass
                safe_atomic_replace(temp_path, self.filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        return total

    def drop(self) -> bool:
        """
        Permanently deletes the table file from disk.
        """
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
            return True
        return False

    def rename(self, new_filepath: str) -> "Table":
        """
        Renames the table file on disk.
        """
        if not new_filepath.endswith(".mgdb"):
            new_filepath += ".mgdb"
        if os.path.exists(new_filepath):
            raise FileExistsError(f"Target table file '{new_filepath}' already exists.")
        os.rename(self.filepath, new_filepath)
        self.filepath = new_filepath
        return self

    def query(self, pipeline: str, show_progress: bool = False) -> QueryResult:
        """Runs a MergenQL pipeline query against this table with non-blocking read lock."""
        with TableLockManager.get_lock(self.filepath).read():
            full_query = f'FROM "{self.filepath}"\n' + pipeline.strip()
            tokens = Lexer(full_query).tokenize()
            plan = Parser(tokens).parse()
            if not isinstance(plan, QueryPlan):
                raise ValueError("Expected a query pipeline")
            return QueryEngine.execute(plan, show_progress=show_progress)


    def sql(self, query_str: str, show_progress: bool = False) -> QueryResult:
        """Executes a standard SQL query against this table."""
        tbl_base = os.path.splitext(os.path.basename(self.filepath))[0]
        tbl_name = os.path.basename(self.filepath)
        clean_path = self.filepath.replace("\\", "/")
        pattern = rf"\b(FROM|UPDATE|DELETE\s+FROM|ALTER\s+TABLE|TRUNCATE\s+TABLE|DROP\s+TABLE)\s+[`\"']?(?:{re.escape(tbl_name)}|{re.escape(tbl_base)})(?:\.mgdb)?[`\"']?\b"
        query_fixed = re.sub(pattern, lambda m: f'{m.group(1)} "{clean_path}"', query_str, flags=re.IGNORECASE)
        return MergenDB.query(query_fixed, show_progress=show_progress)

    def execute(self, query_or_sql: str, show_progress: bool = False) -> QueryResult:
        """Alias for sql / query."""
        cmd_u = query_or_sql.strip().upper()
        if any(cmd_u.startswith(kw) for kw in ("SELECT ", "UPDATE ", "DELETE ", "ALTER ", "DROP ", "TRUNCATE ", "RENAME ")):
            return self.sql(query_or_sql, show_progress=show_progress)
        return self.query(query_or_sql, show_progress=show_progress)

    def find(self, limit: Optional[int] = None, show_progress: bool = False, **kwargs) -> QueryResult:
        """
        Finds rows matching keyword filters.
        Example: table.find(name='abdurrezzak', balance=30)
        """
        pipe = []
        if kwargs:
            conditions = []
            for k, v in kwargs.items():
                if v is None:
                    conditions.append(f"{k} IS NULL")
                elif isinstance(v, (int, float)):
                    conditions.append(f"{k} = {v}")
                else:
                    esc = str(v).replace("'", "''")
                    conditions.append(f"{k} = '{esc}'")
            pipe.append(f"| WHERE {' AND '.join(conditions)}")

        if limit is not None:
            pipe.append(f"| LIMIT {limit}")

        return self.query("\n".join(pipe), show_progress=show_progress)

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Returns the first matching row as a dictionary, or None.
        Example: user = table.find_one(name='abdurrezzak')
        """
        res = self.find(limit=1, **kwargs)
        return res.to_dict()

    def first(self, where: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the first row in the table, optionally filtered by WHERE condition."""
        if where:
            res = self.where(where, limit=1)
        else:
            res = self.query("| LIMIT 1")
        return res.to_dict()

    def all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns all rows as a list of dictionaries."""
        pipe = f"| LIMIT {limit}" if limit else ""
        return self.query(pipe).to_dicts()

    def where(self, condition: str, limit: Optional[int] = None, show_progress: bool = False) -> QueryResult:
        """
        Filters rows by condition.
        Example: table.where("balance > 100 AND city = 'Istanbul'")
        """
        pipe = [f"| WHERE {condition}"]
        if limit is not None:
            pipe.append(f"| LIMIT {limit}")
        return self.query("\n".join(pipe), show_progress=show_progress)

    def select(self, *columns: str, where: Optional[str] = None, order_by: Optional[str] = None, limit: Optional[int] = None, show_progress: bool = False) -> QueryResult:
        """
        Fluent query helper.
        Example: table.select("name", "balance", where="balance > 50", order_by="balance DESC", limit=10)
        """
        pipe = []
        if where:
            pipe.append(f"| WHERE {where}")
        if columns:
            pipe.append(f"| SELECT {', '.join(columns)}")
        if order_by:
            pipe.append(f"| SORT {order_by}")
        if limit is not None:
            pipe.append(f"| LIMIT {limit}")
        return self.query("\n".join(pipe), show_progress=show_progress)

    def search(self, text: str, limit: Optional[int] = None, show_progress: bool = False) -> QueryResult:
        """
        Performs full-text case-insensitive substring search across all STRING columns.
        Example: table.search("abdurrezzak")
        """
        str_cols = [c.name for c in self.schema.columns if c.data_type == DataType.STRING]
        if not str_cols:
            return QueryResult([], [], None)
        esc = str(text).replace("'", "''")
        where_expr = " OR ".join(f"{c} LIKE '%{esc}%'" for c in str_cols)
        return self.where(where_expr, limit=limit, show_progress=show_progress)

    def to_dicts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns table rows as a list of Python dictionaries."""
        return self.all(limit=limit)

    def to_list(self, limit: Optional[int] = None) -> List[List[Any]]:
        """Returns table rows as a list of lists."""
        pipe = f"| LIMIT {limit}" if limit else ""
        return self.query(pipe).to_list()

    def to_df(self, limit: Optional[int] = None):
        """Converts table data directly into a pandas DataFrame."""
        pipe = f"| LIMIT {limit}" if limit else ""
        return self.query(pipe).to_df()

    def show(self, limit: int = 10):
        """Pretty-prints table contents to console."""
        self.query(f"| LIMIT {limit}").show()

    def _ensure_output_ext(self, path: str, expected_ext: str) -> str:
        path = str(path).strip().strip('"').strip("'")
        base, ext = os.path.splitext(path)
        if not ext:
            return f"{path}{expected_ext}"
        if ext.lower() != expected_ext.lower() and ext.lower() in (".csv", ".json", ".jsonl", ".sql"):
            return f"{base}{expected_ext}"
        return path

    def export(self, output_path: str, fmt: Optional[str] = None):
        """Automatically exports table data based on file extension (.csv, .json, .jsonl, .sql) or fmt parameter."""
        if fmt:
            fmt_upper = fmt.upper()
            if fmt_upper in ("CSV", "CVS"):
                return self.export_csv(output_path)
            elif fmt_upper == "JSON":
                return self.export_json(output_path)
            elif fmt_upper == "JSONL":
                return self.export_jsonl(output_path)
            elif fmt_upper == "SQL":
                return self.export_sql(output_path)

        lower = output_path.lower()
        if lower.endswith(".csv"):
            return self.export_csv(output_path)
        elif lower.endswith(".jsonl"):
            return self.export_jsonl(output_path)
        elif lower.endswith(".json"):
            return self.export_json(output_path)
        elif lower.endswith(".sql"):
            return self.export_sql(output_path)
        else:
            return self.export_csv(output_path)

    def export_csv(self, output_path: str):
        """Exports all rows to a CSV file."""
        output_path = self._ensure_output_ext(output_path, ".csv")
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            with builtins.open(output_path, "w", newline="", encoding="utf-8", buffering=256*1024) as f:
                writer = csv.writer(f)
                writer.writerow(col_names)
                for batch, _ in reader.scan():
                    cols = batch.columns
                    writer.writerows(zip(*(cols[c] for c in col_names)))

    def export_json(self, output_path: str):
        """Exports all rows to a standard JSON array file [ {...}, {...} ]."""
        output_path = self._ensure_output_ext(output_path, ".json")
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            with builtins.open(output_path, "w", encoding="utf-8", buffering=256*1024) as f:
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
                f.write("\n]\n")

    def export_jsonl(self, output_path: str):
        """Exports all rows to a JSON Lines (JSONL) file."""
        output_path = self._ensure_output_ext(output_path, ".jsonl")
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            with builtins.open(output_path, "w", encoding="utf-8", buffering=256*1024) as f:
                for batch, _ in reader.scan():
                    cols = batch.columns
                    lines = [json.dumps(dict(zip(col_names, row))) + "\n" for row in zip(*(cols[c] for c in col_names))]
                    f.writelines(lines)

    def export_sql(self, output_path: str):
        """Exports all rows to an SQL INSERT dump file."""
        output_path = self._ensure_output_ext(output_path, ".sql")
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            clean_tbl = os.path.splitext(os.path.basename(self.filepath))[0]
            with builtins.open(output_path, "w", encoding="utf-8", buffering=256*1024) as f:
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

                chunk = []
                for batch, _ in reader.scan():
                    cols = batch.columns
                    for row_vals in zip(*(cols[c] for c in col_names)):
                        formatted = []
                        for val in row_vals:
                            if val is None: formatted.append("NULL")
                            elif isinstance(val, (int, float)): formatted.append(str(val))
                            elif isinstance(val, bool): formatted.append("1" if val else "0")
                            else:
                                esc = str(val).replace("\\", "\\\\").replace("'", "''")
                                formatted.append(f"'{esc}'")
                        chunk.append("(" + ", ".join(formatted) + ")")
                        if len(chunk) >= 1000:
                            f.write(f"INSERT INTO `{clean_tbl}` VALUES\n" + ",\n".join(chunk) + ";\n")
                            chunk = []
                if chunk:
                    f.write(f"INSERT INTO `{clean_tbl}` VALUES\n" + ",\n".join(chunk) + ";\n")


class Database:
    """
    Represents a MergenDB Database container.
    Stores and manages multiple tables and nested sub-tables within a directory.
    """

    def __init__(self, name_or_path: str = "default", base_dir: Optional[str] = None):
        name_str = str(name_or_path).strip().strip("'\"`")
        if name_str in ("", ".", "default"):
            self.name = "default"
            self.path = os.path.abspath(base_dir or ".")
        else:
            self.name = os.path.basename(name_str)
            if base_dir:
                self.path = os.path.abspath(os.path.join(base_dir, name_str))
            else:
                self.path = os.path.abspath(name_str)

        if self.name != "default" and not os.path.exists(self.path):
            os.makedirs(self.path, exist_ok=True)

    @classmethod
    def create(cls, name: str, base_dir: Optional[str] = None) -> 'Database':
        """Creates a new database directory on disk."""
        db = cls(name, base_dir=base_dir)
        os.makedirs(db.path, exist_ok=True)
        return db

    def table_path(self, table_name: str) -> str:
        """Resolves table or subtable file path inside this database."""
        return resolve_table_path(table_name, active_db=self.name, base_dir=os.path.dirname(self.path) if self.name != "default" else self.path)

    def create_table(self, name: str, schema: Union[Schema, List[ColumnDef]], block_size: int = 1024) -> Table:
        """Creates a table or nested sub-table inside this database."""
        if isinstance(schema, list):
            schema = Schema(schema)
        path = resolve_table_path(name, active_db=self.name, for_create=True, base_dir=os.path.dirname(self.path) if self.name != "default" else self.path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return MergenDB.create_table(path, schema, block_size=block_size)

    def table(self, name: str) -> Table:
        """Opens an existing table or sub-table in this database."""
        path = resolve_table_path(name, active_db=self.name, base_dir=os.path.dirname(self.path) if self.name != "default" else self.path)
        return Table(path)

    def __getitem__(self, name: str) -> Table:
        return self.table(name)

    def list_tables(self) -> List[Dict[str, Any]]:
        """Lists all tables and nested sub-tables in this database."""
        return scan_tables_in_dir(self.path, db_name=self.name)

    def tables(self) -> List[str]:
        """Returns flat list of table and sub-table names in this database."""
        return [t["full_name"] for t in self.list_tables()]

    def drop_table(self, name: str) -> bool:
        """Drops a table and any of its nested sub-tables."""
        path = self.table_path(name)
        if os.path.exists(path):
            os.remove(path)
        sub_dir = path[:-5] if path.endswith(".mgdb") else path
        if os.path.exists(sub_dir) and os.path.isdir(sub_dir):
            import shutil
            shutil.rmtree(sub_dir, ignore_errors=True)
        return True

    def truncate_table(self, name: str) -> int:
        return self.table(name).truncate()

    def sql(self, sql_query: str, show_progress: bool = False) -> QueryResult:
        """Executes SQL in this database context."""
        return MergenDB.query(sql_query, active_db=self.name, show_progress=show_progress)

    def query(self, sql_or_pipeline: str, show_progress: bool = False) -> QueryResult:
        return MergenDB.query(sql_or_pipeline, active_db=self.name, show_progress=show_progress)

    def drop(self):
        """Drops the entire database and all contained tables."""
        if self.name != "default" and os.path.exists(self.path):
            import shutil
            shutil.rmtree(self.path, ignore_errors=True)

    def __repr__(self) -> str:
        count = len([t for t in self.list_tables() if t["type"] != "collection"])
        return f"<MergenDB.Database '{self.name}' tables={count}>"

    def __len__(self) -> int:
        return len([t for t in self.list_tables() if t["type"] != "collection"])


class MergenDB:
    """
    High-level entry point for database operations.
    """
    active_database = "default"

    @staticmethod
    def create_table(filepath: str, schema: Schema, block_size: int = 1024, active_db: Optional[str] = None) -> Table:
        resolved = resolve_table_path(filepath, active_db=active_db or getattr(MergenDB, "active_database", "default"), for_create=True)
        parent = os.path.dirname(resolved)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.exists(resolved):
            os.remove(resolved)
        with FileWriter(resolved, schema, block_size=block_size) as writer:
            pass # Creates empty valid .mgdb table with header & footer
        return Table(resolved)

    @staticmethod
    def open_table(filepath: str, active_db: Optional[str] = None) -> Table:
        resolved = resolve_table_path(filepath, active_db=active_db or getattr(MergenDB, "active_database", "default"))
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Table '{filepath}' (resolved to '{resolved}') not found.")
        return Table(resolved)

    @staticmethod
    def _convert_sql_to_pipeline(sql: str, active_db: Optional[str] = None) -> str:
        sql = sql.strip().rstrip(";")
        pattern = (
            r"^\s*SELECT\s+(?P<select>.+?)\s+"
            r"FROM\s+(?P<from>[^\s;]+)"
            r"(?:\s+(?P<join_type>LEFT(?:\s+OUTER)?|INNER)?\s*JOIN\s+(?P<join_tbl>[^\s]+)\s+ON\s+(?P<join_on>[^\s;]+(?:\s*=\s*[^\s;]+)?))?"
            r"(?:\s+WHERE\s+(?P<where>.+?))?"
            r"(?:\s+GROUP\s+BY\s+(?P<group>.+?))?"
            r"(?:\s+HAVING\s+(?P<having>.+?))?"
            r"(?:\s+ORDER\s+BY\s+(?P<order>.+?))?"
            r"(?:\s+LIMIT\s+(?P<limit>\d+))?\s*$"
        )
        m = re.match(pattern, sql, re.IGNORECASE | re.DOTALL)
        if not m:
            return sql

        d = m.groupdict()
        tbl = d["from"].strip().strip("'\"`")
        resolved_tbl = resolve_table_path(tbl, active_db=active_db or getattr(MergenDB, "active_database", "default"))
        pipe = [f'FROM "{resolved_tbl}"']

        if d.get("join_tbl") and d.get("join_on"):
            j_tbl = d["join_tbl"].strip().strip("'\"`")
            resolved_j = resolve_table_path(j_tbl, active_db=active_db or getattr(MergenDB, "active_database", "default"))
            j_type = "LEFT" if (d.get("join_type") and "LEFT" in d["join_type"].upper()) else "INNER"
            pipe.append(f'| {j_type} JOIN "{resolved_j}" ON {d["join_on"].strip()}')

        if d.get("where"):
            pipe.append(f'| WHERE {d["where"].strip()}')

        def split_commas(s: str) -> List[str]:
            parts = []
            curr = []
            depth = 0
            for ch in s:
                if ch == '(':
                    depth += 1
                    curr.append(ch)
                elif ch == ')':
                    depth -= 1
                    curr.append(ch)
                elif ch == ',' and depth == 0:
                    parts.append("".join(curr).strip())
                    curr = []
                else:
                    curr.append(ch)
            if curr:
                parts.append("".join(curr).strip())
            return [p for p in parts if p]

        agg_funcs = ("count(", "sum(", "avg(", "min(", "max(", "median(", "stddev(")
        select_items = split_commas(d["select"])
        has_agg = any(any(af in s.lower() for af in agg_funcs) for s in select_items)

        if has_agg or d.get("group"):
            aggs = [s for s in select_items if any(af in s.lower() for af in agg_funcs)]
            if not aggs:
                aggs = ["count(*)"]
            agg_clause = ", ".join(aggs)
            if d.get("group"):
                pipe.append(f'| AGGREGATE {agg_clause} BY {d["group"].strip()}')
            else:
                pipe.append(f'| AGGREGATE {agg_clause}')

            if d.get("having"):
                hav = d["having"].strip()
                for a in aggs:
                    parts = re.split(r"\s+as\s+", a, flags=re.IGNORECASE)
                    if len(parts) == 2:
                        fn_expr, alias = parts[0].strip(), parts[1].strip()
                        hav = re.sub(re.escape(fn_expr), alias, hav, flags=re.IGNORECASE)
                    else:
                        fn_m = re.match(r"(\w+)\s*\((.*?)\)", a)
                        if fn_m:
                            fname, col = fn_m.group(1).lower(), fn_m.group(2).strip()
                            alias = f"{fname}_{col}" if col and col != "*" else fname
                            hav = re.sub(re.escape(a), alias, hav, flags=re.IGNORECASE)
                pipe.append(f'| HAVING {hav}')
        else:
            if d["select"].strip() != "*":
                pipe.append(f'| SELECT {d["select"].strip()}')

        if d.get("order"):
            pipe.append(f'| SORT {d["order"].strip()}')
        if d.get("limit"):
            pipe.append(f'| LIMIT {d["limit"].strip()}')

        return "\n".join(pipe)

    @staticmethod
    def query(sql_or_pipeline: str, active_db: Optional[str] = None, show_progress: bool = False) -> QueryResult:
        query_str = sql_or_pipeline.strip().rstrip(";")
        t0 = time.perf_counter()
        act_db = active_db or getattr(MergenDB, "active_database", "default")

        # 0.1 SHOW DATABASES
        if re.match(r"^SHOW\s+DATABASES\b", query_str, re.IGNORECASE):
            dbs = list_databases()
            cols = ["Database", "Tables", "Disk_Bytes"]
            rows = [[d["name"], d["tables_count"], d["total_bytes"]] for d in dbs]
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(cols, rows, ExecutionStats(0, 0, 0, 0, 0, len(rows), elapsed_ms))

        # 0.2 CREATE DATABASE
        cdb_m = re.match(r"^CREATE\s+DATABASE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s;]+)$", query_str, re.IGNORECASE)
        if cdb_m:
            db_name = cdb_m.group(1).strip().strip("'\"`")
            Database.create(db_name)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status", "database"], [["OK", db_name]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        # 0.3 DROP DATABASE
        ddb_m = re.match(r"^DROP\s+DATABASE\s+(?:IF\s+EXISTS\s+)?([^\s;]+)$", query_str, re.IGNORECASE)
        if ddb_m:
            db_name = ddb_m.group(1).strip().strip("'\"`")
            Database(db_name).drop()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status", "database"], [["OK", db_name]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        # 0.4 USE <database>
        use_m = re.match(r"^USE\s+([^\s;]+)$", query_str, re.IGNORECASE)
        if use_m:
            target = use_m.group(1).strip().strip("'\"`")
            if target.endswith(".mgdb") or (os.path.isfile(target) and not os.path.isdir(target)):
                MergenDB.active_database = "default"
            else:
                MergenDB.active_database = target
                Database(target)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status", "database"], [["OK", target]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        # 0.5 SHOW TABLES [FROM <database>]
        st_m = re.match(r"^SHOW\s+TABLES(?:\s+FROM\s+([^\s;]+))?$", query_str, re.IGNORECASE)
        if st_m:
            target_db = st_m.group(1).strip().strip("'\"`") if st_m.group(1) else act_db
            db_obj = Database(target_db)
            tbl_list = db_obj.list_tables()
            cols = ["Table", "Type", "Parent", "Rows", "Bytes"]
            rows = [[t["full_name"], t["type"], t["parent"] or "NULL", t["rows"], t["bytes"]] for t in tbl_list]
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(cols, rows, ExecutionStats(0, 0, 0, 0, 0, len(rows), elapsed_ms))

        # 1. UPDATE statement
        update_m = re.match(r"^UPDATE\s+([^\s]+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$", query_str, re.IGNORECASE | re.DOTALL)
        if update_m:
            tbl_name, set_str, where_clause = update_m.groups()
            tbl_path = resolve_table_path(tbl_name, active_db=act_db)
            tbl = Table(tbl_path)
            set_dict = _parse_set_clause(set_str)
            updated = tbl.update(set_dict, where=where_clause)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["rows_affected"], [[updated]], ExecutionStats(0, 0, 0, 0, 0, updated, elapsed_ms))

        # 2. DELETE statement
        delete_m = re.match(r"^DELETE\s+(?:FROM\s+)?([^\s]+)(?:\s+WHERE\s+(.+))?$", query_str, re.IGNORECASE | re.DOTALL)
        if delete_m:
            tbl_name, where_clause = delete_m.groups()
            tbl_path = resolve_table_path(tbl_name, active_db=act_db)
            tbl = Table(tbl_path)
            deleted = tbl.delete(where=where_clause)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["rows_affected"], [[deleted]], ExecutionStats(0, 0, 0, 0, 0, deleted, elapsed_ms))

        # 3. ALTER TABLE statement
        alter_m = re.match(r"^ALTER\s+TABLE\s+([^\s]+)\s+(RENAME\s+COLUMN|DROP\s+COLUMN|ADD\s+COLUMN)\s+(.+)$", query_str, re.IGNORECASE | re.DOTALL)
        if alter_m:
            tbl_name, action, rest = alter_m.groups()
            tbl_path = resolve_table_path(tbl_name, active_db=act_db)
            tbl = Table(tbl_path)
            action_upper = action.upper()
            if "RENAME" in action_upper:
                ren_m = re.match(r"^([^\s]+)\s+TO\s+([^\s]+)$", rest.strip(), re.IGNORECASE)
                if not ren_m:
                    raise SyntaxError(f"Invalid RENAME syntax: ALTER TABLE {tbl_name} RENAME COLUMN {rest}")
                old_col, new_col = ren_m.groups()
                tbl.rename_column(old_col.strip().strip("'\"`"), new_col.strip().strip("'\"`"))
            elif "DROP" in action_upper:
                col_to_drop = rest.strip().strip("'\"`")
                tbl.drop_column(col_to_drop)
            elif "ADD" in action_upper:
                add_m = re.match(r"^([^\s]+)\s+([^\s]+)(?:\s+DEFAULT\s+(.+))?$", rest.strip(), re.IGNORECASE)
                if not add_m:
                    raise SyntaxError(f"Invalid ADD COLUMN syntax: ALTER TABLE {tbl_name} ADD COLUMN {rest}")
                col_name, col_type, def_val = add_m.groups()
                parsed_def = None
                if def_val is not None:
                    def_str = def_val.strip()
                    if (def_str.startswith("'") and def_str.endswith("'")) or (def_str.startswith('"') and def_str.endswith('"')):
                        parsed_def = def_str[1:-1].replace("''", "'")
                    elif def_str.upper() == "NULL":
                        parsed_def = None
                    elif def_str.upper() == "TRUE":
                        parsed_def = True
                    elif def_str.upper() == "FALSE":
                        parsed_def = False
                    else:
                        try:
                            parsed_def = float(def_str) if "." in def_str else int(def_str)
                        except ValueError:
                            parsed_def = def_str
                tbl.add_column(col_name.strip().strip("'\"`"), col_type.strip(), default=parsed_def)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        # 4. DROP TABLE statement
        drop_m = re.match(r"^DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([^\s;]+)$", query_str, re.IGNORECASE)
        if drop_m:
            tbl_name = drop_m.group(1).strip().strip("'\"`")
            tbl_path = resolve_table_path(tbl_name, active_db=act_db)
            tbl = Table(tbl_path)
            tbl.drop()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        # 5. TRUNCATE TABLE statement
        trunc_m = re.match(r"^TRUNCATE\s+(?:TABLE\s+)?([^\s;]+)$", query_str, re.IGNORECASE)
        if trunc_m:
            tbl_name = trunc_m.group(1).strip().strip("'\"`")
            tbl_path = resolve_table_path(tbl_name, active_db=act_db)
            tbl = Table(tbl_path)
            cnt = tbl.truncate()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["rows_affected"], [[cnt]], ExecutionStats(0, 0, 0, 0, 0, cnt, elapsed_ms))

        # 6. RENAME TABLE statement
        ren_tbl_m = re.match(r"^RENAME\s+TABLE\s+([^\s]+)\s+TO\s+([^\s;]+)$", query_str, re.IGNORECASE)
        if ren_tbl_m:
            old_tbl, new_tbl = ren_tbl_m.groups()
            old_path = resolve_table_path(old_tbl, active_db=act_db)
            new_path = resolve_table_path(new_tbl, active_db=act_db, for_create=True)
            tbl = Table(old_path)
            tbl.rename(new_path)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        if query_str.upper().startswith("SELECT ") and "FROM " in query_str.upper():
            query_str = MergenDB._convert_sql_to_pipeline(query_str, active_db=act_db)

        tokens = Lexer(query_str).tokenize()
        ast = Parser(tokens).parse()

        if isinstance(ast, QueryPlan):
            return QueryEngine.execute(ast, show_progress=show_progress)
        elif isinstance(ast, CreateTableNode):
            schema = Schema(ast.columns)
            target_path = resolve_table_path(ast.table_path, active_db=act_db, for_create=True)
            MergenDB.create_table(target_path, schema)
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, 0.0))
        elif isinstance(ast, InsertNode):
            target_path = resolve_table_path(ast.table_path, active_db=act_db)
            table = MergenDB.open_table(target_path)
            table.insert_many(ast.rows)
            return QueryResult(["rows_affected"], [[len(ast.rows)]], ExecutionStats(0, 0, 0, 0, 0, len(ast.rows), 0.0))
        else:
            raise TypeError(f"Unhandled statement type: {type(ast)}")

    @staticmethod
    def from_sqlite(sqlite_path: str, output_mgdb_path: str, table_name: Optional[str] = None, query: Optional[str] = None, block_size: int = 1024) -> Table:
        from mergendb.io.importer import DataImporter
        DataImporter.from_sqlite(sqlite_path, output_mgdb_path, table_name=table_name, query=query, block_size=block_size)
        return Table(output_mgdb_path)

    @staticmethod
    def from_sql_dump(sql_dump_path: str, output_mgdb_path: str, table_name: Optional[str] = None, block_size: int = 1024) -> Table:
        from mergendb.io.importer import DataImporter
        DataImporter.from_sql_dump(sql_dump_path, output_mgdb_path, table_name=table_name, block_size=block_size)
        return Table(output_mgdb_path)

    @staticmethod
    def from_csv(csv_path: str, output_mgdb_path: str, delimiter: str = ",", block_size: int = 1024) -> Table:
        from mergendb.io.importer import DataImporter
        DataImporter.from_csv(csv_path, output_mgdb_path, delimiter=delimiter, block_size=block_size)
        return Table(output_mgdb_path)

    @staticmethod
    def from_jsonl(jsonl_path: str, output_mgdb_path: str, block_size: int = 1024) -> Table:
        from mergendb.io.importer import DataImporter
        DataImporter.from_jsonl(jsonl_path, output_mgdb_path, block_size=block_size)
        return Table(output_mgdb_path)

    @staticmethod
    def from_json(json_path: str, output_mgdb_path: str, block_size: int = 1024) -> Table:
        from mergendb.io.importer import DataImporter
        DataImporter.from_json(json_path, output_mgdb_path, block_size=block_size)
        return Table(output_mgdb_path)



# High-Level Intuitive Aliases & Shortcuts
Connection = Database

def database(name: str = "default", base_dir: Optional[str] = None) -> Database:
    """Gets or creates a Database container."""
    return Database(name, base_dir=base_dir)

def create_database(name: str, base_dir: Optional[str] = None) -> Database:
    """Explicitly creates a new Database container."""
    return Database.create(name, base_dir=base_dir)

def drop_database(name: str, base_dir: Optional[str] = None):
    """Deletes a database directory and all contained tables."""
    Database(name, base_dir=base_dir).drop()

def connect(target: str = "default", base_dir: Optional[str] = None) -> Union[Database, Table]:
    """
    Connects to a database or opens a table file.
    If target ends with .mgdb or is an existing table file, returns Table.
    Otherwise, returns Database instance.
    """
    target_str = str(target).strip()
    if target_str.endswith(".mgdb") or (os.path.isfile(target_str) and not os.path.isdir(target_str)):
        return Table(target_str)
    return Database(target_str, base_dir=base_dir)

def open(target: str = "default", base_dir: Optional[str] = None) -> Union[Database, Table]:
    return connect(target, base_dir=base_dir)

def query(sql_or_pipeline: str, show_progress: bool = False) -> QueryResult:
    return MergenDB.query(sql_or_pipeline, show_progress=show_progress)

def sql(sql_query: str, show_progress: bool = False) -> QueryResult:
    """Executes a standard SQL query directly."""
    return MergenDB.query(sql_query, show_progress=show_progress)

def find(filepath: str, limit: Optional[int] = None, show_progress: bool = False, **kwargs) -> QueryResult:
    """Finds rows matching keyword filters in a table."""
    return Table(filepath).find(limit=limit, show_progress=show_progress, **kwargs)

def search(filepath: str, text: str, limit: Optional[int] = None, show_progress: bool = False) -> QueryResult:
    """Performs full-text search across all string columns."""
    return Table(filepath).search(text, limit=limit, show_progress=show_progress)

def update(filepath: str, set_values: Dict[str, Any], where: Optional[str] = None) -> int:
    """Updates matching rows in a table."""
    return Table(filepath).update(set_values, where=where)

def delete(filepath: str, where: Optional[str] = None) -> int:
    """Deletes matching rows in a table."""
    return Table(filepath).delete(where=where)

def rename_column(filepath: str, old_name: str, new_name: str) -> Table:
    """Renames an existing column in a table."""
    return Table(filepath).rename_column(old_name, new_name)

def drop_column(filepath: str, column_name: str) -> Table:
    """Drops a column from a table."""
    return Table(filepath).drop_column(column_name)

def add_column(filepath: str, column_name: str, data_type: Union[DataType, str], default: Any = None, nullable: bool = True) -> Table:
    """Adds a new column to a table."""
    return Table(filepath).add_column(column_name, data_type, default=default, nullable=nullable)

def truncate(filepath: str) -> int:
    """Clears all rows from a table while keeping schema."""
    return Table(filepath).truncate()

def drop_table(filepath: str) -> bool:
    """Deletes a table file from disk."""
    return Table(filepath).drop()

def rename_table(old_filepath: str, new_filepath: str) -> Table:
    """Renames a table file on disk."""
    return Table(old_filepath).rename(new_filepath)

def create_table(filepath: str, schema: Schema, block_size: int = 1024) -> Table:
    return MergenDB.create_table(filepath, schema, block_size)

def open_table(filepath: str) -> Table:
    return MergenDB.open_table(filepath)

def import_sql(sql_dump_path: str, output_mgdb_path: str, table_name: Optional[str] = None, block_size: int = 1024) -> Table:
    return MergenDB.from_sql_dump(sql_dump_path, output_mgdb_path, table_name=table_name, block_size=block_size)

def import_sqlite(sqlite_path: str, output_mgdb_path: str, table_name: Optional[str] = None, query: Optional[str] = None, block_size: int = 1024) -> Table:
    return MergenDB.from_sqlite(sqlite_path, output_mgdb_path, table_name=table_name, query=query, block_size=block_size)

def import_csv(csv_path: str, output_mgdb_path: str, delimiter: str = ",", block_size: int = 1024) -> Table:
    return MergenDB.from_csv(csv_path, output_mgdb_path, delimiter=delimiter, block_size=block_size)

def export_csv(mgdb_path: str, output_csv_path: str):
    Table(mgdb_path).export_csv(output_csv_path)

def export_json(mgdb_path: str, output_json_path: str):
    Table(mgdb_path).export_json(output_json_path)

def export_jsonl(mgdb_path: str, output_jsonl_path: str):
    Table(mgdb_path).export_jsonl(output_jsonl_path)

def export_sql(mgdb_path: str, output_sql_path: str):
    Table(mgdb_path).export_sql(output_sql_path)

# Retain original functions for 100% backwards compatibility
from_sqlite = import_sqlite
from_sql_dump = import_sql
from_csv = import_csv

