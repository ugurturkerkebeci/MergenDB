from mergendb.query.lexer import Lexer, Token, TokenType
from mergendb.query.parser import Parser
from mergendb.query.ast_nodes import QueryPlan, CreateTableNode, InsertNode
from mergendb.query.planner import QueryPlanner
from mergendb.query.engine import QueryEngine, QueryResult, ExecutionStats

def parse_query(sql_text: str):
    tokens = Lexer(sql_text).tokenize()
    return Parser(tokens).parse()

def execute_query(sql_text: str) -> QueryResult:
    plan = parse_query(sql_text)
    if not isinstance(plan, QueryPlan):
        raise ValueError(f"Expected QueryPlan, got {type(plan).__name__}")
    return QueryEngine.execute(plan)

__all__ = [
    "Lexer",
    "Token",
    "TokenType",
    "Parser",
    "QueryPlan",
    "CreateTableNode",
    "InsertNode",
    "QueryPlanner",
    "QueryEngine",
    "QueryResult",
    "ExecutionStats",
    "parse_query",
    "execute_query",
]
