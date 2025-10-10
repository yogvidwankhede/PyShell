"""
Handles shell expansions like variable, command, and arithmetic substitution.
NOW WITH ARRAY SUPPORT!
"""

import os
import re
import shlex
import subprocess
import glob
import sys

from . import state
from . import builtins


def expand_all(command_line: str) -> str:
    """Performs all expansions in the correct order."""
    # Order matters: tilde -> brace -> parameter -> arithmetic -> command substitution
    text = _expand_tilde(command_line)
    text = _expand_brace(text)
    text = _expand_variables(text)
    text = _expand_arithmetic(text)
    text = _expand_command_substitution(text)
    return text


def _expand_tilde(text: str) -> str:
    """Expands ~ and ~user to home directories."""
    # Get HOME from environment, but ensure it's the actual user home
    # On Windows, prefer USERPROFILE for the actual home directory
    if sys.platform == 'win32':
        home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    else:
        home = os.environ.get('HOME', os.path.expanduser('~'))

    # Handle ~ at start of word
    words = []
    in_quote = None
    current_word = ""

    for char in text:
        if char in ('"', "'") and in_quote is None:
            in_quote = char
            current_word += char
        elif char == in_quote:
            in_quote = None
            current_word += char
        elif char == ' ' and in_quote is None:
            if current_word:
                words.append(current_word)
            words.append(' ')
            current_word = ""
        else:
            current_word += char

    if current_word:
        words.append(current_word)

    # Expand tilde in each word
    result = []
    for word in words:
        if word.startswith('~') and not word.startswith('~/'):
            if word == '~':
                result.append(home)
            else:
                # ~username
                match = re.match(r'^~([a-zA-Z0-9_]+)(.*)', word)
                if match:
                    try:
                        expanded = os.path.expanduser(f"~{match.group(1)}")
                        result.append(expanded + match.group(2))
                    except:
                        result.append(word)
                else:
                    result.append(word)
        elif word.startswith('~/'):
            result.append(home + word[1:])
        else:
            result.append(word)

    return ''.join(result)


def _expand_brace(text: str) -> str:
    """
    Expands brace expressions like {1..10}, {a..z}, {x,y,z}
    """
    # Numeric range expansion: {1..10}
    def expand_numeric_range(match):
        start, end = int(match.group(1)), int(match.group(2))
        if start <= end:
            return ' '.join(str(i) for i in range(start, end + 1))
        else:
            return ' '.join(str(i) for i in range(start, end - 1, -1))

    text = re.sub(r'\{(\d+)\.\.(\d+)\}', expand_numeric_range, text)

    # Character range: {a..z}
    def expand_char_range(match):
        start, end = ord(match.group(1)), ord(match.group(2))
        if start <= end:
            return ' '.join(chr(i) for i in range(start, end + 1))
        else:
            return ' '.join(chr(i) for i in range(start, end - 1, -1))

    text = re.sub(r'\{([a-z])\.\.([a-z])\}', expand_char_range, text)

    # List expansion: {x,y,z}
    def expand_list(match):
        items = match.group(1).split(',')
        return ' '.join(items)

    # Only expand simple braces, not ${...}
    text = re.sub(r'(?<!\$)\{([^{}:]+(?:,[^{}:]+)+)\}', expand_list, text)

    return text


