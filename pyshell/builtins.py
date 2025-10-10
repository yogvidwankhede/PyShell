import os
import sys
import time
import re
from . import state
from .exceptions import ReturnFromFunction

BUILTIN_COMMANDS = [
    'echo', 'exit', 'type', 'pwd', 'cd', 'history', 'clear', 'wc', 'sleep',
    'jobs', 'fg', 'bg', 'ls', 'date', 'alias', 'export', 'unset', 'cat',
    'true', 'false', 'test', '[', 'rm', 'local', 'return', 'source', '.',
    'read', 'printf', 'eval', 'exec', 'shift', 'set', 'declare', 'typeset',
    'let', 'break', 'continue', 'trap', 'wait', 'kill', 'pushd', 'popd',
    'dirs', 'getopts', 'ulimit', 'umask', 'readonly', 'unalias', 'enable',
    'shopt', 'times', 'hash', 'help', 'mapfile', 'readarray', 'complete', 'bind',
    'grep', 'head', 'tail', 'sort', 'uniq', 'cut', 'tr', 'tee'
]


def execute_builtin(name, args, stdin=None, stdout=None, stderr=None):
    """Executes a built-in command, handling I/O redirection."""
    original_stdin, original_stdout, original_stderr = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = stdin or sys.stdin
    sys.stdout = stdout or sys.stdout
    sys.stderr = stderr or sys.stderr

    try:
        if name == "true":
            return 0
        if name == "false":
            return 1

        if name == "echo":
            n_flag = False
            e_flag = False
            start_idx = 0

            for i, arg in enumerate(args):
                if arg == '-n':
                    n_flag = True
                    start_idx = i + 1
                elif arg == '-e':
                    e_flag = True
                    start_idx = i + 1
                elif arg == '-ne' or arg == '-en':
                    n_flag = True
                    e_flag = True
                    start_idx = i + 1
                else:
                    break

            output = " ".join(args[start_idx:])

            if e_flag:
                output = output.replace('\\n', '\n')
                output = output.replace('\\t', '\t')
                output = output.replace('\\r', '\r')
                output = output.replace('\\\\', '\\')

            if n_flag:
                sys.stdout.write(output)
            else:
                sys.stdout.write(output + "\n")
            return 0

        if name == "clear":
            return _builtin_clear(args)

        if name == "ls":
            return _builtin_ls(args)

        if name == "date":
            return _builtin_date(args)

        if name == "rm":
            return _builtin_rm(args)

        if name == "help":
            return _builtin_help(args)

        if name == "hash":
            return _builtin_hash(args)

        if name == "exec":
            return _builtin_exec(args)

        if name == "head":
            return _builtin_head(args)

        if name == "tail":
            return _builtin_tail(args)

        if name == "sort":
            return _builtin_sort(args)

        if name == "uniq":
            return _builtin_uniq(args)

        if name == "wc":
            return _builtin_wc(args)

        if name == "grep":
            return _builtin_grep(args)

        if name == "exit":
            code = int(args[0]) if args else state.last_exit_status
            sys.exit(code)

        if name == "pwd":
            current_dir = os.getcwd().replace('\\', '/')

            # On Windows, show /tmp for the temp directory (for compatibility)
            if sys.platform == 'win32':
                temp_dir = os.environ.get('TEMP', '').replace('\\', '/')
                if current_dir == temp_dir:
                    current_dir = '/tmp'
                elif current_dir == 'C:/':
                    current_dir = '/'

            sys.stdout.write(current_dir + "\n")
            return 0

        if name == "cd":
            if not args:
                target = os.environ.get('HOME', '/')
            elif args[0] == '-':
                target = state.previous_dir
                if not target:
                    sys.stderr.write("cd: OLDPWD not set\n")
                    return 1
                sys.stdout.write(target + "\n")
            else:
                target = os.path.expanduser(args[0])

                # Handle Unix paths on Windows
                if sys.platform == 'win32':
                    if target == '/tmp':
                        target = os.environ.get('TEMP', 'C:\\Windows\\Temp')
                    elif target == '/':
                        target = 'C:\\'

            try:
                prev = os.getcwd()
                os.chdir(target)
                state.previous_dir = prev
                os.environ['PWD'] = os.getcwd()
                os.environ['OLDPWD'] = prev
                return 0
            except FileNotFoundError:
                sys.stderr.write(f"cd: {args[0]}: No such file or directory\n")
                return 1
            except PermissionError:
                sys.stderr.write(f"cd: {args[0]}: Permission denied\n")
                return 1
            except Exception as e:
                sys.stderr.write(f"cd: {args[0]}: {e}\n")
                return 1

        if name == "cat":
            if not args:
                try:
                    content = sys.stdin.read()
                    sys.stdout.write(content)
                    return 0
                except Exception as e:
                    sys.stderr.write(f"cat: error reading stdin: {e}\n")
                    return 1

            for filename in args:
                try:
                    with open(filename, 'r') as f:
                        sys.stdout.write(f.read())
                except FileNotFoundError:
                    sys.stderr.write(
                        f"cat: {filename}: No such file or directory\n")
                    return 1
                except PermissionError:
                    sys.stderr.write(f"cat: {filename}: Permission denied\n")
                    return 1
            return 0

        if name == "sleep":
            if not args:
                sys.stderr.write("sleep: missing operand\n")
                return 1
            try:
                time.sleep(float(args[0]))
                return 0
            except ValueError:
                sys.stderr.write(f"sleep: invalid time interval '{args[0]}'\n")
                return 1

        if name == "test" or name == "[":
            if name == "[":
                if not args or args[-1] != ']':
                    sys.stderr.write("[: missing closing ']'\n")
                    return 2
                args = args[:-1]
            return _builtin_test(args)

        if name == "read":
            return _builtin_read(args)

        if name == "printf":
            return _builtin_printf(args)

        if name == "export":
            return _builtin_export(args)

        if name == "unset":
            return _builtin_unset(args)

        if name == "local":
            return _builtin_local(args)

        if name == "readonly":
            return _builtin_readonly(args)

        if name == "shift":
            return _builtin_shift(args)

        if name == "set":
            return _builtin_set(args)

        if name in ["declare", "typeset"]:
            return _builtin_declare(args)

        if name == "let":
            return _builtin_let(args)

        if name == "return":
            code = int(args[0]) if args else state.last_exit_status
            raise ReturnFromFunction(code)

        if name == "break":
            levels = int(args[0]) if args else 1
            state.break_loop = True
            state.break_levels = levels
            return 0

        if name == "continue":
            levels = int(args[0]) if args else 1
            state.continue_loop = True
            state.continue_levels = levels
            return 0

        if name == "alias":
            return _builtin_alias(args)

        if name == "unalias":
            return _builtin_unalias(args)

        if name == "pushd":
            return _builtin_pushd(args)

        if name == "popd":
            return _builtin_popd(args)

        if name == "dirs":
            return _builtin_dirs(args)

        if name in ["source", "."]:
            return _builtin_source(args)

        if name == "eval":
            return _builtin_eval(args)

        if name == "wait":
            return _builtin_wait(args)

        if name == "type":
            return _builtin_type(args)

        if name == "trap":
            return _builtin_trap(args)

        if name in BUILTIN_COMMANDS:
            sys.stderr.write(f"Built-in '{name}' not fully implemented.\n")
            return 1

        return 1
    finally:
        sys.stdin, sys.stdout, sys.stderr = original_stdin, original_stdout, original_stderr


