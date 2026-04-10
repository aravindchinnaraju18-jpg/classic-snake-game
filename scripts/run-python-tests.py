from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest


class CollectingResult(unittest.TextTestResult):
  def __init__(self, stream, descriptions, verbosity):
    super().__init__(stream, descriptions, verbosity)
    self.successes: list[unittest.case.TestCase] = []

  def addSuccess(self, test):
    super().addSuccess(test)
    self.successes.append(test)


def format_test_name(test: unittest.case.TestCase) -> str:
  return test.id()


def format_failure_message(output: str) -> str:
  lines = [line.strip() for line in output.splitlines() if line.strip()]
  return lines[-1] if lines else "Test failed."


def main() -> int:
  repo_root = Path(__file__).resolve().parents[1]
  sys.path.insert(0, str(repo_root))
  suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
  runner = unittest.TextTestRunner(
    stream=io.StringIO(),
    verbosity=0,
    resultclass=CollectingResult,
  )
  result: CollectingResult = runner.run(suite)

  failed = len(result.failures) + len(result.errors)
  print("Python auth/app test summary")
  print(
    f"{result.testsRun - failed}/{result.testsRun} tests passed"
    f"{', ' + str(failed) + ' failed' if failed else '.'}"
  )
  print("")

  for test in result.successes:
    print(f"[PASS] {format_test_name(test)}")

  for test, output in result.failures:
    print(f"[FAIL] {format_test_name(test)}")
    print(f"  {format_failure_message(output)}")

  for test, output in result.errors:
    print(f"[ERROR] {format_test_name(test)}")
    print(f"  {format_failure_message(output)}")

  return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
  raise SystemExit(main())
