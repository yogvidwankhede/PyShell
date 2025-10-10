from typing import List, Tuple
import sys
Token = Tuple[str, str]

# Operators that control the flow and structure of commands (WITHOUT braces/parens)
_OPERATORS = {'&&', '||', '|', ';', '&', ';;'}

# Operators that handle input/output redirection
_REDIR_TOKENS = {
    '>>', '>', '<',
    '<<',
    '<<<',
    '2>>', '2>',
    '&>',
    '2>&1'
}

# Keywords that have special meaning to the shell
_KEYWORDS = {
    'if', 'then', 'elif', 'else', 'fi',
    'while', 'until', 'do', 'done',
    'for', 'in',
    'case', 'esac',
    'function',
    'select',
    'time',
    '!',
    '[[', ']]'
}

# ALL operators for checking (include parens/braces here for word detection)
_ALL_OPERATORS = sorted(
    list(_OPERATORS | _REDIR_TOKENS), key=len, reverse=True
)

# Structural operators that can start/end compound commands
_STRUCTURAL_OPS = {'(', ')', '{', '}'}


def tokenize(s: str) -> List[Token]:
    """
    Tokenize the input string into a list of tokens.
    Braces and parens in words (like {1..5}, $(...), ${...}) stay in words.
    Standalone braces/parens become operators.
    Newlines are converted to semicolons for statement separation.
    """
    tokens: List[Token] = []
    i = 0
    n = len(s)
    last_was_newline = False

    while i < n:
        # Handle newlines as statement separators
        if s[i] == '\n':
            # Only emit semicolon if we have preceding tokens and last wasn't a separator
            if tokens and tokens[-1][1] not in (';', '&&', '||', '|', 'then', 'do', 'else', 'elif', '{', '('):
                # Check if we're not in a context that expects continuation
                if not (tokens and tokens[-1][0] == 'KEYWORD' and tokens[-1][1] in ('if', 'while', 'until', 'for', 'case')):
                    tokens.append(('OP', ';'))
                    last_was_newline = True
            i += 1
            continue

        # Skip other whitespace
        if s[i].isspace():
            i += 1
            continue

        last_was_newline = False

        # Skip comments - but NOT if preceded by $ (for $#)
        if s[i] == '#':
            # Check if this is part of $# special variable
            if i > 0 and s[i-1] == '$':
                # This is part of $#, not a comment - will be handled in word parsing
                pass
            else:
                # This is a comment
                while i < n and s[i] != '\n':
                    i += 1
                continue

        # Check for redirection/flow operators (NOT including braces/parens)
        found_op = False
        for op in _ALL_OPERATORS:
            if s.startswith(op, i):
                op_type = 'REDIR' if op in _REDIR_TOKENS else 'OP'
                tokens.append((op_type, op))
                i += len(op)
                found_op = True
                break
        if found_op:
            continue

        # Check for structural operators
        if s[i] in _STRUCTURAL_OPS:
            # Parentheses should always be separate tokens (for function definitions)
            if s[i] in '()':
                tokens.append(('OP', s[i]))
                i += 1
                continue

            # For braces, check if part of a word
            if i > 0:
                prev_char = s[i-1]
                # If it's after $, it's part of expansion
                if prev_char == '$' or (prev_char not in ' \t\n|;&'):
                    # Part of a word - parse as word
                    word_start = i
                    word = _parse_word(s, i)
                    if word:
                        tokens.append(('WORD', word))
                        i = word_start + len(word)
                    else:
                        i += 1
                    continue

            # Check ahead - if followed by number or comma, it's brace expansion
            if s[i] == '{' and i + 1 < n:
                # Look ahead for brace expansion patterns
                # But stop at statement separators to avoid treating blocks as expansions
                j = i + 1
                has_dots = False
                has_comma = False
                depth = 1
                hit_separator = False
                while j < n and depth > 0:
                    if s[j] == '{':
                        depth += 1
                    elif s[j] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    # Stop checking if we hit statement separators
                    # This means it's a block, not a brace expansion
                    elif s[j] in ';|&' and depth == 1:
                        hit_separator = True
                        break
                    elif s[j:j+2] == '..':
                        has_dots = True
                    elif s[j] == ',':
                        has_comma = True
                    j += 1

                # Only treat as brace expansion if we found dots/commas AND didn't hit separators
                if (has_dots or has_comma) and not hit_separator:
                    # This is a brace expansion, parse as word
                    word_start = i
                    word = _parse_word(s, i)
                    if word:
                        tokens.append(('WORD', word))
                        i = word_start + len(word)
                        continue

            # This is a standalone structural operator
            tokens.append(('OP', s[i]))
            i += 1
            continue

        # Parse a word (which may contain braces, parens, etc)
        word_start = i
        word = _parse_word(s, i)
        if word:
            tokens.append(('WORD', word))
            i = word_start + len(word)
        else:
            # Shouldn't happen, but skip char if it does
            i += 1

    # Post-process to identify keywords
    final_tokens = []
    for typ, val in tokens:
        if typ == 'WORD' and val in _KEYWORDS:
            final_tokens.append(('KEYWORD', val))
        else:
            final_tokens.append((typ, val))
    # print(f"DEBUG TOKENS: {final_tokens}", file=sys.stderr)
    return final_tokens


