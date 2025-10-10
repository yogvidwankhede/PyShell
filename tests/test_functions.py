"""
Test suite for shell functions:
- Function definition (both styles)
- Function calls with parameters
- Return statements
- Local variables
- Positional parameters
"""

import pytest
import subprocess
import sys

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestFunctionDefinition:
    """Test function definition in different styles."""

    def test_function_style1(self):
        result = subprocess.run(
            SHELL_CMD + [
                "greet() { echo hello; }; greet"
            ],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_function_style2(self):
        result = subprocess.run(
            SHELL_CMD + [
                "function greet { echo hello; }; greet"
            ],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_function_style3(self):
        result = subprocess.run(
            SHELL_CMD + [
                "function greet() { echo hello; }; greet"
            ],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_function_with_multiple_commands(self):
        result = subprocess.run(
            SHELL_CMD + [
                "test_func() { echo first; echo second; }; test_func"
            ],
            capture_output=True, text=True
        )
        assert "first" in result.stdout
        assert "second" in result.stdout


class TestFunctionParameters:
    """Test functions with positional parameters."""

    def test_single_parameter(self):
        result = subprocess.run(
            SHELL_CMD + [
                "greet() { echo Hello $1; }; greet World"
            ],
            capture_output=True, text=True
        )
        assert "Hello World" in result.stdout

    def test_multiple_parameters(self):
        result = subprocess.run(
            SHELL_CMD + [
                "greet() { echo $1 $2; }; greet Hello World"
            ],
            capture_output=True, text=True
        )
        assert "Hello World" in result.stdout

    def test_arithmetic_with_params(self):
        result = subprocess.run(
            SHELL_CMD + [
                "add() { echo $(($1 + $2)); }; add 5 3"
            ],
            capture_output=True, text=True
        )
        assert "8" in result.stdout

    def test_all_parameters_at(self):
        result = subprocess.run(
            SHELL_CMD + [
                'show_all() { echo "$@"; }; show_all one two three'
            ],
            capture_output=True, text=True
        )
        assert "one" in result.stdout
        assert "two" in result.stdout
        assert "three" in result.stdout

    def test_parameter_count(self):
        result = subprocess.run(
            SHELL_CMD + [
                "count() { echo $#; }; count a b c"
            ],
            capture_output=True, text=True
        )
        assert "3" in result.stdout

    def test_no_parameters(self):
        result = subprocess.run(
            SHELL_CMD + [
                "no_params() { echo no params; }; no_params"
            ],
            capture_output=True, text=True
        )
        assert "no params" in result.stdout


class TestFunctionReturn:
    """Test function return statements."""

    def test_return_zero(self):
        result = subprocess.run(
            SHELL_CMD + [
                "success() { return 0; }; success && echo ok"
            ],
            capture_output=True, text=True
        )
        assert "ok" in result.stdout

    def test_return_nonzero(self):
        result = subprocess.run(
            SHELL_CMD + [
                "fail() { return 1; }; fail || echo failed"
            ],
            capture_output=True, text=True
        )
        assert "failed" in result.stdout

    def test_return_with_value(self):
        result = subprocess.run(
            SHELL_CMD + [
                "get_code() { return 42; }; get_code; echo $?"
            ],
            capture_output=True, text=True
        )
        assert "42" in result.stdout

    def test_return_early(self):
        result = subprocess.run(
            SHELL_CMD + [
                "early() { return 0; echo should_not_print; }; early"
            ],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout

    def test_implicit_return(self):
        result = subprocess.run(
            SHELL_CMD + [
                "implicit() { true; }; implicit && echo ok"
            ],
            capture_output=True, text=True
        )
        assert "ok" in result.stdout


class TestLocalVariables:
    """Test local variables in functions."""

    def test_local_variable(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=global; test_local() { local x=local; echo $x; }; "
                "test_local; echo $x"
            ],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n')
        assert "local" in lines[0]
        assert "global" in lines[1]

    def test_local_doesnt_affect_global(self):
        result = subprocess.run(
            SHELL_CMD + [
                "count=0; increment() { local count=5; }; increment; echo $count"
            ],
            capture_output=True, text=True
        )
        assert "0" in result.stdout

    def test_function_modifies_global(self):
        result = subprocess.run(
            SHELL_CMD + [
                "x=1; modify() { x=2; }; modify; echo $x"
            ],
            capture_output=True, text=True
        )
        assert "2" in result.stdout


class TestNestedFunctions:
    """Test calling functions from within functions."""

    def test_function_calls_function(self):
        result = subprocess.run(
            SHELL_CMD + [
                "inner() { echo inner; }; "
                "outer() { echo outer; inner; }; "
                "outer"
            ],
            capture_output=True, text=True
        )
        assert "outer" in result.stdout
        assert "inner" in result.stdout

    def test_nested_with_params(self):
        result = subprocess.run(
            SHELL_CMD + [
                "double() { echo $(($1 * 2)); }; "
                "quad() { double $(double $1); }; "
                "quad 5"
            ],
            capture_output=True, text=True
        )
        assert "20" in result.stdout


class TestFunctionScope:
    """Test variable scoping in functions."""

    def test_parameter_scope(self):
        result = subprocess.run(
            SHELL_CMD + [
                "set -- global_arg; "
                "func() { echo $1; }; "
                "func func_arg"
            ],
            capture_output=True, text=True
        )
        assert "func_arg" in result.stdout
        assert "global_arg" not in result.stdout

    def test_nested_parameter_scope(self):
        result = subprocess.run(
            SHELL_CMD + [
                "outer() { "
                "  inner() { echo inner:$1; }; "
                "  echo outer:$1; "
                "  inner nested; "
                "}; "
                "outer param"
            ],
            capture_output=True, text=True
        )
        assert "outer:param" in result.stdout
        assert "inner:nested" in result.stdout


class TestFunctionWithControlFlow:
    """Test functions containing control flow."""

    def test_function_with_if(self):
        result = subprocess.run(
            SHELL_CMD + [
                "check() { if [ $1 -gt 5 ]; then echo big; else echo small; fi; }; "
                "check 10"
            ],
            capture_output=True, text=True
        )
        assert "big" in result.stdout

    def test_function_with_loop(self):
        result = subprocess.run(
            SHELL_CMD + [
                "count_to() { for i in {1..3}; do echo $i; done; }; count_to"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "3" in result.stdout

    def test_function_with_case(self):
        result = subprocess.run(
            SHELL_CMD + [
                "classify() { case $1 in "
                "  [0-9]) echo digit;; "
                "  [a-z]) echo lower;; "
                "  *) echo other;; "
                "esac; }; "
                "classify 5"
            ],
            capture_output=True, text=True
        )
        assert "digit" in result.stdout


class TestRecursiveFunctions:
    """Test recursive function calls."""

    def test_simple_recursion(self):
        result = subprocess.run(
            SHELL_CMD + [
                "countdown() { "
                "  [ $1 -le 0 ] && return; "
                "  echo $1; "
                "  countdown $(($1 - 1)); "
                "}; "
                "countdown 3"
            ],
            capture_output=True, text=True
        )
        assert "3" in result.stdout
        assert "2" in result.stdout
        assert "1" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
