"""
MergenDB: Ultra-compact, columnar embedded database engine for edge and resource-constrained environments.
"""

from mergendb.client import (
    MergenDB, Table, query, create_table, open_table,
    from_sqlite, from_sql_dump, from_csv
)
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.query.engine import QueryResult

__version__ = "0.3.0"
__author__ = "Uğur Türker Kebeci (ugurturkerkebeci)"
__all__ = [
    "MergenDB",
    "Table",
    "query",
    "create_table",
    "open_table",
    "from_sqlite",
    "from_sql_dump",
    "from_csv",
    "Schema",
    "ColumnDef",
    "DataType",
    "QueryResult"
]
