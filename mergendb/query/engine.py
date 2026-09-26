import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Union
from mergendb.storage.reader import FileReader, ScanStats, ColumnBatch
from mergendb.query.ast_nodes import (
    QueryPlan, ExprNode, BinaryOpNode, ColumnRefNode, LiteralNode,
    ComputeNode, AggregateNode, SortNode
)
from mergendb.query.planner import QueryPlanner

@dataclass
class ExecutionStats:
    total_blocks: int
    blocks_scanned: int
    blocks_skipped: int
    bytes_read: int
    rows_scanned: int
    rows_returned: int
    execution_time_ms: float

class QueryResult:
    def __init__(self, column_names: List[str], rows: List[List[Any]], stats: ExecutionStats):
        self.column_names = column_names
        self.rows = rows
        self.stats = stats

    def __len__(self) -> int:
        return len(self.rows)

    def __repr__(self) -> str:
        return f"<QueryResult rows={len(self.rows)} time={self.stats.execution_time_ms:.2f}ms>"

    def display(self, max_rows: int = 50) -> str:
        """Formats the result as a clean, aligned tabular ASCII text."""
        if not self.column_names:
            return "(Empty result)"

        # Stringify rows for formatting
        str_rows = [[str(val) if val is not None else "NULL" for val in r] for r in self.rows[:max_rows]]

        # Determine column widths
        col_widths = [len(c) for c in self.column_names]
        for r in str_rows:
            for i, val in enumerate(r):
                if len(val) > col_widths[i]:
                    col_widths[i] = len(val)

        # Build table lines
        sep_line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        header_line = "|" + "|".join(f" {self.column_names[i].center(w)} " for i, w in enumerate(col_widths)) + "|"

        lines = [sep_line, header_line, sep_line]
        for r in str_rows:
            row_str = "|" + "|".join(f" {r[i].ljust(w)} " for i, w in enumerate(col_widths)) + "|"
            lines.append(row_str)

        lines.append(sep_line)
        if len(self.rows) > max_rows:
            lines.append(f"... {len(self.rows) - max_rows} more rows hidden ...")

        # Stats summary
        lines.append(
            f"Returned {len(self.rows)} rows in {self.stats.execution_time_ms:.2f} ms | "
            f"Blocks: {self.stats.blocks_scanned} scanned, {self.stats.blocks_skipped} skipped (pruned) | "
            f"Read: {self.stats.bytes_read / 1024:.2f} KB"
        )
        return "\n".join(lines)


class ExpressionEvaluator:
    @classmethod
    def evaluate(cls, expr: ExprNode, cols: Dict[str, List[Any]], row_count: int) -> List[Any]:
        if isinstance(expr, LiteralNode):
            return [expr.value] * row_count

        elif isinstance(expr, ColumnRefNode):
            if expr.name not in cols:
                raise KeyError(f"Column '{expr.name}' not found during evaluation.")
            return cols[expr.name]

        elif isinstance(expr, BinaryOpNode):
            left_vals = cls.evaluate(expr.left, cols, row_count)
            right_vals = cls.evaluate(expr.right, cols, row_count)
            op = expr.op

            res = []
            if op == "+":
                for l, r in zip(left_vals, right_vals):
                    res.append(None if l is None or r is None else l + r)
            elif op == "-":
                for l, r in zip(left_vals, right_vals):
                    res.append(None if l is None or r is None else l - r)
            elif op == "*":
                for l, r in zip(left_vals, right_vals):
                    res.append(None if l is None or r is None else l * r)
            elif op == "/":
                for l, r in zip(left_vals, right_vals):
                    res.append(None if l is None or r is None or r == 0 else l / r)
            elif op == "%":
                for l, r in zip(left_vals, right_vals):
                    res.append(None if l is None or r is None or r == 0 else l % r)
            elif op in ("==", "="):
                for l, r in zip(left_vals, right_vals):
                    res.append(l == r)
            elif op in ("!=", "<>"):
                for l, r in zip(left_vals, right_vals):
                    res.append(l != r)
            elif op == "<":
                for l, r in zip(left_vals, right_vals):
                    res.append(False if l is None or r is None else l < r)
            elif op == "<=":
                for l, r in zip(left_vals, right_vals):
                    res.append(False if l is None or r is None else l <= r)
            elif op == ">":
                for l, r in zip(left_vals, right_vals):
                    res.append(False if l is None or r is None else l > r)
            elif op == ">=":
                for l, r in zip(left_vals, right_vals):
                    res.append(False if l is None or r is None else l >= r)
            elif op == "AND":
                for l, r in zip(left_vals, right_vals):
                    res.append(bool(l and r))
            elif op == "OR":
                for l, r in zip(left_vals, right_vals):
                    res.append(bool(l or r))
            elif op == "LIKE":
                import re
                for l, r in zip(left_vals, right_vals):
                    if l is None or r is None:
                        res.append(False)
                    else:
                        pattern = str(r)
                        regex_pattern = "^" + re.escape(pattern).replace("%", ".*").replace("_", ".") + "$"
                        res.append(bool(re.match(regex_pattern, str(l), re.IGNORECASE)))
            else:
                raise ValueError(f"Unsupported binary operator: {op}")

            return res

        raise TypeError(f"Unknown ExprNode: {type(expr)}")