def _expand_variables(text: str) -> str:
    """
    Performs variable expansion on a string, supporting:
    - $VAR and ${VAR}
    - Arrays: ${arr[0]}, ${arr[@]}, ${arr[*]}
    - ${VAR:-default}
    - ${VAR:=default}
    - ${VAR:+alternate}
    - ${VAR:?error}
    - ${#VAR} (length)
    - ${VAR:offset:length} (substring)
    - ${VAR#pattern}, ${VAR##pattern} (remove prefix)
    - ${VAR%pattern}, ${VAR%%pattern} (remove suffix)
    - ${VAR/pattern/string}, ${VAR//pattern/string} (replace)
    """
    def replace_var(match):
        full_match = match.group(0)

        # ${...} expansion
        if match.group(1) is not None:
            var_expr = match.group(1)

            # Handle array access: ${arr[0]}, ${arr[@]}, ${arr[*]}
            array_match = re.match(
                r'^([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]$', var_expr)
            if array_match:
                array_name = array_match.group(1)
                index_expr = array_match.group(2)

                # Check if it's an indexed array
                if array_name in state.arrays:
                    if index_expr == '@' or index_expr == '*':
                        # Return all elements
                        return ' '.join(state.arrays[array_name])
                    else:
                        # Return specific index
                        try:
                            idx = int(index_expr)
                            if 0 <= idx < len(state.arrays[array_name]):
                                return state.arrays[array_name][idx]
                        except (ValueError, IndexError):
                            pass
                    return ''

                # Check if it's an associative array
                elif array_name in state.assoc_arrays:
                    if index_expr == '@' or index_expr == '*':
                        # Return all values
                        return ' '.join(state.assoc_arrays[array_name].values())
                    else:
                        # Return value for key
                        return state.assoc_arrays[array_name].get(index_expr, '')

                return ''

            # Handle array keys: ${!arr[@]}
            if var_expr.startswith('!'):
                array_name = var_expr[1:]
                # Check for array indices request
                array_indices_match = re.match(
                    r'^([a-zA-Z_][a-zA-Z0-9_]*)\[@\]$', array_name)
                if array_indices_match:
                    arr_name = array_indices_match.group(1)
                    if arr_name in state.arrays:
                        # Return all indices
                        return ' '.join(str(i) for i in range(len(state.arrays[arr_name])))
                    elif arr_name in state.assoc_arrays:
                        # Return all keys
                        return ' '.join(state.assoc_arrays[arr_name].keys())
                return ''

            # Handle special variables
            if var_expr == '?':
                return str(state.last_exit_status)
            if var_expr == '!':
                return str(state.last_background_pid)
            if var_expr == '$':
                return str(os.getpid())
            if var_expr == '0':
                return state.script_name or 'pyshell'
            if var_expr == '#':
                return str(len(state.positional_params))
            if var_expr == '@' or var_expr == '*':
                return ' '.join(state.positional_params)
            if var_expr == '-':
                return state.shell_options
            if var_expr == '_':
                return state.last_arg

            # Positional parameters
            if var_expr.isdigit():
                idx = int(var_expr)
                if 0 < idx <= len(state.positional_params):
                    return state.positional_params[idx - 1]
                return ''

            # ${#VAR} - length (works for arrays too)
            if var_expr.startswith('#'):
                var_name = var_expr[1:]

                # Check if it's an array length: ${#arr[@]}
                array_len_match = re.match(
                    r'^([a-zA-Z_][a-zA-Z0-9_]*)\[@\]$', var_name)
                if array_len_match:
                    arr_name = array_len_match.group(1)
                    if arr_name in state.arrays:
                        return str(len(state.arrays[arr_name]))
                    elif arr_name in state.assoc_arrays:
                        return str(len(state.assoc_arrays[arr_name]))
                    return '0'

                # Regular variable length
                value = _get_var_value(var_name)
                return str(len(value))

            # ${VAR:-default}
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                value = _get_var_value(var_name)
                return value if value else default

            # ${VAR:=default}
            if ':=' in var_expr:
                var_name, default = var_expr.split(':=', 1)
                value = _get_var_value(var_name)
                if not value:
                    state.local_vars[var_name] = default
                    return default
                return value

            # ${VAR:+alternate}
            if ':+' in var_expr:
                var_name, alternate = var_expr.split(':+', 1)
                value = _get_var_value(var_name)
                return alternate if value else ''

            # ${VAR:?error}
            if ':?' in var_expr:
                var_name, error_msg = var_expr.split(':?', 1)
                value = _get_var_value(var_name)
                if not value:
                    print(f"pyshell: {var_name}: {error_msg}", file=sys.stderr)
                    sys.exit(1)
                return value

            # ${VAR:offset:length} - substring
            if ':' in var_expr and not any(op in var_expr for op in [':-', ':=', ':+', ':?']):
                parts = var_expr.split(':', 1)
                var_name = parts[0]
                value = _get_var_value(var_name)

                if len(parts) == 2 and parts[1]:
                    offset_length = parts[1]
                    if ':' in offset_length:
                        offset_str, length_str = offset_length.split(':', 1)
                        offset = int(offset_str) if offset_str else 0
                        length = int(length_str) if length_str else len(value)
                        return value[offset:offset+length]
                    else:
                        offset = int(offset_length) if offset_length else 0
                        return value[offset:]

            # ${VAR##pattern} - remove longest prefix (must check before single #)
            if '##' in var_expr:
                var_name, pattern = var_expr.split('##', 1)
                value = _get_var_value(var_name)
                import fnmatch
                for i in range(len(value), -1, -1):
                    if fnmatch.fnmatch(value[:i], pattern):
                        return value[i:]
                return value

            # ${VAR#pattern} - remove shortest prefix
            if '#' in var_expr:
                var_name, pattern = var_expr.split('#', 1)
                value = _get_var_value(var_name)
                import fnmatch
                for i in range(len(value)):
                    if fnmatch.fnmatch(value[:i+1], pattern):
                        return value[i+1:]
                return value

            # ${VAR%%pattern} - remove longest suffix (must check before single %)
            if '%%' in var_expr:
                var_name, pattern = var_expr.split('%%', 1)
                value = _get_var_value(var_name)
                import fnmatch
                for i in range(len(value) + 1):
                    if fnmatch.fnmatch(value[i:], pattern):
                        return value[:i]
                return value

            # ${VAR%pattern} - remove shortest suffix
            if '%' in var_expr:
                var_name, pattern = var_expr.split('%', 1)
                value = _get_var_value(var_name)
                import fnmatch
                for i in range(len(value), -1, -1):
                    if fnmatch.fnmatch(value[i:], pattern):
                        return value[:i]
                return value

            # ${VAR//pattern/string} - replace all (must check before single /)
            if '//' in var_expr:
                parts = var_expr.split('//', 1)
                var_name = parts[0]
                value = _get_var_value(var_name)
                if len(parts) > 1 and '/' in parts[1]:
                    pattern, replacement = parts[1].split('/', 1)
                    return value.replace(pattern, replacement)
                return value

            # ${VAR/pattern/string} - replace first
            if '/' in var_expr:
                parts = var_expr.split('/', 1)
                var_name = parts[0]
                value = _get_var_value(var_name)
                if len(parts) > 1 and '/' in parts[1]:
                    pattern, replacement = parts[1].split('/', 1)
                    return value.replace(pattern, replacement, 1)
                return value

            # Simple variable
            return _get_var_value(var_expr)

        # $VAR expansion (no braces)
        elif match.group(2) is not None:
            var_name = match.group(2)

            # Special variables
            if var_name == '?':
                return str(state.last_exit_status)
            if var_name == '!':
                return str(state.last_background_pid)
            if var_name == '$':
                return str(os.getpid())
            if var_name == '0':
                return state.script_name or 'pyshell'
            if var_name == '#':
                return str(len(state.positional_params))
            if var_name == '@' or var_name == '*':
                return ' '.join(state.positional_params)
            if var_name == '-':
                return state.shell_options
            if var_name == '_':
                return state.last_arg

            # Positional parameters
            if var_name.isdigit():
                idx = int(var_name)
                if 0 < idx <= len(state.positional_params):
                    return state.positional_params[idx - 1]
                return ''

            # Regular variable
            return _get_var_value(var_name)

        return full_match

    # Match ${...} or $VAR
    pattern = r'(?<!\\)\$\{([^}]+)\}|(?<!\\)\$([a-zA-Z_][a-zA-Z0-9_]*|\?|!|\$|#|@|\*|-|_|\d+)'

    # Repeatedly substitute to handle nested cases
    max_iterations = 10
    for _ in range(max_iterations):
        new_text = re.sub(pattern, replace_var, text)
        if new_text == text:
            break
        text = new_text

    return text.replace('\\$', '$')


