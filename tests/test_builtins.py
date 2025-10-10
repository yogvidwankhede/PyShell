"""
Test suite for built-in commands:
- test/[ command
- read, printf
- export, unset, local, readonly
- shift, set, declare, let
- break, continue
- alias, unalias
- pushd, popd, dirs
- eval, source, type, trap
"""

import pytest
import subprocess
import sys
import os
import tempfile

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestTestCommand:
    """Test the test/[ built-in command."""

    def test_file_exists(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            fname = f.name
        try:
            result = subprocess.run(
                SHELL_CMD + [f"[ -f {fname} ] && echo yes || echo no"],
                capture_output=True, text=True
            )
            assert "yes" in result.stdout
        finally:
            os.unlink(fname)

    def test_directory_exists(self):
        result = subprocess.run(
            SHELL_CMD + ["[ -d /tmp ] && echo yes"],
            capture_output=True, text=True
        )
        assert "yes" in result.stdout

    def test_string_equality(self):
        result = subprocess.run(
            SHELL_CMD + ['[ "hello" = "hello" ] && echo match'],
            capture_output=True, text=True
        )
        assert "match" in result.stdout

    def test_string_inequality(self):
        result = subprocess.run(
            SHELL_CMD + ['[ "a" != "b" ] && echo different'],
            capture_output=True, text=True
        )
        assert "different" in result.stdout

    def test_numeric_less_than(self):
        result = subprocess.run(
            SHELL_CMD + ["[ 5 -lt 10 ] && echo yes"],
            capture_output=True, text=True
        )
        assert "yes" in result.stdout

    def test_numeric_greater_than(self):
        result = subprocess.run(
            SHELL_CMD + ["[ 10 -gt 5 ] && echo yes"],
            capture_output=True, text=True
        )
        assert "yes" in result.stdout

    def test_numeric_equal(self):
        result = subprocess.run(
            SHELL_CMD + ["[ 5 -eq 5 ] && echo equal"],
            capture_output=True, text=True
        )
        assert "equal" in result.stdout

    def test_string_length_zero(self):
        result = subprocess.run(
            SHELL_CMD + ['[ -z "" ] && echo empty'],
            capture_output=True, text=True
        )
        assert "empty" in result.stdout

    def test_string_length_nonzero(self):
        result = subprocess.run(
            SHELL_CMD + ['[ -n "text" ] && echo nonempty'],
            capture_output=True, text=True
        )
        assert "nonempty" in result.stdout

    def test_negation(self):
        result = subprocess.run(
            SHELL_CMD + ["[ ! -f /nonexistent ] && echo ok"],
            capture_output=True, text=True
        )
        assert "ok" in result.stdout


class TestEchoCommand:
    """Test echo built-in with various options."""

    def test_simple_echo(self):
        result = subprocess.run(
            SHELL_CMD + ["echo hello"],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_echo_multiple_words(self):
        result = subprocess.run(
            SHELL_CMD + ["echo one two three"],
            capture_output=True, text=True
        )
        assert "one two three" in result.stdout

    def test_echo_with_n_flag(self):
        result = subprocess.run(
            SHELL_CMD + ["echo -n test"],
            capture_output=True, text=True
        )
        # -n should suppress newline
        assert result.stdout == "test"


class TestPrintfCommand:
    """Test the printf built-in command."""

    def test_printf_string(self):
        result = subprocess.run(
            SHELL_CMD + ["printf 'Hello World'"],
            capture_output=True, text=True
        )
        assert result.stdout == "Hello World"

    def test_printf_with_newline(self):
        result = subprocess.run(
            SHELL_CMD + ["printf 'Line1\\nLine2\\n'"],
            capture_output=True, text=True
        )
        assert "Line1" in result.stdout
        assert "Line2" in result.stdout


class TestExportCommand:
    """Test the export built-in command."""

    def test_export_variable(self):
        result = subprocess.run(
            SHELL_CMD + ["export TEST_VAR=exported; echo $TEST_VAR"],
            capture_output=True, text=True
        )
        assert "exported" in result.stdout

    def test_export_with_assignment(self):
        result = subprocess.run(
            SHELL_CMD + ["export X=value; echo $X"],
            capture_output=True, text=True
        )
        assert "value" in result.stdout


class TestUnsetCommand:
    """Test the unset built-in command."""

    def test_unset_variable(self):
        result = subprocess.run(
            SHELL_CMD + ["x=test; unset x; echo ${x:-unset}"],
            capture_output=True, text=True
        )
        assert "unset" in result.stdout

    def test_unset_nonexistent(self):
        result = subprocess.run(
            SHELL_CMD + ["unset NONEXISTENT; echo ok"],
            capture_output=True, text=True
        )
        assert "ok" in result.stdout


class TestShiftCommand:
    """Test the shift built-in command."""

    def test_shift_parameters(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- a b c; shift; echo $1"],
            capture_output=True, text=True
        )
        assert "b" in result.stdout

    def test_shift_multiple(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- a b c d; shift 2; echo $1"],
            capture_output=True, text=True
        )
        assert "c" in result.stdout

    def test_shift_all(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- x y; shift 2; echo ${1:-empty}"],
            capture_output=True, text=True
        )
        assert "empty" in result.stdout


class TestSetCommand:
    """Test the set built-in command."""

    def test_set_positional_params(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- one two three; echo $1 $2 $3"],
            capture_output=True, text=True
        )
        assert "one two three" in result.stdout

    def test_set_errexit(self):
        result = subprocess.run(
            SHELL_CMD + ["set -e; false; echo should_not_print"],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout

    def test_set_with_double_dash(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- alpha beta; echo $2"],
            capture_output=True, text=True
        )
        assert "beta" in result.stdout


class TestLetCommand:
    """Test the let built-in command."""

    def test_let_arithmetic(self):
        result = subprocess.run(
            SHELL_CMD + ["let x=5+3; echo $x"],
            capture_output=True, text=True
        )
        assert "8" in result.stdout

    def test_let_returns_zero_for_nonzero(self):
        result = subprocess.run(
            SHELL_CMD + ["let 5 && echo success"],
            capture_output=True, text=True
        )
        assert "success" in result.stdout

    def test_let_returns_one_for_zero(self):
        result = subprocess.run(
            SHELL_CMD + ["let 0 || echo failed"],
            capture_output=True, text=True
        )
        assert "failed" in result.stdout


class TestAliasCommand:
    """Test alias and unalias commands."""

    def test_define_alias(self):
        result = subprocess.run(
            SHELL_CMD + ["alias ll='echo listed'; ll"],
            capture_output=True, text=True
        )
        assert "listed" in result.stdout

    def test_alias_with_arguments(self):
        result = subprocess.run(
            SHELL_CMD + ["alias greet='echo Hello'; greet World"],
            capture_output=True, text=True
        )
        assert "Hello" in result.stdout

    def test_unalias(self):
        result = subprocess.run(
            SHELL_CMD + ["alias test='echo test'; unalias test; echo ok"],
            capture_output=True, text=True
        )
        assert "ok" in result.stdout


class TestDirectoryStack:
    """Test pushd, popd, and dirs commands."""

    def test_pushd(self):
        result = subprocess.run(
            SHELL_CMD + ["cd /tmp; pushd / >/dev/null; pwd"],
            capture_output=True, text=True
        )
        assert "/" in result.stdout

    def test_popd(self):
        result = subprocess.run(
            SHELL_CMD + ["cd /tmp; pushd / >/dev/null; popd >/dev/null; pwd"],
            capture_output=True, text=True
        )
        assert "/tmp" in result.stdout


class TestTypeCommand:
    """Test the type built-in command."""

    def test_type_builtin(self):
        result = subprocess.run(
            SHELL_CMD + ["type echo"],
            capture_output=True, text=True
        )
        assert "builtin" in result.stdout.lower()

    def test_type_alias(self):
        result = subprocess.run(
            SHELL_CMD + ["alias mytest='echo test'; type mytest"],
            capture_output=True, text=True
        )
        assert "alias" in result.stdout.lower()


class TestEvalCommand:
    """Test the eval built-in command."""

    def test_eval_simple(self):
        result = subprocess.run(
            SHELL_CMD + ["x='echo hello'; eval $x"],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_eval_complex(self):
        result = subprocess.run(
            SHELL_CMD + ["cmd='x=5'; eval $cmd; echo $x"],
            capture_output=True, text=True
        )
        assert "5" in result.stdout

    def test_eval_with_quotes(self):
        result = subprocess.run(
            SHELL_CMD + ["eval 'echo test'"],
            capture_output=True, text=True
        )
        assert "test" in result.stdout


class TestSourceCommand:
    """Test the source/. built-in command."""

    def test_source_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("TEST_VAR=sourced\n")
            f.write("echo $TEST_VAR\n")
            fname = f.name

        try:
            result = subprocess.run(
                SHELL_CMD + [f"source {fname}"],
                capture_output=True, text=True
            )
            assert "sourced" in result.stdout
        finally:
            os.unlink(fname)

    def test_dot_command(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("echo dot_sourced\n")
            fname = f.name

        try:
            result = subprocess.run(
                SHELL_CMD + [f". {fname}"],
                capture_output=True, text=True
            )
            assert "dot_sourced" in result.stdout
        finally:
            os.unlink(fname)


class TestTrueFalse:
    """Test true and false built-ins."""

    def test_true_command(self):
        result = subprocess.run(
            SHELL_CMD + ["true && echo success"],
            capture_output=True, text=True
        )
        assert "success" in result.stdout

    def test_false_command(self):
        result = subprocess.run(
            SHELL_CMD + ["false || echo failed"],
            capture_output=True, text=True
        )
        assert "failed" in result.stdout


class TestPwdCd:
    """Test pwd and cd commands."""

    def test_pwd(self):
        result = subprocess.run(
            SHELL_CMD + ["pwd"],
            capture_output=True, text=True
        )
        assert len(result.stdout.strip()) > 0

    def test_cd_and_pwd(self):
        result = subprocess.run(
            SHELL_CMD + ["cd /tmp; pwd"],
            capture_output=True, text=True
        )
        assert "/tmp" in result.stdout


class TestCat:
    """Test cat command."""

    def test_cat_with_here_string(self):
        result = subprocess.run(
            SHELL_CMD + ["cat <<< 'test content'"],
            capture_output=True, text=True
        )
        assert "test content" in result.stdout


class TestCommonBuiltins:
    """Tests translated from test_builtins.sh for PyShell builtins."""

    def test_help(self):
        result = subprocess.run(
            SHELL_CMD + ["help"], capture_output=True, text=True)
        assert "help" in result.stdout.lower() or len(result.stdout) > 0

    def test_help_cd(self):
        result = subprocess.run(
            SHELL_CMD + ["help cd"], capture_output=True, text=True)
        assert "cd" in result.stdout.lower()

    def test_ls(self):
        result = subprocess.run(
            SHELL_CMD + ["ls"], capture_output=True, text=True)
        assert len(result.stdout.strip()) > 0

    def test_ls_long(self):
        result = subprocess.run(
            SHELL_CMD + ["ls -l"], capture_output=True, text=True)
        assert len(result.stdout.strip()) > 0

    def test_date(self):
        result = subprocess.run(
            SHELL_CMD + ["date"], capture_output=True, text=True)
        assert any(char.isdigit() for char in result.stdout)

    def test_date_format(self):
        result = subprocess.run(
            SHELL_CMD + ["date +%Y-%m-%d"], capture_output=True, text=True)
        assert "-" in result.stdout.strip()

    def test_grep(self):
        cmd = "echo 'hello world\ntest pattern\nanother line\npattern here' | grep pattern"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert "pattern" in result.stdout

    def test_grep_count(self):
        cmd = "echo 'hello world\ntest pattern\nanother line\npattern here' | grep -c pattern"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert result.stdout.strip().isdigit()

    def test_wc_lines(self):
        cmd = "echo 'line 1\nline 2\nline 3' | wc -l"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert result.stdout.strip().isdigit()

    def test_wc_words(self):
        cmd = "echo 'one two three four five' | wc -w"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert result.stdout.strip().isdigit()

    def test_head(self):
        cmd = "echo 'line 1\nline 2\nline 3\nline 4\nline 5' | head -n 2"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert "line 1" in result.stdout and "line 3" not in result.stdout

    def test_tail(self):
        cmd = "echo 'line 1\nline 2\nline 3\nline 4\nline 5' | tail -n 2"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert "line 4" in result.stdout and "line 2" not in result.stdout

    def test_sort(self):
        cmd = "echo 'zebra\napple\nbanana\ncherry' | sort"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        assert lines == sorted(lines)

    def test_sort_reverse(self):
        cmd = "echo 'zebra\napple\nbanana\ncherry' | sort -r"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        assert lines == sorted(lines, reverse=True)

    def test_uniq(self):
        cmd = "echo 'apple\napple\nbanana\nbanana\nbanana\ncherry' | uniq"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert "apple" in result.stdout and result.stdout.count("apple") == 1

    def test_uniq_count(self):
        cmd = "echo 'apple\napple\nbanana\nbanana\nbanana\ncherry' | uniq -c"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert any(char.isdigit() for char in result.stdout)

    def test_pipeline(self):
        cmd = "echo 'test pattern here\nanother pattern\nno match\npattern again' | grep pattern | wc -l"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert result.stdout.strip().isdigit()

    def test_hash(self):
        cmd = "hash python; hash -l"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True)
        assert "python" in result.stdout.lower()

    def test_clear(self):
        # Interactive: requires pressing Enter
        cmd = "read; clear; echo 'Screen cleared!'"
        result = subprocess.run(
            SHELL_CMD + [cmd], capture_output=True, text=True, input="\n")
        assert "Screen cleared" in result.stdout


    def test_rm(self):
        cmd = "echo 'test content' > test_rm_file.txt; ls test_rm_file.txt; rm test_rm_file.txt; ls test_rm_file.txt 2>&1 | head -n 1"
        result = subprocess.run(SHELL_CMD + [cmd], capture_output=True, text=True)
        combined = result.stdout + result.stderr
        assert "No such file" in combined or "cannot access" in combined



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
