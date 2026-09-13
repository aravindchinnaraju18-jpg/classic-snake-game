"""Runtime configuration, assembled from environment variables and CLI args.

Secrets (SMTP password in particular) are read from the environment so they
never have to be typed on the command line or committed to the repo.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

DEFAULT_BOARD = "pokemoncareers"
DEFAULT_STATE_FILE = "data/job_state.json"
DEFAULT_SMTP_PORT = 587


def _env_bool(name: str, default: bool) -> bool:
  value = os.environ.get(name)
  if value is None:
    return default
  return value.strip().lower() in {"1", "true", "yes", "on"}


def _safe_state_path(raw: str) -> Path:
  """Validate a state-file path coming from the environment or CLI.

  The value reaches us from untrusted-by-default sources (env vars, CLI args),
  so reject parent-directory traversal before it is ever used for file I/O.
  This closes the path-injection flow into job_watcher.state.
  """

  path = Path(raw)
  if ".." in path.parts:
    raise ValueError(f"Invalid state file path (parent traversal not allowed): {raw!r}")
  return path


@dataclass
class Config:
  board: str = DEFAULT_BOARD
  state_file: Path = Path(DEFAULT_STATE_FILE)

  # Email / SMTP settings.
  smtp_host: str = ""
  smtp_port: int = DEFAULT_SMTP_PORT
  smtp_user: str = ""
  smtp_password: str = ""
  smtp_use_tls: bool = True
  email_from: str = ""
  email_to: str = ""

  # When there is no prior snapshot, skip email and just record a baseline.
  notify_on_first_run: bool = False
  # Print the change summary instead of sending email.
  dry_run: bool = False

  def missing_email_settings(self) -> list[str]:
    """Return the names of required email settings that are not set."""

    missing = []
    if not self.smtp_host:
      missing.append("SMTP_HOST")
    if not self.email_to:
      missing.append("EMAIL_TO")
    if not self.email_from:
      missing.append("EMAIL_FROM (or SMTP_USER)")
    return missing


def load_config(args: Optional[object] = None) -> Config:
  """Build a :class:`Config` from the environment, overlaying CLI ``args``.

  ``args`` is the parsed ``argparse`` namespace; any attribute that is set
  (non-``None``) wins over the matching environment variable.
  """

  smtp_user = os.environ.get("SMTP_USER", "")
  config = Config(
    board=os.environ.get("JOB_BOARD_TOKEN", DEFAULT_BOARD),
    state_file=_safe_state_path(os.environ.get("JOB_STATE_FILE", DEFAULT_STATE_FILE)),
    smtp_host=os.environ.get("SMTP_HOST", ""),
    smtp_port=int(os.environ.get("SMTP_PORT", DEFAULT_SMTP_PORT)),
    smtp_user=smtp_user,
    smtp_password=os.environ.get("SMTP_PASSWORD", ""),
    smtp_use_tls=_env_bool("SMTP_USE_TLS", True),
    email_from=os.environ.get("EMAIL_FROM", smtp_user),
    email_to=os.environ.get("EMAIL_TO", ""),
    notify_on_first_run=_env_bool("NOTIFY_ON_FIRST_RUN", False),
  )

  if args is not None:
    if getattr(args, "board", None):
      config.board = args.board
    if getattr(args, "state_file", None):
      config.state_file = _safe_state_path(args.state_file)
    if getattr(args, "to", None):
      config.email_to = args.to
    if getattr(args, "notify_first_run", False):
      config.notify_on_first_run = True
    if getattr(args, "dry_run", False):
      config.dry_run = True

  return config
