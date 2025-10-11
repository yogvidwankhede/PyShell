"""
PyShell main entry point – Full-screen TUI Edition.

Features:
- Two built-in themes: "Dark Modern" and "Light Modern".
- A true full-screen UI with prompt_toolkit for a stable background.
- A simplified, traditional shell-like interface where the prompt follows the output.
- The entire screen is a single, scrollable history buffer.
- Retains the original installer wizard and intro animation.
"""

import sys
import os
import time
import json
from pathlib import Path
from io import StringIO

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import track
from rich import box

import questionary
from questionary import Choice
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style as PromptStyle
from prompt_toolkit.lexers import Lexer

# These imports are assumed to be in a 'pyshell' package/directory.
# Mock them if running as a standalone file.
from pyshell.utils import (
    setup_signal_handlers, setup_history, setup_completer,
    check_and_cleanup_jobs, needs_multiline, collect_multiline
)
from pyshell.tokenizer import tokenize
from pyshell.parser import parse
from pyshell.executor import execute
from pyshell import state
from pyshell.exceptions import ReturnFromFunction
from pyshell.builtins import execute_builtin

# -------------------------------------------------------------------------
# Globals / Config
# -------------------------------------------------------------------------
console = Console()
CONFIG_PATH = Path.home() / ".pyshell_config"
DEFAULT_THEME = "Dark Modern"

# -------------------------------------------------------------------------
# Themes
# -------------------------------------------------------------------------
THEMES = {
    "Dark Modern": {
        "name": "Dark Modern",
        "prompt_color": "#569CD6",
        "success": "[#4EC9B0]✓ Success[/]",
        "error": "[#F44747]✖ Error[/]",
        "border": "#569CD6",
        "bg_rgb": (30, 30, 30),
        "text_color": "#D4D4D4",
    },
    "Light Modern": {
        "name": "Light Modern",
        "prompt_color": "#0000FF",  # Blue
        "success": "[#098658]✓ Success[/]",  # Dark Green
        "error": "[#AF0000]✖ Error[/]",   # Dark Red
        "border": "#007ACC",
        "bg_rgb": (255, 255, 255),  # White
        "text_color": "#000000",   # Black
    }
}


def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

# -------------------------------------------------------------------------
# Theme Selection
# -------------------------------------------------------------------------


def save_theme(theme_name: str) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f)
    except Exception:
        pass


def load_theme():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                t = data.get("theme")
                if t in THEMES:
                    return t
        except Exception:
            pass
    return None


def select_theme():
    saved = load_theme()
    if saved:
        use_saved = questionary.confirm(
            f"Use saved theme: [cyan]{saved}[/cyan]?", default=True).ask()
        if use_saved:
            return saved

    console.print("\n[bold cyan]✧ Select a PyShell Theme[/bold cyan]\n")

    custom_style = questionary.Style([
        ('qmark', 'fg:#569CD6 bold'),
        ('question', 'bold'),
        ('answer', 'fg:#4EC9B0 bold'),
        ('pointer', 'fg:#569CD6 bold'),
        ('highlighted', 'fg:#569CD6 bold noreverse'),
        ('selected', 'noreverse'),
        ('text', ''),
        ('disabled', ''),
    ])

    choices_list = [Choice(t) for t in THEMES.keys()]

    theme_choice = questionary.select(
        "✧ Choose your preferred theme:",
        choices=choices_list,
        qmark="✧",
        pointer="➤",
        style=custom_style,
    ).ask() or DEFAULT_THEME
    save_theme(theme_choice)
    return theme_choice

# -------------------------------------------------------------------------
# Intro & Installer Wizard
# -------------------------------------------------------------------------


def show_intro(theme_name: str) -> None:
    THEME = THEMES[theme_name]
    os.system("cls" if os.name == "nt" else "clear")
    for _ in track(range(25), description=f"[{THEME['border']}]Loading {THEME['name']} theme...[/]", transient=True):
        time.sleep(0.02)

    console.clear()
    banner = Text("\n🚀 PyShell", style=THEME['border'])
    subtitle = Text(f"{THEME['name']} Mode\n", style="dim white")
    console.print(Panel.fit(banner + subtitle, border_style=THEME['border']))
    time.sleep(1)


