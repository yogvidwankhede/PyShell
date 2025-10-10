import os
import sys
import subprocess
import shlex
import io
import re
from contextlib import contextmanager
import fnmatch

from . import state, builtins, expansions, utils
from .ast_nodes import (
    ASTNode, Script, Command, Pipeline, AndOr, If, While, Until, For, Select,
    Case, Block, Subshell, FunctionDef, ArrayAssignment, TestCommand, TryCatch
)
from .exceptions import ReturnFromFunction

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
main_script_path = os.path.join(project_root, 'main.py')


@contextmanager
def _apply_redirections(redirects: list):
    popen_kwargs = {}
    herestring_stream = None
    files_to_close = []

    try:
        for op, target in redirects:
            if op == '2>&1':
                popen_kwargs['stderr'] = subprocess.STDOUT
            elif op == '<<<':
                expanded_target = expansions.expand_all(target)
                herestring_stream = io.StringIO(expanded_target + '\n')
                popen_kwargs['stdin'] = herestring_stream
            elif op in ('>', '>>', '<', '2>', '2>>', '&>'):
                target = expansions.expand_all(target)
                if len(target) >= 2:
                    if (target[0] == "'" and target[-1] == "'"):
                        target = target[1:-1]
                    elif (target[0] == '"' and target[-1] == '"'):
                        target = target[1:-1]

                # Handle /dev/null on Windows
                if sys.platform == 'win32' and target in ('/dev/null', '\\dev\\null'):
                    target = 'NUL'

                if target != 'NUL':
                    target = os.path.normpath(target)
                    if not os.path.isabs(target):
                        target = os.path.abspath(target)

                if op == '>':
                    if state.option_noclobber and os.path.exists(target):
                        raise FileExistsError(
                            f"cannot overwrite existing file: {target}")
                    f = open(target, 'w')
                    popen_kwargs['stdout'] = f
                    files_to_close.append(f)
                elif op == '>>':
                    f = open(target, 'a')
                    popen_kwargs['stdout'] = f
                    files_to_close.append(f)
                elif op == '<':
                    f = open(target, 'r')
                    popen_kwargs['stdin'] = f
                    files_to_close.append(f)
                elif op == '2>':
                    f = open(target, 'w')
                    popen_kwargs['stderr'] = f
                    files_to_close.append(f)
                elif op == '2>>':
                    f = open(target, 'a')
                    popen_kwargs['stderr'] = f
                    files_to_close.append(f)
                elif op == '&>':
                    f = open(target, 'w')
                    popen_kwargs['stdout'] = f
                    popen_kwargs['stderr'] = f
                    files_to_close.append(f)

        yield popen_kwargs
    finally:
        if herestring_stream:
            herestring_stream.close()
        for f in files_to_close:
            f.close()


def _print_trace(node):
    """Print command trace for set -x."""
    try:
        if isinstance(node, Command):
            print(f"+ {' '.join(node.words)}", file=sys.stderr)
    except:
        pass


