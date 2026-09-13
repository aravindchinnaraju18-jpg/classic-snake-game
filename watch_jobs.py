"""Convenience entry point so the watcher can run as ``python watch_jobs.py``.

This mirrors ``app.py`` for the Snake app and simply delegates to the
``job_watcher`` package CLI.
"""

from job_watcher.__main__ import run

if __name__ == "__main__":
  raise SystemExit(run())
