"""
Test suite for special variables:
- $? (exit status)
- $! (last background PID)
- $$ (current PID)
- $0 (script name)
- $1, $2, ... (positional parameters)
- $# (parameter count)
- $@ and $* (all parameters)
- $- (shell options)
- $_ (last argument)
"""

import pytest
import subprocess
import sys
import os

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestExitStatus:
    """Test $? special variable."""

    def test_exit_status_success(self):
        result = subprocess.run(
            SHELL_CMD + ["true; echo $?"],
            capture_output=True, text=True
        )
        assert "0" in result.stdout

    def test_exit_status_failure(self):
        result = subprocess.run(
            SHELL_CMD + ["false; echo $?"],
            capture_output=True, text=True
        )
        assert "1" in result.stdout

    def test_exit_status_command(self):
        result = subprocess.run(
            SHELL_CMD + ["echo test; echo $?"],
            capture_output=True, text=True
        )
        assert "0" in result.stdout


class TestPositionalParameters:
    """Test $1, $2, $#, $@, $* variables."""

    def test_positional_param_1(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- first second third; echo $1"],
            capture_output=True, text=True
        )
        assert "first" in result.stdout

    def test_positional_param_2(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- first second third; echo $2"],
            capture_output=True, text=True
        )
        assert "second" in result.stdout

    def test_positional_param_count(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- a b c d; echo $#"],
            capture_output=True, text=True
        )
        assert "4" in result.stdout

    def test_all_params_at(self):
        result = subprocess.run(
            SHELL_CMD + ['set -- one two three; echo "$@"'],
            capture_output=True, text=True
        )
        assert "one" in result.stdout
        assert "two" in result.stdout
        assert "three" in result.stdout

    def test_all_params_star(self):
        result = subprocess.run(
            SHELL_CMD + ['set -- x y z; echo "$*"'],
            capture_output=True, text=True
        )
        # $* joins with spaces
        output = result.stdout.strip()
        assert "x" in output and "y" in output and "z" in output


class TestProcessID:
    """Test $$ special variable."""

    def test_current_pid(self):
        result = subprocess.run(
            SHELL_CMD + ["echo $$"],
            capture_output=True, text=True
        )
        # Should print a number (PID)
        assert result.stdout.strip().isdigit()


class TestScriptName:
    """Test $0 special variable."""

    def test_script_name(self):
        result = subprocess.run(
            SHELL_CMD + ["echo $0"],
            capture_output=True, text=True
        )
        # Should have some output (script name or 'pyshell')
        assert len(result.stdout.strip()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
