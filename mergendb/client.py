import os
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
    """

    def __init__(self, filepath: str):
        self.filepath = filepath

    @property
    def schema(self) -> Schema:
        with FileReader(self.filepath) as reader:
            return reader.schema

    @property
    def row_count(self) -> int:
        with FileReader(self.filepath) as reader:
            return reader.total_rows

    def insert_many(self, rows: List[Any], block_size: int = 1024):
        """
        Appends rows to the table. If file exists, merges existing blocks with new ones.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Table file '{self.filepath}' does not exist. Call create_table first.")

        # Read existing schema and all existing rows
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

    def query(self, pipeline: str) -> QueryResult:
        full_query = f'FROM "{self.filepath}"\n' + pipeline.strip()
        tokens = Lexer(full_query).tokenize()
        plan = Parser(tokens).parse()
        if not isinstance(plan, QueryPlan):
            raise ValueError("Expected a query pipeline")
        return QueryEngine.execute(plan)


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
            raise FileNotFoundError(f"File '{filepath}' not found.")
        return Table(filepath)

    @staticmethod
    def query(sql_or_pipeline: str) -> QueryResult:
        tokens = Lexer(sql_or_pipeline).tokenize()
        ast = Parser(tokens).parse()

        if isinstance(ast, QueryPlan):
            return QueryEngine.execute(ast)
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

def query(sql_or_pipeline: str) -> QueryResult:
    return MergenDB.query(sql_or_pipeline)

def create_table(filepath: str, schema: Schema, block_size: int = 1024) -> Table:
    return MergenDB.create_table(filepath, schema, block_size)

def open_table(filepath: str) -> Table:
    return MergenDB.open_table(filepath)

def from_sqlite(sqlite_path: str, output_mgdb_path: str, table_name: Optional[str] = None, query: Optional[str] = None, block_size: int = 1024) -> Table:
    return MergenDB.from_sqlite(sqlite_path, output_mgdb_path, table_name=table_name, query=query, block_size=block_size)

def from_sql_dump(sql_dump_path: str, output_mgdb_path: str, table_name: Optional[str] = None, block_size: int = 1024) -> Table:
    return MergenDB.from_sql_dump(sql_dump_path, output_mgdb_path, table_name=table_name, block_size=block_size)

def from_csv(csv_path: str, output_mgdb_path: str, delimiter: str = ",", block_size: int = 1024) -> Table:
    return MergenDB.from_csv(csv_path, output_mgdb_path, delimiter=delimiter, block_size=block_size)
