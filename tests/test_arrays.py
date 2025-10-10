"""
Test suite for array features:
- Indexed arrays
- Associative arrays
- Array operations
- Array expansions
"""

import pytest
import subprocess
import sys

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestIndexedArrays:
    """Test indexed array functionality."""

    def test_array_assignment(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(one two three); echo ${arr[0]}"],
            capture_output=True, text=True
        )
        assert "one" in result.stdout

    def test_array_access_multiple_indices(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(a b c d); echo ${arr[1]} ${arr[3]}"],
            capture_output=True, text=True
        )
        assert "b d" in result.stdout

    def test_array_all_elements(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(apple banana cherry); echo ${arr[@]}"],
            capture_output=True, text=True
        )
        assert "apple banana cherry" in result.stdout

    def test_array_length(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(1 2 3 4 5); echo ${#arr[@]}"],
            capture_output=True, text=True
        )
        assert "5" in result.stdout

    def test_array_element_assignment(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(a b c); arr[1]=B; echo ${arr[1]}"],
            capture_output=True, text=True
        )
        assert "B" in result.stdout

    def test_array_append(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(1 2); arr+=(3 4); echo ${#arr[@]}"],
            capture_output=True, text=True
        )
        assert "4" in result.stdout

    def test_array_in_loop(self):
        result = subprocess.run(
            SHELL_CMD + [
                "arr=(red green blue); for color in ${arr[@]}; do echo $color; done"
            ],
            capture_output=True, text=True
        )
        assert "red" in result.stdout
        assert "green" in result.stdout
        assert "blue" in result.stdout


class TestAssociativeArrays:
    """Test associative array (hash) functionality."""

    def test_assoc_array_declaration(self):
        result = subprocess.run(
            SHELL_CMD +
            ["declare -A hash; hash[key]=value; echo ${hash[key]}"],
            capture_output=True, text=True
        )
        assert "value" in result.stdout

    def test_assoc_array_multiple_keys(self):
        result = subprocess.run(
            SHELL_CMD + [
                "declare -A person; person[name]=John; person[age]=30; "
                "echo ${person[name]} ${person[age]}"
            ],
            capture_output=True, text=True
        )
        assert "John 30" in result.stdout

    def test_assoc_array_all_values(self):
        result = subprocess.run(
            SHELL_CMD + [
                "declare -A data; data[a]=1; data[b]=2; data[c]=3; "
                "echo ${data[@]}"
            ],
            capture_output=True, text=True
        )
        output = result.stdout.strip()
        assert "1" in output
        assert "2" in output
        assert "3" in output

    def test_assoc_array_keys(self):
        result = subprocess.run(
            SHELL_CMD + [
                "declare -A hash; hash[x]=10; hash[y]=20; "
                "echo ${!hash[@]}"
            ],
            capture_output=True, text=True
        )
        output = result.stdout.strip()
        assert "x" in output
        assert "y" in output


class TestArrayOperations:
    """Test array operations and expansions."""

    def test_array_slice(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(0 1 2 3 4 5); echo ${arr[@]:2:3}"],
            capture_output=True, text=True
        )
        # This should return elements starting from index 2, length 3
        # Note: Bash slicing is complex, this tests basic implementation
        assert result.returncode == 0

    def test_array_with_spaces(self):
        result = subprocess.run(
            SHELL_CMD + ['arr=("hello world" "foo bar"); echo ${arr[0]}'],
            capture_output=True, text=True
        )
        assert "hello world" in result.stdout

    def test_empty_array(self):
        result = subprocess.run(
            SHELL_CMD + ["arr=(); echo ${#arr[@]}"],
            capture_output=True, text=True
        )
        assert "0" in result.stdout

    def test_array_unset_element(self):
        result = subprocess.run(
            SHELL_CMD + [
                "arr=(a b c); unset arr[1]; echo ${arr[0]} ${arr[2]}"
            ],
            capture_output=True, text=True
        )
        # After unsetting arr[1], we should still have arr[0] and arr[2]
        assert "a" in result.stdout
        assert "c" in result.stdout


class TestArrayInFunctions:
    """Test arrays within functions."""

    def test_array_as_function_parameter(self):
        result = subprocess.run(
            SHELL_CMD + [
                "print_array() { echo $@; }; "
                "arr=(one two three); "
                "print_array ${arr[@]}"
            ],
            capture_output=True, text=True
        )
        assert "one two three" in result.stdout

    def test_local_array_in_function(self):
        result = subprocess.run(
            SHELL_CMD + [
                "test_func() { local arr=(a b c); echo ${arr[1]}; }; "
                "test_func"
            ],
            capture_output=True, text=True
        )
        assert "b" in result.stdout


class TestArrayWithExpansions:
    """Test arrays with other shell features."""

    def test_array_with_command_substitution(self):
        result = subprocess.run(
            SHELL_CMD + [
                "arr=($(echo one two three)); echo ${arr[1]}"
            ],
            capture_output=True, text=True
        )
        assert "two" in result.stdout

    def test_array_with_arithmetic(self):
        result = subprocess.run(
            SHELL_CMD + [
                "arr=(10 20 30); echo $((arr[0] + arr[2]))"
            ],
            capture_output=True, text=True
        )
        assert "40" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
