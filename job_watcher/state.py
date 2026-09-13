"""Persist the last-seen job board snapshot between runs.

The snapshot is a small JSON document so it is easy to inspect, diff, and (for
the GitHub Actions deployment) commit back to the repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Optional

from .scraper import Job

STATE_VERSION = 1


def load_snapshot(path: Path) -> Optional[Dict[str, Job]]:
  """Return the stored ``{id: Job}`` map, or ``None`` if there is no snapshot.

  ``None`` means "first run": the caller establishes a baseline rather than
  emailing every existing posting as if it were new.
  """

  if not path.exists():
    return None

  raw = json.loads(path.read_text(encoding="utf-8"))
  jobs = raw.get("jobs", [])
  return {job["id"]: Job.from_dict(job) for job in jobs if job.get("id")}


def save_snapshot(path: Path, board: str, jobs: Dict[str, Job]) -> None:
  """Write the current ``{id: Job}`` map to ``path`` atomically."""

  path.parent.mkdir(parents=True, exist_ok=True)
  document = {
    "version": STATE_VERSION,
    "board": board,
    "fetched_at": datetime.now(timezone.utc).isoformat(),
    "jobs": [job.to_dict() for job in sorted(jobs.values(), key=lambda j: j.title.lower())],
  }
  # Write to a sibling temp file then replace, so an interrupted run can never
  # leave a half-written snapshot that corrupts the next comparison.
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
  tmp.replace(path)
