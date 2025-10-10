"""
Test suite for control flow:
- if/elif/else/fi
- while loops
- until loops
- for loops
- case statements
- break/continue
"""

import pytest
import subprocess
import sys

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestIfStatement:
    """Test if/elif/else/fi statements."""

    def test_simple_if_true(self):
        result = subprocess.run(
            SHELL_CMD + ["if true; then echo yes; fi"],
            capture_output=True, text=True
        )
        assert "yes" in result.stdout

    def test_simple_if_false(self):
        result = subprocess.run(
            SHELL_CMD + ["if false; then echo yes; else echo no; fi"],
            capture_output=True, text=True
        )
        assert "no" in result.stdout

    def test_if_with_test_command(self):
        result = subprocess.run(
            SHELL_CMD + ["if [ 5 -lt 10 ]; then echo yes; fi"],
            capture_output=True, text=True
        )
        assert "yes" in result.stdout

    def test_elif_first_match(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=1; if [ $x -eq 0 ]; then echo zero; "
                "elif [ $x -eq 1 ]; then echo one; "
                "else echo other; fi"
            ],
            capture_output=True, text=True
        )
        assert "one" in result.stdout

    def test_elif_second_match(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=2; if [ $x -eq 0 ]; then echo zero; "
                "elif [ $x -eq 1 ]; then echo one; "
                "elif [ $x -eq 2 ]; then echo two; "
                "else echo other; fi"
            ],
            capture_output=True, text=True
        )
        assert "two" in result.stdout

    def test_elif_else(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=5; if [ $x -eq 0 ]; then echo zero; "
                "elif [ $x -eq 1 ]; then echo one; "
                "else echo other; fi"
            ],
            capture_output=True, text=True
        )
        assert "other" in result.stdout

    def test_multiple_elif(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=3; if [ $x -eq 1 ]; then echo one; "
                "elif [ $x -eq 2 ]; then echo two; "
                "elif [ $x -eq 3 ]; then echo three; "
                "elif [ $x -eq 4 ]; then echo four; "
                "else echo other; fi"
            ],
            capture_output=True, text=True
        )
        assert "three" in result.stdout

    def test_nested_if(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=5; if [ $x -gt 0 ]; then "
                "  if [ $x -lt 10 ]; then echo medium; fi; "
                "fi"
            ],
            capture_output=True, text=True
        )
        assert "medium" in result.stdout


