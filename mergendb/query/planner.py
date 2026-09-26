from typing import List, Tuple, Any, Optional, Set
from mergendb.query.ast_nodes import (
    QueryPlan, ExprNode, BinaryOpNode, ColumnRefNode, LiteralNode
)

class QueryPlanner:
    """
    Optimizes MergenQL query execution by:
    1. Extracting pushdown predicates for ZoneMap block skipping at storage level.
    2. Pruning unused columns so only referenced columns are ever read from disk.
    """

    @classmethod
    def extract_pushdown_predicates(cls, expr: Optional[ExprNode]) -> List[Tuple[str, str, Any]]:
        """
        Recursively extracts simple AND-connected predicates like `col > 10` or `status == 'active'`
        that can be checked against ZoneMaps before reading blocks.
        """
        if expr is None:
            return []

        predicates: List[Tuple[str, str, Any]] = []

        if isinstance(expr, BinaryOpNode):
            if expr.op == "AND":
                predicates.extend(cls.extract_pushdown_predicates(expr.left))
                predicates.extend(cls.extract_pushdown_predicates(expr.right))
            elif expr.op in ("==", "=", "!=", ">", ">=", "<", "<="):
                # Check for col OP literal
                if isinstance(expr.left, ColumnRefNode) and isinstance(expr.right, LiteralNode):
                    predicates.append((expr.left.name, expr.op, expr.right.value))
                # Check for literal OP col
                elif isinstance(expr.left, LiteralNode) and isinstance(expr.right, ColumnRefNode):
                    # Flip operator
                    flipped_ops = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!=", "=": "="}
                    predicates.append((expr.right.name, flipped_ops.get(expr.op, expr.op), expr.left.value))

        return predicates

    @classmethod
    def collect_required_columns(cls, plan: QueryPlan) -> Optional[List[str]]:
        """
        Finds all column names needed anywhere in the query (WHERE, SELECT, COMPUTE, AGG, SORT).
        If SELECT is omitted and no AGG, returns None (meaning all columns).
        """
        # If user specified SELECT *, or no SELECT and no AGG, we need all columns
        if plan.select_columns is None and plan.aggregate is None:
            return None

        required: Set[str] = set()

        def collect_from_expr(e: Optional[ExprNode]):
            if e is None:
                return
            if isinstance(e, ColumnRefNode):
                required.add(e.name)
            elif isinstance(e, BinaryOpNode):
                collect_from_expr(e.left)
                collect_from_expr(e.right)

        collect_from_expr(plan.where_expr)

        for comp in plan.computes:
            collect_from_expr(comp.expr)

        computed_names = {c.target_column for c in plan.computes}
        if plan.aggregate:
            for agg in plan.aggregate.aggregations:
                computed_names.add(agg.alias)

        if plan.select_columns:
            for col in plan.select_columns:
                if col not in computed_names:
                    required.add(col)

        if plan.aggregate:
            for agg in plan.aggregate.aggregations:
                if agg.column and agg.column != "*":
                    required.add(agg.column)
            for g in plan.aggregate.group_by:
                required.add(g)

        if plan.sort:
            if plan.sort.column not in computed_names:
                required.add(plan.sort.column)

        return list(required)

    @classmethod
    def collect_filter_columns(cls, expr: Optional[ExprNode]) -> List[str]:
        """Collects all column names referenced in the WHERE filter expression."""
        if expr is None:
            return []
        cols: Set[str] = set()

        def collect(e: Optional[ExprNode]):
            if e is None:
                return
            if isinstance(e, ColumnRefNode):
                cols.add(e.name)
            elif isinstance(e, BinaryOpNode):
                collect(e.left)
                collect(e.right)

        collect(expr)
        return list(cols)
