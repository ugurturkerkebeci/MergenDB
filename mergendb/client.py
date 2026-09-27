import os
import re
import csv
import json
from typing import List, Dict, Any, Union, Optional
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.storage.writer import FileWriter
from mergendb.storage.reader import FileReader
from mergendb.query.engine import QueryEngine, QueryResult
from mergendb.query.parser import Parser
from mergendb.query.lexer import Lexer
from mergendb.query.ast_nodes import QueryPlan, CreateTableNode, InsertNode


class Table:
    """
    Represents a MergenDB columnar table file.
    Provides intuitive, Pythonic data manipulation and querying methods.
    """

    def __init__(self, filepath: str):
        if not filepath.endswith(".mgdb") and not os.path.exists(filepath):
            filepath += ".mgdb"
        self.filepath = filepath

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
        Appends rows to the table. If file exists, merges existing blocks with new ones.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' does not exist. Call create_table first.")

        with FileReader(self.filepath) as reader:
            schema = reader.schema
            existing_rows = []
            for batch, _ in reader.scan():
                cols = batch.columns
                col_names = schema.column_names()
                for i in range(batch.row_count):
                    existing_rows.append([cols[c][i] for c in col_names])

        all_rows = existing_rows + rows
        temp_path = self.filepath + ".tmp"
        with FileWriter(temp_path, schema, block_size=block_size) as writer:
            writer.write_rows(all_rows)

        os.replace(temp_path, self.filepath)

    def query(self, pipeline: str, show_progress: bool = False) -> QueryResult:
        """Runs a MergenQL pipeline query against this table."""
        full_query = f'FROM "{self.filepath}"\n' + pipeline.strip()
        tokens = Lexer(full_query).tokenize()
        plan = Parser(tokens).parse()
        if not isinstance(plan, QueryPlan):
            raise ValueError("Expected a query pipeline")
        return QueryEngine.execute(plan, show_progress=show_progress)

    def sql(self, query_str: str, show_progress: bool = False) -> QueryResult:
        """Executes a standard SQL query against this table."""
        tbl_base = os.path.splitext(os.path.basename(self.filepath))[0]
        clean_path = self.filepath.replace("\\", "/")
        query_fixed = re.sub(rf"\bFROM\s+[`\"']?{re.escape(tbl_base)}[`\"']?\b", lambda m: f'FROM "{clean_path}"', query_str, flags=re.IGNORECASE)
        return MergenDB.query(query_fixed, show_progress=show_progress)

    def execute(self, query_or_sql: str, show_progress: bool = False) -> QueryResult:
        """Alias for sql / query."""
        if query_or_sql.strip().upper().startswith("SELECT "):
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

    def export(self, output_path: str):
        """Automatically exports table data based on file extension (.csv, .json, .jsonl, .sql)."""
        lower = output_path.lower()
        if lower.endswith(".csv"):
            self.export_csv(output_path)
        elif lower.endswith(".json") or lower.endswith(".jsonl"):
            self.export_json(output_path)
        elif lower.endswith(".sql"):
            self.export_sql(output_path)
        else:
            raise ValueError(f"Unsupported export format for '{output_path}'. Use .csv, .json, or .sql.")

    def export_csv(self, output_path: str):
        """Exports all rows to a CSV file."""
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            with open(output_path, "w", newline="", encoding="utf-8", buffering=256*1024) as f:
                writer = csv.writer(f)
                writer.writerow(col_names)
                for batch, _ in reader.scan():
                    cols = batch.columns
                    writer.writerows(zip(*(cols[c] for c in col_names)))

    def export_json(self, output_path: str):
        """Exports all rows to a JSONL file."""
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            with open(output_path, "w", encoding="utf-8", buffering=256*1024) as f:
                for batch, _ in reader.scan():
                    cols = batch.columns
                    lines = [json.dumps(dict(zip(col_names, row))) + "\n" for row in zip(*(cols[c] for c in col_names))]
                    f.writelines(lines)

    def export_sql(self, output_path: str):
        """Exports all rows to an SQL INSERT dump file."""
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            clean_tbl = os.path.splitext(os.path.basename(self.filepath))[0]
            with open(output_path, "w", encoding="utf-8", buffering=256*1024) as f:
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


class MergenDB:
    """
    High-level entry point for database operations.
    """

    @staticmethod
    def create_table(filepath: str, schema: Schema, block_size: int = 1024) -> Table:
        if os.path.exists(filepath):
            os.remove(filepath)
        with FileWriter(filepath, schema, block_size=block_size) as writer:
            pass # Creates empty valid .mgdb table with header & footer
        return Table(filepath)

    @staticmethod
    def open_table(filepath: str) -> Table:
        if not os.path.exists(filepath):
            if os.path.exists(filepath + ".mgdb"):
                filepath += ".mgdb"
            else:
                raise FileNotFoundError(f"File '{filepath}' not found.")
        return Table(filepath)

    @staticmethod
    def _convert_sql_to_pipeline(sql: str) -> str:
        sql = sql.strip().rstrip(";")
        m = re.match(r"SELECT\s+(.+?)\s+FROM\s+([^\s;]+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$", sql, re.IGNORECASE)
        if not m:
            return sql

        cols, tbl, where_clause, order_by, limit_val = m.groups()
        tbl = tbl.strip().strip("'\"`")
        if not tbl.endswith(".mgdb") and not os.path.exists(tbl):
            tbl += ".mgdb"
        pipe = [f'FROM "{tbl}"']

        if where_clause:
            pipe.append(f"| WHERE {where_clause}")
        if cols.strip() != "*":
            pipe.append(f"| SELECT {cols}")
        if order_by:
            pipe.append(f"| SORT {order_by}")
        if limit_val:
            pipe.append(f"| LIMIT {limit_val}")

        return "\n".join(pipe)

    @staticmethod
    def query(sql_or_pipeline: str, show_progress: bool = False) -> QueryResult:
        query_str = sql_or_pipeline.strip().rstrip(";")
        if query_str.upper().startswith("SELECT ") and "FROM " in query_str.upper():
            query_str = MergenDB._convert_sql_to_pipeline(query_str)

        tokens = Lexer(query_str).tokenize()
        ast = Parser(tokens).parse()

        if isinstance(ast, QueryPlan):
            return QueryEngine.execute(ast, show_progress=show_progress)
        elif isinstance(ast, CreateTableNode):
            schema = Schema(ast.columns)
            MergenDB.create_table(ast.table_path, schema)
            return QueryResult([], [], None)
        elif isinstance(ast, InsertNode):
            table = MergenDB.open_table(ast.table_path)
            table.insert_many(ast.rows)
            return QueryResult([], [], None)
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


# High-Level Intuitive Aliases & Shortcuts
Database = Table
Connection = Table
connect = Table
open = Table

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

def export_sql(mgdb_path: str, output_sql_path: str):
    Table(mgdb_path).export_sql(output_sql_path)

# Retain original functions for 100% backwards compatibility
from_sqlite = import_sqlite
from_sql_dump = import_sql
from_csv = import_csv