def _builtin_test(args):
    """Implements the test/[ command."""
    if not args:
        return 1

    # Handle negation
    if args[0] == '!':
        result = _builtin_test(args[1:])
        return 0 if result != 0 else 1

    if len(args) == 1:
        # [ string ] - true if string is not empty
        # Handle empty string case
        return 0 if args[0] and args[0] != '' else 1

    if len(args) == 2:
        op, arg = args

        if op == '-f':
            # Test if file exists - use the path exactly as provided
            # On Windows, this might have backslashes or forward slashes
            try:
                result = os.path.isfile(arg)
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-d':
            # Handle Unix paths on Windows
            if sys.platform == 'win32':
                if arg == '/tmp':
                    arg = os.environ.get('TEMP', 'C:\\Windows\\Temp')
                elif arg == '/':
                    arg = 'C:\\'

            try:
                result = os.path.isdir(arg)
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-e':
            try:
                result = os.path.exists(arg)
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-r':
            try:
                result = os.access(arg, os.R_OK)
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-w':
            try:
                result = os.access(arg, os.W_OK)
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-x':
            try:
                result = os.access(arg, os.X_OK)
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-s':
            try:
                result = os.path.exists(arg) and os.path.getsize(arg) > 0
                return 0 if result else 1
            except Exception:
                return 1
        if op == '-z':
            # FIXED: empty string check - return 0 (true) if string is empty
            return 0 if (not arg or arg == '' or arg == '""' or arg == "''") else 1
        if op == '-n':
            return 0 if (arg and arg != '' and arg != '""' and arg != "''") else 1

    if len(args) == 3:
        left, op, right = args
        if op == '==' or op == '=':
            return 0 if left == right else 1
        if op == '!=':
            return 0 if left != right else 1
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

    if len(args) >= 3:
        if '-a' in args:
            idx = args.index('-a')
            left_result = _builtin_test(args[:idx])
            right_result = _builtin_test(args[idx+1:])
            return 0 if (left_result == 0 and right_result == 0) else 1
        if '-o' in args:
            idx = args.index('-o')
            left_result = _builtin_test(args[:idx])
            right_result = _builtin_test(args[idx+1:])
            return 0 if (left_result == 0 or right_result == 0) else 1

    return 1


def _builtin_read(args):
    """Read input into variables."""
    try:
        line = sys.stdin.readline()
        if not line:
            return 1

        line = line.rstrip('\n')

        if not args:
            state.local_vars['REPLY'] = line
            return 0

        words = line.split()
        for i, var in enumerate(args):
            if i < len(words):
                if i == len(args) - 1:
                    state.local_vars[var] = ' '.join(words[i:])
                else:
                    state.local_vars[var] = words[i]
            else:
                state.local_vars[var] = ''

        return 0
    except EOFError:
        return 1


def _builtin_printf(args):
    """Printf command."""
    if not args:
        return 0

    fmt = args[0]
    values = args[1:]

    fmt = fmt.replace('\\n', '\n')
    fmt = fmt.replace('\\t', '\t')
    fmt = fmt.replace('\\r', '\r')
    fmt = fmt.replace('\\\\', '\\')

    try:
        if values:
            sys.stdout.write(fmt % tuple(values))
        else:
            sys.stdout.write(fmt)
        return 0
    except Exception as e:
        sys.stderr.write(f"printf: {e}\n")
        return 1


def _builtin_export(args):
    """Export variables to environment."""
    if not args:
        for var in state.exported_vars:
            value = state.local_vars.get(var, os.environ.get(var, ''))
            sys.stdout.write(f"declare -x {var}=\"{value}\"\n")
        return 0

    for arg in args:
        if '=' in arg:
            var, value = arg.split('=', 1)
            state.local_vars[var] = value
            os.environ[var] = value
            state.exported_vars.add(var)
        else:
            if arg in state.local_vars:
                os.environ[arg] = str(state.local_vars[arg])
            state.exported_vars.add(arg)

    return 0