def _get_var_value(var_name: str) -> str:
    """Get variable value from local vars or environment."""
    if var_name in state.local_vars:
        return str(state.local_vars[var_name])
    return os.environ.get(var_name, "")


def _expand_arithmetic(text: str) -> str:
    """
    Expands arithmetic expressions: $((expression))
    Variables are expanded BEFORE evaluation.
    """
    pattern = r'\$\(\(([^)]+)\)\)'

    def replace_arith(match):
        expr = match.group(1)

        # CRITICAL: Expand variables BEFORE evaluation (including array access)
        expr = _expand_variables(expr)

        # ADDITIONAL: Expand bare array access like arr[0] (not ${arr[0]})
        # This pattern matches: word[number] or word[word]
        def expand_bare_array(m):
            arr_name = m.group(1)
            index_expr = m.group(2)

            # Expand any variables in the index
            index_expr = _expand_variables(index_expr)

            if arr_name in state.arrays:
                try:
                    idx = int(index_expr)
                    if 0 <= idx < len(state.arrays[arr_name]):
                        return state.arrays[arr_name][idx]
                except (ValueError, IndexError):
                    pass
            elif arr_name in state.assoc_arrays:
                return state.assoc_arrays[arr_name].get(index_expr, '0')

            return '0'

        expr = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]',
                      expand_bare_array, expr)

        try:
            result = _eval_arithmetic(expr)
            return str(result)
        except Exception as e:
            print(f"pyshell: arithmetic error: {e}", file=sys.stderr)
            return "0"

    return re.sub(pattern, replace_arith, text)