def show_installer_wizard(theme_name: str) -> bool:
    """
    Shows installer wizard and returns True if should continue to shell, False to exit.
    """
    THEME = THEMES[theme_name]
    console.print(
        "\n[bold white]Installation wizard for [cyan]PyShell[/cyan][/bold white]\n")

    custom_style = questionary.Style([
        ('qmark', 'fg:#569CD6 bold'),
        ('question', 'bold'),
        ('answer', 'fg:#4EC9B0 bold'),
        ('pointer', 'fg:#569CD6 bold'),
        ('highlighted', 'fg:#569CD6 bold noreverse'),
        ('selected', 'noreverse'),
        ('text', ''),
        ('disabled', ''),
    ])

    choices_list = ["🔧  Install PyShell", "🧹  Uninstall PyShell", "🚪  Exit"]

    choice = questionary.select(
        "✧ Select an action:",
        choices=choices_list,
        qmark="✧",
        pointer="➤",
        style=custom_style,
    ).ask()

    if choice == "🔧  Install PyShell":
        install_pyshell(theme_name)
        return True
    elif choice == "🧹  Uninstall PyShell":
        uninstalled = uninstall_pyshell(theme_name)
        return not uninstalled  # Exit if uninstalled successfully
    else:  # Exit
        console.print(f"\n[{THEME['border']}]Goodbye! 👋[/]\n")
        return False


def install_pyshell(theme_name: str) -> None:
    """Install PyShell to the system."""
    THEME = THEMES[theme_name]
    console.print(
        f"\n[{THEME['border']}]Starting PyShell installation...[/]\n")

    try:
        # Check if already installed
        install_marker = Path.home() / ".pyshell_installed"
        if install_marker.exists():
            console.print(
                f"[{THEME['border']}]ℹ PyShell is already installed![/]")
            overwrite = questionary.confirm(
                "Do you want to reinstall?", default=False).ask()
            if not overwrite:
                console.print(
                    f"[{THEME['border']}]Installation cancelled.[/]\n")
                return

        # Simulate installation steps
        steps = [
            "Checking system requirements",
            "Creating installation directory",
            "Copying files",
            "Setting up configuration",
            "Registering PyShell",
            "Finalizing installation"
        ]

        for step in track(steps, description=f"[{THEME['border']}]Installing...[/]"):
            time.sleep(0.3)

        # Create installation marker
        install_marker.write_text("installed")

        console.print(
            f"\n{THEME['success']} PyShell installed successfully!\n")
        console.print(
            f"[{THEME['border']}]You can now use PyShell from your terminal.[/]\n")

    except Exception as e:
        console.print(f"\n{THEME['error']} Installation failed: {e}\n")


def uninstall_pyshell(theme_name: str) -> bool:
    """
    Uninstall PyShell from the system.
    Returns True if successfully uninstalled or nothing to uninstall, False if cancelled.
    """
    THEME = THEMES[theme_name]

    # Check if installed
    install_marker = Path.home() / ".pyshell_installed"
    if not install_marker.exists():
        console.print(
            f"\n[{THEME['border']}]ℹ PyShell is not installed. Nothing to uninstall.[/]")
        console.print(f"[{THEME['border']}]Goodbye! 👋[/]\n")
        return True  # Exit since there's nothing to uninstall

    console.print(
        f"\n[{THEME['border']}]Starting PyShell uninstallation...[/]\n")

    # Confirm uninstallation
    confirm = questionary.confirm(
        "Are you sure you want to uninstall PyShell?", default=False).ask()

    if not confirm:
        console.print(f"[{THEME['border']}]Uninstallation cancelled.[/]\n")
        return False

    try:
        # Simulate uninstallation steps
        steps = [
            "Removing configuration files",
            "Cleaning up directories",
            "Unregistering PyShell",
            "Finalizing uninstallation"
        ]

        for step in track(steps, description=f"[{THEME['border']}]Uninstalling...[/]"):
            time.sleep(0.3)

        # Remove installation marker
        install_marker.unlink()

        # Optionally remove config
        remove_config = questionary.confirm(
            "Remove saved theme configuration?", default=False).ask()
        if remove_config and CONFIG_PATH.exists():
            CONFIG_PATH.unlink()

        console.print(
            f"\n{THEME['success']} PyShell uninstalled successfully!")
        console.print(f"[{THEME['border']}]Goodbye! 👋[/]\n")

        return True

    except Exception as e:
        console.print(f"\n{THEME['error']} Uninstallation failed: {e}\n")
        return False