def _builtin_unset(args):
    """Unset variables or functions."""
    for var in args:
        if var in state.readonly_vars:
            sys.stderr.write(
                f"unset: {var}: cannot unset: readonly variable\n")
            return 1

        state.local_vars.pop(var, None)
        os.environ.pop(var, None)
        state.exported_vars.discard(var)
        state.functions.pop(var, None)

    return 0


def _builtin_local(args):
    """Declare local variables (function scope)."""
    if state.function_nesting == 0:
        sys.stderr.write("local: can only be used in a function\n")
        return 1

    if not hasattr(state, 'local_scope_stack'):
        state.local_scope_stack = []

    # Check if this is an array assignment by parsing the full command
    # Join args to detect patterns like: arr=(val1 val2 val3)
    full_arg = ' '.join(args)

    # Try to detect array assignment pattern: name=(...)
    import re
    array_pattern = r'^([a-zA-Z_][a-zA-Z0-9_]*)(\+)?=\((.*?)\)$'
    array_match = re.match(array_pattern, full_arg, re.DOTALL)

    if array_match:
        # This is an array assignment
        var_name = array_match.group(1)
        is_append = (array_match.group(2) == '+')
        values_str = array_match.group(3) if array_match.group(3) else ''

        # Save old array in scope if it exists
        if len(state.local_scope_stack) > 0:
            if var_name not in state.local_scope_stack[-1]:
                if var_name in state.arrays:
                    state.local_scope_stack[-1][f"__array_{var_name}"] = state.arrays[var_name][:]
                else:
                    state.local_scope_stack[-1][f"__array_{var_name}"] = None

        # Parse values - use shlex to properly handle quoted strings
        import shlex
        try:
            values = shlex.split(values_str) if values_str.strip() else []
        except ValueError:
            # If shlex fails, fall back to simple split
            values = values_str.split() if values_str.strip() else []

        if is_append and var_name in state.arrays:
            state.arrays[var_name].extend(values)
        else:
            state.arrays[var_name] = values
            state.declared_arrays[var_name] = 'indexed'

        return 0

    # Regular variable handling for non-array assignments
    for arg in args:
        # Handle array assignment: arr=(val1 val2 val3) or arr+=(val1 val2)
        # Match pattern: name=(stuff) or name+=(stuff)
        if '=' in arg and '(' in arg and ')' in arg:
            # Try to match array assignment pattern
            match = re.match(
                r'^([a-zA-Z_][a-zA-Z0-9_]*)(\+)?=\((.*)?\)$', arg, re.DOTALL)
            if match:
                var_name = match.group(1)
                is_append = (match.group(2) == '+')
                values_str = match.group(3) if match.group(3) else ''

                # Save old array in scope if it exists
                if len(state.local_scope_stack) > 0:
                    if var_name not in state.local_scope_stack[-1]:
                        if var_name in state.arrays:
                            state.local_scope_stack[-1][f"__array_{var_name}"] = state.arrays[var_name][:]
                        else:
                            state.local_scope_stack[-1][f"__array_{var_name}"] = None

                # Parse values - split by whitespace but preserve quotes
                import shlex
                try:
                    values = shlex.split(
                        values_str) if values_str.strip() else []
                except ValueError:
                    values = values_str.split() if values_str.strip() else []

                if is_append and var_name in state.arrays:
                    state.arrays[var_name].extend(values)
                else:
                    state.arrays[var_name] = values
                    state.declared_arrays[var_name] = 'indexed'

                continue

        # Regular variable handling
        if '=' in arg and not ('(' in arg and ')' in arg):
            var, value = arg.split('=', 1)
            # Save old value if it exists
            if len(state.local_scope_stack) > 0:
                if var not in state.local_scope_stack[-1]:
                    state.local_scope_stack[-1][var] = state.local_vars.get(
                        var)
            state.local_vars[var] = value
        else:
            # Just declaring without assignment
            if len(state.local_scope_stack) > 0:
                if arg not in state.local_scope_stack[-1]:
                    state.local_scope_stack[-1][arg] = state.local_vars.get(
                        arg)
            if not ('(' in arg and ')' in arg):  # Don't set to empty if it was an array
                state.local_vars[arg] = ''

    return 0


def _builtin_readonly(args):
    """Mark variables as readonly."""
    if not args:
        for var in state.readonly_vars:
            value = state.local_vars.get(var, '')
            sys.stdout.write(f"declare -r {var}=\"{value}\"\n")
        return 0

    for arg in args:
        if '=' in arg:
            var, value = arg.split('=', 1)
            state.local_vars[var] = value
            state.readonly_vars.add(var)
        else:
            state.readonly_vars.add(arg)

    return 0


def _builtin_shift(args):
    """Shift positional parameters."""
    n = int(args[0]) if args else 1

    if n > len(state.positional_params):
        return 1

    state.positional_params = state.positional_params[n:]
    return 0


