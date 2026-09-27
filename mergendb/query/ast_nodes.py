from dataclasses import dataclass
from typing import List, Optional, Any, Tuple
from mergendb.core.schema import ColumnDef

class ASTNode:
    pass

@dataclass
class ExprNode(ASTNode):
    pass

@dataclass
class LiteralNode(ExprNode):
    value: Any

@dataclass
class ColumnRefNode(ExprNode):
    name: str

@dataclass
class BinaryOpNode(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode

@dataclass
class ComputeNode(ASTNode):
    target_column: str
    expr: ExprNode

@dataclass
class AggFuncNode(ASTNode):
    func: str        # 'count', 'sum', 'avg', 'min', 'max'
    column: Optional[str]
    alias: str

@dataclass
class JoinNode(ASTNode):
    right_table: str
    left_key: str
    right_key: str
    join_type: str = "INNER"  # 'INNER' or 'LEFT'

@dataclass
class AggregateNode(ASTNode):
    aggregations: List[AggFuncNode]
    group_by: List[str]
    having_expr: Optional[ExprNode] = None

@dataclass
class SortNode(ASTNode):
    column: str
    descending: bool = False

@dataclass
class QueryPlan(ASTNode):
    table_source: str
    join: Optional[JoinNode] = None
    where_expr: Optional[ExprNode] = None
    computes: List[ComputeNode] = None
    select_columns: Optional[List[str]] = None
    aggregate: Optional[AggregateNode] = None
    sort: Optional[SortNode] = None
    limit: Optional[int] = None

    def __post_init__(self):
        if self.computes is None:
            self.computes = []

@dataclass
class CreateTableNode(ASTNode):
    table_path: str
    columns: List[ColumnDef]

@dataclass
class InsertNode(ASTNode):
    table_path: str
    rows: List[List[Any]]
