"""
MergenDB: Ultra-compact, columnar embedded database engine for edge and resource-constrained environments.
"""

from mergendb.client import (
    MergenDB, Table, Database, Connection,
    connect, open, query, sql, find, search,
    create_table, open_table,
    import_sql, import_sqlite, import_csv,
    export_csv, export_json, export_sql,
    from_sqlite, from_sql_dump, from_csv
)
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.query.engine import QueryResult
from mergendb.server.server import start_server

__version__ = "0.5.0"
__author__ = "Uğur Türker Kebeci (ugurturkerkebeci)"
__all__ = [
    # Primary intuitive developer API
    "connect",
    "open",
    "find",
    "search",
    "sql",
    "query",
    "Table",
    "Database",
    "Connection",
    "import_sql",
    "import_sqlite",
    "import_csv",
    "export_csv",
    "export_json",
    "export_sql",

    # Original engine classes and functions
    "MergenDB",
    "create_table",
    "open_table",
    "from_sqlite",
    "from_sql_dump",
    "from_csv",
    "start_server",
    "Schema",
    "ColumnDef",
    "DataType",
    "QueryResult"
]
