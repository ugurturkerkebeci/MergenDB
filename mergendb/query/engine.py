import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Union
from mergendb.storage.reader import FileReader, ScanStats, ColumnBatch
from mergendb.storage.lock import TableLockManager
from mergendb.core.schema import Schema
from mergendb.core.types import DataType
from mergendb.io.progress import ProgressBar
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

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, index):
        return self.rows[index]

    @property
    def first(self) -> Optional[List[Any]]:
        return self.rows[0] if self.rows else None

    def to_dicts(self) -> List[Dict[str, Any]]:
        """Converts query result rows into a list of Python dictionaries."""
        return [dict(zip(self.column_names, r)) for r in self.rows]

    def to_dict(self) -> Optional[Dict[str, Any]]:
        """Returns the first matching row as a dictionary, or None."""
        return dict(zip(self.column_names, self.rows[0])) if self.rows else None

    def to_list(self) -> List[List[Any]]:
        """Returns raw list of rows."""
        return self.rows

    def to_df(self):
        """Converts result into a pandas DataFrame (if pandas is installed)."""
        try:
            import pandas as pd
            return pd.DataFrame(self.rows, columns=self.column_names)
        except ImportError:
            raise ImportError("pandas is required for to_df(). Install with 'pip install pandas'.")

    def show(self, max_rows: int = 50):
        """Prints the result table directly to stdout."""
        print(self.display(max_rows=max_rows))

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
            if expr.name in cols:
                return cols[expr.name]
            bare = expr.name.split(".")[-1]
            if bare in cols:
                return cols[bare]
            for k in cols:
                if k.split(".")[-1] == bare:
                    return cols[k]
            raise KeyError(f"Column '{expr.name}' not found during evaluation.")

        elif isinstance(expr, BinaryOpNode):
            op = expr.op

            # Fast-path: ColumnRef OP Literal (most common query pattern)
            if isinstance(expr.left, ColumnRefNode) and isinstance(expr.right, LiteralNode):
                col_name = expr.left.name
                if col_name not in cols:
                    bare = col_name.split(".")[-1]
                    if bare in cols:
                        col_name = bare
                    else:
                        for k in cols:
                            if k.split(".")[-1] == bare:
                                col_name = k
                                break
                if col_name not in cols:
                    raise KeyError(f"Column '{col_name}' not found during evaluation.")
                r_val = expr.right.value

                # Fast pushdown directly on encoded/dictionary data (e.g. via LazyColumnDict)
                if hasattr(cols, "evaluate_predicate"):
                    fast_mask = cols.evaluate_predicate(col_name, op, r_val)
                    if fast_mask is not None:
                        return fast_mask

                left_vals = cols[col_name]

                # Robust type coercion: if column is string, coerce literal to string
                if left_vals and r_val is not None:
                    sample = next((v for v in left_vals if v is not None), None)
                    if isinstance(sample, str) and not isinstance(r_val, str):
                        r_val = str(r_val)
                    elif isinstance(sample, (int, float)) and isinstance(r_val, str):
                        try:
                            r_val = int(r_val) if isinstance(sample, int) else float(r_val)
                        except (ValueError, TypeError):
                            pass

                if op in ("==", "="):
                    return [l == r_val for l in left_vals]
                elif op in ("!=", "<>"):
                    return [l != r_val for l in left_vals]
                elif op == "<":
                    return [False if l is None or r_val is None else l < r_val for l in left_vals]
                elif op == "<=":
                    return [False if l is None or r_val is None else l <= r_val for l in left_vals]
                elif op == ">":
                    return [False if l is None or r_val is None else l > r_val for l in left_vals]
                elif op == ">=":
                    return [False if l is None or r_val is None else l >= r_val for l in left_vals]
                elif op == "LIKE":
                    pat = str(r_val) if r_val is not None else ""
                    if pat.startswith("%") and pat.endswith("%") and "%" not in pat[1:-1] and "_" not in pat:
                        sub = pat[1:-1].lower()
                        return [False if l is None else (sub in str(l).lower()) for l in left_vals]
                    elif pat.startswith("%") and not pat.endswith("%") and "%" not in pat[1:] and "_" not in pat:
                        sub = pat[1:].lower()
                        return [False if l is None else str(l).lower().endswith(sub) for l in left_vals]
                    elif not pat.startswith("%") and pat.endswith("%") and "%" not in pat[:-1] and "_" not in pat:
                        sub = pat[:-1].lower()
                        return [False if l is None else str(l).lower().startswith(sub) for l in left_vals]
                    else:
                        import re
                        regex = re.compile("^" + re.escape(pat).replace("%", ".*").replace("_", ".") + "$", re.IGNORECASE)
                        return [False if l is None else bool(regex.match(str(l))) for l in left_vals]

            elif isinstance(expr.left, LiteralNode) and isinstance(expr.right, ColumnRefNode):
                flipped_ops = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!=", "=": "="}
                flipped_op = flipped_ops.get(op, op)
                return cls.evaluate(BinaryOpNode(flipped_op, expr.right, expr.left), cols, row_count)

            if op == "AND":
                left_vals = cls.evaluate(expr.left, cols, row_count)
                if not any(left_vals):
                    return left_vals
                right_vals = cls.evaluate(expr.right, cols, row_count)
                return [bool(l and r) for l, r in zip(left_vals, right_vals)]

            if op == "OR":
                left_vals = cls.evaluate(expr.left, cols, row_count)
                if all(left_vals):
                    return left_vals
                right_vals = cls.evaluate(expr.right, cols, row_count)
                return [bool(l or r) for l, r in zip(left_vals, right_vals)]

            left_vals = cls.evaluate(expr.left, cols, row_count)
            right_vals = cls.evaluate(expr.right, cols, row_count)

            # Robust type coercion for generic paths
            if left_vals and right_vals:
                sl = next((v for v in left_vals if v is not None), None)
                sr = next((v for v in right_vals if v is not None), None)
                if isinstance(sl, str) and not isinstance(sr, str) and sr is not None:
                    right_vals = [str(r) if r is not None else None for r in right_vals]
                elif isinstance(sr, str) and not isinstance(sl, str) and sl is not None:
                    left_vals = [str(l) if l is not None else None for l in left_vals]

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
                return [l == r for l, r in zip(left_vals, right_vals)]
            elif op in ("!=", "<>"):
                return [l != r for l, r in zip(left_vals, right_vals)]
            elif op == "<":
                return [False if l is None or r is None else l < r for l, r in zip(left_vals, right_vals)]
            elif op == "<=":
                return [False if l is None or r is None else l <= r for l, r in zip(left_vals, right_vals)]
            elif op == ">":
                return [False if l is None or r is None else l > r for l, r in zip(left_vals, right_vals)]
            elif op == ">=":
                return [False if l is None or r is None else l >= r for l, r in zip(left_vals, right_vals)]
            elif op == "LIKE":
                import re
                for l, r in zip(left_vals, right_vals):
                    if l is None or r is None:
                        res.append(False)
                    else:
                        pattern = str(r)
                        regex_pattern = "^" + re.escape(pattern).replace("%", ".*").replace("_", ".") + "$"
                        res.append(bool(re.match(regex_pattern, str(l), re.IGNORECASE)))
                return res
            else:
                raise ValueError(f"Unsupported binary operator: {op}")

            return res

        raise TypeError(f"Unknown ExprNode: {type(expr)}")