def _eval_arithmetic(expr: str) -> int:
    """
    Safely evaluates arithmetic expressions.
    Supports: +, -, *, /, %, **, //, &, |, ^, <<, >>, <, >, <=, >=, ==, !=
    """
    expr = expr.strip()

    if not expr:
        return 0

    # Replace any remaining variable names that look like identifiers with 0


    def replace_identifiers(match):
        var_name = match.group(0)
    
        # Check if this is array access: arr[0]
        # This would have been expanded earlier, but check for pattern
        if var_name in state.local_vars:
            return str(state.local_vars[var_name])
        if var_name in state.arrays and len(state.arrays[var_name]) > 0:
            return str(state.arrays[var_name][0])
        return '0'
    
    
    # Don't replace array access patterns like "arr[0]"
    # They should have been expanded by _expand_variables already
    expr = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b(?!\[)', replace_identifiers, expr)

    # Allow basic arithmetic operations
    allowed_chars = set('0123456789+-*/%() &|^<>=!')
    if not all(c in allowed_chars or c.isspace() for c in expr):
        raise ValueError(f"Invalid arithmetic expression: {expr}")

    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return int(result)
    except Exception as e:
        raise ValueError(f"Cannot evaluate: {expr}") from e


def _expand_command_substitution(text: str) -> str:
    """
    Expands command substitution: $(command) or `command`
    """
    def replace_dollar_paren(match):
        command = match.group(1)
        return _execute_command_substitution(command)

    def replace_backtick(match):
        command = match.group(1)
        return _execute_command_substitution(command)

    result = text
    pattern = r'\$\(([^)]+)\)'
    result = re.sub(pattern, replace_dollar_paren, result)

    pattern = r'`([^`]+)`'
    result = re.sub(pattern, replace_backtick, result)

    return result


def _execute_command_substitution(command: str) -> str:
    """
    Executes a command and returns its output.
    """
    try:
        from . import tokenizer, parser, executor

        tokens = tokenizer.tokenize(command)
        ast = parser.parse(tokens)

        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            executor.execute(ast)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        return output.rstrip('\n')

    except Exception as e:
        print(f"pyshell: command substitution error: {e}", file=sys.stderr)
        return ""


def expand_glob(parts: list) -> list:
    """
    Performs glob expansion (*, ?, []) on a list of command parts.
    """
    if not parts:
        return []

    out = [parts[0]]  # Command name is not globbed

    for arg in parts[1:]:
        arg = os.path.expanduser(arg)

        if any(c in arg for c in '*?['):
            matches = glob.glob(arg)
            if matches:
                out.extend(sorted(matches))
            else:
                out.append(arg)
        else:
            out.append(arg)

    return out