# -------------------------------------------------------------------------
# Full-Screen TUI REPL
# -------------------------------------------------------------------------
def run_shell_tui(theme_name: str):
    THEME = THEMES[theme_name]
    # --- Style Configuration ---
    bg_hex = rgb_to_hex(*THEME["bg_rgb"])
    text_hex = THEME["text_color"]
    prompt_str = "PyShell > "

    style = PromptStyle.from_dict({
        # A single style for the entire screen background and default text
        '': f'bg:{bg_hex} {text_hex}',
        'prompt': f'bold {THEME["prompt_color"]}',
        'window': f'bg:{bg_hex}',
        'frame': f'bg:{bg_hex}',
    })

    # --- Custom Lexer for coloring the prompt ---
    class PyShellLexer(Lexer):
        def lex_document(self, document):
            lines = document.lines

            def get_line(i):
                line = lines[i]
                if line.startswith(prompt_str):
                    return [('class:prompt', prompt_str), ('', line[len(prompt_str):])]
                else:
                    return [('', line)]
            return get_line

    # --- Data and Buffers ---
    # This function finds the start of the editable command area
    def get_editable_start_pos(buff):
        text = buff.text
        last_prompt_index = text.rfind(prompt_str)
        return last_prompt_index + len(prompt_str) if last_prompt_index != -1 else 0

    # A single buffer for the entire session history and current command
    main_buffer = Buffer(read_only=False)
    main_buffer.text = f"Welcome to PyShell! Type 'exit' or press Ctrl+D to quit.\n{prompt_str}"
    main_buffer.cursor_position = len(main_buffer.text)

    # --- Layout ---
    # The layout is now just a single window that fills the screen
    root_container = Window(
        content=BufferControl(
            buffer=main_buffer,
            lexer=PyShellLexer(),
        ),
        wrap_lines=True,
        style=f'bg:{bg_hex} {text_hex}'
    )
    layout = Layout(root_container, focused_element=root_container)

    # --- Key Bindings ---
    kb = KeyBindings()

    @kb.add('c-d')
    def _(event):
        event.app.exit()

    @kb.add('enter')
    def _(event):
        doc = main_buffer.document
        main_buffer.cursor_position = len(
            doc.text)  # Ensure cursor is at the end
        command = doc.text[get_editable_start_pos(main_buffer):].strip()
        # "Commit" the entered command to history
        main_buffer.insert_text('\n')

        if command.lower() == 'exit':
            event.app.exit()
            return

        if not command:
            main_buffer.insert_text(prompt_str)
            return

        # Execute command and capture all output
        old_stdout, old_stderr = sys.stdout, sys.stderr
        redirected_output = StringIO()
        sys.stdout = sys.stderr = redirected_output

        exit_code = 0
        try:
            tokens = tokenize(command)
            ast = parse(tokens)
            exit_code = execute(ast)
        except Exception as e:
            exit_code = 1
            print(f"Error: {e}")

        sys.stdout, sys.stderr = old_stdout, old_stderr
        command_output = redirected_output.getvalue().rstrip()

        if command_output:
            main_buffer.insert_text(command_output + '\n')

        # Append success or error message
        msg = THEME["success"] if exit_code == 0 else THEME["error"]
        main_buffer.insert_text(Text.from_markup(msg).plain + '\n')

        # Add the next prompt
        main_buffer.insert_text(prompt_str)

    # --- Application ---
    app = Application(layout=layout, key_bindings=kb,
                      style=style, full_screen=True)
    app.run()


# -------------------------------------------------------------------------
# Command mode for -c
# -------------------------------------------------------------------------
def run_command(command_string: str) -> int:
    try:
        state.non_interactive = True
        tokens = tokenize(command_string)
        ast = parse(tokens)
        return execute(ast)
    except SyntaxError as e:
        console.print(f"[bold red]Syntax error:[/bold red] {e}")
        return 2
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1


# -------------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--run-builtin":
        try:
            sys.exit(execute_builtin(sys.argv[2], sys.argv[3:]))
        except Exception as e:
            console.print(
                f"[bold red]Error in background builtin:[/bold red] {e}")
            sys.exit(1)

    elif len(sys.argv) > 2 and sys.argv[1] == "-c":
        sys.exit(run_command(sys.argv[2]))

    else:
        theme_name = select_theme()
        show_intro(theme_name)
        should_continue = show_installer_wizard(theme_name)
        if should_continue:
            run_shell_tui(theme_name)
