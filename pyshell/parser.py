import sys
from typing import List, Optional, Tuple
from .tokenizer import Token
from .ast_nodes import (
    ASTNode, Script, Sequence, AndOr, Pipeline, Command, If, While, Until,
    For, Select, Case, Block, Subshell, FunctionDef, FunctionCall,
    TestCommand, ArrayAssignment, TryCatch
)
from . import tokenizer as tok_module


def parse(tokens: List[Token]) -> Script:
    """Convenience wrapper for the Parser class."""
    return Parser(tokens).parse_toplevel_script()


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.heredocs = []

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            self.pos += 1
            return self.tokens[self.pos - 1]
        return None

    def accept(self, typ: str, val: Optional[str] = None) -> Optional[Token]:
        t = self.peek()
        if t and t[0] == typ and (val is None or t[1] == val):
            return self.next()
        return None

    def expect(self, typ: str, val: Optional[str] = None) -> Token:
        t = self.accept(typ, val)
        if t:
            return t
        raise SyntaxError(
            f"Expected {typ} with value {val}, but got {self.peek()}")

    def parse_toplevel_script(self) -> Script:
        """Parses a complete script until the end of the tokens."""
        stmts = []
        while self.peek():
            stmt = self.parse_and_or()
            if not stmt:
                break
            stmts.append(stmt)
            self.accept('OP', ';')
        return Script(stmts)

    def _parse_statements_until(self, terminators: List[str]) -> Script:
        """Helper to parse a block of statements until a terminating keyword is found."""
        stmts = []
        while self.peek() and not (self.peek()[0] == 'KEYWORD' and self.peek()[1] in terminators):
            stmt = self.parse_and_or()
            if not stmt:
                break
            stmts.append(stmt)
            self.accept('OP', ';')
        return Script(stmts)

    def parse_and_or(self) -> Optional[ASTNode]:
        node = self.parse_pipeline()
        while t := self.accept('OP', '&&') or self.accept('OP', '||'):
            right = self.parse_pipeline()
            if not right:
                raise SyntaxError(f"Expected command after '{t[1]}'")
            node = AndOr(node, t[1], right)
        return node

    def parse_pipeline(self) -> Optional[ASTNode]:
        commands = [self.parse_command_or_compound()]
        if not commands[0]:
            return None
        while self.accept('OP', '|'):
            cmd = self.parse_command_or_compound()
            if not cmd:
                raise SyntaxError("Expected command after '|'")
            commands.append(cmd)
        return Pipeline(commands) if len(commands) > 1 else commands[0]

    def parse_command_or_compound(self) -> Optional[ASTNode]:
        t = self.peek()
        if not t:
            return None

        # Check for [[ test command
        if t[0] == 'KEYWORD' and t[1] == '[[':
            return self.parse_test_command()

        if t[0] == 'KEYWORD':
            if t[1] == 'if':
                return self.parse_if()
            if t[1] == 'while':
                return self.parse_while()
            if t[1] == 'until':
                return self.parse_until()
            if t[1] == 'for':
                return self.parse_for()
            if t[1] == 'select':
                return self.parse_select()
            if t[1] == 'case':
                return self.parse_case()
            if t[1] == 'function':
                return self.parse_function_keyword_style()

        if t[0] == 'OP' and t[1] == '(':
            return self.parse_subshell()

        if t[0] == 'OP' and t[1] == '{':
            return self.parse_block()

        # Check for builtin commands that might have array assignments
        # These should NOT be parsed as separate ArrayAssignment nodes
        if t[0] == 'WORD' and t[1] in ('local', 'declare', 'typeset', 'readonly', 'export'):
            # These builtins can have array assignments as arguments
            # Parse them as regular commands, not as separate array assignments
            return self.parse_command()

        # Check for array assignment: name=(...)
        array_assign = self.try_parse_array_assignment()
        if array_assign:
            return array_assign

        # Check for function definition: name() { ... }
        if t[0] == 'WORD' and self.pos + 2 < len(self.tokens):
            t1 = self.tokens[self.pos + 1]
            t2 = self.tokens[self.pos + 2]
            if t1 == ('OP', '(') and t2 == ('OP', ')'):
                return self.parse_function_def()

        return self.parse_command()

    def try_parse_array_assignment(self) -> Optional[ArrayAssignment]:
        """Try to parse array assignment: arr=(val1 val2 val3) or arr+=(val4 val5)"""
        if not (self.peek() and self.peek()[0] == 'WORD'):
            return None

        # Check if there was a builtin command just before this position
        # If so, don't parse as array assignment - let parse_command handle it
        if self.pos > 0:
            prev_token = self.tokens[self.pos - 1]
            if prev_token[0] == 'WORD' and prev_token[1] in ('local', 'declare', 'typeset', 'readonly', 'export'):
                return None

        # Save position in case we need to backtrack
        saved_pos = self.pos
        word = self.peek()[1]

        # Pattern: "arr=" followed by "("
        # OR "arr+=" followed by "("
        if word.endswith('=') or word.endswith('+='):
            # Check if next token is opening paren
            if self.pos + 1 >= len(self.tokens) or self.tokens[self.pos + 1] != ('OP', '('):
                self.pos = saved_pos
                return None

            # Extract variable name
            if word.endswith('+='):
                var_name = word[:-2]  # Remove +=
                is_append = True
            else:
                var_name = word[:-1]  # Remove =
                is_append = False

            # Check for empty array: arr=()
            if self.pos + 2 < len(self.tokens) and self.tokens[self.pos + 2] == ('OP', ')'):
                # Check if this might be a function definition
                # Functions would have: name() { or name() \n {
                if self.pos + 3 < len(self.tokens) and self.tokens[self.pos + 3] == ('OP', '{'):
                    # This is a function definition, not an array
                    self.pos = saved_pos
                    return None

                # Empty array
                self.pos += 3  # Skip "arr=", "(", ")"
                return ArrayAssignment(var_name, [], is_append)

            # Skip "arr=" and "("
            self.pos += 2

            # Collect values until ")" - PRESERVE QUOTED STRINGS
            values = []
            while self.peek() and self.peek() != ('OP', ')'):
                if self.peek()[0] in ('WORD', 'KEYWORD'):
                    val = self.next()[1]
                    # Keep the value as-is with quotes preserved
                    values.append(val)
                else:
                    self.next()  # Skip non-word tokens

            # Consume closing ")"
            if self.peek() == ('OP', ')'):
                self.next()
                return ArrayAssignment(var_name, values, is_append)
            else:
                # Malformed - restore position
                self.pos = saved_pos
                return None

        # Not an array assignment
        self.pos = saved_pos
        return None

    def parse_test_command(self) -> TestCommand:
        """Parse [[ ... ]] test command"""
        self.expect('KEYWORD', '[[')

        # Collect all tokens until ]]
        expr_tokens = []
        while self.peek() and not (self.peek()[0] == 'KEYWORD' and self.peek()[1] == ']]'):
            expr_tokens.append(self.next()[1])

        self.expect('KEYWORD', ']]')

        return TestCommand(expr_tokens)

    def parse_subshell(self) -> Subshell:
        self.expect('OP', '(')
        start_pos = self.pos
        depth = 1
        while depth > 0:
            if not self.peek():
                raise SyntaxError("Unexpected EOF in subshell")
            t = self.next()
            if t[1] == '(':
                depth += 1
            if t[1] == ')':
                depth -= 1

        inner_tokens = self.tokens[start_pos: self.pos - 1]
        inner_ast = Parser(inner_tokens).parse_toplevel_script()
        return Subshell(inner_ast)

    def parse_block(self) -> Block:
        """Parse { ... } block."""
        self.expect('OP', '{')
        start_pos = self.pos
        depth = 1
        while depth > 0:
            if not self.peek():
                raise SyntaxError("Unexpected EOF in block")
            t = self.next()
            if t[1] == '{':
                depth += 1
            if t[1] == '}':
                depth -= 1

        body_tokens = self.tokens[start_pos: self.pos - 1]
        body = Parser(body_tokens).parse_toplevel_script()
        return Block(body)

    def parse_function_def(self) -> FunctionDef:
        name_token = self.expect('WORD')
        self.expect('OP', '(')
        self.expect('OP', ')')

        body = self.parse_command_or_compound()
        if not body:
            raise SyntaxError("Expected function body")

        return FunctionDef(name_token[1], body)

    def parse_function_keyword_style(self) -> FunctionDef:
        """Parse function name() { ... } or function name { ... } style."""
        self.expect('KEYWORD', 'function')
        name_token = self.expect('WORD')

        # Optional parentheses
        if self.peek() and self.peek()[0] == 'OP' and self.peek()[1] == '(':
            self.expect('OP', '(')
            self.expect('OP', ')')

        body = self.parse_command_or_compound()
        if not body:
            raise SyntaxError("Expected function body")

        return FunctionDef(name_token[1], body)

    def parse_command(self) -> Optional[Command]:
        words, redirects = [], []
        no_arg_redirs = {'2>&1'}

        # Check if this is a builtin that might have array assignments
        first_word = self.peek()
        is_builtin_with_arrays = (first_word and first_word[0] == 'WORD' and
                                  first_word[1] in ('local', 'declare', 'typeset', 'readonly', 'export'))

        while t := self.peek():
            if t[0] in ('WORD', 'KEYWORD'):
                words.append(self.next()[1])
            elif t[0] == 'OP' and t[1] == '(' and is_builtin_with_arrays and len(words) > 1:
                # This is likely part of an array assignment for a builtin command
                # Collect the entire array: (a b c)
                # Append ( to the previous word (which should be arr=)
                words[-1] = words[-1] + '('
                self.next()  # Skip the (

                # Collect array elements
                array_elements = []
                while self.peek() and self.peek() != ('OP', ')'):
                    if self.peek()[0] in ('WORD', 'KEYWORD'):
                        array_elements.append(self.next()[1])
                    else:
                        self.next()  # Skip unexpected tokens

                # Add elements to the last word
                if array_elements:
                    words[-1] = words[-1] + ' '.join(array_elements) + ')'
                else:
                    words[-1] = words[-1] + ')'

                # Consume the closing )
                if self.peek() == ('OP', ')'):
                    self.next()
            elif t[0] == 'REDIR':
                op = self.next()[1]
                if op in no_arg_redirs:
                    redirects.append((op, None))
                elif op == '<<':
                    delimiter = self.expect('WORD')[1]
                    # Here-document: treat as here-string for simplicity
                    # In a full implementation, this would read multi-line input
                    content = ""  # Placeholder
                    redirects.append(('<<<', content))
                else:
                    target = self.expect('WORD')
                    redirects.append((op, target[1]))
            else:
                break

        background = self.accept('OP', '&') is not None
        return Command(words, redirects, background) if words or redirects else None

    def parse_if(self) -> If:
        self.expect('KEYWORD', 'if')
        cond = self._parse_statements_until(['then'])
        self.expect('KEYWORD', 'then')
        then_body = self._parse_statements_until(['elif', 'else', 'fi'])

        elif_chain = None
        while self.peek() and self.peek()[0] == 'KEYWORD' and self.peek()[1] == 'elif':
            self.expect('KEYWORD', 'elif')
            elif_cond = self._parse_statements_until(['then'])
            self.expect('KEYWORD', 'then')
            elif_body = self._parse_statements_until(['elif', 'else', 'fi'])

            elif_node = If(elif_cond, elif_body, None)
            if elif_chain is None:
                elif_chain = elif_node
            else:
                current = elif_chain
                while current.else_body and isinstance(current.else_body, If):
                    current = current.else_body
                current.else_body = elif_node

        else_body = None
        if self.accept('KEYWORD', 'else'):
            else_body = self._parse_statements_until(['fi'])

        self.expect('KEYWORD', 'fi')

        if elif_chain:
            current = elif_chain
            while current.else_body and isinstance(current.else_body, If):
                current = current.else_body
            current.else_body = else_body
            return If(cond, then_body, elif_chain)
        else:
            return If(cond, then_body, else_body)

    def parse_while(self) -> While:
        self.expect('KEYWORD', 'while')
        cond = self._parse_statements_until(['do'])
        self.expect('KEYWORD', 'do')
        body = self._parse_statements_until(['done'])
        self.expect('KEYWORD', 'done')
        return While(cond, body)

    def parse_until(self) -> Until:
        self.expect('KEYWORD', 'until')
        cond = self._parse_statements_until(['do'])
        self.expect('KEYWORD', 'do')
        body = self._parse_statements_until(['done'])
        self.expect('KEYWORD', 'done')
        return Until(cond, body)

    def parse_for(self) -> For:
        self.expect('KEYWORD', 'for')
        var = self.expect('WORD')[1]

        self.expect('KEYWORD', 'in')

        items = []
        while t := self.peek():
            if (t[0] == 'OP' and t[1] == ';') or (t[0] == 'KEYWORD' and t[1] == 'do'):
                break
            items.append(self.next()[1])

        self.accept('OP', ';')
        self.expect('KEYWORD', 'do')

        body = self._parse_statements_until(['done'])
        self.expect('KEYWORD', 'done')
        return For(var, items, body)

    def parse_select(self) -> Select:
        """Parse select menu: select var in item1 item2; do ...; done"""
        self.expect('KEYWORD', 'select')
        var = self.expect('WORD')[1]

        self.expect('KEYWORD', 'in')

        items = []
        while t := self.peek():
            if (t[0] == 'OP' and t[1] == ';') or (t[0] == 'KEYWORD' and t[1] == 'do'):
                break
            items.append(self.next()[1])

        self.accept('OP', ';')
        self.expect('KEYWORD', 'do')

        body = self._parse_statements_until(['done'])
        self.expect('KEYWORD', 'done')
        return Select(var, items, body)

    def parse_case(self) -> Case:
        """Parse case statement."""
        self.expect('KEYWORD', 'case')
        expr = self.expect('WORD')[1]
        self.expect('KEYWORD', 'in')

        clauses = []
        while self.peek() and not (self.peek()[0] == 'KEYWORD' and self.peek()[1] == 'esac'):
            patterns = []
            while True:
                pattern = self.expect('WORD')[1]
                patterns.append(pattern)
                if self.accept('OP', '|'):
                    continue
                else:
                    break

            self.expect('OP', ')')

            body_stmts = []
            while self.peek() and not (self.peek()[0] == 'OP' and self.peek()[1] == ';;'):
                if self.peek()[0] == 'KEYWORD' and self.peek()[1] == 'esac':
                    break
                stmt = self.parse_and_or()
                if stmt:
                    body_stmts.append(stmt)
                self.accept('OP', ';')

            self.accept('OP', ';;')
            clauses.append((patterns, Script(body_stmts)))

        self.expect('KEYWORD', 'esac')
        return Case(expr, clauses)
