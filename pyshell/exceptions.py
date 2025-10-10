"""
Defines custom exceptions used for shell control flow.
"""


class ReturnFromFunction(Exception):
    """Raised when a 'return' statement is executed inside a shell function."""

    def __init__(self, code=0):
        self.code = int(code)
        super().__init__(f"Return from function with code {code}")


class BreakLoop(Exception):
    """Raised when a 'break' statement is executed (for nested break levels)."""

    def __init__(self, levels=1):
        self.levels = int(levels)
        super().__init__(f"Break loop with {levels} level(s)")


class ContinueLoop(Exception):
    """Raised when a 'continue' statement is executed (for nested continue levels)."""

    def __init__(self, levels=1):
        self.levels = int(levels)
        super().__init__(f"Continue loop with {levels} level(s)")


class ShellExit(Exception):
    """Raised when 'exit' command is called."""

    def __init__(self, code=0):
        self.code = int(code)
        super().__init__(f"Shell exit with code {code}")