def _builtin_set(args):
    """Set shell options or positional parameters."""
    if not args:
        for var, value in sorted(state.local_vars.items()):
            sys.stdout.write(f"{var}={value}\n")
        return 0

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '-e':
            state.option_errexit = True
        elif arg == '+e':
            state.option_errexit = False
        elif arg == '-u':
            state.option_nounset = True
        elif arg == '+u':
            state.option_nounset = False
        elif arg == '-x':
            state.option_xtrace = True
        elif arg == '+x':
            state.option_xtrace = False
        elif arg == '-f':
            state.option_noglob = True
        elif arg == '+f':
            state.option_noglob = False
        elif arg == '-C':
            state.option_noclobber = True
        elif arg == '+C':
            state.option_noclobber = False
        elif arg == '-o':
            if i + 1 < len(args):
                option = args[i + 1]
                if option == 'pipefail':
                    state.option_pipefail = True
                i += 1
        elif arg == '+o':
            if i + 1 < len(args):
                option = args[i + 1]
                if option == 'pipefail':
                    state.option_pipefail = False
                i += 1
        elif arg == '--':
            state.positional_params = args[i+1:]
            break
        elif not arg.startswith('-') and not arg.startswith('+'):
            state.positional_params = args[i:]
            break

        i += 1

    return 0


def _builtin_declare(args):
    """Declare variables with attributes."""
    for arg in args:
        if '=' in arg:
            var, value = arg.split('=', 1)
            state.local_vars[var] = value
        else:
            state.local_vars[arg] = ''

    return 0


def _builtin_let(args):
    """Evaluate arithmetic expressions."""
    if not args:
        return 1

    from .expansions import _eval_arithmetic, _expand_variables

    result = 0
    for expr in args:
        # Check if it's an assignment
        if '=' in expr and not any(op in expr for op in ['==', '!=', '<=', '>=']):
            # Split on first =
            parts = expr.split('=', 1)
            var_name = parts[0].strip()
            value_expr = parts[1].strip()

            # Expand variables in the value expression
            value_expr = _expand_variables(value_expr)

            try:
                result = _eval_arithmetic(value_expr)
                state.local_vars[var_name] = str(result)
            except Exception as e:
                sys.stderr.write(f"let: {e}\n")
                return 1
        else:
            # Just evaluate the expression
            expr = _expand_variables(expr)
            try:
                result = _eval_arithmetic(expr)
            except Exception as e:
                sys.stderr.write(f"let: {e}\n")
                return 1

    return 0 if result != 0 else 1


def _builtin_alias(args):
    """Define or display aliases."""
    if not args:
        for name, value in sorted(state.aliases.items()):
            sys.stdout.write(f"alias {name}='{value}'\n")
        return 0

    for arg in args:
        if '=' in arg:
            name, value = arg.split('=', 1)
            value = value.strip('\'"')
            state.aliases[name] = value
        else:
            if arg in state.aliases:
                sys.stdout.write(f"alias {arg}='{state.aliases[arg]}'\n")
            else:
                sys.stderr.write(f"alias: {arg}: not found\n")
                return 1

    return 0


def _builtin_unalias(args):
    """Remove alias definitions."""
    for name in args:
        if name in state.aliases:
            del state.aliases[name]
        else:
            sys.stderr.write(f"unalias: {name}: not found\n")
            return 1

    return 0


def _builtin_pushd(args):
    """Push directory onto stack."""
    if not args:
        if not state.dir_stack:
            sys.stderr.write("pushd: no other directory\n")
            return 1

        current = os.getcwd()
        target = state.dir_stack[0]
        state.dir_stack[0] = current

        try:
            os.chdir(target)
            _builtin_dirs([])
            return 0
        except Exception as e:
            sys.stderr.write(f"pushd: {target}: {e}\n")
            return 1

    target = os.path.expanduser(args[0])
    current = os.getcwd()

    try:
        os.chdir(target)
        state.dir_stack.insert(0, current)
        _builtin_dirs([])
        return 0
    except Exception as e:
        sys.stderr.write(f"pushd: {args[0]}: {e}\n")
        return 1


def _builtin_popd(args):
    """Pop directory from stack."""
    if not state.dir_stack:
        sys.stderr.write("popd: directory stack empty\n")
        return 1

    target = state.dir_stack.pop(0)

    try:
        os.chdir(target)
        _builtin_dirs([])
        return 0
    except Exception as e:
        sys.stderr.write(f"popd: {target}: {e}\n")
        return 1


def _builtin_dirs(args):
    """Display directory stack."""
    dirs = [os.getcwd()] + state.dir_stack
    sys.stdout.write(' '.join(dirs) + '\n')
    return 0


