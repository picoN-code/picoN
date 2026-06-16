#!/usr/bin/env python3
"""picoN interpreter - a radically readable programming language."""

import sys
import re


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

KEYWORDS = frozenset({
    'store', 'as', 'set', 'to',
    'add', 'subtract', 'multiply', 'divide', 'from', 'by',
    'say', 'blank',
    'ask', 'into', 'number',
    'if', 'then', 'otherwise', 'end',
    'and', 'or', 'not',
    'repeat', 'times',
    'while',
    'count',
    'stop', 'loop',
    'next', 'step',
    'define', 'using',
    'run', 'with',
    'give', 'back',
    'note',
    'is', 'greater', 'less', 'than', 'at', 'least', 'most',
    'yes', 'no',
    'text',
})

TEXT_DELIMITER = 'text'


class TokenType:
    KEYWORD = 'KEYWORD'
    IDENTIFIER = 'IDENTIFIER'
    NUMBER = 'NUMBER'
    COMMA = 'COMMA'
    PERIOD = 'PERIOD'
    NEWLINE = 'NEWLINE'


class Token:
    __slots__ = ('type', 'value', 'line')

    def __init__(self, type, value, line):
        self.type = type
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line={self.line})'


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, line, message):
        self.line = line
        super().__init__(f'Line {line}: {message}')


class Lexer:
    """Tokenize picoN source into a flat list of Token objects."""

    def __init__(self, source):
        self.source = source
        self.tokens = []
        self.line_num = 0

    def lex(self):
        for raw_line in self.source.splitlines():
            self.line_num += 1
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('note'):
                continue
            self._lex_line(line)
            self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line_num))
        return self.tokens

    def _lex_line(self, line):
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if ch in ' \t':
                i += 1
                continue
            if ch == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', self.line_num))
                i += 1
                continue
            if ch == '.':
                self.tokens.append(Token(TokenType.PERIOD, '.', self.line_num))
                i += 1
                continue
            if ch in '0123456789' or (ch == '-' and i + 1 < n and line[i + 1] in '0123456789'):
                start = i
                i += 1
                while i < n and line[i] in '0123456789':
                    i += 1
                # Check for decimal point followed by digits
                if i < n and line[i] == '.' and i + 1 < n and line[i + 1] in '0123456789':
                    i += 1
                    while i < n and line[i] in '0123456789':
                        i += 1
                    num_str = line[start:i]
                    val = float(num_str)
                else:
                    num_str = line[start:i]
                    val = int(num_str)
                self.tokens.append(Token(TokenType.NUMBER, val, self.line_num))
                continue
            if ch.isalpha():
                start = i
                while i < n and line[i].isalpha():
                    i += 1
                word = line[start:i]
                lower = word.lower()
                if lower in KEYWORDS:
                    self.tokens.append(Token(TokenType.KEYWORD, lower, self.line_num))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, word, self.line_num))
                continue
            raise LexError(self.line_num, f"Invalid character: '{ch}'")


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------

class ASTNode:
    line = 0


class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements


class Store(ASTNode):
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line


class Set(ASTNode):
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line


class Arithmetic(ASTNode):
    def __init__(self, op, target, value, line):
        self.op = op  # 'add', 'subtract', 'multiply', 'divide'
        self.target = target
        self.value = value
        self.line = line


class Say(ASTNode):
    def __init__(self, values, line):
        self.values = values  # list of expression nodes; empty = say blank
        self.line = line


class Ask(ASTNode):
    def __init__(self, prompt, name, as_number, line):
        self.prompt = prompt
        self.name = name
        self.as_number = as_number
        self.line = line


class If(ASTNode):
    def __init__(self, condition, then_body, otherwise_body, line):
        self.condition = condition
        self.then_body = then_body
        self.otherwise_body = otherwise_body
        self.line = line


class While(ASTNode):
    def __init__(self, condition, body, line):
        self.condition = condition
        self.body = body
        self.line = line


class Repeat(ASTNode):
    def __init__(self, count, body, line):
        self.count = count  # expression node
        self.body = body
        self.line = line


class Count(ASTNode):
    def __init__(self, name, start, end, body, line):
        self.name = name
        self.start = start
        self.end = end
        self.body = body
        self.line = line