def execute(node: ASTNode) -> int:
    """Main execution dispatcher."""
    if state.option_xtrace:
        _print_trace(node)

    node_type = type(node)

    if node_type is Script:
        rc = 0
        for stmt in node.stmts:
            rc = execute(stmt)
            state.last_exit_status = rc

            if state.break_loop or state.continue_loop:
                break

            if state.option_errexit and rc != 0:
                if not isinstance(stmt, (If, While, Until)):
                    sys.exit(rc)

        return rc

    if node_type is Command:
        return _execute_command_node(node)

    if node_type is ArrayAssignment:
        return _execute_array_assignment(node)

    if node_type is TestCommand:
        return _execute_test_command(node)

    if node_type is Pipeline:
        return _execute_pipeline(node)

    if node_type is AndOr:
        left_rc = execute(node.left)
        state.last_exit_status = left_rc

        if node.op == '&&' and left_rc == 0:
            right_rc = execute(node.right)
            state.last_exit_status = right_rc
            return right_rc
        elif node.op == '||' and left_rc != 0:
            right_rc = execute(node.right)
            state.last_exit_status = right_rc
            return right_rc

        return left_rc

    if node_type is If:
        saved_errexit = state.option_errexit
        state.option_errexit = False

        cond_rc = execute(node.cond)

        state.option_errexit = saved_errexit

        if cond_rc == 0:
            return execute(node.then_body)
        elif node.else_body:
            return execute(node.else_body)
        return 0

    if node_type is While:
        rc = 0
        while True:
            if state.break_loop:
                state.break_levels -= 1
                if state.break_levels <= 0:
                    state.break_loop = False
                break

            cond_rc = execute(node.cond)
            if cond_rc != 0:
                break

            rc = execute(node.body)

            if state.continue_loop:
                state.continue_levels -= 1
                if state.continue_levels <= 0:
                    state.continue_loop = False
                continue

            if state.break_loop:
                break

        return rc

    if node_type is Until:
        rc = 0
        while True:
            if state.break_loop:
                state.break_levels -= 1
                if state.break_levels <= 0:
                    state.break_loop = False
                break

            cond_rc = execute(node.cond)
            if cond_rc == 0:
                break

            rc = execute(node.body)

            if state.continue_loop:
                state.continue_levels -= 1
                if state.continue_levels <= 0:
                    state.continue_loop = False
                continue

            if state.break_loop:
                break

        return rc

    if node_type is For:
        rc = 0

        expanded_items = []
        for item in node.items:
            expanded_item = expansions.expand_all(item)
            expanded_items.append(expanded_item)

        items_str = " ".join(expanded_items)

        if not state.option_noglob:
            try:
                words = shlex.split(items_str)
            except ValueError:
                words = items_str.split()

            import glob as glob_module
            final_items = []
            for word in words:
                if any(c in word for c in '*?['):
                    matches = glob_module.glob(word)
                    if matches:
                        final_items.extend(sorted(matches))
                    else:
                        final_items.append(word)
                else:
                    final_items.append(word)
            items = final_items
        else:
            items = items_str.split()

        original_value = state.local_vars.get(node.var)

        for item in items:
            if state.break_loop:
                state.break_levels -= 1
                if state.break_levels <= 0:
                    state.break_loop = False
                break

            state.local_vars[node.var] = item
            rc = execute(node.body)

            if state.continue_loop:
                state.continue_levels -= 1
                if state.continue_levels <= 0:
                    state.continue_loop = False
                continue

            if state.break_loop:
                state.break_levels -= 1
                if state.break_levels <= 0:
                    state.break_loop = False
                break

        if original_value is not None:
            state.local_vars[node.var] = original_value
        else:
            state.local_vars.pop(node.var, None)

        return rc

    if node_type is Select:
        return _execute_select(node)

    if node_type is Case:
        expr_value = expansions.expand_all(node.expr)
        rc = 0

        for patterns, body in node.clauses:
            for pattern in patterns:
                expanded_pattern = expansions.expand_all(pattern)
                if fnmatch.fnmatch(expr_value, expanded_pattern):
                    rc = execute(body)
                    return rc

        return rc

    if node_type is FunctionDef:
        state.functions[node.name] = node.body
        return 0

    if node_type is Block:
        return execute(node.body)

    if node_type is Subshell:
        state.subshell_depth += 1
        rc = execute(node.body)
        state.subshell_depth -= 1
        return rc

    return 0