def _parse_word(s: str, start: int) -> str:
    """
    Parse a word starting at position start.
    A word can contain:
    - Regular characters
    - Quoted strings
    - Brace expansions {1..5}, {a,b,c}
    - Variable expansions ${var}, $var
    - Command substitutions $(cmd), `cmd`
    - Arithmetic expansions $((expr))
    - Windows paths with backslashes
    """
    word = ''
    i = start
    n = len(s)

    while i < n:
        c = s[i]

        # End word on whitespace or main operators
        if c.isspace():
            break
        if c in '|;&':
            break
        # End word on parentheses (for function definitions)
        if c in '()':
            break
        # Only treat # as comment if it's not part of $#
        if c == '#' and i > start and s[i-1] != '$':
            break

        # Check for multi-char operators
        if i < n - 1:
            two_char = s[i:i+2]
            if two_char in {'&&', '||', '>>', '<<', '2>', '&>'}:
                break
            if i < n - 2:
                three_char = s[i:i+3]
                if three_char in {'<<<', '2>&'}:
                    break

        # Handle quotes
        if c in ('"', "'"):
            quote = c
            word += c
            i += 1
            while i < n and s[i] != quote:
                if c == '"' and s[i] == '\\' and i + 1 < n:
                    # Handle escape sequences in double quotes
                    next_c = s[i + 1]
                    if next_c in ('"', '\\', '$', '`'):
                        word += next_c
                        i += 2
                        continue
                word += s[i]
                i += 1
            if i < n:
                word += s[i]  # Closing quote
                i += 1
            continue

        # Handle backslash escapes (improved for Windows paths)
        if c == '\\' and i + 1 < n:
            next_char = s[i + 1]
            # In unquoted context, backslash only escapes special characters
            # For Windows paths, backslash should be kept as-is for most characters
            if next_char in (' ', '\t', '\n', '|', '&', ';', '(', ')', '<', '>', '"', "'", '\\', '$', '`'):
                word += next_char
                i += 2
                continue
            else:
                # Not escaping anything special, keep the backslash (for Windows paths)
                word += c
                i += 1
                continue

        # Handle ${...} parameter expansion
        if c == '$' and i + 1 < n and s[i + 1] == '{':
            word += '${'
            i += 2
            depth = 1
            while i < n and depth > 0:
                if s[i] == '{':
                    depth += 1
                elif s[i] == '}':
                    depth -= 1
                word += s[i]
                i += 1
            continue

        # Handle $((...)arithmetic expansion
        if c == '$' and i + 2 < n and s[i + 1:i + 3] == '((':
            word += '$(('
            i += 3
            depth = 2
            while i < n and depth > 0:
                if s[i] == '(':
                    depth += 1
                elif s[i] == ')':
                    depth -= 1
                word += s[i]
                i += 1
            continue

        # Handle $(...) command substitution
        if c == '$' and i + 1 < n and s[i + 1] == '(':
            word += '$('
            i += 2
            depth = 1
            while i < n and depth > 0:
                if s[i] == '(':
                    depth += 1
                elif s[i] == ')':
                    depth -= 1
                word += s[i]
                i += 1
            continue

        # Handle `...` command substitution
        if c == '`':
            word += c
            i += 1
            while i < n and s[i] != '`':
                if s[i] == '\\' and i + 1 < n:
                    word += s[i + 1]
                    i += 2
                    continue
                word += s[i]
                i += 1
            if i < n:
                word += s[i]  # Closing backtick
                i += 1
            continue

        # Handle {1..5} or {a,b,c} brace expansions
        if c == '{':
            word += c
            i += 1
            depth = 1
            while i < n and depth > 0:
                if s[i] == '{':
                    depth += 1
                elif s[i] == '}':
                    depth -= 1
                word += s[i]
                i += 1
            continue

        # Regular character
        word += c
        i += 1

    return word
