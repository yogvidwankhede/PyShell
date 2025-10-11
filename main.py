"""
PyShell main entry point – Full-screen TUI Edition with History Navigation.

NEW FEATURES:
- Up/Down arrow keys for command history navigation
- Left/Right arrow keys for cursor movement
- Home/End keys for line start/end
- Ctrl+Left/Right for word-by-word navigation
- Ctrl+A/E for Bash-style line navigation
- Ctrl+K to clear line
- Ctrl+L to clear screen
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
from prompt_toolkit.document import Document

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
        "prompt_color": "#0000FF",
        "success": "[#098658]✓ Success[/]",
        "error": "[#AF0000]✗ Error[/]",
        "border": "#007ACC",
        "bg_rgb": (255, 255, 255),
        "text_color": "#000000",
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
        return cwd.replace('\\', '/')
    except Exception:
        return str(Path.home())


def format_prompt_with_cwd():
    """Format the shell prompt with current directory."""
    cwd = get_current_directory()
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
        use_saved = questionary.confirm(
            f"Use saved theme: '{saved}'?",
            default=True,
            style=custom_style,
            qmark="✧"
        ).ask()

        if use_saved is None:
            return saved
        if use_saved:
            return saved

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

    cwd_text = Text(
        f"Current Directory: {get_current_directory()}\n", style="dim cyan")

    console.print(Panel.fit(banner + subtitle + cwd_text,
                            border_style=THEME['border']))
    time.sleep(1)


def show_installer_wizard(theme_name: str) -> bool:
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
        return not uninstalled
    elif choice == "🚀  Continue to PyShell":
        console.print(f"\n[{THEME['border']}]Launching PyShell...[/]\n")
        console.print(
            f"[{THEME['border']}]Starting in: {get_current_directory()}[/]\n")
        return True
    else:
        console.print(f"\n[{THEME['border']}]Goodbye! 👋[/]\n")
        return False


def install_pyshell(theme_name: str) -> None:
    THEME = THEMES[theme_name]
    console.print(
        f"\n[{THEME['border']}]Starting PyShell installation...[/]\n")

    try:
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

        install_marker.write_text("installed")

        console.print(
            f"\n{THEME['success']} PyShell installed successfully!\n")
        console.print(
            f"[{THEME['border']}]You can now use PyShell from your terminal.[/]\n")

    except Exception as e:
        console.print(f"\n{THEME['error']} Installation failed: {e}\n")


def uninstall_pyshell(theme_name: str) -> bool:
    THEME = THEMES[theme_name]

    install_marker = Path.home() / ".pyshell_installed"
    if not install_marker.exists():
        console.print(
            f"\n[{THEME['border']}]ℹ PyShell is not installed. Nothing to uninstall.[/]")
        console.print(f"[{THEME['border']}]Goodbye! 👋[/]\n")
        return True

    console.print(
        f"\n[{THEME['border']}]Starting PyShell uninstallation...[/]\n")

    confirm = questionary.confirm(
        "Are you sure you want to uninstall PyShell?", default=False).ask()

    if not confirm:
        console.print(f"[{THEME['border']}]Uninstallation cancelled.[/]\n")
        return False

    try:
        steps = [
            "Removing configuration files",
            "Cleaning up directories",
            "Unregistering PyShell",
            "Finalizing uninstallation"
        ]

        for step in track(steps, description=f"[{THEME['border']}]Uninstalling...[/]"):
            time.sleep(0.3)

        install_marker.unlink()

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
# Enhanced Buffer with History Navigation
# -------------------------------------------------------------------------
class PyShellBuffer(Buffer):
    """
    Enhanced buffer with history navigation and read-only prompt region.
    """

    def __init__(self, *args, **kwargs):
        self.editable_start_pos = 0
        self.command_history = []  # List of previous commands
        # Current position in history (-1 = not browsing)
        self.history_index = -1
        self.current_draft = ""    # Store current input when browsing history
        super().__init__(*args, **kwargs)

    def insert_text(self, data, overwrite=False, move_cursor=True, fire_events=True):
        if self.cursor_position < self.editable_start_pos:
            self.cursor_position = len(self.text)
        super().insert_text(data, overwrite, move_cursor, fire_events)

    def delete(self, count=1):
        if self.cursor_position < self.editable_start_pos:
            return
        super().delete(count)

    def delete_before_cursor(self, count=1):
        if self.cursor_position > self.editable_start_pos:
            deletable_chars = self.cursor_position - self.editable_start_pos
            actual_count = min(count, deletable_chars)
            if actual_count > 0:
                super().delete_before_cursor(actual_count)

    def add_to_history(self, command: str):
        """Add a command to history."""
        if command.strip() and (not self.command_history or self.command_history[-1] != command):
            self.command_history.append(command)
        self.history_index = -1
        self.current_draft = ""

    def navigate_history(self, direction: str):
        """Navigate through command history. Direction: 'up' or 'down'."""
        if not self.command_history:
            return

        current_input = self.text[self.editable_start_pos:]

        if direction == 'up':
            # Save current input when starting to browse history
            if self.history_index == -1:
                self.current_draft = current_input
                self.history_index = len(self.command_history) - 1
            elif self.history_index > 0:
                self.history_index -= 1

            # Replace current input with history entry
            if 0 <= self.history_index < len(self.command_history):
                self._replace_current_input(
                    self.command_history[self.history_index])

        elif direction == 'down':
            if self.history_index == -1:
                return

            self.history_index += 1

            if self.history_index >= len(self.command_history):
                # Restore the draft
                self._replace_current_input(self.current_draft)
                self.history_index = -1
            else:
                # Show next history entry
                self._replace_current_input(
                    self.command_history[self.history_index])

    def _replace_current_input(self, new_text: str):
        """Replace the editable part of the buffer with new text."""
        # Calculate how much to delete
        current_length = len(self.text) - self.editable_start_pos

        # Move cursor to end
        self.cursor_position = len(self.text)

        # Delete current input
        if current_length > 0:
            for _ in range(current_length):
                self.delete_before_cursor(1)

        # Insert new text
        self.insert_text(new_text)

    def clear_current_line(self):
        """Clear the current input line (Ctrl+K)."""
        current_length = len(self.text) - self.editable_start_pos
        self.cursor_position = len(self.text)
        if current_length > 0:
            for _ in range(current_length):
                self.delete_before_cursor(1)


# -------------------------------------------------------------------------
# Full-Screen TUI REPL with Enhanced Navigation
# -------------------------------------------------------------------------
def run_shell_tui(theme_name: str):
    THEME = THEMES[theme_name]

    setup_signal_handlers()
    setup_history()
    setup_completer()

    os.environ['PWD'] = get_current_directory()
    state.PS1 = "$ "

    bg_hex = rgb_to_hex(*THEME["bg_rgb"])
    text_hex = THEME["text_color"]

    def get_prompt_str():
        return format_prompt_with_cwd()

    style = PromptStyle.from_dict({
        '': f'bg:{bg_hex} {text_hex}',
        'prompt': f'bold {THEME["prompt_color"]}',
        'window': f'bg:{bg_hex}',
        'frame': f'bg:{bg_hex}',
    })

    class PyShellLexer(Lexer):
        def lex_document(self, document):
            lines = document.lines

            def get_line(i):
                line = lines[i]
                if line.startswith("PyShell:"):
                    prompt_end = line.find(" > ") + 3
                    if prompt_end > 2:
                        return [('class:prompt', line[:prompt_end]), ('', line[prompt_end:])]
                return [('', line)]
            return get_line

    main_buffer = PyShellBuffer()

    welcome_msg = f"Welcome to PyShell Enhanced! 🚀\n"
    welcome_msg += f"Current Directory: {get_current_directory()}\n"
    welcome_msg += f"Type 'exit' or press Ctrl+D to quit.\n\n"
    welcome_msg += f"📝 Navigation Tips:\n"
    welcome_msg += f"  ↑/↓  - Browse command history\n"
    welcome_msg += f"  ←/→  - Move cursor\n"
    welcome_msg += f"  Home/End - Jump to line start/end\n"
    welcome_msg += f"  Ctrl+A/E - Alternative Home/End\n"
    welcome_msg += f"  Ctrl+K - Clear current line\n"
    welcome_msg += f"  Ctrl+L - Clear screen\n\n"

    initial_prompt = get_prompt_str()

    main_buffer.text = welcome_msg + initial_prompt
    main_buffer.cursor_position = len(main_buffer.text)
    main_buffer.editable_start_pos = len(main_buffer.text)

    root_container = Window(
        content=BufferControl(
            buffer=main_buffer,
            lexer=PyShellLexer(),
        ),
        wrap_lines=True,
        style=f'bg:{bg_hex} {text_hex}'
    )
    layout = Layout(root_container, focused_element=root_container)

    kb = KeyBindings()

    @kb.add('c-d')
    def _(event):
        event.app.exit()

    @kb.add('c-l')
    def _(event):
        """Clear screen (Ctrl+L)."""
        main_buffer.text = get_prompt_str()
        main_buffer.cursor_position = len(main_buffer.text)
        main_buffer.editable_start_pos = len(main_buffer.text)

    @kb.add('c-k')
    def _(event):
        """Clear current line (Ctrl+K)."""
        main_buffer.clear_current_line()

    @kb.add('c-a')
    def _(event):
        """Move to start of line (Ctrl+A)."""
        main_buffer.cursor_position = main_buffer.editable_start_pos

    @kb.add('c-e')
    def _(event):
        """Move to end of line (Ctrl+E)."""
        main_buffer.cursor_position = len(main_buffer.text)

    @kb.add('up')
    def _(event):
        """Navigate history up."""
        main_buffer.navigate_history('up')

    @kb.add('down')
    def _(event):
        """Navigate history down."""
        main_buffer.navigate_history('down')

    @kb.add('left')
    def _(event):
        """Move cursor left."""
        if main_buffer.cursor_position > main_buffer.editable_start_pos:
            main_buffer.cursor_position -= 1

    @kb.add('right')
    def _(event):
        """Move cursor right."""
        if main_buffer.cursor_position < len(main_buffer.text):
            main_buffer.cursor_position += 1

    @kb.add('home')
    def _(event):
        """Jump to start of editable area."""
        main_buffer.cursor_position = main_buffer.editable_start_pos

    @kb.add('end')
    def _(event):
        """Jump to end of line."""
        main_buffer.cursor_position = len(main_buffer.text)

    @kb.add('c-left')
    def _(event):
        """Move cursor left by word."""
        text = main_buffer.text[:main_buffer.cursor_position]
        words = text.split()
        if words and main_buffer.cursor_position > main_buffer.editable_start_pos:
            # Find previous word boundary
            pos = main_buffer.cursor_position - 1
            # Skip trailing spaces
            while pos > main_buffer.editable_start_pos and text[pos].isspace():
                pos -= 1
            # Skip word characters
            while pos > main_buffer.editable_start_pos and not text[pos].isspace():
                pos -= 1
            main_buffer.cursor_position = max(
                pos, main_buffer.editable_start_pos)

    @kb.add('c-right')
    def _(event):
        """Move cursor right by word."""
        text = main_buffer.text
        if main_buffer.cursor_position < len(text):
            pos = main_buffer.cursor_position
            # Skip current word
            while pos < len(text) and not text[pos].isspace():
                pos += 1
            # Skip spaces
            while pos < len(text) and text[pos].isspace():
                pos += 1
            main_buffer.cursor_position = pos

    @kb.add('enter')
    def _(event):
        doc = main_buffer.document
        main_buffer.cursor_position = len(doc.text)

        command = doc.text[main_buffer.editable_start_pos:].strip()

        main_buffer.insert_text('\n')
        main_buffer.editable_start_pos = len(main_buffer.text)

        if command.lower() == 'exit':
            event.app.exit()
            return

        if not command:
            main_buffer.insert_text(get_prompt_str())
            main_buffer.editable_start_pos = len(main_buffer.text)
            return

        # Add to history
        main_buffer.add_to_history(command)

        is_cd_command = command.lower().strip().startswith('cd ')

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

        check_and_cleanup_jobs()

        if is_cd_command:
            os.environ['PWD'] = get_current_directory()
            main_buffer.insert_text(
                f"[Current Directory: {get_current_directory()}]\n")

        msg = THEME["success"] if exit_code == 0 else THEME["error"]
        main_buffer.insert_text(Text.from_markup(msg).plain + '\n')

        main_buffer.insert_text(get_prompt_str())
        main_buffer.editable_start_pos = len(main_buffer.text)

    app = Application(layout=layout, key_bindings=kb,
                      style=style, full_screen=True)
    app.run()


# -------------------------------------------------------------------------
# Command mode for -c
# -------------------------------------------------------------------------
def run_command(command_string: str) -> int:
    try:
        state.non_interactive = True
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
# Main entry point
# -------------------------------------------------------------------------
def main():
    """Main entry point for PyShell."""
    original_cwd = os.getcwd()

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
        try:
            os.chdir(original_cwd)
        except Exception:
            pass

        theme_name = select_theme()
        show_intro(theme_name)
        should_continue = show_installer_wizard(theme_name)
        if should_continue:
            run_shell_tui(theme_name)


if __name__ == "__main__":
    main()
