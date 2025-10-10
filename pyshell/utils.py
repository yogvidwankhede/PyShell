"""
Contains miscellaneous utility functions for the shell, such as signal handling,
job control, tab completion, and history management.
"""
import os
import sys
import readline
import shlex
import glob
import signal
import atexit
import shutil

try:
    import psutil
except ImportError:
    psutil = None

from . import state
from . import builtins

# --- Signal Handlers ---


def setup_signal_handlers():
    def _handle_sigtstp(sig, frame):
        state.is_suspending = True

    def _handle_sigint(sig, frame):
        if state.current_foreground_proc and state.current_foreground_proc.poll() is None:
            try:
                os.kill(state.current_foreground_proc.pid, signal.SIGINT)
            except OSError:
                pass
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()

    try:
        signal.signal(signal.SIGTSTP, _handle_sigtstp)
        signal.signal(signal.SIGINT, _handle_sigint)
    except (AttributeError, ValueError):
        pass

# --- Path and Interpreter Utilities ---


def _get_abs_interpreter_path(command_name):
    for d in os.environ.get('PATH', '').split(os.pathsep):
        full_path = os.path.join(d, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return command_name


def find_executable(name):
    """Find an executable in PATH, handling Windows extensions."""
    if os.path.isabs(name) and os.path.isfile(name) and os.access(name, os.X_OK):
        return name

    if sys.platform == 'win32':
        pathext = os.environ.get(
            'PATHEXT', '.COM;.EXE;.BAT;.CMD').split(os.pathsep)

        if os.path.splitext(name)[1]:
            names_to_try = [name]
        else:
            names_to_try = [name + ext for ext in pathext]
    else:
        names_to_try = [name]

    for directory in os.environ.get('PATH', '').split(os.pathsep):
        for try_name in names_to_try:
            full_path = os.path.join(directory, try_name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                return full_path

    return None


state.NODE_INTERPRETER_PATH = _get_abs_interpreter_path('node')
state.JAVA_INTERPRETER_PATH = _get_abs_interpreter_path('java')


# --- Job Control ---
def _get_job_status(proc):
    if proc.poll() is not None:
        return "Done"
    if psutil:
        try:
            p = psutil.Process(proc.pid)
            return state.JOB_STATUS_STOPPED if p.status() == psutil.STATUS_STOPPED else state.JOB_STATUS_RUNNING
        except psutil.NoSuchProcess:
            return "Done"
    return state.JOB_STATUS_RUNNING


def check_and_cleanup_jobs():
    surviving = []
    for jid, proc, cmdline, status in state.running_jobs:
        if proc.poll() is not None:
            print(f"\n[{jid}]   Done    {cmdline}")
            sys.stdout.write(f"{get_prompt()}{readline.get_line_buffer()}")
            sys.stdout.flush()
        else:
            surviving.append((jid, proc, cmdline, _get_job_status(proc)))
    state.running_jobs = surviving

# --- History ---


def _save_history_on_exit():
    histfile = os.environ.get('HISTFILE')
    if not histfile:
        return
    try:
        with open(os.path.expanduser(histfile), 'a', encoding='utf-8') as f:
            for cmd in state.manual_history[state.last_saved_index:]:
                if cmd:
                    f.write(cmd + '\n')
            state.last_saved_index = len(state.manual_history)
    except IOError:
        pass


def setup_history():
    atexit.register(_save_history_on_exit)
    histfile = os.environ.get('HISTFILE')
    if histfile and os.path.exists(os.path.expanduser(histfile)):
        try:
            readline.read_history_file(os.path.expanduser(histfile))
            state.manual_history = [readline.get_history_item(
                i) for i in range(1, readline.get_current_history_length() + 1)]
            state.last_saved_index = len(state.manual_history)
        except IOError:
            pass

# --- Enhanced Completion ---


def completer(text, st):
    line = readline.get_line_buffer()
    words = line.split()

    if state.last_text != text:
        state.last_text = text
        matches = []

        # Variable completion
        if text.startswith("$"):
            var_prefix = text[1:]
            matches.extend(
                f"${k}" for k in os.environ if k.startswith(var_prefix))
            matches.extend(
                f"${k}" for k in state.local_vars if k.startswith(var_prefix))
            matches.extend(
                f"${k}" for k in state.arrays if k.startswith(var_prefix))

        # Command completion
        elif not words or (len(words) == 1 and not line.endswith(' ')):
            # Built-in commands
            matches.extend(
                c for c in builtins.BUILTIN_COMMANDS if c.startswith(text))

            # Aliases
            matches.extend(a for a in state.aliases if a.startswith(text))

            # Functions
            matches.extend(f for f in state.functions if f.startswith(text))

            # Executables in PATH
            for d in os.environ.get('PATH', '').split(os.pathsep):
                try:
                    if os.path.isdir(d):
                        matches.extend(f for f in os.listdir(d)
                                       if f.startswith(text) and os.access(os.path.join(d, f), os.X_OK))
                except OSError:
                    continue

        # Path/file completion
        else:
            expanded_text = os.path.expanduser(text)
            if '*' not in expanded_text and '?' not in expanded_text:
                expanded_text += '*'

            try:
                matches.extend(glob.glob(expanded_text))
            except:
                pass

            # Add directory completions with trailing slash
            dir_matches = []
            for match in matches:
                if os.path.isdir(match) and not match.endswith('/'):
                    dir_matches.append(match + '/')
            matches.extend(dir_matches)

        state.last_matches = sorted(list(set(matches)))

    return state.last_matches[st] if st < len(state.last_matches) else None


def setup_completer():
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')

    # Enable additional readline features
    try:
        readline.parse_and_bind('set show-all-if-ambiguous on')
        readline.parse_and_bind('set completion-ignore-case on')
        readline.parse_and_bind('set show-mode-in-prompt on')
    except:
        pass

# --- Multi-line Input ---


# Replace the needs_multiline and collect_multiline functions in utils.py

def needs_multiline(line):
    """Check if line needs continuation."""
    stripped = line.strip()

    # Check for line continuation character
    if stripped.endswith('\\'):
        return True

    # Check for pipe at end
    if stripped.endswith('|'):
        return True

    # Check for open control structures
    if stripped.startswith(('if', 'while', 'until', 'for', 'case', 'function')):
        return True

    # Check if we're inside a control structure (contains then/do but no fi/done)
    if 'then' in stripped and 'fi' not in stripped:
        return True
    if 'do' in stripped and 'done' not in stripped:
        return True
    if stripped.startswith('case ') and 'esac' not in stripped:
        return True

    # Check for unclosed braces or parentheses
    open_braces = stripped.count('{') - stripped.count('}')
    open_parens = stripped.count('(') - stripped.count(')')

    if open_braces > 0 or open_parens > 0:
        return True

    return False


def collect_multiline(first_line):
    """Collect multi-line input for complex commands."""
    lines = [first_line]

    # Track what we're looking for
    looking_for = None

    # Check what structure we're in
    if 'if' in first_line and 'then' in first_line:
        looking_for = 'fi'
    elif first_line.strip().startswith('while') and 'do' in first_line:
        looking_for = 'done'
    elif first_line.strip().startswith('until') and 'do' in first_line:
        looking_for = 'done'
    elif first_line.strip().startswith('for') and 'do' in first_line:
        looking_for = 'done'
    elif first_line.strip().startswith('case'):
        looking_for = 'esac'
    elif first_line.strip().startswith('if'):
        looking_for = 'then'  # First, we need 'then', then we'll look for 'fi'
    elif first_line.strip().startswith(('while', 'until', 'for')):
        looking_for = 'do'  # First need 'do', then 'done'

    max_lines = 100  # Safety limit
    line_count = 0

    while line_count < max_lines:
        try:
            next_line = input(state.PS2)
            lines.append(next_line)
            line_count += 1

            stripped = next_line.strip()

            # Update what we're looking for based on what we see
            if looking_for == 'then' and 'then' in stripped:
                looking_for = 'fi'
            elif looking_for == 'do' and 'do' in stripped:
                looking_for = 'done'

            # Check if we found the closing keyword
            if looking_for == 'fi' and stripped == 'fi':
                break
            elif looking_for == 'done' and stripped == 'done':
                break
            elif looking_for == 'esac' and stripped == 'esac':
                break

            # Alternative: check for balanced structures
            combined = '\n'.join(lines)

            # Count keywords
            if_count = combined.count(
                ' if ') + sum(1 for l in lines if l.strip().startswith('if '))
            fi_count = sum(1 for l in lines if l.strip() == 'fi')

            while_count = sum(1 for l in lines if l.strip(
            ).startswith(('while ', 'until ', 'for ')))
            done_count = sum(1 for l in lines if l.strip() == 'done')

            case_count = sum(1 for l in lines if l.strip().startswith('case '))
            esac_count = sum(1 for l in lines if l.strip() == 'esac')

            # Check if structures are balanced
            if if_count > 0 and if_count == fi_count:
                if while_count == 0 or while_count == done_count:
                    if case_count == 0 or case_count == esac_count:
                        break

            # Check for balanced braces and parens
            open_braces = combined.count('{') - combined.count('}')
            open_parens = combined.count('(') - combined.count(')')

            # If everything is balanced and we have closing keywords, we're done
            if open_braces == 0 and open_parens == 0:
                if (if_count == 0 or if_count == fi_count) and \
                   (while_count == 0 or while_count == done_count) and \
                   (case_count == 0 or case_count == esac_count):
                    break

        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

    return '\n'.join(lines)

# --- Prompt ---


def get_prompt():
    """Generate the shell prompt with variable expansion."""
    prompt = state.PS1

    # Expand common prompt escapes
    prompt = prompt.replace('\\u', os.environ.get('USER', 'user'))

    # Handle hostname (Unix-only)
    if hasattr(os, 'uname'):
        prompt = prompt.replace('\\h', os.uname().nodename.split('.')[0])
        prompt = prompt.replace('\\H', os.uname().nodename)
    else:
        prompt = prompt.replace('\\h', 'localhost')
        prompt = prompt.replace('\\H', 'localhost')

    prompt = prompt.replace('\\w', os.getcwd())
    prompt = prompt.replace('\\W', os.path.basename(os.getcwd()))

    # Handle prompt character (# for root on Unix, $ for normal users)
    # Check if geteuid exists (Unix) before calling it
    if hasattr(os, 'geteuid'):
        prompt = prompt.replace('\\$', '#' if os.geteuid() == 0 else '$')
    else:
        prompt = prompt.replace('\\$', '$')

    prompt = prompt.replace('\\n', '\n')
    prompt = prompt.replace('\\r', '\r')
    prompt = prompt.replace('\\t', __import__('time').strftime('%H:%M:%S'))
    prompt = prompt.replace('\\d', __import__('time').strftime('%a %b %d'))

    return prompt


# --- Command Hashing ---

_command_cache = {}


def hash_command(name):
    """Cache the full path of a command."""
    if name not in _command_cache:
        path = find_executable(name)
        if path:
            _command_cache[name] = path
    return _command_cache.get(name)


def clear_hash():
    """Clear the command cache."""
    _command_cache.clear()


# --- Script Execution ---

def execute_script(script_path, args):
    """Execute a shell script."""
    # Save current state
    saved_params = state.positional_params[:]
    saved_script_name = state.script_name

    # Set new state
    state.positional_params = args
    state.script_name = script_path

    try:
        with open(script_path, 'r') as f:
            script_content = f.read()

        # Check for shebang
        if script_content.startswith('#!'):
            first_line = script_content.split('\n')[0]
            # If it's our shell, execute it
            if 'pyshell' in first_line or 'python' in first_line:
                script_content = '\n'.join(script_content.split('\n')[1:])
            else:
                # Execute with the specified interpreter
                import subprocess
                interpreter = first_line[2:].strip().split()[0]
                result = subprocess.run([interpreter, script_path] + args)
                return result.returncode

        # Execute the script
        from . import tokenizer, parser, executor

        tokens = tokenizer.tokenize(script_content)
        ast = parser.parse(tokens)
        return executor.execute(ast)

    except FileNotFoundError:
        print(
            f"pyshell: {script_path}: No such file or directory", file=sys.stderr)
        return 127
    except Exception as e:
        print(f"pyshell: error executing {script_path}: {e}", file=sys.stderr)
        return 1
    finally:
        # Restore state
        state.positional_params = saved_params
        state.script_name = saved_script_name
