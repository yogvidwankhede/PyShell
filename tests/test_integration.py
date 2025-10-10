"""
Integration tests combining multiple features:
- Real-world scripts
- Complex pipelines
- Multiple features together
"""

import pytest
import subprocess
import sys
import os
import tempfile

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestRealWorldScripts:
    """Test realistic shell script scenarios."""

    def test_count_files_by_extension(self):
        """Count files with specific extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "test1.txt"), 'w').close()
            open(os.path.join(tmpdir, "test2.txt"), 'w').close()
            open(os.path.join(tmpdir, "test.md"), 'w').close()

            # Use forward slashes for cross-platform compatibility
            tmpdir_path = tmpdir.replace('\\', '/')

            result = subprocess.run(
                SHELL_CMD + [
                    f"cd '{tmpdir_path}'; "
                    f"count=0; "
                    f"for f in *.txt; do count=$((count + 1)); done; "
                    f"echo $count"
                ],
                capture_output=True, text=True
            )
            assert "2" in result.stdout

    def test_backup_script(self):
        """Simulate a backup script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "source.txt")
            with open(src, 'w') as f:
                f.write("important data")

            # Use forward slashes
            src_path = src.replace('\\', '/')
            backup_path = os.path.join(tmpdir, "backup.txt").replace('\\', '/')

            result = subprocess.run(
                SHELL_CMD + [
                    f"if [ -f '{src_path}' ]; then "
                    f"  cat '{src_path}' > '{backup_path}'; "
                    f"  echo backed_up; "
                    f"fi"
                ],
                capture_output=True, text=True
            )
            assert "backed_up" in result.stdout
            assert os.path.exists(os.path.join(tmpdir, "backup.txt"))

    def test_find_and_process(self):
        """Find files and process them."""
        result = subprocess.run(
            SHELL_CMD + [
                "for i in {1..5}; do "
                "  [ $i -eq 3 ] && continue; "
                "  echo $i; "
                "done"
            ],
            capture_output=True, text=True
        )
        assert "1" in result.stdout
        assert "2" in result.stdout
        assert "4" in result.stdout
        assert "5" in result.stdout


class TestComplexPipelines:
    """Test complex pipeline scenarios."""

    def test_multi_stage_processing(self):
        """Test multi-stage data processing."""
        result = subprocess.run(
            SHELL_CMD + ["echo 'one two three' | cat | cat"],
            capture_output=True, text=True
        )
        assert "one two three" in result.stdout