class QueryEngine:
    """
    Executes MergenQL QueryPlans over compressed columnar storage with vector processing.
    """

    @classmethod
    def execute(cls, plan: QueryPlan) -> QueryResult:
        start_time = time.perf_counter()

        # Step 1: Optimize plan (Pushdowns & Column Pruning)
        pushdown_preds = QueryPlanner.extract_pushdown_predicates(plan.where_expr)
        needed_columns = QueryPlanner.collect_required_columns(plan)

        # Open storage reader
        reader = FileReader(plan.table_source)

        total_blocks = len(reader.blocks)
        blocks_scanned = 0
        blocks_skipped = 0
        bytes_read = 0
        rows_scanned = 0

        collected_rows: List[List[Any]] = []

        # Step 2: Stream blocks
        try:
            # Check if this query involves aggregation
            is_aggregate = plan.aggregate is not None

            # Accumulator state for aggregations:
            # group_key -> { 'count': int, 'sums': Dict[alias, float], 'mins': ..., 'maxs': ... }
            agg_state: Dict[Tuple, Dict[str, Any]] = {}

            for batch, scan_stats in reader.scan(columns=needed_columns, predicates=pushdown_preds):
                blocks_scanned = scan_stats.blocks_scanned
                blocks_skipped = scan_stats.blocks_skipped
                bytes_read = scan_stats.bytes_read
                rows_scanned = scan_stats.rows_scanned

                current_cols = dict(batch.columns)
                count = batch.row_count

                # Filter evaluation (if where_expr exists)
                if plan.where_expr is not None:
                    mask = ExpressionEvaluator.evaluate(plan.where_expr, current_cols, count)
                    # Filter all column vectors by mask
                    for k in current_cols:
                        current_cols[k] = [v for v, m in zip(current_cols[k], mask) if m]
                    count = sum(1 for m in mask if m)

                if count == 0:
                    continue

                # Compute expressions
                for comp in plan.computes:
                    comp_vals = ExpressionEvaluator.evaluate(comp.expr, current_cols, count)
                    current_cols[comp.target_column] = comp_vals

                # Handle Aggregation
                if is_aggregate:
                    cls._accumulate_aggregate(plan.aggregate, current_cols, count, agg_state)
                else:
                    # Determine columns to project
                    proj_cols = plan.select_columns if plan.select_columns is not None else list(current_cols.keys())
                    for i in range(count):
                        row = [current_cols[c][i] for c in proj_cols]
                        collected_rows.append(row)

            # Post-Scan Processing
            final_columns: List[str] = []

            if is_aggregate:
                final_columns, collected_rows = cls._finalize_aggregate(plan.aggregate, agg_state)
            else:
                if plan.select_columns is not None:
                    final_columns = plan.select_columns
                else:
                    final_columns = reader.schema.column_names() + [c.target_column for c in plan.computes]

            # Sorting
            if plan.sort is not None:
                sort_col = plan.sort.column
                if sort_col in final_columns:
                    col_idx = final_columns.index(sort_col)
                    # Safe sort handling None values
                    def sort_key(row):
                        v = row[col_idx]
                        return (1 if v is None else 0, v)
                    collected_rows.sort(key=sort_key, reverse=plan.sort.descending)

            # Limit
            if plan.limit is not None and plan.limit >= 0:
                collected_rows = collected_rows[:plan.limit]

        finally:
            reader.close()

        end_time = time.perf_counter()
        exec_ms = (end_time - start_time) * 1000.0

        stats = ExecutionStats(
            total_blocks=total_blocks,
            blocks_scanned=blocks_scanned,
            blocks_skipped=blocks_skipped,
            bytes_read=bytes_read,
            rows_scanned=rows_scanned,
            rows_returned=len(collected_rows),
            execution_time_ms=exec_ms
        )

        return QueryResult(final_columns, collected_rows, stats)

    @classmethod
    def _accumulate_aggregate(
        cls,
        agg_node: AggregateNode,
        cols: Dict[str, List[Any]],
        count: int,
        state: Dict[Tuple, Dict[str, Any]]
    ):
        group_cols = agg_node.group_by

        for i in range(count):
            if group_cols:
                key = tuple(cols[g][i] for g in group_cols)
            else:
                key = ()

            if key not in state:
                state[key] = {
                    "count": 0,
                    "sums": {},
                    "mins": {},
                    "maxs": {},
                    "values": {},
                }

            entry = state[key]
            entry["count"] += 1

            for func_node in agg_node.aggregations:
                alias = func_node.alias
                fn = func_node.func
                val = cols[func_node.column][i] if func_node.column and func_node.column != "*" else None

                if fn in ("sum", "avg"):
                    if val is not None:
                        entry["sums"][alias] = entry["sums"].get(alias, 0.0) + float(val)
                elif fn in ("median", "stddev"):
                    if val is not None:
                        if alias not in entry["values"]:
                            entry["values"][alias] = []
                        entry["values"][alias].append(float(val))
                elif fn == "min":
                    if val is not None:
                        if alias not in entry["mins"] or val < entry["mins"][alias]:
                            entry["mins"][alias] = val
                elif fn == "max":
                    if val is not None:
                        if alias not in entry["maxs"] or val > entry["maxs"][alias]:
                            entry["maxs"][alias] = val

    @classmethod
    def _finalize_aggregate(
        cls,
        agg_node: AggregateNode,
        state: Dict[Tuple, Dict[str, Any]]
    ) -> Tuple[List[str], List[List[Any]]]:
        col_names = list(agg_node.group_by) + [a.alias for a in agg_node.aggregations]
        rows: List[List[Any]] = []

        if not state and not agg_node.group_by:
            # Global agg on empty set
            empty_row = []
            for a in agg_node.aggregations:
                if a.func == "count":
                    empty_row.append(0)
                else:
                    empty_row.append(None)
            return col_names, [empty_row]

        for key, entry in state.items():
            row = list(key)
            row_count = entry["count"]

            for a in agg_node.aggregations:
                fn = a.func
                alias = a.alias
                if fn == "count":
                    row.append(row_count)
                elif fn == "sum":
                    row.append(entry["sums"].get(alias, 0.0))
                elif fn == "avg":
                    total = entry["sums"].get(alias, 0.0)
                    row.append(total / row_count if row_count > 0 else None)
                elif fn == "median":
                    vals = sorted(entry["values"].get(alias, []))
                    if not vals:
                        row.append(None)
                    else:
                        mid = len(vals) // 2
                        med = (vals[mid] + vals[~mid]) / 2 if len(vals) % 2 == 0 else vals[mid]
                        row.append(med)
                elif fn == "stddev":
                    import math
                    vals = entry["values"].get(alias, [])
                    if len(vals) < 2:
                        row.append(0.0)
                    else:
                        mean = sum(vals) / len(vals)
                        variance = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
                        row.append(math.sqrt(variance))
                elif fn == "min":
                    row.append(entry["mins"].get(alias, None))
                elif fn == "max":
                    row.append(entry["maxs"].get(alias, None))
                else:
                    row.append(None)

            rows.append(row)

        return col_names, rows