def _execute_test_command(node: TestCommand) -> int:
    """Execute [[ ... ]] test command with advanced features"""
    expr = node.expr

    if not expr:
        return 1

    # Handle negation
    if expr[0] == '!':
        result = _execute_test_command(TestCommand(expr[1:]))
        return 0 if result != 0 else 1

    # Single expression
    if len(expr) == 1:
        # Expand and check if non-empty
        value = expansions.expand_all(expr[0])
        return 0 if value else 1

    # Binary operators
    if len(expr) == 3:
        left = expansions.expand_all(expr[0])
        op = expr[1]
        right = expansions.expand_all(expr[2])

        # String comparison
        if op == '=' or op == '==':
            return 0 if left == right else 1
        if op == '!=':
            return 0 if left != right else 1

        # Pattern matching
        if op == '=~':
            # Regex matching
            try:
                import re
                match = re.search(right, left)
                if match:
                    # Store match groups
                    state.BASH_REMATCH = [
                        match.group(0)] + list(match.groups())
                    state.regex_match_groups = state.BASH_REMATCH[:]
                    return 0
                else:
                    state.BASH_REMATCH = []
                    state.regex_match_groups = []
                    return 1
            except re.error:
                return 2

        # Numeric comparison
        try:
            if op == '-eq':
                return 0 if int(left) == int(right) else 1
            if op == '-ne':
                return 0 if int(left) != int(right) else 1
            if op == '-lt':
                return 0 if int(left) < int(right) else 1
            if op == '-le':
                return 0 if int(left) <= int(right) else 1
            if op == '-gt':
                return 0 if int(left) > int(right) else 1
            if op == '-ge':
                return 0 if int(left) >= int(right) else 1
        except ValueError:
            return 2

    # Unary file test operators
    if len(expr) == 2:
        op, arg = expr
        arg = expansions.expand_all(arg)

        if op == '-f':
            return 0 if os.path.isfile(arg) else 1
        if op == '-d':
            return 0 if os.path.isdir(arg) else 1
        if op == '-e':
            return 0 if os.path.exists(arg) else 1
        if op == '-z':
            return 0 if not arg else 1
        if op == '-n':
            return 0 if arg else 1

    # Complex expressions with && and ||
    if '&&' in expr:
        idx = expr.index('&&')
        left_result = _execute_test_command(TestCommand(expr[:idx]))
        right_result = _execute_test_command(TestCommand(expr[idx+1:]))
        return 0 if (left_result == 0 and right_result == 0) else 1

    if '||' in expr:
        idx = expr.index('||')
        left_result = _execute_test_command(TestCommand(expr[:idx]))
        right_result = _execute_test_command(TestCommand(expr[idx+1:]))
        return 0 if (left_result == 0 or right_result == 0) else 1

    return 1


def _execute_select(node: Select) -> int:
    """Execute select menu"""
    # Expand items
    expanded_items = []
    for item in node.items:
        expanded = expansions.expand_all(item)
        expanded_items.extend(shlex.split(expanded))

    # Display menu
    print(f"{state.PS3}", end='', file=sys.stderr)
    for i, item in enumerate(expanded_items, 1):
        print(f"{i}) {item}", file=sys.stderr)

    # Read selection
    try:
        selection = input(f"{state.PS3}")
        idx = int(selection) - 1
        if 0 <= idx < len(expanded_items):
            state.local_vars[node.var] = expanded_items[idx]
            return execute(node.body)
    except (ValueError, EOFError, KeyboardInterrupt):
        pass

    return 1