class TestCombinedFeatures:
    """Test multiple features working together."""

    def test_function_with_arithmetic_and_loops(self):
        """Function using arithmetic and loops."""
        result = subprocess.run(
            SHELL_CMD + [
                "sum() { "
                "  total=0; "
                "  for num in $@; do "
                "    total=$((total + num)); "
                "  done; "
                "  echo $total; "
                "}; "
                "sum 1 2 3 4 5"
            ],
            capture_output=True, text=True
        )
        assert "15" in result.stdout

    def test_conditional_with_command_substitution(self):
        """Test conditional with command substitution."""
        result = subprocess.run(
            SHELL_CMD + [
                "result=$(echo test); "
                "if [ $result = test ]; then "
                "  echo success; "
                "fi"
            ],
            capture_output=True, text=True
        )
        assert "success" in result.stdout

    def test_case_with_parameter_expansion(self):
        """Test case statement with parameter expansion."""
        result = subprocess.run(
            SHELL_CMD + [
                "file=document.txt; "
                "ext=${file##*.}; "
                "case $ext in "
                "  txt) echo text_file ;; "
                "  *) echo other ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "text_file" in result.stdout

    def test_nested_loops_with_break(self):
        """Test nested loops with break."""
        result = subprocess.run(
            SHELL_CMD + [
                "for i in 1 2 3; do "
                "  for j in a b c; do "
                "    echo $i$j; "
                "    [ $j = b ] && break; "
                "  done; "
                "done"
            ],
            capture_output=True, text=True
        )
        assert "1a" in result.stdout
        assert "1b" in result.stdout
        assert "2a" in result.stdout


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_error_recovery_with_or(self):
        """Test error recovery using || operator."""
        result = subprocess.run(
            SHELL_CMD + ["false || echo recovered"],
            capture_output=True, text=True
        )
        assert "recovered" in result.stdout

    def test_success_chain_with_and(self):
        """Test success chaining using && operator."""
        result = subprocess.run(
            SHELL_CMD + [
                "true && echo step1 && echo step2"
            ],
            capture_output=True, text=True
        )
        assert "step1" in result.stdout
        assert "step2" in result.stdout


class TestScriptExecution:
    """Test executing shell scripts."""

    def test_execute_simple_script(self):
        """Test executing a simple shell script."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\n")
            f.write("echo Hello from script\n")
            f.write("x=10\n")
            f.write("y=20\n")
            f.write("echo $((x + y))\n")
            fname = f.name

        try:
            # Use forward slashes
            fname_path = fname.replace('\\', '/')
            result = subprocess.run(
                SHELL_CMD + [f"source '{fname_path}'"],
                capture_output=True, text=True
            )
            assert "Hello from script" in result.stdout
            assert "30" in result.stdout
        finally:
            os.unlink(fname)

    def test_script_with_functions(self):
        """Test script containing function definitions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("greet() {\n")
            f.write("  echo Hello $1\n")
            f.write("}\n")
            f.write("greet World\n")
            fname = f.name

        try:
            fname_path = fname.replace('\\', '/')
            result = subprocess.run(
                SHELL_CMD + [f"source '{fname_path}'"],
                capture_output=True, text=True
            )
            assert "Hello World" in result.stdout
        finally:
            os.unlink(fname)


class TestAdvancedStringManipulation:
    """Test advanced string manipulation scenarios."""

    def test_filename_manipulation(self):
        """Test extracting parts of filenames."""
        result = subprocess.run(
            SHELL_CMD + [
                "path=/home/user/document.txt; "
                "filename=${path##*/}; "
                "basename=${filename%.*}; "
                "extension=${filename##*.}; "
                "echo $basename $extension"
            ],
            capture_output=True, text=True
        )
        assert "document txt" in result.stdout

    def test_string_replacement_in_loop(self):
        """Test string replacement in a loop."""
        result = subprocess.run(
            SHELL_CMD + [
                "for word in hello world test; do "
                "  echo ${word/l/L}; "
                "done"
            ],
            capture_output=True, text=True
        )
        assert "heLlo" in result.stdout
        assert "worLd" in result.stdout


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_menu_system(self):
        """Test a simple menu-like system."""
        result = subprocess.run(
            SHELL_CMD + [
                "choice=2; "
                "case $choice in "
                "  1) echo Option One ;; "
                "  2) echo Option Two ;; "
                "  3) echo Option Three ;; "
                "  *) echo Invalid ;; "
                "esac"
            ],
            capture_output=True, text=True
        )
        assert "Option Two" in result.stdout

    def test_validation_loop(self):
        """Test input validation pattern."""
        result = subprocess.run(
            SHELL_CMD + [
                "valid=false; "
                "count=0; "
                "until [ \"$valid\" = \"true\" ]; do "
                "  count=$((count + 1)); "
                "  [ $count -gt 2 ] && valid=true; "
                "done; "
                "echo $count"
            ],
            capture_output=True, text=True,
            timeout=5  # Add timeout to prevent infinite loops
        )
        assert "3" in result.stdout

    def test_conditional_execution_chain(self):
        """Test chained conditional execution."""
        result = subprocess.run(
            SHELL_CMD + [
                "step1() { return 0; }; "
                "step2() { echo step2; return 0; }; "
                "step3() { echo step3; }; "
                "step1 && step2 && step3"
            ],
            capture_output=True, text=True
        )
        assert "step2" in result.stdout
        assert "step3" in result.stdout


class TestArrayLikeOperations:
    """Test array-like operations using loops."""

    def test_iterate_list(self):
        """Test iterating over a list of items."""
        result = subprocess.run(
            SHELL_CMD + [
                "items='apple banana cherry'; "
                "for item in $items; do "
                "  echo fruit:$item; "
                "done"
            ],
            capture_output=True, text=True
        )
        assert "fruit:apple" in result.stdout
        assert "fruit:banana" in result.stdout
        assert "fruit:cherry" in result.stdout

    def test_filter_list(self):
        """Test filtering items from a list."""
        result = subprocess.run(
            SHELL_CMD + [
                "for num in 1 2 3 4 5; do "
                "  [ $((num % 2)) -eq 0 ] && echo $num; "
                "done"
            ],
            capture_output=True, text=True
        )
        assert "2" in result.stdout
        assert "4" in result.stdout
        assert "1" not in result.stdout.replace("2", "").replace("4", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