class QueryEngine:
    """
    Executes MergenQL QueryPlans over compressed columnar storage with vector processing.
    """

    @classmethod
    def _coerce_expr_literals(cls, expr: Optional[ExprNode], schema: Schema):
        if expr is None:
            return
        if isinstance(expr, BinaryOpNode):
            if isinstance(expr.left, ColumnRefNode) and isinstance(expr.right, LiteralNode):
                if schema.has_column(expr.left.name):
                    dt = schema.get_column(expr.left.name).data_type
                    cls._coerce_val(expr.right, dt)
            elif isinstance(expr.right, ColumnRefNode) and isinstance(expr.left, LiteralNode):
                if schema.has_column(expr.right.name):
                    dt = schema.get_column(expr.right.name).data_type
                    cls._coerce_val(expr.left, dt)
            cls._coerce_expr_literals(expr.left, schema)
            cls._coerce_expr_literals(expr.right, schema)

    @classmethod
    def _coerce_val(cls, lit_node: LiteralNode, dt: DataType):
        if lit_node.value is None:
            return
        try:
            if dt == DataType.STRING and not isinstance(lit_node.value, str):
                lit_node.value = str(lit_node.value)
            elif dt in (DataType.INT32, DataType.INT64) and not isinstance(lit_node.value, int):
                lit_node.value = int(lit_node.value)
            elif dt in (DataType.FLOAT32, DataType.FLOAT64) and not isinstance(lit_node.value, float):
                lit_node.value = float(lit_node.value)
        except (ValueError, TypeError):
            pass

    @classmethod
    def execute(cls, plan: QueryPlan, show_progress: bool = False) -> QueryResult:
        start_time = time.perf_counter()

        # Open storage reader with concurrent read lock
        lock_ctx = TableLockManager.get_lock(plan.table_source).read()
        lock_ctx.__enter__()
        reader = None
        right_reader = None

        try:
            reader = FileReader(plan.table_source)
            # Pre-coerce literals to column schema types for zero-overhead evaluation
            cls._coerce_expr_literals(plan.where_expr, reader.schema)

            # Step 1: Optimize plan (Pushdowns & Column Pruning)
            pushdown_preds = QueryPlanner.extract_pushdown_predicates(plan.where_expr)
            needed_columns = QueryPlanner.collect_required_columns(plan)
            filter_cols = QueryPlanner.collect_filter_columns(plan.where_expr)

            # Prepare Hash JOIN if plan.join is specified
            right_cols: List[str] = []
            right_tbl = ""
            left_tbl = os.path.splitext(os.path.basename(plan.table_source))[0]
            l_key = ""
            r_key = ""
            right_hash: Dict[Any, List[Dict[str, Any]]] = {}

            if plan.join:
                right_path = plan.join.right_table
                if not os.path.exists(right_path):
                    if os.path.exists(right_path + ".mgdb"):
                        right_path = right_path + ".mgdb"
                    else:
                        left_dir = os.path.dirname(plan.table_source)
                        candidate = os.path.join(left_dir, plan.join.right_table)
                        if os.path.exists(candidate):
                            right_path = candidate
                        elif os.path.exists(candidate + ".mgdb"):
                            right_path = candidate + ".mgdb"

                if not os.path.exists(right_path):
                    raise FileNotFoundError(f"Right table '{plan.join.right_table}' not found for JOIN.")

                right_reader = FileReader(right_path)
                right_tbl = os.path.splitext(os.path.basename(right_path))[0]
                right_cols = right_reader.schema.column_names()

                l_key = plan.join.left_key.split(".")[-1]
                r_key = plan.join.right_key.split(".")[-1]

                # Auto-swap keys if user inverted them in ON clause
                if not reader.schema.has_column(l_key) and right_reader.schema.has_column(l_key) and reader.schema.has_column(r_key):
                    l_key, r_key = r_key, l_key

                # Read right table into hash table
                for r_batch, r_stats in right_reader.scan():
                    r_cols_dict = r_batch.columns
                    for r_idx in range(r_batch.row_count):
                        k_val = r_cols_dict[r_key][r_idx]
                        if k_val is not None:
                            r_row_dict = {c: r_cols_dict[c][r_idx] for c in right_cols}
                            if k_val not in right_hash:
                                right_hash[k_val] = []
                            right_hash[k_val].append(r_row_dict)

                # Restrict pushdown and late materialization to safe left columns
                pushdown_preds = [p for p in pushdown_preds if reader.schema.has_column(p[0])]
                filter_cols = [c for c in filter_cols if reader.schema.has_column(c)]

            def get_matches(k_val):
                if k_val in right_hash:
                    return right_hash[k_val]
                if isinstance(k_val, str):
                    try:
                        iv = int(k_val)
                        if iv in right_hash:
                            return right_hash[iv]
                    except ValueError:
                        pass
                elif isinstance(k_val, int):
                    sv = str(k_val)
                    if sv in right_hash:
                        return right_hash[sv]
                return None

            filter_fn = None
            late_mat_enabled = False
            if filter_cols and plan.where_expr is not None and not plan.join:
                def filter_evaluator(cdata):
                    row_cnt = getattr(cdata, "row_count", None) or len(next(iter(cdata.values())))
                    return ExpressionEvaluator.evaluate(plan.where_expr, cdata, row_cnt)
                filter_fn = filter_evaluator
                late_mat_enabled = True

            total_blocks = len(reader.blocks)
            blocks_scanned = 0
            blocks_skipped = 0
            bytes_read = 0
            rows_scanned = 0

            pbar = None
            if show_progress and reader.total_rows > 0:
                tbl_label = os.path.basename(plan.table_source)
                pbar = ProgressBar(f"Querying '{tbl_label}'", total_rows=reader.total_rows)

            collected_rows: List[List[Any]] = []

            # Step 2: Stream blocks
            is_aggregate = plan.aggregate is not None
            agg_state: Dict[Tuple, Dict[str, Any]] = {}

            # Columns needed for scanning the left reader
            if plan.select_columns is not None or plan.join is not None:
                scan_reader_cols = [c.split(".")[-1] for c in needed_columns if reader.schema.has_column(c.split(".")[-1])]
                if plan.join and l_key not in scan_reader_cols:
                    scan_reader_cols.append(l_key)
                if not scan_reader_cols:
                    scan_reader_cols = None
            else:
                scan_reader_cols = None

            # Determine projected scan columns
            needed_extra_sort = False
            if not is_aggregate and plan.select_columns is not None:
                scan_cols = list(plan.select_columns)
                if plan.sort is not None and plan.sort.column not in scan_cols:
                    scan_cols.append(plan.sort.column)
                    needed_extra_sort = True
            else:
                scan_cols = None

            for batch, scan_stats in reader.scan(
                columns=scan_reader_cols,
                predicates=pushdown_preds,
                filter_columns=filter_cols if late_mat_enabled else None,
                filter_fn=filter_fn if late_mat_enabled else None
            ):
                blocks_scanned = scan_stats.blocks_scanned
                blocks_skipped = scan_stats.blocks_skipped
                bytes_read = scan_stats.bytes_read
                rows_scanned = scan_stats.rows_scanned
                if pbar:
                    pbar.update(rows_scanned)

                current_cols = dict(batch.columns)
                count = batch.row_count

                # If late materialization was applied, batch is ALREADY filtered!
                if plan.where_expr is not None and not late_mat_enabled and not plan.join:
                    mask = ExpressionEvaluator.evaluate(plan.where_expr, current_cols, count)
                    for k in current_cols:
                        current_cols[k] = [v for v, m in zip(current_cols[k], mask) if m]
                    count = mask.count(True) if hasattr(mask, "count") else sum(1 for m in mask if m)

                if count == 0:
                    continue

                # Hash Join Execution
                if plan.join:
                    joined_cols: Dict[str, List[Any]] = {}
                    for c in current_cols:
                        joined_cols[c] = []
                        joined_cols[f"{left_tbl}.{c}"] = []
                    for c in right_cols:
                        joined_cols[f"{right_tbl}.{c}"] = []
                        if c not in current_cols:
                            joined_cols[c] = []

                    matched_count = 0
                    for i in range(count):
                        l_val = current_cols[l_key][i]
                        matches = get_matches(l_val)
                        if matches:
                            for r_row in matches:
                                matched_count += 1
                                for c in current_cols:
                                    val = current_cols[c][i]
                                    joined_cols[c].append(val)
                                    joined_cols[f"{left_tbl}.{c}"].append(val)
                                for c in right_cols:
                                    r_val = r_row[c]
                                    joined_cols[f"{right_tbl}.{c}"].append(r_val)
                                    if c not in current_cols:
                                        joined_cols[c].append(r_val)
                        elif plan.join.join_type == "LEFT":
                            matched_count += 1
                            for c in current_cols:
                                val = current_cols[c][i]
                                joined_cols[c].append(val)
                                joined_cols[f"{left_tbl}.{c}"].append(val)
                            for c in right_cols:
                                joined_cols[f"{right_tbl}.{c}"].append(None)
                                if c not in current_cols:
                                    joined_cols[c].append(None)

                    current_cols = joined_cols
                    count = matched_count

                    if count == 0:
                        continue

                    # Filter with WHERE after join
                    if plan.where_expr is not None:
                        mask = ExpressionEvaluator.evaluate(plan.where_expr, current_cols, count)
                        for k in current_cols:
                            current_cols[k] = [v for v, m in zip(current_cols[k], mask) if m]
                        count = mask.count(True) if hasattr(mask, "count") else sum(1 for m in mask if m)

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
                    if scan_cols is not None:
                        proj_cols = scan_cols
                    else:
                        if plan.join:
                            proj_cols = []
                            for c in reader.schema.column_names():
                                proj_cols.append(c)
                            for c in right_cols:
                                if c not in reader.schema.column_names():
                                    proj_cols.append(c)
                                else:
                                    proj_cols.append(f"{right_tbl}.{c}")
                        else:
                            proj_cols = list(current_cols.keys())

                    for i in range(count):
                        row = [cls._get_col_value(current_cols, c, i) for c in proj_cols]
                        collected_rows.append(row)

                    # Early exit on LIMIT if no sort and no aggregate!
                    if plan.sort is None and plan.limit is not None and len(collected_rows) >= plan.limit:
                        collected_rows = collected_rows[:plan.limit]
                        if pbar:
                            pbar.finish(f"Matched {len(collected_rows)} rows (early exit on LIMIT)")
                            pbar = None
                        break

            if pbar:
                pbar.finish()

            if getattr(reader, "last_scan_stats", None) is not None:
                blocks_scanned = reader.last_scan_stats.blocks_scanned
                blocks_skipped = reader.last_scan_stats.blocks_skipped
                bytes_read = reader.last_scan_stats.bytes_read
                rows_scanned = reader.last_scan_stats.rows_scanned

            # Post-Scan Processing
            final_columns: List[str] = []

            if is_aggregate:
                final_columns, collected_rows = cls._finalize_aggregate(plan.aggregate, agg_state)
            else:
                if plan.select_columns is not None:
                    final_columns = plan.select_columns
                else:
                    if plan.join:
                        final_columns = []
                        for c in reader.schema.column_names():
                            final_columns.append(c)
                        for c in right_cols:
                            if c not in reader.schema.column_names():
                                final_columns.append(c)
                            else:
                                final_columns.append(f"{right_tbl}.{c}")
                    else:
                        final_columns = reader.schema.column_names() + [c.target_column for c in plan.computes]

            # Sorting
            if plan.sort is not None:
                sort_col = plan.sort.column
                sort_target_cols = scan_cols if scan_cols is not None else final_columns
                col_idx = None
                if sort_col in sort_target_cols:
                    col_idx = sort_target_cols.index(sort_col)
                else:
                    bare = sort_col.split(".")[-1]
                    for idx, sc in enumerate(sort_target_cols):
                        if sc == bare or sc.split(".")[-1] == bare:
                            col_idx = idx
                            break
                if col_idx is not None:
                    def sort_key(row):
                        v = row[col_idx]
                        return (1 if v is None else 0, v)
                    collected_rows.sort(key=sort_key, reverse=plan.sort.descending)

            # Strip extra sort column if it was appended
            if needed_extra_sort:
                target_len = len(final_columns)
                collected_rows = [r[:target_len] for r in collected_rows]

            # Limit
            if plan.limit is not None and plan.limit >= 0:
                collected_rows = collected_rows[:plan.limit]

        finally:
            if reader is not None:
                reader.close()
            if right_reader is not None:
                right_reader.close()
            lock_ctx.__exit__(None, None, None)

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
    def _get_col_value(cls, cols: Dict[str, List[Any]], col_name: str, idx: int) -> Any:
        if col_name in cols:
            return cols[col_name][idx]
        bare = col_name.split(".")[-1]
        if bare in cols:
            return cols[bare][idx]
        for k in cols:
            if k.split(".")[-1] == bare:
                return cols[k][idx]
        raise KeyError(f"Column '{col_name}' not found.")

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
                key = tuple(cls._get_col_value(cols, g, i) for g in group_cols)
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
                val = cls._get_col_value(cols, func_node.column, i) if func_node.column and func_node.column != "*" else None

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

        if agg_node.having_expr is not None and rows:
            agg_cols = {col: [r[i] for r in rows] for i, col in enumerate(col_names)}
            mask = ExpressionEvaluator.evaluate(agg_node.having_expr, agg_cols, len(rows))
            rows = [r for r, m in zip(rows, mask) if m]

        return col_names, rows