def _execute_command_node(node: Command, stdin=None, stdout=None, stderr=None) -> int:
    """Executes a single command, handling assignments, expansions, and redirections."""
    assignments = {}
    words = []
    is_assignment_block = True

    # SPECIAL CASE: Check if this is a builtin command with array assignment
    # Pattern: local arr=(a b c) or declare arr=(x y z)
    # This gets tokenized as: ["local", "arr=(a", "b", "c);"] or similar
    if node.words and len(node.words) > 1 and node.words[0] in ('local', 'declare', 'typeset', 'readonly'):
        # print(f"DEBUG: node.words = {node.words}", file=sys.stderr)
        # print(f"DEBUG: has_array = {any('=(' in word for word in node.words[1:])}", file=sys.stderr)
        # Check if any word after the command contains "=("
        has_array_assignment = any('=(' in word for word in node.words[1:])

        if has_array_assignment:
            # Reconstruct array assignments
            reconstructed_args = []
            i = 1  # Start from index 1, skip the command name

            while i < len(node.words):
                word = node.words[i]

                # Check if this word contains "=(" - potential array assignment start
                if '=(' in word:
                    # Collect all words until we find one ending with ")"
                    array_parts = [word]

                    # If this word already ends with ), we're done
                    if word.endswith(')') or word.endswith(');'):
                        # Remove trailing semicolon if present
                        if word.endswith(');'):
                            array_parts[0] = word[:-1]
                        reconstructed_args.append(array_parts[0])
                        i += 1
                        continue

                    # Otherwise, keep collecting
                    i += 1
                    while i < len(node.words):
                        current_word = node.words[i]

                        # Remove trailing semicolon if present
                        if current_word.endswith(');'):
                            # Has both ) and ; - remove the semicolon
                            array_parts.append(current_word[:-1])
                            i += 1
                            break
                        elif current_word.endswith(')'):
                            # Just closing paren
                            array_parts.append(current_word)
                            i += 1
                            break
                        elif current_word.endswith(';'):
                            # Semicolon but no closing paren - this shouldn't happen in valid syntax
                            # but handle it anyway
                            array_parts.append(current_word[:-1])
                            i += 1
                            break
                        else:
                            # Regular array element
                            array_parts.append(current_word)
                            i += 1

                    # Reconstruct the full array assignment
                    full_array_arg = ' '.join(array_parts)
                    reconstructed_args.append(full_array_arg)
                else:
                    # Regular argument (not part of array assignment)
                    reconstructed_args.append(word)
                    i += 1

            # Now execute the builtin with reconstructed args
            cmd_name = node.words[0]
            args = reconstructed_args

            current_stdin = stdin or sys.stdin
            current_stdout = stdout or sys.stdout
            current_stderr = stderr or sys.stderr

            if current_stderr == subprocess.STDOUT:
                current_stderr = current_stdout

            try:
                return builtins.execute_builtin(cmd_name, args, stdin=current_stdin,
                                                stdout=current_stdout, stderr=current_stderr)
            except ReturnFromFunction as e:
                if state.function_nesting > 0:
                    raise
                print("pyshell: return: can only return from a function",
                      file=sys.stderr)
                return 1

    for word in node.words:
        if '=' in word and is_assignment_block and not word.startswith('='):
            # Check for array element assignment FIRST: arr[1]=value
            array_match = re.match(
                r'^([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]=(.*)', word, re.DOTALL)
            if array_match:
                array_name = array_match.group(1)
                index = array_match.group(2)
                raw_value = array_match.group(3)

                if array_name in state.readonly_vars:
                    print(
                        f"pyshell: {array_name}: readonly variable", file=sys.stderr)
                    return 1

                value = expansions.expand_all(raw_value)
                index = expansions.expand_all(index)

                # Remove quotes from value if present
                if len(value) >= 2:
                    if (value[0] == "'" and value[-1] == "'") or (value[0] == '"' and value[-1] == '"'):
                        value = value[1:-1]

                # Try as indexed array first
                try:
                    idx = int(index)
                    if array_name not in state.arrays:
                        state.arrays[array_name] = []
                    while len(state.arrays[array_name]) <= idx:
                        state.arrays[array_name].append('')
                    state.arrays[array_name][idx] = value
                except ValueError:
                    # Associative array
                    if array_name not in state.assoc_arrays:
                        state.assoc_arrays[array_name] = {}
                    state.assoc_arrays[array_name][index] = value

                continue

            # Regular variable assignment
            match = re.match(
                r'^([a-zA-Z_][a-zA-Z_0-9]*)=(.*)', word, re.DOTALL)
            if match:
                var_name = match.group(1)

                if var_name in state.readonly_vars:
                    print(
                        f"pyshell: {var_name}: readonly variable", file=sys.stderr)
                    return 1

                raw_value = match.group(2)
                value = expansions.expand_all(raw_value)

                if len(value) >= 2:
                    if (value[0] == "'" and value[-1] == "'"):
                        value = value[1:-1]
                    elif (value[0] == '"' and value[-1] == '"'):
                        value = value[1:-1]

                assignments[var_name] = value
            else:
                is_assignment_block = False
                words.append(word)
        else:
            is_assignment_block = False
            words.append(word)

    for var, value in assignments.items():
        # Check if it's an array element assignment: arr[0]=value
        array_elem_match = re.match(
            r'^([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]$', var)
        if array_elem_match:
            array_name = array_elem_match.group(1)
            index = array_elem_match.group(2)

            # Handle indexed array
            if array_name in state.arrays or array_name not in state.assoc_arrays:
                try:
                    idx = int(index)
                    if array_name not in state.arrays:
                        state.arrays[array_name] = []
                    # Extend array if needed
                    while len(state.arrays[array_name]) <= idx:
                        state.arrays[array_name].append('')
                    state.arrays[array_name][idx] = value
                except ValueError:
                    # If index is not a number, treat as associative array
                    if array_name not in state.assoc_arrays:
                        state.assoc_arrays[array_name] = {}
                    state.assoc_arrays[array_name][index] = value
            else:
                # Associative array
                if array_name not in state.assoc_arrays:
                    state.assoc_arrays[array_name] = {}
                state.assoc_arrays[array_name][index] = value
        else:
            # Regular variable assignment
            state.local_vars[var] = value
            if var in state.exported_vars:
                os.environ[var] = value

    if not words:
        return 0

    # Check for alias expansion BEFORE other expansions
    if words[0] in state.aliases:
        alias_value = state.aliases[words[0]]
        alias_words = shlex.split(alias_value)
        words = alias_words + words[1:]

    # Now expand all the words
    with _apply_redirections(node.redirects) as popen_kwargs:
        expanded_line = expansions.expand_all(" ".join(words))

        try:
            # On Windows, escape backslashes to prevent shlex from treating them as escapes
            if sys.platform == 'win32':
                expanded_line = expanded_line.replace('\\', '\\\\')

            expanded_words = shlex.split(expanded_line)
            if not expanded_words:
                return 0
        except ValueError as e:
            print(f"shell: parse error: {e}", file=sys.stderr)
            return 1

        if not state.option_noglob:
            final_words = expansions.expand_glob(expanded_words)
        else:
            final_words = expanded_words

        cmd_name, args = final_words[0], final_words[1:]

        if args:
            state.last_arg = args[-1]
        else:
            state.last_arg = cmd_name

        # Check if it's a function
        if cmd_name in state.functions:
            return _execute_function(cmd_name, args)

        current_stdin = stdin or popen_kwargs.get('stdin') or sys.stdin
        current_stdout = stdout or popen_kwargs.get('stdout') or sys.stdout
        current_stderr = stderr or popen_kwargs.get('stderr') or sys.stderr

        if cmd_name in builtins.BUILTIN_COMMANDS:
            if node.background:
                proc_args = [sys.executable, main_script_path,
                             '--run-builtin', cmd_name] + args
                p = subprocess.Popen(proc_args)
                jid = state.next_job_id
                state.next_job_id += 1
                state.running_jobs.append(
                    (jid, p, " ".join(words), state.JOB_STATUS_RUNNING))
                state.last_background_pid = p.pid
                print(f"[{jid}] {p.pid}")
                return 0
            else:
                if current_stderr == subprocess.STDOUT:
                    current_stderr = current_stdout

                try:
                    return builtins.execute_builtin(cmd_name, args, stdin=current_stdin,
                                                    stdout=current_stdout, stderr=current_stderr)
                except ReturnFromFunction as e:
                    if state.function_nesting > 0:
                        raise
                    print(
                        "pyshell: return: can only return from a function", file=sys.stderr)
                    return 1

        executable = utils.find_executable(cmd_name)
        if not executable:
            print(f"shell: command not found: {cmd_name}", file=sys.stderr)
            return 127

        try:
            is_test_env = not sys.stdout.isatty()
            stderr_to_stdout = (current_stderr == subprocess.STDOUT)

            if is_test_env:
                final_stdout = subprocess.PIPE
                final_stderr = subprocess.STDOUT if stderr_to_stdout else subprocess.PIPE

                try:
                    if current_stdin != sys.stdin and hasattr(current_stdin, 'fileno'):
                        current_stdin.fileno()
                        final_stdin = current_stdin
                    else:
                        final_stdin = None
                except (AttributeError, io.UnsupportedOperation):
                    final_stdin = None
            else:
                final_stdout = current_stdout
                final_stderr = current_stderr
                final_stdin = current_stdin

            env = os.environ.copy()
            for var in state.exported_vars:
                if var in state.local_vars:
                    env[var] = str(state.local_vars[var])

            proc = subprocess.Popen(
                [executable] + args,
                stdin=final_stdin,
                stdout=final_stdout,
                stderr=final_stderr,
                env=env
            )

            if node.background:
                jid = state.next_job_id
                state.next_job_id += 1
                state.running_jobs.append(
                    (jid, proc, " ".join(words), state.JOB_STATUS_RUNNING))
                state.last_background_pid = proc.pid
                print(f"[{jid}] {proc.pid}")
                return 0

            if is_test_env:
                stdout_data, stderr_data = proc.communicate()
                if stdout_data:
                    sys.stdout.write(stdout_data.decode())
                if stderr_data and not stderr_to_stdout:
                    sys.stderr.write(stderr_data.decode())
                return proc.returncode
            else:
                state.current_foreground_proc = proc
                rc = proc.wait()
                state.current_foreground_proc = None
                return rc

        except FileExistsError as e:
            print(f"shell: {e}", file=sys.stderr)
            return 1
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(
                f"shell: execution error for '{cmd_name}': {e}", file=sys.stderr)
            return 1