def _builtin_source(args):
    """Execute commands from a file in current shell."""
    if not args:
        sys.stderr.write("source: filename argument required\n")
        return 1

    filename = args[0]

    # CRITICAL FIX: Use the filename exactly as provided
    # Don't call os.path.abspath on already absolute paths as it can corrupt them
    # Only resolve relative paths
    if not os.path.isabs(filename):
        filename = os.path.join(os.getcwd(), filename)
    # For absolute paths, use them exactly as provided

    try:
        with open(filename, 'r') as f:
            script = f.read()

        from . import tokenizer, parser, executor

        tokens = tokenizer.tokenize(script)
        ast = parser.parse(tokens)
        return executor.execute(ast)

    except FileNotFoundError:
        sys.stderr.write(f"source: {args[0]}: No such file or directory\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"source: {e}\n")
        return 1


def _builtin_eval(args):
    """Evaluate arguments as a shell command."""
    if not args:
        return 0

    command = ' '.join(args)

    try:
        from . import tokenizer, parser, executor

        tokens = tokenizer.tokenize(command)
        ast = parser.parse(tokens)
        return executor.execute(ast)

    except Exception as e:
        sys.stderr.write(f"eval: {e}\n")
        return 1


def _builtin_wait(args):
    """Wait for background jobs."""
    import subprocess

    if not args:
        for jid, proc, cmdline, status in state.running_jobs:
            proc.wait()
        state.running_jobs.clear()
        return 0

    return 0


def _builtin_type(args):
    """Display command type."""
    from . import utils

    for cmd in args:
        if cmd in BUILTIN_COMMANDS:
            sys.stdout.write(f"{cmd} is a shell builtin\n")
        elif cmd in state.aliases:
            sys.stdout.write(f"{cmd} is aliased to `{state.aliases[cmd]}'\n")
        elif cmd in state.functions:
            sys.stdout.write(f"{cmd} is a function\n")
        else:
            executable = utils.find_executable(cmd)
            if executable:
                sys.stdout.write(f"{cmd} is {executable}\n")
            else:
                sys.stdout.write(f"{cmd}: not found\n")
                return 1

    return 0


def _builtin_trap(args):
    """Set signal handlers."""
    if not args:
        for sig, cmd in state.trap_handlers.items():
            sys.stdout.write(f"trap -- '{cmd}' {sig}\n")
        return 0

    if len(args) < 2:
        return 0

    command = args[0]
    signals = args[1:]

    for sig in signals:
        state.trap_handlers[sig] = command

    return 0


def _builtin_declare(args):
    """Declare variables with attributes - ENHANCED WITH ARRAY SUPPORT"""
    if not args:
        # Show all variables
        for var, value in sorted(state.local_vars.items()):
            sys.stdout.write(f"declare -- {var}=\"{value}\"\n")
        # Show arrays
        for arr, values in sorted(state.arrays.items()):
            sys.stdout.write(
                f"declare -a {arr}=({' '.join(repr(v) for v in values)})\n")
        # Show associative arrays
        for arr, values in sorted(state.assoc_arrays.items()):
            sys.stdout.write(
                f"declare -A {arr}=({' '.join(f'[{k}]={repr(v)}' for k, v in values.items())})\n")
        return 0

    # Parse flags
    is_associative = False
    is_indexed = False
    is_readonly = False
    is_export = False

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '-A':
            is_associative = True
            i += 1
        elif arg == '-a':
            is_indexed = True
            i += 1
        elif arg == '-r':
            is_readonly = True
            i += 1
        elif arg == '-x':
            is_export = True
            i += 1
        elif '=' in arg:
            # Variable assignment
            var, value = arg.split('=', 1)
            state.local_vars[var] = value

            if is_readonly:
                state.readonly_vars.add(var)
            if is_export:
                state.exported_vars.add(var)
                os.environ[var] = value

            i += 1
        else:
            # Just declare the variable
            var = arg

            if is_associative:
                state.assoc_arrays[var] = {}
                state.declared_arrays[var] = 'associative'
            elif is_indexed:
                state.arrays[var] = []
                state.declared_arrays[var] = 'indexed'
            else:
                if var not in state.local_vars:
                    state.local_vars[var] = ''

            if is_readonly:
                state.readonly_vars.add(var)
            if is_export:
                state.exported_vars.add(var)

            i += 1

    return 0


def _builtin_mapfile(args):
    """Read lines from stdin into an array"""
    array_name = 'MAPFILE'

    # Parse options
    i = 0
    while i < len(args):
        if args[i] == '-t':
            # Strip trailing newlines (default behavior)
            i += 1
        elif not args[i].startswith('-'):
            array_name = args[i]
            i += 1
            break
        else:
            i += 1

    # Read lines into array
    lines = []
    try:
        for line in sys.stdin:
            lines.append(line.rstrip('\n'))
    except KeyboardInterrupt:
        pass

    state.arrays[array_name] = lines
    state.declared_arrays[array_name] = 'indexed'

    return 0


def _builtin_grep(args):
    """Simple grep implementation."""
    import re

    # Parse options
    ignore_case = False
    invert_match = False
    count_only = False
    line_number = False
    pattern = None
    files = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '-i':
            ignore_case = True
        elif arg == '-v':
            invert_match = True
        elif arg == '-c':
            count_only = True
        elif arg == '-n':
            line_number = True
        elif arg.startswith('-'):
            # Handle combined flags like -in
            if 'i' in arg:
                ignore_case = True
            if 'v' in arg:
                invert_match = True
            if 'c' in arg:
                count_only = True
            if 'n' in arg:
                line_number = True
        else:
            if pattern is None:
                pattern = arg
            else:
                files.append(arg)
        i += 1

    if pattern is None:
        sys.stderr.write("grep: no pattern specified\n")
        return 2

    # Compile regex
    try:
        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)
    except re.error as e:
        sys.stderr.write(f"grep: invalid pattern: {e}\n")
        return 2

    # Process input
    match_count = 0
    line_num = 0
    found_match = False

    try:
        if not files:
            # Read from stdin
            for line in sys.stdin:
                line_num += 1
                line = line.rstrip('\n')
                matches = bool(regex.search(line))

                if invert_match:
                    matches = not matches

                if matches:
                    match_count += 1
                    found_match = True
                    if not count_only:
                        if line_number:
                            sys.stdout.write(f"{line_num}:{line}\n")
                        else:
                            sys.stdout.write(line + "\n")

            if count_only:
                sys.stdout.write(f"{match_count}\n")
        else:
            # Read from files
            for filename in files:
                try:
                    with open(filename, 'r') as f:
                        file_line_num = 0
                        for line in f:
                            file_line_num += 1
                            line = line.rstrip('\n')
                            matches = bool(regex.search(line))

                            if invert_match:
                                matches = not matches

                            if matches:
                                match_count += 1
                                found_match = True
                                if not count_only:
                                    prefix = f"{filename}:" if len(
                                        files) > 1 else ""
                                    if line_number:
                                        sys.stdout.write(
                                            f"{prefix}{file_line_num}:{line}\n")
                                    else:
                                        sys.stdout.write(f"{prefix}{line}\n")
                except FileNotFoundError:
                    sys.stderr.write(
                        f"grep: {filename}: No such file or directory\n")
                    return 2
                except PermissionError:
                    sys.stderr.write(f"grep: {filename}: Permission denied\n")
                    return 2

            if count_only:
                sys.stdout.write(f"{match_count}\n")

        return 0 if found_match else 1

    except KeyboardInterrupt:
        return 130
    except Exception as e:
        sys.stderr.write(f"grep: {e}\n")
        return 2


