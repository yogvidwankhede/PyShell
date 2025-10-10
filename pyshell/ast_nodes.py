"""
Defines the classes for the Abstract Syntax Tree (AST).

Each class represents a different type of command or structure in the shell language,
such as a simple command, a pipeline, or an if-statement.
"""

from typing import List, Optional, Tuple


class ASTNode:
    pass


class Script(ASTNode):
    def __init__(self, stmts: List[ASTNode]):
        self.stmts = stmts


class Sequence(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right


class AndOr(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op  # '&&' or '||'
        self.right = right


class Pipeline(ASTNode):
    def __init__(self, commands: List[ASTNode]):
        self.commands = commands


class Command(ASTNode):
    def __init__(self, words: List[str], redirects: List[Tuple[str, str]] = None, background: bool = False):
        self.words = words
        self.redirects = redirects or []
        self.background = background


class If(ASTNode):
    def __init__(self, cond: ASTNode, then_body: ASTNode, else_body: Optional[ASTNode]):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body


class While(ASTNode):
    def __init__(self, cond: ASTNode, body: ASTNode):
        self.cond = cond
        self.body = body


class Until(ASTNode):
    def __init__(self, cond: ASTNode, body: ASTNode):
        self.cond = cond
        self.body = body


class For(ASTNode):
    """Represents a for loop, like 'for var in item1 item2; do ...; done'."""

    def __init__(self, var: str, items: List[str], body: ASTNode):
        self.var = var
        self.items = items
        self.body = body


class Case(ASTNode):
    def __init__(self, expr: str, clauses: List[Tuple[List[str], ASTNode]]):
        self.expr = expr
        self.clauses = clauses  # list of (patterns, body)


class Block(ASTNode):
    def __init__(self, body: ASTNode):
        self.body = body


class Subshell(ASTNode):
    def __init__(self, body: ASTNode):
        self.body = body


class FunctionDef(ASTNode):
    def __init__(self, name: str, body: ASTNode):
        self.name = name
        self.body = body


class FunctionCall(ASTNode):
    def __init__(self, name: str, args: List[str]):
        self.name = name
        self.args = args


class Select(ASTNode):
    """Represents a select menu, like 'select var in item1 item2; do ...; done'."""

    def __init__(self, var: str, items: List[str], body: ASTNode):
        self.var = var
        self.items = items
        self.body = body


class ArrayAssignment(ASTNode):
    """Represents array assignment: arr=(val1 val2 val3) or arr+=(val4 val5)"""

    def __init__(self, name: str, values: List[str], is_append: bool = False):
        self.name = name
        self.values = values
        self.is_append = is_append


class TestCommand(ASTNode):
    """Represents [[ ... ]] test command with advanced features"""

    def __init__(self, expr: List[str]):
        self.expr = expr


class TryCatch(ASTNode):
    """Represents try-catch error handling (if implemented)"""

    def __init__(self, try_body: ASTNode, catch_body: Optional[ASTNode] = None):
        self.try_body = try_body
        self.catch_body = catch_body