class Define(ASTNode):
    def __init__(self, name, params, body, line):
        self.name = name
        self.params = params  # list of strings or empty
        self.body = body
        self.line = line


class Run(ASTNode):
    def __init__(self, name, args, line):
        self.name = name
        self.args = args  # list of expression nodes
        self.line = line


class GiveBack(ASTNode):
    def __init__(self, value, line):
        self.value = value
        self.line = line


class StopLoop(ASTNode):
    pass


class NextStep(ASTNode):
    pass


# ---------------------------------------------------------------------------
# Condition nodes
# ---------------------------------------------------------------------------

class CondEq:
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line

class CondNeq:
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line

class CondGt:
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line

class CondLt:
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line

class CondGte:
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line

class CondLte:
    def __init__(self, name, value, line):
        self.name = name
        self.value = value
        self.line = line

class CondAnd:
    def __init__(self, left, right, line):
        self.left = left
        self.right = right
        self.line = line

class CondOr:
    def __init__(self, left, right, line):
        self.left = left
        self.right = right
        self.line = line

class CondNot:
    def __init__(self, cond, line):
        self.cond = cond
        self.line = line


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, line, message):
        self.line = line
        super().__init__(f'Line {line}: Syntax error: {message}')


class RuntimeError_(Exception):
    def __init__(self, line, message):
        self.line = line
        super().__init__(f'Line {line}: Runtime error: {message}')


class BreakLoop(Exception):
    pass


class NextIteration(Exception):
    pass