def _builtin_wc(args):
    """Word count implementation - counts lines, words, and characters."""
    # Parse options
    count_lines = False
    count_words = False
    count_chars = False
    count_bytes = False
    files = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '-l':
            count_lines = True
        elif arg == '-w':
            count_words = True
        elif arg == '-c':
            count_bytes = True
        elif arg == '-m':
            count_chars = True
        elif arg.startswith('-'):
            # Handle combined flags like -lwc
            if 'l' in arg:
                count_lines = True
            if 'w' in arg:
                count_words = True
            if 'c' in arg:
                count_bytes = True
            if 'm' in arg:
                count_chars = True
        else:
            files.append(arg)
        i += 1

    # If no options specified, count all three (lines, words, bytes)
    if not (count_lines or count_words or count_chars or count_bytes):
        count_lines = True
        count_words = True
        count_bytes = True

    total_lines = 0
    total_words = 0
    total_chars = 0
    total_bytes = 0

    def count_text(text):
        """Count lines, words, and characters in text."""
        lines = text.count('\n')
        words = len(text.split())
        chars = len(text)
        byte_count = len(text.encode('utf-8'))
        return lines, words, chars, byte_count

    def print_counts(lines, words, chars, byte_count, filename=None):
        """Print counts in wc format."""
        output = []
        if count_lines:
            output.append(f"{lines:8}")
        if count_words:
            output.append(f"{words:8}")
        if count_chars:
            output.append(f"{chars:8}")
        elif count_bytes:
            output.append(f"{byte_count:8}")

        result = " ".join(output)
        if filename:
            result += f" {filename}"
        sys.stdout.write(result + "\n")

    try:
        if not files:
            # Read from stdin
            text = sys.stdin.read()
            lines, words, chars, byte_count = count_text(text)
            print_counts(lines, words, chars, byte_count)
            return 0
        else:
            # Read from files
            for filename in files:
                try:
                    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                        text = f.read()

                    lines, words, chars, byte_count = count_text(text)
                    total_lines += lines
                    total_words += words
                    total_chars += chars
                    total_bytes += byte_count

                    print_counts(lines, words, chars, byte_count, filename)

                except FileNotFoundError:
                    sys.stderr.write(
                        f"wc: {filename}: No such file or directory\n")
                    return 1
                except PermissionError:
                    sys.stderr.write(f"wc: {filename}: Permission denied\n")
                    return 1
                except Exception as e:
                    sys.stderr.write(f"wc: {filename}: {e}\n")
                    return 1

            # Print total if multiple files
            if len(files) > 1:
                print_counts(total_lines, total_words,
                             total_chars, total_bytes, "total")

            return 0

    except KeyboardInterrupt:
        return 130
    except Exception as e:
        sys.stderr.write(f"wc: {e}\n")
        return 1


def _builtin_head(args):
    """Print first N lines (default 10)."""
    n = 10
    files = []

    i = 0
    while i < len(args):
        if args[i] == '-n' and i + 1 < len(args):
            n = int(args[i + 1])
            i += 2
        elif args[i].startswith('-') and args[i][1:].isdigit():
            n = int(args[i][1:])
            i += 1
        else:
            files.append(args[i])
            i += 1

    try:
        if not files:
            for i, line in enumerate(sys.stdin):
                if i >= n:
                    break
                sys.stdout.write(line)
        else:
            for filename in files:
                with open(filename, 'r') as f:
                    for i, line in enumerate(f):
                        if i >= n:
                            break
                        sys.stdout.write(line)
        return 0
    except Exception as e:
        sys.stderr.write(f"head: {e}\n")
        return 1


def _builtin_tail(args):
    """Print last N lines (default 10)."""
    n = 10
    files = []

    i = 0
    while i < len(args):
        if args[i] == '-n' and i + 1 < len(args):
            n = int(args[i + 1])
            i += 2
        elif args[i].startswith('-') and args[i][1:].isdigit():
            n = int(args[i][1:])
            i += 1
        else:
            files.append(args[i])
            i += 1

    try:
        if not files:
            lines = sys.stdin.readlines()
            for line in lines[-n:]:
                sys.stdout.write(line)
        else:
            for filename in files:
                with open(filename, 'r') as f:
                    lines = f.readlines()
                for line in lines[-n:]:
                    sys.stdout.write(line)
        return 0
    except Exception as e:
        sys.stderr.write(f"tail: {e}\n")
        return 1


def _builtin_sort(args):
    """Sort lines of text."""
    reverse = False
    numeric = False
    unique = False
    files = []

    for arg in args:
        if arg == '-r':
            reverse = True
        elif arg == '-n':
            numeric = True
        elif arg == '-u':
            unique = True
        else:
            files.append(arg)

    try:
        if not files:
            lines = sys.stdin.readlines()
        else:
            lines = []
            for filename in files:
                with open(filename, 'r') as f:
                    lines.extend(f.readlines())

        # Remove newlines for sorting
        lines = [line.rstrip('\n') for line in lines]

        if numeric:
            def sort_key(line):
                try:
                    return float(line.split()[0])
                except:
                    return 0
            lines.sort(key=sort_key, reverse=reverse)
        else:
            lines.sort(reverse=reverse)

        if unique:
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            lines = unique_lines

        for line in lines:
            sys.stdout.write(line + '\n')

        return 0
    except Exception as e:
        sys.stderr.write(f"sort: {e}\n")
        return 1