class TestWhileLoop:
    """Test while loops."""

    def test_simple_while(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; while [ $i -lt 3 ]; do echo $i; i=$((i + 1)); done"
            ],
            capture_output=True, text=True
        )
        assert "0" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout

    def test_while_with_break(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; while true; do echo $i; i=$((i + 1)); "
                "[ $i -eq 3 ] && break; done"
            ],
            capture_output=True, text=True
        )
        assert "0" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" not in result.stdout

    def test_while_with_continue(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; while [ $i -lt 5 ]; do i=$((i + 1)); "
                "[ $i -eq 3 ] && continue; echo $i; done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "4" in result.stdout
        assert "5" in result.stdout

    def test_while_false_never_executes(self):
        result = subprocess.run(
            SHELL_CMD + [
                "while false; do echo should_not_print; done; echo after"
            ],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout
        assert "after" in result.stdout


class TestUntilLoop:
    """Test until loops."""

    def test_simple_until(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; until [ $i -eq 3 ]; do echo $i; i=$((i + 1)); done"
            ],
            capture_output=True, text=True
        )
        assert "0" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" not in result.stdout

    def test_until_with_break(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; until false; do echo $i; i=$((i + 1)); "
                "[ $i -eq 3 ] && break; done"
            ],
            capture_output=True, text=True
        )
        assert "0" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout

    def test_until_true_never_executes(self):
        result = subprocess.run(
            SHELL_CMD + [
                "until true; do echo should_not_print; done; echo after"
            ],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout
        assert "after" in result.stdout


class TestForLoop:
    """Test for loops."""

    def test_for_list(self):
        result = subprocess.run(
            SHELL_CMD + ["for i in one two three; do echo $i; done"],
            capture_output=True, text=True
        )
        assert "one" in result.stdout
        assert "two" in result.stdout
        assert "three" in result.stdout

    def test_for_range(self):
        result = subprocess.run(
            SHELL_CMD + ["for i in {1..5}; do echo $i; done"],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" in result.stdout
        assert "4" in result.stdout
        assert "5" in result.stdout

    def test_for_with_break(self):
        result = subprocess.run(
            SHELL_CMD + [
                "for i in 1 2 3 4 5; do echo $i; [ $i = 3 ] && break; done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" in result.stdout
        assert "4" not in result.stdout

    def test_for_with_continue(self):
        result = subprocess.run(
            SHELL_CMD + [
                "for i in 1 2 3 4 5; do [ $i = 3 ] && continue; echo $i; done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "4" in result.stdout
        assert "5" in result.stdout

    def test_for_empty_list(self):
        result = subprocess.run(
            SHELL_CMD + ["for i in ; do echo $i; done; echo done"],
            capture_output=True, text=True
        )
        assert "done" in result.stdout

    def test_for_with_variables(self):
        result = subprocess.run(
            SHELL_CMD + [
                "list='a b c'; for item in $list; do echo $item; done"
            ],
            capture_output=True, text=True
        )
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout


class TestCaseStatement:
    """Test case statements."""

    def test_case_exact_match(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=apple; case $x in "
                "apple) echo fruit ;; "
                "*) echo unknown ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "fruit" in result.stdout

    def test_case_wildcard(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=test.txt; case $x in "
                "*.txt) echo text_file ;; "
                "*) echo unknown ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "text_file" in result.stdout

    def test_case_multiple_patterns(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=banana; case $x in "
                "apple|orange) echo citrus ;; "
                "banana|grape) echo other_fruit ;; "
                "*) echo unknown ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "other_fruit" in result.stdout

    def test_case_default(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=unknown; case $x in "
                "apple) echo fruit ;; "
                "*) echo default ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "default" in result.stdout

    def test_case_with_numbers(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=2; case $x in "
                "1) echo one ;; "
                "2) echo two ;; "
                "3) echo three ;; "
                "*) echo other ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "two" in result.stdout

    def test_case_pattern_matching(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=file123; case $x in "
                "file[0-9]*) echo matched ;; "
                "*) echo no_match ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "matched" in result.stdout


class TestBreakContinue:
    """Test break and continue with levels."""

    def test_break_single_level(self):
        result = subprocess.run(
            SHELL_CMD + [
                "for i in 1 2 3; do echo $i; break; done; echo after"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" not in result.stdout
        assert "after" in result.stdout

    def test_continue_single_level(self):
        result = subprocess.run(
            SHELL_CMD + [
                "for i in 1 2 3; do [ $i = 2 ] && continue; echo $i; done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "3" in result.stdout

    def test_break_in_while(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; while [ $i -lt 10 ]; do i=$((i + 1)); "
                "[ $i -eq 5 ] && break; echo $i; done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "4" in result.stdout
        assert "5" not in result.stdout

    def test_continue_in_while(self):
        result = subprocess.run(
            SHELL_CMD + [
                "i=0; while [ $i -lt 5 ]; do i=$((i + 1)); "
                "[ $i -eq 3 ] && continue; echo $i; done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "4" in result.stdout
        assert "5" in result.stdout


class TestLogicalOperators:
    """Test && and || operators."""

    def test_and_operator_success(self):
        result = subprocess.run(
            SHELL_CMD + ["true && echo success"],
            capture_output=True, text=True
        )
        assert "success" in result.stdout

    def test_and_operator_failure(self):
        result = subprocess.run(
            SHELL_CMD + ["false && echo should_not_print"],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout

    def test_or_operator_success(self):
        result = subprocess.run(
            SHELL_CMD + ["true || echo should_not_print"],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout

    def test_or_operator_failure(self):
        result = subprocess.run(
            SHELL_CMD + ["false || echo fallback"],
            capture_output=True, text=True
        )
        assert "fallback" in result.stdout

    def test_chained_and_operators(self):
        result = subprocess.run(
            SHELL_CMD + ["true && echo first && echo second"],
            capture_output=True, text=True
        )
        assert "first" in result.stdout
        assert "second" in result.stdout

    def test_chained_or_operators(self):
        result = subprocess.run(
            SHELL_CMD + ["false || false || echo third"],
            capture_output=True, text=True
        )
        assert "third" in result.stdout

    def test_mixed_operators(self):
        result = subprocess.run(
            SHELL_CMD + ["true && false || echo fallback"],
            capture_output=True, text=True
        )
        assert "fallback" in result.stdout

    def test_and_short_circuit(self):
        result = subprocess.run(
            SHELL_CMD + ["false && echo not_executed; echo after"],
            capture_output=True, text=True
        )
        assert "not_executed" not in result.stdout
        assert "after" in result.stdout

    def test_or_short_circuit(self):
        result = subprocess.run(
            SHELL_CMD + ["true || echo not_executed; echo after"],
            capture_output=True, text=True
        )
        assert "not_executed" not in result.stdout
        assert "after" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
