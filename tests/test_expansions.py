"""
Test suite for all expansion features:
- Variable expansion
- Command substitution
- Arithmetic expansion
- Parameter expansion
- Tilde expansion
- Brace expansion
"""

import pytest
import subprocess
import sys
import os

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestVariableExpansion:
    """Test basic variable expansion."""

    def test_simple_variable(self):
        result = subprocess.run(
            SHELL_CMD + ["x=hello; echo $x"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "hello"

    def test_braced_variable(self):
        result = subprocess.run(
            SHELL_CMD + ["name=world; echo ${name}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "world"

    def test_special_variable_exit_status(self):
        result = subprocess.run(
            SHELL_CMD + ["true; echo $?"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "0"

        result = subprocess.run(
            SHELL_CMD + ["false; echo $?"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "1"


class TestCommandSubstitution:
    """Test command substitution with $() and backticks."""

    def test_dollar_paren_substitution(self):
        result = subprocess.run(
            SHELL_CMD + ["echo $(echo hello)"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "hello"

    def test_nested_substitution(self):
        result = subprocess.run(
            SHELL_CMD + ["x=$(echo test); echo $x"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "test"

    def test_substitution_in_string(self):
        result = subprocess.run(
            SHELL_CMD + ['echo "Result: $(echo success)"'],
            capture_output=True, text=True
        )
        assert "Result: success" in result.stdout


class TestArithmeticExpansion:
    """Test arithmetic expansion with $((...))."""

    def test_simple_addition(self):
        result = subprocess.run(
            SHELL_CMD + ["echo $((5 + 3))"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "8"

    def test_multiplication(self):
        result = subprocess.run(
            SHELL_CMD + ["echo $((6 * 7))"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "42"

    def test_complex_expression(self):
        result = subprocess.run(
            SHELL_CMD + ["echo $((10 + 5 * 2))"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "20"

    def test_variable_in_arithmetic(self):
        result = subprocess.run(
            SHELL_CMD + ["x=10; y=5; echo $((x + y))"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "15"

    def test_arithmetic_assignment(self):
        result = subprocess.run(
            SHELL_CMD + ["x=5; y=$((x * 2)); echo $y"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "10"


class TestParameterExpansion:
    """Test advanced parameter expansion."""

    def test_default_value(self):
        result = subprocess.run(
            SHELL_CMD + ["echo ${unset_var:-default}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "default"

    def test_assign_default(self):
        result = subprocess.run(
            SHELL_CMD + ["echo ${new_var:=assigned}; echo $new_var"],
            capture_output=True, text=True
        )
        assert "assigned" in result.stdout

    def test_string_length(self):
        result = subprocess.run(
            SHELL_CMD + ["text=hello; echo ${#text}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "5"

    def test_substring(self):
        result = subprocess.run(
            SHELL_CMD + ["text=hello; echo ${text:1:3}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "ell"

    def test_remove_prefix(self):
        result = subprocess.run(
            SHELL_CMD + ["file=test.txt; echo ${file#*.}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "txt"

    def test_remove_suffix(self):
        result = subprocess.run(
            SHELL_CMD + ["file=document.txt; echo ${file%.txt}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "document"

    def test_replace_first(self):
        result = subprocess.run(
            SHELL_CMD + ["text=hello; echo ${text/l/L}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "heLlo"

    def test_replace_all(self):
        result = subprocess.run(
            SHELL_CMD + ["text=hello; echo ${text//l/L}"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "heLLo"


class TestTildeExpansion:
    """Test tilde expansion."""

    def test_tilde_home(self):
        result = subprocess.run(
            SHELL_CMD + ["echo ~"],
            capture_output=True, text=True
        )
        home = os.path.expanduser("~")
        assert result.stdout.strip() == home

    def test_tilde_with_path(self):
        result = subprocess.run(
            SHELL_CMD + ["echo ~/test"],
            capture_output=True, text=True
        )
        home = os.path.expanduser("~")
        assert result.stdout.strip() == f"{home}/test"


class TestBraceExpansion:
    """Test brace expansion."""

    def test_numeric_range(self):
        result = subprocess.run(
            SHELL_CMD + ["echo {1..5}"],
            capture_output=True, text=True
        )
        assert "1 2 3 4 5" in result.stdout

    def test_char_range(self):
        result = subprocess.run(
            SHELL_CMD + ["echo {a..e}"],
            capture_output=True, text=True
        )
        assert "a b c d e" in result.stdout

    def test_list_expansion(self):
        result = subprocess.run(
            SHELL_CMD + ["echo {one,two,three}"],
            capture_output=True, text=True
        )
        assert "one two three" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