def _builtin_uniq(args):
    """Remove duplicate adjacent lines."""
    count = False

    for arg in args:
        if arg == '-c':
            count = True

    try:
        lines = sys.stdin.readlines()

        if not lines:
            return 0

        prev_line = None
        line_count = 0

        for line in lines:
            line = line.rstrip('\n')

            if line == prev_line:
                line_count += 1
            else:
                if prev_line is not None:
                    if count:
                        sys.stdout.write(f"{line_count:7} {prev_line}\n")
                    else:
                        sys.stdout.write(prev_line + '\n')
                prev_line = line
                line_count = 1

        # Print last line
        if prev_line is not None:
            if count:
                sys.stdout.write(f"{line_count:7} {prev_line}\n")
            else:
                sys.stdout.write(prev_line + '\n')

        return 0
    except Exception as e:
        sys.stderr.write(f"uniq: {e}\n")
        return 1


def _builtin_clear(args):
    """Clear the terminal screen."""
    import os
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')
    return 0


def _builtin_ls(args):
    """List directory contents."""
    import stat
    import time

    show_all = False
    long_format = False
    human_readable = False
    paths = []

    for arg in args:
        if arg == '-a':
            show_all = True
        elif arg == '-l':
            long_format = True
        elif arg == '-h':
            human_readable = True
        elif arg == '-la' or arg == '-al':
            show_all = True
            long_format = True
        elif arg == '-lh' or arg == '-hl':
            long_format = True
            human_readable = True
        elif arg == '-lah' or arg == '-alh' or arg == '-hla' or arg == '-hal':
            show_all = True
            long_format = True
            human_readable = True
        elif not arg.startswith('-'):
            paths.append(arg)

    if not paths:
        paths = ['.']

    def format_size(size):
        """Format size in human-readable format."""
        if not human_readable:
            return str(size)

        for unit in ['B', 'K', 'M', 'G', 'T']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}P"

    def format_permissions(mode):
        """Format file permissions."""
        perms = []
        # File type
        if stat.S_ISDIR(mode):
            perms.append('d')
        elif stat.S_ISLNK(mode):
            perms.append('l')
        else:
            perms.append('-')

        # Owner permissions
        perms.append('r' if mode & stat.S_IRUSR else '-')
        perms.append('w' if mode & stat.S_IWUSR else '-')
        perms.append('x' if mode & stat.S_IXUSR else '-')

        # Group permissions
        perms.append('r' if mode & stat.S_IRGRP else '-')
        perms.append('w' if mode & stat.S_IWGRP else '-')
        perms.append('x' if mode & stat.S_IXGRP else '-')

        # Other permissions
        perms.append('r' if mode & stat.S_IROTH else '-')
        perms.append('w' if mode & stat.S_IWOTH else '-')
        perms.append('x' if mode & stat.S_IXOTH else '-')

        return ''.join(perms)

    try:
        for path in paths:
            try:
                entries = os.listdir(path)

                if not show_all:
                    entries = [e for e in entries if not e.startswith('.')]

                entries.sort()

                if long_format:
                    for entry in entries:
                        full_path = os.path.join(path, entry)
                        try:
                            stats = os.stat(full_path)
                            perms = format_permissions(stats.st_mode)
                            size = format_size(stats.st_size)
                            mtime = time.strftime(
                                '%b %d %H:%M', time.localtime(stats.st_mtime))

                            # Number of links (simplified)
                            nlinks = 1

                            sys.stdout.write(
                                f"{perms} {nlinks:3} {size:>8} {mtime} {entry}\n")
                        except (OSError, PermissionError):
                            sys.stdout.write(f"?????????? ? ? ? {entry}\n")
                else:
                    # Simple format
                    for entry in entries:
                        sys.stdout.write(entry + "  ")
                    sys.stdout.write("\n")

            except FileNotFoundError:
                sys.stderr.write(
                    f"ls: cannot access '{path}': No such file or directory\n")
                return 2
            except PermissionError:
                sys.stderr.write(
                    f"ls: cannot open directory '{path}': Permission denied\n")
                return 2

        return 0

    except Exception as e:
        sys.stderr.write(f"ls: {e}\n")
        return 1


def _builtin_date(args):
    """Display or set the system date and time."""
    import time

    if not args:
        # Default format
        sys.stdout.write(time.strftime('%a %b %d %H:%M:%S %Z %Y\n'))
        return 0

    # Handle format string
    if args[0].startswith('+'):
        format_str = args[0][1:]
        sys.stdout.write(time.strftime(format_str + '\n'))
        return 0

    # Other date options not implemented
    sys.stdout.write(time.strftime('%a %b %d %H:%M:%S %Z %Y\n'))
    return 0


