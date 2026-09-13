"""Compare two snapshots of a job board to find what changed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .scraper import Job


@dataclass
class ChangedJob:
  """A posting present in both snapshots whose details changed."""

  before: Job
  after: Job

  def fields_changed(self) -> List[Tuple[str, str, str]]:
    """Return ``(field, old, new)`` tuples for each differing field."""

    changes: List[Tuple[str, str, str]] = []
    for label, attr in (("Title", "title"), ("Location", "location"), ("Last updated", "updated_at")):
      old = getattr(self.before, attr)
      new = getattr(self.after, attr)
      if old != new:
        changes.append((label, old, new))
    return changes


@dataclass
class JobChanges:
  """The difference between a previous and current job board snapshot."""

  added: List[Job] = field(default_factory=list)
  removed: List[Job] = field(default_factory=list)
  changed: List[ChangedJob] = field(default_factory=list)

  @property
  def has_changes(self) -> bool:
    return bool(self.added or self.removed or self.changed)

  @property
  def total(self) -> int:
    return len(self.added) + len(self.removed) + len(self.changed)


def diff_jobs(previous: Dict[str, Job], current: Dict[str, Job]) -> JobChanges:
  """Diff two ``{id: Job}`` maps into added/removed/changed buckets."""

  changes = JobChanges()

  for job_id, job in current.items():
    if job_id not in previous:
      changes.added.append(job)
    elif job.fingerprint != previous[job_id].fingerprint:
      changes.changed.append(ChangedJob(before=previous[job_id], after=job))

  for job_id, job in previous.items():
    if job_id not in current:
      changes.removed.append(job)

  changes.added.sort(key=lambda job: job.title.lower())
  changes.removed.sort(key=lambda job: job.title.lower())
  changes.changed.sort(key=lambda change: change.after.title.lower())
  return changes
