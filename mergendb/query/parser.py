from typing import List, Optional, Any, Union
from mergendb.query.lexer import Lexer, Token, TokenType
from mergendb.core.schema import ColumnDef
from mergendb.core.types import DataType
from mergendb.query.ast_nodes import (
    ASTNode, ExprNode, LiteralNode, ColumnRefNode, BinaryOpNode,
    ComputeNode, AggFuncNode, AggregateNode, SortNode, QueryPlan,
    CreateTableNode, InsertNode, JoinNode
)

TYPE_MAP = {
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

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek_next(self) -> Optional[Token]:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None

    def _match(self, *types: TokenType) -> bool:
        if self._current().type in types:
            self.pos += 1
            return True
        return False

    def _expect(self, token_type: TokenType, err_msg: str = "") -> Token:
        t = self._current()
        if t.type != token_type:
            raise SyntaxError(f"Line {t.line}:{t.column} - Expected {token_type.name}, got {t.type.name}. {err_msg}")
        self.pos += 1
        return t

    def parse(self) -> ASTNode:
        curr = self._current()
        if curr.type == TokenType.FROM:
            return self._parse_query_plan()
        elif curr.type == TokenType.CREATE:
            return self._parse_create_table()
        elif curr.type == TokenType.INSERT:
            return self._parse_insert()
        else:
            raise SyntaxError(f"Unexpected starting token: {curr.type.name} at line {curr.line}")

    def _parse_query_plan(self) -> QueryPlan:
        self._expect(TokenType.FROM)
        source_tok = self._current()
        if source_tok.type not in (TokenType.STRING_LITERAL, TokenType.IDENTIFIER):
            raise SyntaxError(f"Expected table name or path after FROM, got {source_tok.type.name}")
        self.pos += 1
        table_source = source_tok.value

        plan = QueryPlan(table_source=table_source)

        # Parse pipe stages
        while self._match(TokenType.PIPE):
            stage_tok = self._current()

            if self._current().type in (TokenType.JOIN, TokenType.INNER, TokenType.LEFT):
                join_type = "INNER"
                if self._match(TokenType.INNER):
                    self._expect(TokenType.JOIN)
                elif self._match(TokenType.LEFT):
                    self._expect(TokenType.JOIN)
                    join_type = "LEFT"
                else:
                    self._expect(TokenType.JOIN)

                target_tok = self._current()
                if target_tok.type not in (TokenType.IDENTIFIER, TokenType.STRING_LITERAL):
                    raise SyntaxError(f"Expected table name after JOIN, got {target_tok.type.name}")
                self.pos += 1
                right_table = target_tok.value

                self._expect(TokenType.ON, "Expected ON clause in JOIN")
                left_key = self._expect(TokenType.IDENTIFIER, "Expected left key column name").value
                self._expect(TokenType.EQ, "Expected '=' in JOIN condition")
                right_key = self._expect(TokenType.IDENTIFIER, "Expected right key column name").value

                plan.join = JoinNode(right_table=right_table, left_key=left_key, right_key=right_key, join_type=join_type)
            elif self._match(TokenType.WHERE):
                expr = self._parse_expression()
                plan.where_expr = expr
            elif self._match(TokenType.COMPUTE):
                target_col = self._expect(TokenType.IDENTIFIER).value
                self._expect(TokenType.EQ, "Expected '=' in COMPUTE clause")
                expr = self._parse_expression()
                plan.computes.append(ComputeNode(target_column=target_col, expr=expr))
            elif self._match(TokenType.SELECT):
                cols = []
                while True:
                    c = self._expect(TokenType.IDENTIFIER).value
                    cols.append(c)
                    if not self._match(TokenType.COMMA):
                        break
                plan.select_columns = cols
            elif self._match(TokenType.AGGREGATE):
                plan.aggregate = self._parse_aggregate()
            elif self._match(TokenType.HAVING):
                if not plan.aggregate:
                    raise SyntaxError("HAVING clause requires a preceding AGGREGATE stage.")
                plan.aggregate.having_expr = self._parse_expression()
            elif self._match(TokenType.SORT):
                col = self._expect(TokenType.IDENTIFIER).value
                desc = False
                if self._match(TokenType.DESC):
                    desc = True
                elif self._match(TokenType.ASC):
                    desc = False
                plan.sort = SortNode(column=col, descending=desc)
            elif self._match(TokenType.LIMIT):
                lim = self._expect(TokenType.INT_LITERAL).value
                plan.limit = int(lim)
            else:
                raise SyntaxError(f"Unknown pipeline stage: {stage_tok.value} at line {stage_tok.line}")

        return plan

    def _parse_aggregate(self) -> AggregateNode:
        aggs: List[AggFuncNode] = []
        while True:
            func_tok = self._expect(TokenType.IDENTIFIER, "Expected aggregate function name (count, sum, avg, min, max)")
            func_name = func_tok.value.lower()
            self._expect(TokenType.LPAREN)
            col_name = None
            if self._current().type == TokenType.IDENTIFIER:
                col_name = self._expect(TokenType.IDENTIFIER).value
            elif self._current().type == TokenType.STAR:
                self.pos += 1
                col_name = "*"
            self._expect(TokenType.RPAREN)

            alias = f"{func_name}_{col_name}" if col_name and col_name != "*" else func_name
            if self._match(TokenType.AS):
                alias = self._expect(TokenType.IDENTIFIER).value

            aggs.append(AggFuncNode(func=func_name, column=col_name, alias=alias))
            if not self._match(TokenType.COMMA):
                break

        group_by: List[str] = []
        if self._match(TokenType.GROUP):
            self._expect(TokenType.BY)
            while True:
                g_col = self._expect(TokenType.IDENTIFIER).value
                group_by.append(g_col)
                if not self._match(TokenType.COMMA):
                    break
        elif self._match(TokenType.BY):
            while True:
                g_col = self._expect(TokenType.IDENTIFIER).value
                group_by.append(g_col)
                if not self._match(TokenType.COMMA):
                    break

        having_expr = None
        if self._match(TokenType.HAVING):
            having_expr = self._parse_expression()

        return AggregateNode(aggregations=aggs, group_by=group_by, having_expr=having_expr)

    def _parse_create_table(self) -> CreateTableNode:
        self._expect(TokenType.CREATE)
        self._expect(TokenType.TABLE)
        target = self._current()
        if target.type not in (TokenType.IDENTIFIER, TokenType.STRING_LITERAL):
            raise SyntaxError(f"Expected table name, got {target.type.name}")
        self.pos += 1
        table_path = target.value

        self._expect(TokenType.LPAREN)
        columns: List[ColumnDef] = []
        while True:
            col_name = self._expect(TokenType.IDENTIFIER).value
            type_name = self._expect(TokenType.IDENTIFIER).value.lower()
            if type_name not in TYPE_MAP:
                raise ValueError(f"Unknown data type '{type_name}' in CREATE TABLE")
            columns.append(ColumnDef(name=col_name, data_type=TYPE_MAP[type_name]))
            if not self._match(TokenType.COMMA):
                break
        self._expect(TokenType.RPAREN)
        return CreateTableNode(table_path=table_path, columns=columns)

    def _parse_insert(self) -> InsertNode:
        self._expect(TokenType.INSERT)
        self._expect(TokenType.INTO)
        target = self._current()
        if target.type not in (TokenType.IDENTIFIER, TokenType.STRING_LITERAL):
            raise SyntaxError(f"Expected table name, got {target.type.name}")
        self.pos += 1
        table_path = target.value

        self._expect(TokenType.VALUES)
        rows: List[List[Any]] = []
        while True:
            self._expect(TokenType.LPAREN)
            row_vals = []
            while True:
                curr = self._current()
                if curr.type in (TokenType.INT_LITERAL, TokenType.FLOAT_LITERAL, TokenType.STRING_LITERAL, TokenType.BOOL_LITERAL):
                    self.pos += 1
                    row_vals.append(curr.value)
                else:
                    raise SyntaxError(f"Expected literal value, got {curr.type.name}")
                if not self._match(TokenType.COMMA):
                    break
            self._expect(TokenType.RPAREN)
            rows.append(row_vals)
            if not self._match(TokenType.COMMA):
                break

        return InsertNode(table_path=table_path, rows=rows)

    # ---------------- Expression Parsing (Operator Precedence) ----------------
    def _parse_expression(self) -> ExprNode:
        return self._parse_or()

    def _parse_or(self) -> ExprNode:
        expr = self._parse_and()
        while self._match(TokenType.OR):
            right = self._parse_and()
            expr = BinaryOpNode(op="OR", left=expr, right=right)
        return expr

    def _parse_and(self) -> ExprNode:
        expr = self._parse_comparison()
        while self._match(TokenType.AND):
            right = self._parse_comparison()
            expr = BinaryOpNode(op="AND", left=expr, right=right)
        return expr

    def _parse_comparison(self) -> ExprNode:
        expr = self._parse_additive()
        curr = self._current()
        if curr.type in (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE, TokenType.LIKE):
            self.pos += 1
            right = self._parse_additive()
            op = "LIKE" if curr.type == TokenType.LIKE else curr.value
            return BinaryOpNode(op=op, left=expr, right=right)
        return expr

    def _parse_additive(self) -> ExprNode:
        expr = self._parse_multiplicative()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._current()
            self.pos += 1
            right = self._parse_multiplicative()
            expr = BinaryOpNode(op=op_tok.value, left=expr, right=right)
        return expr

    def _parse_multiplicative(self) -> ExprNode:
        expr = self._parse_primary()
        while self._current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._current()
            self.pos += 1
            right = self._parse_primary()
            expr = BinaryOpNode(op=op_tok.value, left=expr, right=right)
        return expr

    def _parse_primary(self) -> ExprNode:
        curr = self._current()
        if curr.type in (TokenType.INT_LITERAL, TokenType.FLOAT_LITERAL, TokenType.STRING_LITERAL, TokenType.BOOL_LITERAL):
            self.pos += 1
            return LiteralNode(value=curr.value)
        elif curr.type == TokenType.IDENTIFIER:
            self.pos += 1
            return ColumnRefNode(name=curr.value)
        elif self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr
        else:
            raise SyntaxError(f"Unexpected token in expression: {curr.value} ({curr.type.name}) at line {curr.line}")