def _builtin_rm(args):
    """Remove files or directories (supports -r, -f, -rf)."""
    import shutil
    import sys
    import os

    recursive = False
    force = False
    files = []

    # Parse arguments
    for arg in args:
        if arg in ("-r", "-R"):
            recursive = True
        elif arg == "-f":
            force = True
        elif arg in ("-rf", "-fr"):
            recursive = True
            force = True
        elif not arg.startswith("-"):
            files.append(arg)

    # No operands
    if not files:
        if not force:
            sys.stderr.write("rm: missing operand\n")
        return 1

    errors = 0

    for filepath in files:
        filepath = os.path.expanduser(filepath)

        # File/directory does not exist
        if not os.path.exists(filepath):
            if not force:
                sys.stderr.write(
                    f"rm: cannot remove '{filepath}': No such file or directory\n"
                )
                errors += 1
            continue

        # If it's a directory
        if os.path.isdir(filepath):
            if recursive:
                try:
                    shutil.rmtree(filepath)
                except FileNotFoundError:
                    if not force:
                        sys.stderr.write(
                            f"rm: cannot remove '{filepath}': No such file or directory\n"
                        )
                        errors += 1
                except PermissionError:
                    if not force:
                        sys.stderr.write(
                            f"rm: cannot remove '{filepath}': Permission denied\n"
                        )
                        errors += 1
                except Exception as e:
                    if not force:
                        sys.stderr.write(
                            f"rm: cannot remove '{filepath}': {e}\n")
                        errors += 1
            else:
                if not force:
                    sys.stderr.write(
                        f"rm: cannot remove '{filepath}': Is a directory\n"
                    )
                    errors += 1
            continue

        # If it's a regular file
        try:
            os.remove(filepath)
        except FileNotFoundError:
            if not force:
                sys.stderr.write(
                    f"rm: cannot remove '{filepath}': No such file or directory\n"
                )
                errors += 1
        except PermissionError:
            if not force:
                sys.stderr.write(
                    f"rm: cannot remove '{filepath}': Permission denied\n"
                )
                errors += 1
        except Exception as e:
            if not force:
                sys.stderr.write(f"rm: cannot remove '{filepath}': {e}\n")
                errors += 1

    return 1 if errors > 0 else 0



def _builtin_help(args):
    """Display help information about builtin commands."""
    if not args:
        sys.stdout.write("PyShell built-in commands:\n\n")

        categories = {
            "File Operations": ["cd", "pwd", "ls", "cat", "rm", "pushd", "popd", "dirs"],
            "Text Processing": ["echo", "printf", "read", "grep", "wc"],
            "Variables": ["export", "unset", "local", "readonly", "declare", "set"],
            "Control Flow": ["if", "while", "for", "case", "break", "continue", "return"],
            "Functions": ["function", "return"],
            "Job Control": ["jobs", "fg", "bg", "wait", "kill"],
            "Aliases": ["alias", "unalias"],
            "Scripting": ["source", ".", "eval", "exec", "test", "["],
            "System": ["exit", "sleep", "date", "clear", "type", "help"],
        }

        for category, commands in categories.items():
            sys.stdout.write(f"{category}:\n  ")
            sys.stdout.write(", ".join(commands))
            sys.stdout.write("\n\n")

        sys.stdout.write(
            "Type 'help <command>' for more information on a specific command.\n")
        return 0

    # Help for specific command
    cmd = args[0]
    help_text = {
        "cd": "cd [dir] - Change the current directory",
        "pwd": "pwd - Print working directory",
        "echo": "echo [args...] - Display a line of text",
        "exit": "exit [n] - Exit the shell with status n",
        "export": "export VAR=value - Set environment variable",
        "cat": "cat [file...] - Concatenate and print files",
        "grep": "grep [options] pattern [file...] - Search for pattern",
        "wc": "wc [options] [file...] - Count lines, words, characters",
        "ls": "ls [options] [path...] - List directory contents",
        "rm": "rm [options] file... - Remove files or directories",
        "test": "test expression - Evaluate conditional expression",
        "[": "[ expression ] - Evaluate conditional expression",
        "if": "if condition; then commands; fi - Conditional execution",
        "while": "while condition; do commands; done - Loop while true",
        "for": "for var in list; do commands; done - Iterate over list",
        "alias": "alias name='command' - Create command alias",
        "source": "source file - Execute commands from file",
        "function": "function name { commands; } - Define function",
    }

    if cmd in help_text:
        sys.stdout.write(help_text[cmd] + "\n")
    else:
        sys.stdout.write(f"No help available for '{cmd}'\n")

    return 0


def _builtin_hash(args):
    """Remember or display program locations."""
    from . import utils

    if not args or args[0] == '-l':
        # Display hash table
        if hasattr(utils, '_command_cache') and utils._command_cache:
            sys.stdout.write("hits\tcommand\n")
            for cmd, path in utils._command_cache.items():
                sys.stdout.write(f"   1\t{path}\n")
        return 0

    if args[0] == '-r':
        # Clear hash table
        if len(args) > 1:
            # Remove specific command
            if hasattr(utils, '_command_cache'):
                for cmd in args[1:]:
                    utils._command_cache.pop(cmd, None)
        else:
            # Clear all
            if hasattr(utils, '_command_cache'):
                utils._command_cache.clear()
        return 0

    # Hash specific commands
    for cmd in args:
        path = utils.find_executable(cmd)
        if path:
            if not hasattr(utils, '_command_cache'):
                utils._command_cache = {}
            utils._command_cache[cmd] = path
        else:
            sys.stderr.write(f"hash: {cmd}: not found\n")
            return 1

    return 0


def _builtin_exec(args):
    """Replace the shell with a command."""
    if not args:
        return 0

    # In a real shell, exec replaces the process
    # Here we simulate by executing and then exiting
    from . import utils

    cmd_name = args[0]
    cmd_args = args[1:]

    executable = utils.find_executable(cmd_name)
    if not executable:
        sys.stderr.write(f"exec: {cmd_name}: not found\n")
        return 127

    # Execute command and exit
    import subprocess
    result = subprocess.run([executable] + cmd_args)
    sys.exit(result.returncode)
