"""
The main entry point for the PyShell application.
"""
import sys
import os

from pyshell.utils import (
    setup_signal_handlers, setup_history, setup_completer,
    check_and_cleanup_jobs, get_prompt, needs_multiline, collect_multiline
)
from pyshell.tokenizer import tokenize
from pyshell.parser import parse
from pyshell.executor import execute
from pyshell import state
from pyshell.exceptions import ReturnFromFunction
from pyshell.builtins import execute_builtin


def repl():
    """Main Read-Eval-Print Loop."""
    setup_signal_handlers()
    setup_history()
    setup_completer()

    while True:
        try:
            check_and_cleanup_jobs()
            raw = input(get_prompt())
            if not raw.strip():
                continue

            if needs_multiline(raw):
                raw = collect_multiline(raw)

            state.manual_history.append(raw)

            # Don't expand here - let executor handle it
            tokens = tokenize(raw)
            ast = parse(tokens)
            exit_code = execute(ast)
            state.last_exit_status = exit_code

        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        except SyntaxError as e:
            print(f"Syntax error: {e}", file=sys.stderr)
            state.last_exit_status = 2
        except ReturnFromFunction:
            print("return: can only be used in a function", file=sys.stderr)
            state.last_exit_status = 1
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            state.last_exit_status = 1


def run_command(command_string):
    """Run a single command (for -c option)."""
    try:
        # Set a flag to indicate we're in non-interactive mode
        state.non_interactive = True

        tokens = tokenize(command_string)
        ast = parse(tokens)
        exit_code = execute(ast)
        return exit_code
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Handle the internal call to run a built-in in the background
    if len(sys.argv) > 2 and sys.argv[1] == '--run-builtin':
        command_name = sys.argv[2]
        args = sys.argv[3:]
        try:
            rc = execute_builtin(command_name, args)
            sys.exit(rc)
        except Exception as e:
            print(
                f"Error in background builtin '{command_name}': {e}", file=sys.stderr)
            sys.exit(1)

    # Handle -c option for running commands
    elif len(sys.argv) > 2 and sys.argv[1] == '-c':
        command = sys.argv[2]
        sys.exit(run_command(command))

    # Default: run REPL
    else:
        repl()
