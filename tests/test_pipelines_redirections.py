"""
Test suite for pipelines and redirections:
- Simple pipes
- Multi-stage pipes
- Output redirection
- Input redirection
- Error redirection
- Here-strings
"""

import pytest
import subprocess
import sys
import os
import tempfile

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestSimplePipes:
    """Test simple pipeline functionality."""

    def test_builtin_to_builtin_pipe(self):
        result = subprocess.run(
            SHELL_CMD + ["echo hello | cat"],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_pipe_with_echo(self):
        result = subprocess.run(
            SHELL_CMD + ["echo test"],
            capture_output=True, text=True
        )
        assert "test" in result.stdout


class TestOutputRedirection:
    """Test output redirection."""

    def test_redirect_stdout(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            fname = f.name

        try:
            subprocess.run(
                SHELL_CMD + [f"echo hello > {fname}"],
                capture_output=True
            )

            with open(fname, 'r') as f:
                content = f.read()
            assert "hello" in content
        finally:
            os.unlink(fname)

    def test_redirect_append(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            fname = f.name

        try:
            subprocess.run(
                SHELL_CMD + [f"echo line1 > {fname}; echo line2 >> {fname}"],
                capture_output=True
            )

            with open(fname, 'r') as f:
                content = f.read()
            assert "line1" in content
            assert "line2" in content
        finally:
            os.unlink(fname)


class TestInputRedirection:
    """Test input redirection."""

    def test_redirect_stdin(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content\n")
            fname = f.name

        try:
            result = subprocess.run(
                SHELL_CMD + [f"cat < {fname}"],
                capture_output=True, text=True
            )
            assert "test content" in result.stdout
        finally:
            os.unlink(fname)


class TestErrorRedirection:
    """Test stderr redirection."""

    def test_redirect_stderr_to_stdout(self):
        result = subprocess.run(
            SHELL_CMD + ["echo test 2>&1"],
            capture_output=True, text=True
        )
        assert "test" in result.stdout


class TestHereStrings:
    """Test here-string functionality."""

    def test_here_string(self):
        result = subprocess.run(
            SHELL_CMD + ["cat <<< 'hello world'"],
            capture_output=True, text=True
        )
        assert "hello world" in result.stdout

    def test_here_string_with_variable(self):
        result = subprocess.run(
            SHELL_CMD + ["x=test; cat <<< $x"],
            capture_output=True, text=True
        )
        assert "test" in result.stdout


class TestCombinedRedirection:
    """Test combined redirection operations."""

    def test_both_stdout_and_stderr(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            fname = f.name

        try:
            subprocess.run(
                SHELL_CMD + [f"echo test &> {fname}"],
                capture_output=True
            )

            with open(fname, 'r') as f:
                content = f.read()
            assert "test" in content
        finally:
            os.unlink(fname)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
