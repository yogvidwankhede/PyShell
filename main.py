"""
PyShell main entry point – Full-screen TUI Edition with CWD support.

Features:
- Opens in the current working directory (matching standard shells)
- Two built-in themes: "Dark Modern" and "Light Modern"
- A true full-screen UI with prompt_toolkit for a stable background
- A simplified, traditional shell-like interface where the prompt follows the output
- The entire screen is a single, scrollable history buffer
- Retains the original installer wizard and intro animation
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
from pyshell.utils import (
    setup_signal_handlers, setup_history, setup_completer,
    check_and_cleanup_jobs, needs_multiline, collect_multiline, get_prompt
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
        "error": "[#F44747]✗ Error[/]",
        "border": "#569CD6",
        "bg_rgb": (30, 30, 30),
        "text_color": "#D4D4D4",
    },
    "Light Modern": {
        "name": "Light Modern",
        "prompt_color": "#0000FF",  # Blue
        "success": "[#098658]✓ Success[/]",  # Dark Green
        "error": "[#AF0000]✗ Error[/]",  # Dark Red
        "border": "#007ACC",
        "bg_rgb": (255, 255, 255),  # White
        "text_color": "#000000",  # Black
    }
}


def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

# -------------------------------------------------------------------------
# Directory and Path Utilities
# -------------------------------------------------------------------------


def get_current_directory():
    """Get the current working directory in a clean format."""
    try:
        cwd = os.getcwd()
        # Normalize path separators for consistency
        return cwd.replace('\\', '/')
    except Exception:
        return str(Path.home())


def format_prompt_with_cwd():
    """Format the shell prompt with current directory."""
    cwd = get_current_directory()
    # Show just the directory name, or full path if desired
    dir_name = Path(cwd).name or cwd
    return f"PyShell:{dir_name} > "


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
    # Check if theme is already saved (existing user)
    saved = load_theme()

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

    if saved:
        # MODIFICATION: Ask existing user if they want to use their saved theme.
        use_saved = questionary.confirm(
            f"Use saved theme: '{saved}'?",
            default=True,
            style=custom_style,
            qmark="🎨"
        ).ask()

        if use_saved is None:  # User cancelled with Ctrl+C
            return saved  # Default to saved theme on cancel
        if use_saved:
            return saved
        # If 'no', fall through to show the full theme selection list.

    # New user OR existing user who wants to change theme
    console.print("\n[bold cyan]✧ Select a PyShell Theme[/bold cyan]\n")

    choices_list = [Choice(t) for t in THEMES.keys()]

    theme_choice = questionary.select(
        "Choose your preferred theme:",
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

    # Show current directory
    cwd_text = Text(
        f"Current Directory: {get_current_directory()}\n", style="dim cyan")

    console.print(Panel.fit(banner + subtitle + cwd_text,
                            border_style=THEME['border']))
    time.sleep(1)


def show_installer_wizard(theme_name: str) -> bool:
    """
    Shows installer wizard and returns True if should continue to shell, False to exit.
    """
    THEME = THEMES[theme_name]
    console.print(
        "\n[bold white]Installation wizard for [cyan]PyShell[/cyan][/bold white]\n"
    )

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

    install_marker = Path.home() / ".pyshell_installed"

    # Adjust menu based on installation status
    if install_marker.exists():
        choices_list = [
            "🚀  Continue to PyShell",
            "🧹  Uninstall PyShell",
            "🚪  Exit"
        ]
    else:
        choices_list = [
            "🔧  Install PyShell",
            "🚪  Exit"
        ]

    choice = questionary.select(
        "Select an action:",
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
    elif choice == "🚀  Continue to PyShell":
        console.print(f"\n[{THEME['border']}]Launching PyShell...[/]\n")
        console.print(
            f"[{THEME['border']}]Starting in: {get_current_directory()}[/]\n")
        return True
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
# MODIFICATION: Custom Buffer to create a read-only prompt region.
class PyShellBuffer(Buffer):
    """
    A custom buffer that prevents editing of text before a designated
    'editable_start_pos'. This makes the prompt and past output read-only.
    """

    def __init__(self, *args, **kwargs):
        self.editable_start_pos = 0
        super().__init__(*args, **kwargs)

    def insert_text(self, data, overwrite=False, move_cursor=True, fire_events=True):
        # Allow insertion only if the cursor is in the editable area.
        if self.cursor_position < self.editable_start_pos:
            self.cursor_position = len(self.text)  # Move cursor to end
        super().insert_text(data, overwrite, move_cursor, fire_events)

    def delete(self, count=1):
        # Allow deletion only if the selection starts in the editable area.
        if self.cursor_position < self.editable_start_pos:
            return
        super().delete(count)

    def delete_before_cursor(self, count=1):
        # Allow backspace only if it doesn't cross into the read-only part.
        if self.cursor_position > self.editable_start_pos:
            # Calculate how many characters can be safely deleted.
            deletable_chars = self.cursor_position - self.editable_start_pos
            actual_count = min(count, deletable_chars)
            if actual_count > 0:
                super().delete_before_cursor(actual_count)


def run_shell_tui(theme_name: str):
    THEME = THEMES[theme_name]

    # Initialize shell utilities
    setup_signal_handlers()
    setup_history()
    setup_completer()

    # Set up initial environment
    os.environ['PWD'] = get_current_directory()
    state.PS1 = "$ "  # Will be overridden by format_prompt_with_cwd()

    # --- Style Configuration ---
    bg_hex = rgb_to_hex(*THEME["bg_rgb"])
    text_hex = THEME["text_color"]

    def get_prompt_str():
        """Get current prompt string with directory."""
        return format_prompt_with_cwd()

    style = PromptStyle.from_dict({
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
                # Check if line starts with any prompt pattern
                if line.startswith("PyShell:"):
                    # Find where the prompt ends (after " > ")
                    prompt_end = line.find(" > ") + 3
                    if prompt_end > 2:
                        return [('class:prompt', line[:prompt_end]), ('', line[prompt_end:])]
                return [('', line)]
            return get_line

    # --- Data and Buffers ---
    # MODIFICATION: Use the custom PyShellBuffer for read-only prompt behavior.
    main_buffer = PyShellBuffer()

    # Initialize with welcome message and first prompt
    welcome_msg = f"Welcome to PyShell!\nCurrent Directory: {get_current_directory()}\n"
    welcome_msg += f"Type 'exit' or press Ctrl+D to quit.\n\n"
    initial_prompt = get_prompt_str()

    main_buffer.text = welcome_msg + initial_prompt
    main_buffer.cursor_position = len(main_buffer.text)
    # MODIFICATION: Set the initial read-only boundary after the first prompt.
    main_buffer.editable_start_pos = len(main_buffer.text)

    # --- Layout ---
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
        main_buffer.cursor_position = len(doc.text)

        # MODIFICATION: Get command from the editable part of the buffer.
        command = doc.text[main_buffer.editable_start_pos:].strip()

        # "Commit" the entered command
        main_buffer.insert_text('\n')
        # MODIFICATION: Lock the submitted command line.
        main_buffer.editable_start_pos = len(main_buffer.text)

        if command.lower() == 'exit':
            event.app.exit()
            return

        if not command:
            # Add a new prompt if the user just pressed Enter
            main_buffer.insert_text(get_prompt_str())
            main_buffer.editable_start_pos = len(main_buffer.text)
            return

        # Check for directory change commands to update prompt
        command_lower = command.lower().strip()
        is_cd_command = command_lower.startswith('cd ')

        # Execute command and capture all output
        old_stdout, old_stderr = sys.stdout, sys.stderr
        redirected_output = StringIO()
        sys.stdout = sys.stderr = redirected_output

        exit_code = 0
        try:
            tokens = tokenize(command)
            ast = parse(tokens)
            exit_code = execute(ast)
            state.last_exit_status = exit_code
        except Exception as e:
            exit_code = 1
            print(f"Error: {e}")

        sys.stdout, sys.stderr = old_stdout, old_stderr
        command_output = redirected_output.getvalue().rstrip()

        if command_output:
            main_buffer.insert_text(command_output + '\n')

        # Check for background jobs
        check_and_cleanup_jobs()

        # Update environment PWD if directory changed
        if is_cd_command:
            os.environ['PWD'] = get_current_directory()
            # Show the new directory after cd command
            main_buffer.insert_text(
                f"[Current Directory: {get_current_directory()}]\n")

        # Append success or error message
        msg = THEME["success"] if exit_code == 0 else THEME["error"]
        main_buffer.insert_text(Text.from_markup(msg).plain + '\n')

        # Add the next prompt (with updated directory)
        main_buffer.insert_text(get_prompt_str())

        # MODIFICATION: Update the read-only boundary for the new prompt.
        main_buffer.editable_start_pos = len(main_buffer.text)

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
        # Ensure we're in the current directory
        os.environ['PWD'] = get_current_directory()

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
# Main entry point function (for setup.py console_scripts)
# -------------------------------------------------------------------------
def main():
    """Main entry point for PyShell when installed as a package."""
    # Store the original working directory
    original_cwd = os.getcwd()

    # Handle builtin execution in background
    if len(sys.argv) > 2 and sys.argv[1] == "--run-builtin":
        try:
            sys.exit(execute_builtin(sys.argv[2], sys.argv[3:]))
        except Exception as e:
            console.print(
                f"[bold red]Error in background builtin:[/bold red] {e}")
            sys.exit(1)

    # Handle -c command mode
    elif len(sys.argv) > 2 and sys.argv[1] == "-c":
        sys.exit(run_command(sys.argv[2]))

    # Interactive mode
    else:
        # Make sure we're in the directory where the shell was launched
        try:
            os.chdir(original_cwd)
        except Exception:
            pass

        theme_name = select_theme()
        show_intro(theme_name)
        should_continue = show_installer_wizard(theme_name)
        if should_continue:
            run_shell_tui(theme_name)


# -------------------------------------------------------------------------
# Entry point when run directly
# -------------------------------------------------------------------------
if __name__ == "__main__":
    main()
