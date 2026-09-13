"""Watch a Greenhouse job board and email when postings change.

The package fetches the public Greenhouse board feed, compares it against a
stored snapshot, and sends an email summarising anything that was added,
removed, or changed since the previous run.
"""

from .config import Config, load_config
from .diff import JobChanges, diff_jobs
from .scraper import Job, fetch_jobs
from .watcher import run_once

__all__ = [
  "Config",
  "load_config",
  "Job",
  "fetch_jobs",
  "JobChanges",
  "diff_jobs",
  "run_once",
]