class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """Parse a flat token stream into an AST."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # -- token stream helpers --

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def expect_keyword(self, kw):
        tok = self.peek()
        if tok is None or tok.type != TokenType.KEYWORD or tok.value != kw:
            raise ParseError(tok.line if tok else 0, f"Expected '{kw}', got {tok!r}")
        return self.advance()

    def expect_period(self):
        tok = self.peek()
        if tok is None or tok.type != TokenType.PERIOD:
            line = tok.line if tok else 0
            raise ParseError(line, "Expected '.'")
        return self.advance()

    def expect_comma(self):
        tok = self.peek()
        if tok is None or tok.type != TokenType.COMMA:
            line = tok.line if tok else 0
            raise ParseError(line, "Expected ','")
        return self.advance()

    def expect_newline(self):
        tok = self.peek()
        if tok is not None and tok.type == TokenType.NEWLINE:
            return self.advance()

    def skip_newlines(self):
        while self.peek() and self.peek().type == TokenType.NEWLINE:
            self.advance()

    def is_keyword(self, kw):
        tok = self.peek()
        return tok is not None and tok.type == TokenType.KEYWORD and tok.value == kw

    def is_identifier(self):
        tok = self.peek()
        return tok is not None and tok.type == TokenType.IDENTIFIER

    def is_number(self):
        tok = self.peek()
        return tok is not None and tok.type == TokenType.NUMBER

    def match_keyword(self, kw):
        if self.is_keyword(kw):
            return self.advance()
        return None

    def match_newline_or_period(self):
        tok = self.peek()
        if tok and tok.type == TokenType.NEWLINE:
            self.advance()
            return True
        if tok and tok.type == TokenType.PERIOD:
            self.advance()
            return True
        return False

    # -- main parse --

    def parse(self):
        self.skip_newlines()
        stmts = []
        while self.peek() is not None:
            self.skip_newlines()
            if self.peek() is None:
                break
            stmts.append(self.parse_statement())
            self.skip_newlines()
        return Program(stmts)

    def parse_statement(self):
        tok = self.peek()
        if tok is None:
            raise ParseError(0, 'Unexpected end of input')
        if tok.type == TokenType.KEYWORD:
            kw = tok.value
            if kw == 'store':
                return self.parse_store()
            if kw == 'set':
                return self.parse_set()
            if kw in ('add', 'subtract', 'multiply', 'divide'):
                return self.parse_arithmetic()
            if kw == 'say':
                return self.parse_say()
            if kw == 'ask':
                return self.parse_ask()
            if kw == 'if':
                return self.parse_if()
            if kw == 'while':
                return self.parse_while()
            if kw == 'repeat':
                return self.parse_repeat()
            if kw == 'count':
                return self.parse_count()
            if kw == 'define':
                return self.parse_define()
            if kw == 'run':
                return self.parse_run()
            if kw == 'give':
                return self.parse_give_back()
            if kw == 'stop':
                return self.parse_stop_loop()
            if kw == 'next':
                return self.parse_next_step()
        raise ParseError(tok.line, f"Unexpected token: {tok.value!r}")

    # -- expression parser (recursive descent) --

    def parse_expr(self):
        return self.parse_or_expr()

    def parse_or_expr(self):
        left = self.parse_and_expr()
        while self.is_keyword('or'):
            self.advance()
            right = self.parse_and_expr()
            left = ('or', left, right)
        return left

    def parse_and_expr(self):
        left = self.parse_not_expr()
        while self.is_keyword('and'):
            self.advance()
            right = self.parse_not_expr()
            left = ('and', left, right)
        return left

    def parse_not_expr(self):
        if self.is_keyword('not'):
            line = self.peek().line
            self.advance()
            operand = self.parse_not_expr()
            return ('not', operand, line)
        return self.parse_atom()

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise ParseError(0, 'Unexpected end of expression')

        # text literal: text ... text
        if tok.type == TokenType.KEYWORD and tok.value == TEXT_DELIMITER:
            return self.parse_text_literal()

        # number literal
        if tok.type == TokenType.NUMBER:
            self.advance()
            return ('number', tok.value, tok.line)

        # boolean literal
        if tok.type == TokenType.KEYWORD and tok.value in ('yes', 'no'):
            self.advance()
            return ('boolean', tok.value == 'yes', tok.line)

        # function call expression: run NAME [with ARGS]
        if tok.type == TokenType.KEYWORD and tok.value == 'run':
            return self.parse_run_expr()

        # identifier (variable reference)
        if tok.type == TokenType.IDENTIFIER:
            self.advance()
            return ('var', tok.value, tok.line)

        raise ParseError(tok.line, f"Unexpected token in expression: {tok.value!r}")

    def parse_text_literal(self):
        """Parse 'text ... text' delimited string."""
        start_line = self.peek().line
        self.advance()  # consume opening 'text'
        words = []
        depth = 1
        while self.peek() is not None:
            tok = self.peek()
            if tok.type == TokenType.KEYWORD and tok.value == TEXT_DELIMITER:
                depth -= 1
                if depth == 0:
                    self.advance()
                    return ('text', ' '.join(words), start_line)
                else:
                    words.append(tok.value)
                    self.advance()
            elif tok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                words.append(tok.value)
                self.advance()
            elif tok.type == TokenType.NUMBER:
                words.append(str(tok.value))
                self.advance()
            elif tok.type == TokenType.COMMA:
                words.append(',')
                self.advance()
            else:
                break
        raise ParseError(start_line, 'Unterminated text literal (missing closing text)')

    def parse_value(self):
        """Parse a single value expression (no and/or/not)."""
        return self.parse_atom()

    # -- condition parser --

    def parse_condition(self):
        return self.parse_or_condition()

    def parse_or_condition(self):
        left = self.parse_and_condition()
        while self.is_keyword('or'):
            self.advance()
            right = self.parse_and_condition()
            line = left.line if hasattr(left, 'line') else 0
            left = CondOr(left, right, line)
        return left

    def parse_and_condition(self):
        left = self.parse_not_condition()
        while self.is_keyword('and'):
            self.advance()
            right = self.parse_not_condition()
            line = left.line if hasattr(left, 'line') else 0
            left = CondAnd(left, right, line)
        return left

    def parse_not_condition(self):
        if self.is_keyword('not'):
            line = self.peek().line
            self.advance()
            cond = self.parse_not_condition()
            return CondNot(cond, line)
        return self.parse_simple_condition()

    def parse_simple_condition(self):
        tok = self.peek()
        if tok is None:
            raise ParseError(0, 'Unexpected end of condition')

        # Handle parenthesized-like: not handled in picoN, so skip

        # NAME is VALUE
        # NAME is not VALUE
        # NAME is greater than VALUE
        # NAME is less than VALUE
        # NAME is at least VALUE
        # NAME is at most VALUE
        if tok.type == TokenType.IDENTIFIER:
            name = tok.value
            name_line = tok.line
            self.advance()
            self.expect_keyword('is')
            # Check for 'not'
            if self.match_keyword('not'):
                val = self.parse_value()
                return CondNeq(name, val, name_line)
            # Check for 'greater than'
            if self.is_keyword('greater'):
                self.advance()
                self.expect_keyword('than')
                val = self.parse_value()
                return CondGt(name, val, name_line)
            # Check for 'less than'
            if self.is_keyword('less'):
                self.advance()
                self.expect_keyword('than')
                val = self.parse_value()
                return CondLt(name, val, name_line)
            # Check for 'at least' / 'at most'
            if self.is_keyword('at'):
                self.advance()
                if self.match_keyword('least'):
                    val = self.parse_value()
                    return CondGte(name, val, name_line)
                if self.match_keyword('most'):
                    val = self.parse_value()
                    return CondLte(name, val, name_line)
                raise ParseError(name_line, "Expected 'least' or 'most' after 'at'")
            # Simple equality: NAME is VALUE
            val = self.parse_value()
            return CondEq(name, val, name_line)

        raise ParseError(tok.line, f"Unexpected token in condition: {tok.value!r}")

    # -- statement parsers --

    def parse_store(self):
        tok = self.expect_keyword('store')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected variable name after 'store'")
        name = name_tok.value
        self.advance()
        self.expect_keyword('as')
        value = self.parse_value()
        self.expect_period()
        return Store(name, value, tok.line)

    def parse_set(self):
        tok = self.expect_keyword('set')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected variable name after 'set'")
        name = name_tok.value
        self.advance()
        self.expect_keyword('to')
        value = self.parse_value()
        self.expect_period()
        return Set(name, value, tok.line)

    def parse_arithmetic(self):
        op_tok = self.advance()
        op = op_tok.value
        if op == 'add':
            val = self.parse_value()
            self.expect_keyword('to')
            target = self.peek()
            if target is None or target.type != TokenType.IDENTIFIER:
                raise ParseError(op_tok.line, "Expected variable name after 'to'")
            name = target.value
            self.advance()
            self.expect_period()
            return Arithmetic(op, name, val, op_tok.line)
        elif op == 'subtract':
            val = self.parse_value()
            self.expect_keyword('from')
            target = self.peek()
            if target is None or target.type != TokenType.IDENTIFIER:
                raise ParseError(op_tok.line, "Expected variable name after 'from'")
            name = target.value
            self.advance()
            self.expect_period()
            return Arithmetic(op, name, val, op_tok.line)
        elif op in ('multiply', 'divide'):
            target = self.peek()
            if target is None or target.type != TokenType.IDENTIFIER:
                raise ParseError(op_tok.line, "Expected variable name")
            name = target.value
            self.advance()
            self.expect_keyword('by')
            val = self.parse_value()
            self.expect_period()
            return Arithmetic(op, name, val, op_tok.line)
        else:
            raise ParseError(op_tok.line, f"Unknown arithmetic operator: {op}")

    def parse_say(self):
        tok = self.expect_keyword('say')
        # Check for 'say blank'
        if self.is_keyword('blank'):
            self.advance()
            self.expect_period()
            return Say([], tok.line)
        values = []
        values.append(self.parse_value())
        while self.match_comma():
            values.append(self.parse_value())
        self.expect_period()
        return Say(values, tok.line)

    def match_comma(self):
        tok = self.peek()
        if tok and tok.type == TokenType.COMMA:
            self.advance()
            return True
        return False

    def parse_ask(self):
        tok = self.expect_keyword('ask')
        # Collect words until 'into' keyword as the prompt string
        prompt_words = []
        while not self.is_keyword('into'):
            ptok = self.peek()
            if ptok is None:
                raise ParseError(tok.line, "Expected 'into' in ask statement")
            if ptok.type == TokenType.KEYWORD and ptok.value == 'text':
                # text-delimited string within prompt
                prompt_words.append(self.parse_text_literal()[1])
            elif ptok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                prompt_words.append(ptok.value)
                self.advance()
            elif ptok.type == TokenType.NUMBER:
                prompt_words.append(str(ptok.value))
                self.advance()
            else:
                break
        prompt = ('text', ' '.join(prompt_words), tok.line)
        self.expect_keyword('into')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected variable name after 'into'")
        name = name_tok.value
        self.advance()
        as_number = False
        if self.match_keyword('as'):
            if self.match_keyword('number'):
                as_number = True
            else:
                raise ParseError(tok.line, "Expected 'number' after 'as'")
        self.expect_period()
        return Ask(prompt, name, as_number, tok.line)

    def parse_if(self):
        tok = self.expect_keyword('if')
        condition = self.parse_condition()
        self.expect_keyword('then')
        self.expect_newline()
        then_body = self.parse_body_until(['otherwise', 'end'])
        otherwise_body = []
        if self.is_keyword('otherwise'):
            self.advance()
            self.expect_newline()
            otherwise_body = self.parse_body_until(['end'])
        self.expect_keyword('end')
        self.expect_keyword('if')
        self.expect_period()
        return If(condition, then_body, otherwise_body, tok.line)

    def parse_while(self):
        tok = self.expect_keyword('while')
        condition = self.parse_condition()
        self.expect_newline()
        body = self.parse_body_until(['end'])
        self.expect_keyword('end')
        self.expect_keyword('while')
        self.expect_period()
        return While(condition, body, tok.line)

    def parse_repeat(self):
        tok = self.expect_keyword('repeat')
        count = self.parse_value()
        self.expect_keyword('times')
        self.expect_newline()
        body = self.parse_body_until(['end'])
        self.expect_keyword('end')
        self.expect_keyword('repeat')
        self.expect_period()
        return Repeat(count, body, tok.line)

    def parse_count(self):
        tok = self.expect_keyword('count')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected loop variable name")
        name = name_tok.value
        self.advance()
        self.expect_keyword('from')
        start = self.parse_value()
        self.expect_keyword('to')
        end = self.parse_value()
        self.expect_newline()
        body = self.parse_body_until(['end'])
        self.expect_keyword('end')
        self.expect_keyword('count')
        self.expect_period()
        return Count(name, start, end, body, tok.line)

    def parse_define(self):
        tok = self.expect_keyword('define')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected function name")
        name = name_tok.value
        self.advance()
        params = []
        if self.match_keyword('using'):
            param_tok = self.peek()
            if param_tok is None or param_tok.type != TokenType.IDENTIFIER:
                raise ParseError(tok.line, "Expected parameter name")
            params.append(param_tok.value)
            self.advance()
            while self.match_comma():
                param_tok = self.peek()
                if param_tok is None or param_tok.type != TokenType.IDENTIFIER:
                    raise ParseError(tok.line, "Expected parameter name")
                params.append(param_tok.value)
                self.advance()
        self.expect_newline()
        body = self.parse_body_until(['end'])
        self.expect_keyword('end')
        self.expect_keyword('define')
        self.expect_period()
        return Define(name, params, body, tok.line)

    def parse_run(self):
        tok = self.expect_keyword('run')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected function name after 'run'")
        name = name_tok.value
        self.advance()
        args = []
        if self.match_keyword('with'):
            args.append(self.parse_value())
            while self.match_comma():
                args.append(self.parse_value())
        self.expect_period()
        return Run(name, args, tok.line)

    def parse_run_expr(self):
        tok = self.expect_keyword('run')
        name_tok = self.peek()
        if name_tok is None or name_tok.type != TokenType.IDENTIFIER:
            raise ParseError(tok.line, "Expected function name after 'run'")
        name = name_tok.value
        self.advance()
        args = []
        if self.match_keyword('with'):
            args.append(self.parse_value())
            while self.match_comma():
                args.append(self.parse_value())
        return ('run_call', name, args, tok.line)

    def parse_give_back(self):
        tok = self.expect_keyword('give')
        self.expect_keyword('back')
        value = self.parse_value()
        self.expect_period()
        return GiveBack(value, tok.line)

    def parse_stop_loop(self):
        tok = self.expect_keyword('stop')
        self.expect_keyword('loop')
        self.expect_period()
        return StopLoop()

    def parse_next_step(self):
        tok = self.expect_keyword('next')
        self.expect_keyword('step')
        self.expect_period()
        return NextStep()

    def parse_body_until(self, stop_keywords):
        """Parse statements until we hit a stop keyword (end/otherwise)."""
        stmts = []
        self.skip_newlines()
        while self.peek() is not None:
            tok = self.peek()
            if tok.type == TokenType.KEYWORD and tok.value in stop_keywords:
                break
            if tok.type == TokenType.KEYWORD and tok.value == 'end':
                break
            stmts.append(self.parse_statement())
            self.skip_newlines()
        return stmts


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter:
    """Execute a picoN AST."""

    def __init__(self):
        self.globals = {}
        self.functions = {}
        self.call_stack = []
        self.output = []  # captured output for testing

    def run(self, program):
        for stmt in program.statements:
            self.exec_stmt(stmt)

    def exec_stmt(self, node):
        if isinstance(node, Store):
            val = self.eval_expr(node.value)
            self.globals[node.name] = val
        elif isinstance(node, Set):
            if node.name not in self.globals:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            self.globals[node.name] = self.eval_expr(node.value)
        elif isinstance(node, Arithmetic):
            if node.target not in self.globals:
                raise RuntimeError_(node.line, f"Variable '{node.target}' not defined")
            val = self.globals[node.target]
            amount = self.eval_expr(node.value)
            if node.op == 'add':
                self.globals[node.target] = self._to_number(val, node.line) + self._to_number(amount, node.line)
            elif node.op == 'subtract':
                self.globals[node.target] = self._to_number(val, node.line) - self._to_number(amount, node.line)
            elif node.op == 'multiply':
                self.globals[node.target] = self._to_number(val, node.line) * self._to_number(amount, node.line)
            elif node.op == 'divide':
                divisor = self._to_number(amount, node.line)
                if divisor == 0:
                    raise RuntimeError_(node.line, 'Division by zero')
                self.globals[node.target] = self._to_number(val, node.line) / divisor
        elif isinstance(node, Say):
            if not node.values:
                print()
                return
            parts = []
            for expr in node.values:
                val = self.eval_expr(expr)
                formatted = self._format_value(val)
                if formatted:
                    parts.append(formatted)
            print(' '.join(parts))
        elif isinstance(node, Ask):
            prompt = self.eval_expr(node.prompt)
            try:
                raw = input(prompt + ' ')
            except EOFError:
                raw = ''
            if node.as_number:
                try:
                    self.globals[node.name] = int(raw)
                except ValueError:
                    try:
                        self.globals[node.name] = float(raw)
                    except ValueError:
                        raise RuntimeError_(node.line, f"Cannot convert '{raw}' to number")
            else:
                self.globals[node.name] = raw
        elif isinstance(node, If):
            cond_val = self.eval_condition(node.condition)
            if cond_val:
                self.exec_block(node.then_body)
            else:
                self.exec_block(node.otherwise_body)
        elif isinstance(node, While):
            while self.eval_condition(node.condition):
                try:
                    self.exec_block(node.body)
                except BreakLoop:
                    break
                except NextIteration:
                    continue
        elif isinstance(node, Repeat):
            count_val = self._to_number(self.eval_expr(node.count), node.line)
            for _ in range(int(count_val)):
                try:
                    self.exec_block(node.body)
                except BreakLoop:
                    break
                except NextIteration:
                    continue
        elif isinstance(node, Count):
            start_val = int(self._to_number(self.eval_expr(node.start), node.line))
            end_val = int(self._to_number(self.eval_expr(node.end), node.line))
            for i in range(start_val, end_val + 1):
                self.globals[node.name] = i
                try:
                    self.exec_block(node.body)
                except BreakLoop:
                    break
                except NextIteration:
                    continue
        elif isinstance(node, Define):
            self.functions[node.name] = node
        elif isinstance(node, Run):
            args = [self.eval_expr(a) for a in node.args]
            self.call_function(node.name, args, node.line)
        elif isinstance(node, GiveBack):
            val = self.eval_expr(node.value)
            raise ReturnValue(val)
        elif isinstance(node, StopLoop):
            raise BreakLoop()
        elif isinstance(node, NextStep):
            raise NextIteration()
        else:
            raise RuntimeError_(0, f'Unknown node type: {type(node).__name__}')

    def exec_block(self, stmts):
        for stmt in stmts:
            self.exec_stmt(stmt)

    def call_function(self, name, args, line):
        if name not in self.functions:
            raise RuntimeError_(line, f"Function '{name}' not defined")
        func = self.functions[name]
        if len(args) != len(func.params):
            raise RuntimeError_(line, f"Function '{name}' expects {len(func.params)} arguments, got {len(args)}")
        # Create local scope
        saved = {k: self.globals[k] for k in func.params if k in self.globals}
        for pname, aval in zip(func.params, args):
            self.globals[pname] = aval
        try:
            self.exec_block(func.body)
            ret_val = None
        except ReturnValue as rv:
            ret_val = rv.value
        # Restore scope
        for pname in func.params:
            if pname in saved:
                self.globals[pname] = saved[pname]
            elif pname in self.globals:
                del self.globals[pname]
        return ret_val

    def eval_expr(self, node):
        if isinstance(node, tuple):
            tag = node[0]
            if tag == 'number':
                return node[1]
            elif tag == 'text':
                return node[1]
            elif tag == 'boolean':
                return node[1]
            elif tag == 'var':
                name = node[1]
                if name not in self.globals:
                    raise RuntimeError_(node[2], f"Variable '{name}' not defined")
                return self.globals[name]
            elif tag == 'or':
                left = self.eval_expr(node[1])
                right = self.eval_expr(node[2])
                return left or right
            elif tag == 'and':
                left = self.eval_expr(node[1])
                right = self.eval_expr(node[2])
                return left and right
            elif tag == 'not':
                val = self.eval_expr(node[1])
                return not val
            elif tag == 'run_call':
                name = node[1]
                args = [self.eval_expr(a) for a in node[2]]
                return self.call_function(name, args, node[3])
        raise RuntimeError_(0, f'Invalid expression: {node!r}')

    def eval_condition(self, node):
        if isinstance(node, CondEq):
            left = self.globals.get(node.name)
            if left is None:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            right = self.eval_expr(node.value)
            return left == right
        elif isinstance(node, CondNeq):
            left = self.globals.get(node.name)
            if left is None:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            right = self.eval_expr(node.value)
            return left != right
        elif isinstance(node, CondGt):
            left = self.globals.get(node.name)
            if left is None:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            right = self.eval_expr(node.value)
            return self._to_number(left, node.line) > self._to_number(right, node.line)
        elif isinstance(node, CondLt):
            left = self.globals.get(node.name)
            if left is None:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            right = self.eval_expr(node.value)
            return self._to_number(left, node.line) < self._to_number(right, node.line)
        elif isinstance(node, CondGte):
            left = self.globals.get(node.name)
            if left is None:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            right = self.eval_expr(node.value)
            return self._to_number(left, node.line) >= self._to_number(right, node.line)
        elif isinstance(node, CondLte):
            left = self.globals.get(node.name)
            if left is None:
                raise RuntimeError_(node.line, f"Variable '{node.name}' not defined")
            right = self.eval_expr(node.value)
            return self._to_number(left, node.line) <= self._to_number(right, node.line)
        elif isinstance(node, CondAnd):
            return self.eval_condition(node.left) and self.eval_condition(node.right)
        elif isinstance(node, CondOr):
            return self.eval_condition(node.left) or self.eval_condition(node.right)
        elif isinstance(node, CondNot):
            return not self.eval_condition(node.cond)
        raise RuntimeError_(0, f'Invalid condition: {node!r}')

    def _to_number(self, val, line):
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            try:
                return int(val)
            except ValueError:
                try:
                    return float(val)
                except ValueError:
                    raise RuntimeError_(line, f"Cannot convert '{val}' to number")
        raise RuntimeError_(line, f"Cannot convert {type(val).__name__} to number")

    def _format_value(self, val):
        if isinstance(val, bool):
            return 'yes' if val else 'no'
        return str(val)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print('Usage: picon.py <filename.pico>')
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)

    try:
        lexer = Lexer(source)
        tokens = lexer.lex()
        parser = Parser(tokens)
        program = parser.parse()
        interpreter = Interpreter()
        interpreter.run(program)
    except LexError as e:
        print(f'Lex error: {e}')
        sys.exit(1)
    except ParseError as e:
        print(f'Parse error: {e}')
        sys.exit(1)
    except RuntimeError_ as e:
        print(f'Runtime error: {e}')
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nInterrupted.')
        sys.exit(130)
    except EOFError:
        pass


if __name__ == '__main__':
    main()
