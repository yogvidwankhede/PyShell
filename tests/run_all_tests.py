"""
Master test runner for PyShell.
Runs all test suites and generates a comprehensive report.
"""

import subprocess
import sys
import os
from datetime import datetime

# Test files to run
TEST_FILES = [
    "test_expansions.py",
    "test_builtins.py",
    "test_control_flow.py",
    "test_pipelines_redirections.py",
    "test_functions.py",
    "test_shell_options.py",
    "test_integration.py"
]

# Feature categories for reporting
FEATURE_CATEGORIES = {
    "test_expansions.py": "Expansions (Variable, Command Substitution, Arithmetic, Parameter, Tilde, Brace)",
    "test_builtins.py": "Built-in Commands (40+ commands)",
    "test_control_flow.py": "Control Flow (if/elif/else, while, until, for, case, break, continue)",
    "test_pipelines_redirections.py": "Pipelines & Redirections",
    "test_functions.py": "Functions (Definition, Parameters, Return, Local Variables)",
    "test_shell_options.py": "Shell Options (set -e, -u, -x, -f, -C, -o pipefail)",
    "test_integration.py": "Integration Tests (Real-world scenarios)"
}


def print_header():
    """Print test suite header."""
    print("=" * 80)
    print(" " * 20 + "PyShell Test Suite")
    print(" " * 15 + "Testing All 35 Features")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()


def print_footer(results):
    """Print test suite footer with summary."""
    print()
    print("=" * 80)
    print(" " * 25 + "Test Summary")
    print("=" * 80)

    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_tests = total_passed + total_failed

    for test_file, result in results.items():
        category = FEATURE_CATEGORIES.get(test_file, test_file)
        status = "✓ PASSED" if result['failed'] == 0 else "✗ FAILED"
        print(f"{status:12} | {category}")
        print(
            f"             | Passed: {result['passed']}, Failed: {result['failed']}")

    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(
        f"Passed:      {total_passed} ({100*total_passed//total_tests if total_tests > 0 else 0}%)")
    print(f"Failed:      {total_failed}")
    print("=" * 80)

    if total_failed == 0 and total_tests > 0:
        print()
        print(" " * 20 + "🎉 ALL TESTS PASSED! 🎉")
        print(" " * 15 + "Your shell is fully functional!")
        print()
    elif total_tests == 0:
        print()
        print(" " * 20 + "⚠️  No tests were run")
        print(" " * 18 + "Check that test files exist")
        print()
    else:
        print()
        print(" " * 20 + "⚠️  Some tests failed")
        print(" " * 18 + "Check output above for details")
        print()

    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


def parse_pytest_output(output):
    """Parse pytest output to extract pass/fail counts."""
    passed = 0
    failed = 0

    for line in output.split('\n'):
        if 'passed' in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if 'passed' in part.lower() and i > 0:
                    try:
                        passed = int(parts[i-1])
                    except (ValueError, IndexError):
                        pass

        if 'failed' in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if 'failed' in part.lower() and i > 0:
                    try:
                        failed = int(parts[i-1])
                    except (ValueError, IndexError):
                        pass

    if passed == 0 and failed == 0:
        for line in output.split('\n'):
            if 'PASSED' in line:
                passed += 1
            elif 'FAILED' in line:
                failed += 1

    return passed, failed


def run_tests():
    """Run all test files and collect results."""
    print_header()

    results = {}
    all_success = True

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    for test_file in TEST_FILES:
        # Build path relative to script location
        test_path = os.path.join(script_dir, test_file)

        print(f"\n{'='*80}")
        print(f"Running: {FEATURE_CATEGORIES.get(test_file, test_file)}")
        print(f"File: {test_file}")
        print(f"Path: {test_path}")
        print('='*80)

        if not os.path.exists(test_path):
            print(f"⚠️  Test file not found: {test_path}")
            print(
                f"Please ensure {test_file} is in the same directory as this script.")
            results[test_file] = {'passed': 0, 'failed': 0}
            continue

        try:
            # Run pytest with verbose output
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Print output
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            # Parse results
            passed, failed = parse_pytest_output(result.stdout + result.stderr)
            results[test_file] = {'passed': passed, 'failed': failed}

            if result.returncode != 0 and failed > 0:
                all_success = False

        except subprocess.TimeoutExpired:
            print(f"⚠️  Test timed out: {test_file}")
            results[test_file] = {'passed': 0, 'failed': 1}
            all_success = False

        except Exception as e:
            print(f"⚠️  Error running test: {e}")
            results[test_file] = {'passed': 0, 'failed': 1}
            all_success = False

    print_footer(results)

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(run_tests())