def _execute_array_assignment(node: ArrayAssignment) -> int:
    """Execute array assignment: arr=(val1 val2 val3)"""
    # Expand all values
    expanded_values = []
    for val in node.values:
        # Check if value is quoted
        is_quoted = (val.startswith('"') and val.endswith('"') and len(val) >= 2) or \
            (val.startswith("'") and val.endswith("'") and len(val) >= 2)

        if is_quoted:
            # Remove quotes first, then expand (for double quotes) or use as-is (for single quotes)
            if val.startswith('"'):
                # Double quotes - expand variables
                inner_val = val[1:-1]
                expanded = expansions.expand_all(inner_val)
                expanded_values.append(expanded)
            else:
                # Single quotes - no expansion
                expanded_values.append(val[1:-1])
        else:
            # Not quoted - expand and potentially split
            expanded = expansions.expand_all(val)

            # Split on whitespace if expanded from command substitution or other expansions
            # But only if the original value suggested it might expand
            if '$' in val or '`' in val:
                try:
                    import shlex
                    split_vals = shlex.split(expanded)
                    expanded_values.extend(split_vals)
                except:
                    expanded_values.append(expanded)
            else:
                expanded_values.append(expanded)

    if node.is_append:
        # Append to existing array
        if node.name in state.arrays:
            state.arrays[node.name].extend(expanded_values)
        else:
            state.arrays[node.name] = expanded_values
    else:
        # Create new array
        state.arrays[node.name] = expanded_values

    # Mark as declared
    state.declared_arrays[node.name] = 'indexed'

    return 0


