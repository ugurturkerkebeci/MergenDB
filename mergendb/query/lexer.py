from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Any

class TokenType(Enum):
    # Pipeline & structure
    PIPE = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()

    # Keywords
    FROM = auto()
    WHERE = auto()
    SELECT = auto()
    COMPUTE = auto()
    AGGREGATE = auto()
    BY = auto()
    SORT = auto()
    LIMIT = auto()
    ASC = auto()
    DESC = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    AS = auto()
    CREATE = auto()
    TABLE = auto()
    INSERT = auto()
    INTO = auto()
    VALUES = auto()

    # Literals & Identifiers
    IDENTIFIER = auto()
    STRING_LITERAL = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    BOOL_LITERAL = auto()

    # Operators
    EQ = auto()      # == or =
    NEQ = auto()     # != or <>
    LT = auto()      # <
    LTE = auto()     # <=
    GT = auto()      # >
    GTE = auto()     # >=
    PLUS = auto()    # +
    MINUS = auto()   # -
    STAR = auto()    # *
    SLASH = auto()   # /
    PERCENT = auto() # %

    EOF = auto()

KEYWORDS = {
    "from": TokenType.FROM,
    "where": TokenType.WHERE,
    "select": TokenType.SELECT,
    "compute": TokenType.COMPUTE,
    "aggregate": TokenType.AGGREGATE,
    "by": TokenType.BY,
    "sort": TokenType.SORT,
    "limit": TokenType.LIMIT,
    "asc": TokenType.ASC,
    "desc": TokenType.DESC,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "as": TokenType.AS,
    "create": TokenType.CREATE,
    "table": TokenType.TABLE,
    "insert": TokenType.INSERT,
    "into": TokenType.INTO,
    "values": TokenType.VALUES,
    "true": TokenType.BOOL_LITERAL,
    "false": TokenType.BOOL_LITERAL,
}

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1

    def _peek(self) -> Optional[str]:
        if self.pos < len(self.text):
            return self.text[self.pos]
        return None

    def _advance(self) -> Optional[str]:
        ch = self._peek()
        if ch is not None:
            self.pos += 1
            if ch == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return ch

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < len(self.text):
            ch = self._peek()

            # Skip whitespace
            if ch in (' ', '\t', '\r', '\n'):
                self._advance()
                continue

            # Skip comments (# or --)
            if ch == '#' or (ch == '-' and self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '-'):
                while self._peek() is not None and self._peek() != '\n':
                    self._advance()
                continue

            start_line = self.line
            start_col = self.column

            # Pipe
            if ch == '|':
                self._advance()
                tokens.append(Token(TokenType.PIPE, '|', start_line, start_col))
            elif ch == '(':
                self._advance()
                tokens.append(Token(TokenType.LPAREN, '(', start_line, start_col))
            elif ch == ')':
                self._advance()
                tokens.append(Token(TokenType.RPAREN, ')', start_line, start_col))
            elif ch == ',':
                self._advance()
                tokens.append(Token(TokenType.COMMA, ',', start_line, start_col))
            elif ch == '+':
                self._advance()
                tokens.append(Token(TokenType.PLUS, '+', start_line, start_col))
            elif ch == '-':
                self._advance()
                tokens.append(Token(TokenType.MINUS, '-', start_line, start_col))
            elif ch == '*':
                self._advance()
                tokens.append(Token(TokenType.STAR, '*', start_line, start_col))
            elif ch == '/':
                self._advance()
                tokens.append(Token(TokenType.SLASH, '/', start_line, start_col))
            elif ch == '%':
                self._advance()
                tokens.append(Token(TokenType.PERCENT, '%', start_line, start_col))
            elif ch == '=':
                self._advance()
                if self._peek() == '=':
                    self._advance()
                    tokens.append(Token(TokenType.EQ, '==', start_line, start_col))
                else:
                    tokens.append(Token(TokenType.EQ, '=', start_line, start_col))
            elif ch == '!':
                self._advance()
                if self._peek() == '=':
                    self._advance()
                    tokens.append(Token(TokenType.NEQ, '!=', start_line, start_col))
                else:
                    raise SyntaxError(f"Unexpected character '!' at line {start_line}, col {start_col}")
            elif ch == '<':
                self._advance()
                if self._peek() == '=':
                    self._advance()
                    tokens.append(Token(TokenType.LTE, '<=', start_line, start_col))
                elif self._peek() == '>':
                    self._advance()
                    tokens.append(Token(TokenType.NEQ, '<>', start_line, start_col))
                else:
                    tokens.append(Token(TokenType.LT, '<', start_line, start_col))
            elif ch == '>':
                self._advance()
                if self._peek() == '=':
                    self._advance()
                    tokens.append(Token(TokenType.GTE, '>=', start_line, start_col))
                else:
                    tokens.append(Token(TokenType.GT, '>', start_line, start_col))
            elif ch in ('"', "'"):
                quote_char = self._advance()
                str_val = []
                while self._peek() is not None and self._peek() != quote_char:
                    if self._peek() == '\\':
                        self._advance()
                        escaped = self._advance()
                        if escaped == 'n': str_val.append('\n')
                        elif escaped == 'r': str_val.append('\r')
                        elif escaped in ('"', "'", '\\'): str_val.append(escaped)
                        else:
                            # Preserve backslash for file paths like C:\tables
                            str_val.append('\\')
                            if escaped is not None:
                                str_val.append(escaped)
                    else:
                        str_val.append(self._advance())
                if self._peek() == quote_char:
                    self._advance()
                tokens.append(Token(TokenType.STRING_LITERAL, "".join(str_val), start_line, start_col))
            elif ch.isdigit():
                num_str = []
                is_float = False
                while self._peek() is not None and (self._peek().isdigit() or self._peek() == '.'):
                    if self._peek() == '.':
                        if is_float:
                            break
                        is_float = True
                    num_str.append(self._advance())
                val_str = "".join(num_str)
                if is_float:
                    tokens.append(Token(TokenType.FLOAT_LITERAL, float(val_str), start_line, start_col))
                else:
                    tokens.append(Token(TokenType.INT_LITERAL, int(val_str), start_line, start_col))
            elif ch.isalpha() or ch == '_':
                ident = []
                while self._peek() is not None and (self._peek().isalnum() or self._peek() in ('_', '.')):
                    ident.append(self._advance())
                ident_str = "".join(ident)
                lower_str = ident_str.lower()
                if lower_str in KEYWORDS:
                    t_type = KEYWORDS[lower_str]
                    if t_type == TokenType.BOOL_LITERAL:
                        tokens.append(Token(t_type, lower_str == "true", start_line, start_col))
                    else:
                        tokens.append(Token(t_type, lower_str, start_line, start_col))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, ident_str, start_line, start_col))
            else:
                self._advance()
                raise SyntaxError(f"Unexpected token '{ch}' at line {start_line}, col {start_col}")

        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens
