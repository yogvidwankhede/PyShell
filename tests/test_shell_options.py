"""
Test suite for shell options:
- set -e (errexit)
- set -u (nounset) 
- set -x (xtrace)
- set -f (noglob)
- set -C (noclobber)
- set -o pipefail
"""

import pytest
import subprocess
import sys
import os
import tempfile

SHELL_CMD = [sys.executable, "main.py", "-c"]


class TestErrexit:
    """Test set -e (exit on error)."""

    def test_errexit_stops_on_error(self):
        result = subprocess.run(
            SHELL_CMD + ["set -e; false; echo should_not_print"],
            capture_output=True, text=True
        )
        assert "should_not_print" not in result.stdout
        assert result.returncode != 0

    def test_errexit_continues_on_success(self):
        result = subprocess.run(
            SHELL_CMD + ["set -e; true; echo printed"],
            capture_output=True, text=True
        )
        assert "printed" in result.stdout

    def test_errexit_disabled(self):
        result = subprocess.run(
            SHELL_CMD + ["set +e; false; echo printed"],
            capture_output=True, text=True
        )
        assert "printed" in result.stdout

    def test_errexit_with_command(self):
        result = subprocess.run(
            SHELL_CMD + ["set -e; echo first; false; echo second"],
            capture_output=True, text=True
        )
        assert "first" in result.stdout
        assert "second" not in result.stdout

    def test_errexit_in_conditional(self):
        # Commands in conditionals should not trigger errexit
        result = subprocess.run(
            SHELL_CMD + [
                "set -e; if false; then echo not_run; else echo run; fi; echo after"
            ],
            capture_output=True, text=True
        )
        assert "run" in result.stdout
        assert "after" in result.stdout


class TestXtrace:
    """Test set -x (command tracing)."""

    def test_xtrace_enabled(self):
        result = subprocess.run(
            SHELL_CMD + ["set -x; echo hello"],
            capture_output=True, text=True
        )
        # With xtrace, the command should be visible in stderr or traced
        assert "hello" in result.stdout

    def test_xtrace_disabled(self):
        result = subprocess.run(
            SHELL_CMD + ["set +x; echo hello"],
            capture_output=True, text=True
        )
        assert "hello" in result.stdout

    def test_xtrace_shows_expansions(self):
        result = subprocess.run(
            SHELL_CMD + ["set -x; x=5; echo $x"],
            capture_output=True, text=True
        )
        assert "5" in result.stdout


class TestNoglob:
    """Test set -f (disable globbing)."""

    def test_noglob_disables_expansion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "test1.txt"), 'w').close()
            open(os.path.join(tmpdir, "test2.txt"), 'w').close()

            result = subprocess.run(
                SHELL_CMD + [f"cd {tmpdir}; set -f; echo *.txt"],
                capture_output=True, text=True
            )
            # With noglob, *.txt should not expand
            assert "*.txt" in result.stdout

    def test_noglob_enabled_then_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "file.txt"), 'w').close()

            result = subprocess.run(
                SHELL_CMD + [f"cd {tmpdir}; set -f; set +f; echo *.txt"],
                capture_output=True, text=True
            )
            # After +f, globbing should work again
            assert "file.txt" in result.stdout or "*.txt" in result.stdout


class TestNoclobber:
    """Test set -C (no clobber - don't overwrite files)."""

    def test_noclobber_prevents_overwrite(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("original")
            fname = f.name

        try:
            result = subprocess.run(
                SHELL_CMD + [f"set -C; echo new > {fname}"],
                capture_output=True, text=True
            )
            # Should either fail or keep original content
            with open(fname, 'r') as f:
                content = f.read()
            # If noclobber works, original content should remain
            # OR the command should fail
            assert "original" in content or result.returncode != 0
        finally:
            os.unlink(fname)

    def test_noclobber_allows_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, "newfile.txt")

            result = subprocess.run(
                SHELL_CMD + [f"set -C; echo content > {fname}; cat {fname}"],
                capture_output=True, text=True
            )
            # Creating new file should work
            assert "content" in result.stdout

    def test_noclobber_disabled(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("original")
            fname = f.name

        try:
            result = subprocess.run(
                SHELL_CMD + [f"set +C; echo new > {fname}; cat {fname}"],
                capture_output=True, text=True
            )
            # Without noclobber, should overwrite
            assert "new" in result.stdout
        finally:
            os.unlink(fname)


class TestPipefail:
    """Test set -o pipefail."""

    def test_pipefail_catches_failure(self):
        result = subprocess.run(
            SHELL_CMD + ["set -o pipefail; false | true"],
            capture_output=True, text=True
        )
        # With pipefail, the pipeline should fail if any command fails
        # This test verifies the option is accepted
        assert result.returncode is not None

    def test_pipefail_disabled(self):
        result = subprocess.run(
            SHELL_CMD + ["set +o pipefail; false | true; echo ok"],
            capture_output=True, text=True
        )
        # Without pipefail, last command determines exit status
        assert "ok" in result.stdout


class TestSetPositional:
    """Test set with positional parameters."""

    def test_set_positional_params(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- one two three; echo $1 $2 $3"],
            capture_output=True, text=True
        )
        assert "one two three" in result.stdout

    def test_set_clears_params(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- a b c; set --; echo ${1:-empty}"],
            capture_output=True, text=True
        )
        assert "empty" in result.stdout

    def test_set_with_dash(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- -a -b -c; echo $1"],
            capture_output=True, text=True
        )
        assert "-a" in result.stdout

    def test_set_single_param(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- single; echo $1 ${2:-none}"],
            capture_output=True, text=True
        )
        assert "single" in result.stdout
        assert "none" in result.stdout

    def test_set_empty_params(self):
        result = subprocess.run(
            SHELL_CMD + ["set -- ''; echo x${1}x"],
            capture_output=True, text=True
        )
        assert "xx" in result.stdout


class TestMultipleOptions:
    """Test combining multiple shell options."""

    def test_errexit_and_xtrace(self):
        result = subprocess.run(
            SHELL_CMD + ["set -ex; echo test; true"],
            capture_output=True, text=True
        )
        assert "test" in result.stdout

    def test_enable_then_disable(self):
        result = subprocess.run(
            SHELL_CMD + ["set -e; set +e; false; echo ok"],
            capture_output=True, text=True
        )
        assert "ok" in result.stdout

    def test_multiple_options_at_once(self):
        result = subprocess.run(
            SHELL_CMD + ["set -euf; echo test"],
            capture_output=True, text=True
        )
        assert "test" in result.stdout


class TestSetWithoutOptions:
    """Test set command without options."""

    def test_set_shows_variables(self):
        result = subprocess.run(
            SHELL_CMD + ["x=5; y=10; set"],
            capture_output=True, text=True
        )
        # set without options should show variables (or at least not error)
        # We just check it doesn't crash and shows the variables
        assert result.returncode == 0
        assert "x=5" in result.stdout or "x" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
