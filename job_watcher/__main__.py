"""Command-line entry point: ``python -m job_watcher``."""

from __future__ import annotations

from argparse import ArgumentParser
import sys
import time

from .config import load_config
from .diff import JobChanges
from .notifier import render_text
from .watcher import RunResult, run_once


def build_parser() -> ArgumentParser:
  parser = ArgumentParser(
    prog="job_watcher",
    description="Watch a Greenhouse job board and email when postings change.",
  )
  parser.add_argument("--board", help="Greenhouse board token (default: pokemoncareers).")
  parser.add_argument("--state-file", dest="state_file", help="Where to store the snapshot JSON.")
  parser.add_argument("--to", help="Recipient email address (overrides EMAIL_TO).")
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print the change summary instead of sending email.",
  )
  parser.add_argument(
    "--notify-first-run",
    dest="notify_first_run",
    action="store_true",
    help="Email on the very first run instead of silently recording a baseline.",
  )
  parser.add_argument(
    "--interval",
    type=int,
    default=0,
    help="Run continuously, checking every N seconds (0 = run once and exit).",
  )
  return parser


def _describe(result: RunResult, board: str) -> str:
  if result.first_run:
    suffix = " (emailed)" if result.notified else ""
    return f"Baseline recorded for {board}: {result.job_count} postings{suffix}."
  if not result.has_changes:
    return f"No changes on {board} ({result.job_count} postings)."
  changes: JobChanges = result.changes  # type: ignore[assignment]
  action = "emailed" if result.notified else "detected (dry run, not emailed)"
  return f"{changes.total} change(s) {action} on {board}:\n\n{render_text(board, changes)}"


def run(argv: list[str] | None = None) -> int:
  args = build_parser().parse_args(argv)
  config = load_config(args)

  # Validate email settings up front unless we are only printing.
  if not config.dry_run:
    missing = config.missing_email_settings()
    if missing:
      print(
        "Missing email settings: " + ", ".join(missing) + ".\n"
        "Set them as environment variables, or pass --dry-run to preview changes.",
        file=sys.stderr,
      )
      return 2

  interval = max(0, args.interval)
  while True:
    try:
      result = run_once(config)
      print(_describe(result, config.board))
    except Exception as error:  # noqa: BLE001 - surface any failure but keep looping.
      print(f"Watch cycle failed: {error}", file=sys.stderr)
      if interval == 0:
        return 1

    if interval == 0:
      return 0
    time.sleep(interval)


if __name__ == "__main__":
  raise SystemExit(run())
