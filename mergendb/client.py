import os
import re
import csv
import json
import time
import builtins
from typing import List, Dict, Any, Union, Optional
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType, cast_value
from mergendb.storage.writer import FileWriter
from mergendb.storage.reader import FileReader
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
        Appends rows to the table with streaming block preservation.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' does not exist. Call create_table first.")

        temp_path = self.filepath + ".tmp"
        with FileReader(self.filepath) as reader:
            schema = reader.schema
            with FileWriter(temp_path, schema, block_size=block_size) as writer:
                for batch, _ in reader.scan():
                    writer.write_columns(batch.columns, batch.row_count)
                writer.write_rows(rows)

        os.replace(temp_path, self.filepath)

    def rename_column(self, old_name: str, new_name: str) -> "Table":
        """
        Renames an existing column in the table schema and data.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        temp_path = self.filepath + ".tmp"
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

        os.replace(temp_path, self.filepath)
        return self

    def drop_column(self, column_name: str) -> "Table":
        """
        Permanently drops a column from the table schema and data.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")

        temp_path = self.filepath + ".tmp"
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

        os.replace(temp_path, self.filepath)
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

        temp_path = self.filepath + ".tmp"
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

        os.replace(temp_path, self.filepath)
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

        temp_path = self.filepath + ".tmp"
        updated_count = 0

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

        os.replace(temp_path, self.filepath)
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

        temp_path = self.filepath + ".tmp"
        deleted_count = 0

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

        os.replace(temp_path, self.filepath)
        return deleted_count

    def truncate(self) -> int:
        """
        Removes all rows from the table while preserving schema.
        Returns number of rows removed.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' not found.")
        with FileReader(self.filepath) as reader:
            schema = reader.schema
            total = reader.total_rows

        temp_path = self.filepath + ".tmp"
        with FileWriter(temp_path, schema) as writer:
            pass

        os.replace(temp_path, self.filepath)
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

    def export(self, output_path: str):
        """Automatically exports table data based on file extension (.csv, .json, .jsonl, .sql)."""
        lower = output_path.lower()
        if lower.endswith(".csv"):
            self.export_csv(output_path)
        elif lower.endswith(".jsonl"):
            self.export_jsonl(output_path)
        elif lower.endswith(".json"):
            self.export_json(output_path)
        elif lower.endswith(".sql"):
            self.export_sql(output_path)
        else:
            raise ValueError(f"Unsupported export format for '{output_path}'. Use .csv, .json, .jsonl, or .sql.")

    def export_csv(self, output_path: str):
        """Exports all rows to a CSV file."""
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
        with FileReader(self.filepath) as reader:
            col_names = reader.schema.column_names()
            with builtins.open(output_path, "w", encoding="utf-8", buffering=256*1024) as f:
                for batch, _ in reader.scan():
                    cols = batch.columns
                    lines = [json.dumps(dict(zip(col_names, row))) + "\n" for row in zip(*(cols[c] for c in col_names))]
                    f.writelines(lines)

    def export_sql(self, output_path: str):
        """Exports all rows to an SQL INSERT dump file."""
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
        t0 = time.perf_counter()

        # 1. UPDATE statement
        update_m = re.match(r"^UPDATE\s+([^\s]+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$", query_str, re.IGNORECASE | re.DOTALL)
        if update_m:
            tbl_name, set_str, where_clause = update_m.groups()
            tbl = Table(tbl_name.strip().strip("'\"`"))
            set_dict = _parse_set_clause(set_str)
            updated = tbl.update(set_dict, where=where_clause)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["rows_affected"], [[updated]], ExecutionStats(0, 0, 0, 0, 0, updated, elapsed_ms))

        # 2. DELETE statement
        delete_m = re.match(r"^DELETE\s+(?:FROM\s+)?([^\s]+)(?:\s+WHERE\s+(.+))?$", query_str, re.IGNORECASE | re.DOTALL)
        if delete_m:
            tbl_name, where_clause = delete_m.groups()
            tbl = Table(tbl_name.strip().strip("'\"`"))
            deleted = tbl.delete(where=where_clause)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["rows_affected"], [[deleted]], ExecutionStats(0, 0, 0, 0, 0, deleted, elapsed_ms))

        # 3. ALTER TABLE statement
        alter_m = re.match(r"^ALTER\s+TABLE\s+([^\s]+)\s+(RENAME\s+COLUMN|DROP\s+COLUMN|ADD\s+COLUMN)\s+(.+)$", query_str, re.IGNORECASE | re.DOTALL)
        if alter_m:
            tbl_name, action, rest = alter_m.groups()
            tbl = Table(tbl_name.strip().strip("'\"`"))
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
            tbl = Table(tbl_name)
            tbl.drop()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        # 5. TRUNCATE TABLE statement
        trunc_m = re.match(r"^TRUNCATE\s+(?:TABLE\s+)?([^\s;]+)$", query_str, re.IGNORECASE)
        if trunc_m:
            tbl_name = trunc_m.group(1).strip().strip("'\"`")
            tbl = Table(tbl_name)
            cnt = tbl.truncate()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["rows_affected"], [[cnt]], ExecutionStats(0, 0, 0, 0, 0, cnt, elapsed_ms))

        # 6. RENAME TABLE statement
        ren_tbl_m = re.match(r"^RENAME\s+TABLE\s+([^\s]+)\s+TO\s+([^\s;]+)$", query_str, re.IGNORECASE)
        if ren_tbl_m:
            old_tbl, new_tbl = ren_tbl_m.groups()
            tbl = Table(old_tbl.strip().strip("'\"`"))
            tbl.rename(new_tbl.strip().strip("'\"`"))
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, elapsed_ms))

        if query_str.upper().startswith("SELECT ") and "FROM " in query_str.upper():
            query_str = MergenDB._convert_sql_to_pipeline(query_str)

        tokens = Lexer(query_str).tokenize()
        ast = Parser(tokens).parse()

        if isinstance(ast, QueryPlan):
            return QueryEngine.execute(ast, show_progress=show_progress)
        elif isinstance(ast, CreateTableNode):
            schema = Schema(ast.columns)
            MergenDB.create_table(ast.table_path, schema)
            return QueryResult(["status"], [["OK"]], ExecutionStats(0, 0, 0, 0, 0, 1, 0.0))
        elif isinstance(ast, InsertNode):
            table = MergenDB.open_table(ast.table_path)
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

