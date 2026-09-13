"""Orchestrate a single watch cycle: fetch, diff, notify, persist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import Config
from .diff import JobChanges, diff_jobs
from .notifier import Sender, send_changes
from .scraper import Fetcher, fetch_jobs
from .state import load_snapshot, save_snapshot


@dataclass
class RunResult:
  first_run: bool
  changes: Optional[JobChanges]
  notified: bool
  job_count: int

  @property
  def has_changes(self) -> bool:
    return bool(self.changes and self.changes.has_changes)


def run_once(
  config: Config,
  *,
  fetcher: Optional[Fetcher] = None,
  sender: Optional[Sender] = None,
) -> RunResult:
  """Run one fetch/diff/notify cycle and update the stored snapshot.

  ``fetcher`` and ``sender`` are injection points for tests and alternate
  transports; production code leaves them as ``None`` to use the real
  Greenhouse fetch and SMTP send.
  """

  board = fetch_jobs(config.board, fetcher=fetcher)
  current = board.as_map()
  previous = load_snapshot(config.state_file)

  if previous is None:
    # First run: establish a baseline. Only email if explicitly asked to.
    changes = diff_jobs({}, current)
    notified = False
    if config.notify_on_first_run and changes.has_changes and not config.dry_run:
      send_changes(config, changes, sender=sender)
      notified = True
    save_snapshot(config.state_file, config.board, current)
    return RunResult(first_run=True, changes=changes, notified=notified, job_count=len(current))

  changes = diff_jobs(previous, current)
  notified = False
  if changes.has_changes and not config.dry_run:
    send_changes(config, changes, sender=sender)
    notified = True

  # Persist only after a successful notify (or when there was nothing to send),
  # so a transient email failure does not swallow the change on the next run.
  save_snapshot(config.state_file, config.board, current)
  return RunResult(first_run=False, changes=changes, notified=notified, job_count=len(current))
