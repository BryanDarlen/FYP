"""
Test runner — runs all tests in this directory and reports overall pass/fail.

Run from the project root:
    python tests/run_all.py
"""
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent

TEST_FILES = [
    "test_validation.py",
    "test_features.py",
    "test_train.py",
]


def main() -> int:
    print(f"Running {len(TEST_FILES)} test files ...\n")

    results = []
    for name in TEST_FILES:
        path = TESTS_DIR / name
        if not path.exists():
            print(f"  SKIP   {name}  (file not found)")
            results.append((name, "SKIP"))
            continue

        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        # Strip noisy module-level prints from upstream code; keep the test's
        # final PASS/FAIL line and any failure detail.
        last_line = proc.stdout.strip().split("\n")[-1] if proc.stdout.strip() else ""

        if proc.returncode == 0:
            print(f"  PASS   {name}  -> {last_line}")
            results.append((name, "PASS"))
        else:
            print(f"  FAIL   {name}  (exit {proc.returncode})")
            if proc.stdout.strip():
                for line in proc.stdout.strip().split("\n")[-10:]:
                    print(f"         {line}")
            if proc.stderr.strip():
                for line in proc.stderr.strip().split("\n")[-5:]:
                    print(f"  stderr {line}")
            results.append((name, "FAIL"))

    print()
    n_pass = sum(1 for _, s in results if s == "PASS")
    n_fail = sum(1 for _, s in results if s == "FAIL")
    if n_fail:
        print(f"OVERALL: {n_pass}/{len(results)} passed, {n_fail} failed")
        return 1
    print(f"OVERALL: {n_pass}/{len(results)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