def _execute_function(name: str, args: list) -> int:
    """Execute a shell function."""
    saved_params = state.positional_params[:]
    saved_nesting = state.function_nesting

    if not hasattr(state, 'local_scope_stack'):
        state.local_scope_stack = []

    state.local_scope_stack.append({})

    state.positional_params = args
    state.function_nesting += 1

    try:
        body = state.functions[name]
        rc = execute(body)
        return rc
    except ReturnFromFunction as e:
        return e.code
    finally:
        if state.local_scope_stack:
            local_scope = state.local_scope_stack.pop()
            for var, old_value in local_scope.items():
                # Handle array restoration
                if var.startswith('__array_'):
                    array_name = var[8:]  # Remove '__array_' prefix
                    if old_value is None:
                        state.arrays.pop(array_name, None)
                        state.declared_arrays.pop(array_name, None)
                    else:
                        state.arrays[array_name] = old_value
                elif old_value is None:
                    state.local_vars.pop(var, None)
                else:
                    state.local_vars[var] = old_value

        state.positional_params = saved_params
        state.function_nesting = saved_nesting


def _execute_pipeline(node: Pipeline) -> int:
    """Execute a pipeline with proper handling of builtins and external commands."""
    if len(node.commands) == 1:
        return execute(node.commands[0])

    processes = []

    try:
        # First pass: check if first command is a builtin that we can execute in-memory
        first_cmd = node.commands[0]
        if isinstance(first_cmd, Command):
            expanded_line = expansions.expand_all(" ".join(first_cmd.words))
            first_words = shlex.split(expanded_line)
            first_cmd_name = first_words[0] if first_words else ""

            # If first command is echo (or other simple builtin), execute it to get output
            if first_cmd_name == "echo" and len(node.commands) > 1:
                # Execute echo to string
                import io
                echo_output = io.StringIO()
                echo_args = first_words[1:]
                builtins.execute_builtin("echo", echo_args, stdin=sys.stdin,
                                         stdout=echo_output, stderr=sys.stderr)
                initial_input = echo_output.getvalue()

                # Now execute remaining commands with this as input
                stdin_data = initial_input.encode() if initial_input else b''

                for i, cmd in enumerate(node.commands[1:], start=1):
                    is_last = (i == len(node.commands) - 1)

                    if isinstance(cmd, Command):
                        expanded_line = expansions.expand_all(
                            " ".join(cmd.words))
                        expanded_words = shlex.split(expanded_line)
                        cmd_name = expanded_words[0] if expanded_words else ""
                        args = expanded_words[1:] if len(
                            expanded_words) > 1 else []

                        if is_last:
                            stdout = None
                        else:
                            stdout = subprocess.PIPE

                        env = os.environ.copy()
                        for var in state.exported_vars:
                            if var in state.local_vars:
                                env[var] = str(state.local_vars[var])

                        if cmd_name in builtins.BUILTIN_COMMANDS:
                            proc_args = [sys.executable, main_script_path,
                                         '--run-builtin', cmd_name] + args
                            proc = subprocess.Popen(proc_args, stdin=subprocess.PIPE,
                                                    stdout=stdout, stderr=sys.stderr, env=env)
                        else:
                            executable = utils.find_executable(cmd_name)
                            if not executable:
                                print(
                                    f"shell: command not found: {cmd_name}", file=sys.stderr)
                                return 127
                            proc = subprocess.Popen([executable] + args, stdin=subprocess.PIPE,
                                                    stdout=stdout, stderr=sys.stderr, env=env)

                        # Send input and get output
                        if is_last:
                            proc.communicate(stdin_data)
                            return proc.returncode
                        else:
                            stdin_data, _ = proc.communicate(stdin_data)

                return 0

        # Default pipeline execution for other cases
        for i, cmd in enumerate(node.commands):
            is_first = (i == 0)
            is_last = (i == len(node.commands) - 1)

            if isinstance(cmd, Command):
                expanded_line = expansions.expand_all(" ".join(cmd.words))
                expanded_words = shlex.split(expanded_line)
                cmd_name = expanded_words[0] if expanded_words else ""
                args = expanded_words[1:] if len(expanded_words) > 1 else []

                if is_first:
                    stdin = None
                else:
                    stdin = processes[-1].stdout

                if is_last:
                    stdout = None
                else:
                    stdout = subprocess.PIPE

                env = os.environ.copy()
                for var in state.exported_vars:
                    if var in state.local_vars:
                        env[var] = str(state.local_vars[var])

                if cmd_name in builtins.BUILTIN_COMMANDS:
                    proc_args = [sys.executable, main_script_path,
                                 '--run-builtin', cmd_name] + args
                    proc = subprocess.Popen(proc_args, stdin=stdin, stdout=stdout,
                                            stderr=sys.stderr, env=env)
                else:
                    executable = utils.find_executable(cmd_name)
                    if not executable:
                        print(
                            f"shell: command not found: {cmd_name}", file=sys.stderr)
                        return 127
                    proc = subprocess.Popen([executable] + args, stdin=stdin,
                                            stdout=stdout, stderr=sys.stderr, env=env)

                processes.append(proc)

                if len(processes) > 1 and processes[-2].stdout:
                    processes[-2].stdout.close()

        rc = 0
        for proc in processes:
            proc_rc = proc.wait()
            rc = proc_rc

        if state.option_pipefail:
            for proc in processes:
                if proc.returncode != 0:
                    return proc.returncode

        return rc

    except Exception as e:
        print(f"shell: pipeline error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
