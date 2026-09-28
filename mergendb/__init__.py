"""
MergenDB: Ultra-compact, columnar embedded database engine for edge and resource-constrained environments.
"""

from mergendb.client import (
    MergenDB, Table, Database, Connection,
    database, create_database, drop_database, list_databases,
    connect, open, query, sql, find, search,
    update, delete, rename_column, drop_column, add_column,
    truncate, drop_table, rename_table,
    create_table, open_table,
    import_sql, import_sqlite, import_csv,
    export_csv, export_json, export_jsonl, export_sql,
    from_sqlite, from_sql_dump, from_csv
)
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.query.engine import QueryResult
from mergendb.server.server import start_server

def test(verbose: bool = True):
    """Runs full system verification and device hardware benchmark."""
    from mergendb.testing.suite import run_diagnostics
    return run_diagnostics(verbose=verbose)

def benchmark(verbose: bool = True):
    """Benchmarks device capabilities, import/export speeds, and scan throughput."""
    from mergendb.testing.suite import run_diagnostics
    return run_diagnostics(verbose=verbose)

def diagnose(verbose: bool = True):
    """Alias for mergendb.test() / mergendb.benchmark()."""
    from mergendb.testing.suite import run_diagnostics
    return run_diagnostics(verbose=verbose)

__version__ = "0.6.6"
__author__ = "Uğur Türker Kebeci (ugurturkerkebeci)"
__all__ = [
    # Primary intuitive developer API
    "connect",
    "open",
    "find",
    "search",
    "sql",
    "query",
    "update",
    "delete",
    "rename_column",
    "drop_column",
    "add_column",
    "truncate",
    "drop_table",
    "rename_table",
    "Table",
    "Database",
    "Connection",
    "database",
    "create_database",
    "drop_database",
    "list_databases",
    "import_sql",
    "import_sqlite",
    "import_csv",
    "export_csv",
    "export_json",
    "export_jsonl",
    "export_sql",
    "test",
    "benchmark",
    "diagnose",

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
