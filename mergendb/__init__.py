"""
MergenDB: Ultra-compact, columnar embedded database engine for edge and resource-constrained environments.
"""

from mergendb.client import MergenDB, Table, query, create_table, open_table
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType
from mergendb.query.engine import QueryResult

__version__ = "0.1.0"
__all__ = [
    "MergenDB",
    "Table",
    "query",
    "create_table",
    "open_table",
    "Schema",
    "ColumnDef",
    "DataType",
    "QueryResult"
]
