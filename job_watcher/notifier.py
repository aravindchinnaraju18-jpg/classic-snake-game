"""Render change summaries and deliver them over SMTP."""

from __future__ import annotations

from email.message import EmailMessage
from email.utils import formatdate
from html import escape
import smtplib
from typing import Callable, Optional

from .config import Config
from .diff import JobChanges

# Injectable so tests can assert on the built message without opening a socket.
Sender = Callable[[EmailMessage, Config], None]


def build_subject(board: str, changes: JobChanges) -> str:
  parts = []
  if changes.added:
    parts.append(f"{len(changes.added)} new")
  if changes.changed:
    parts.append(f"{len(changes.changed)} updated")
  if changes.removed:
    parts.append(f"{len(changes.removed)} removed")
  summary = ", ".join(parts) if parts else "no changes"
  return f"[{board}] Job board update: {summary}"


def render_text(board: str, changes: JobChanges) -> str:
  lines = [f"Changes on the {board} job board:", ""]

  if changes.added:
    lines.append(f"NEW POSTINGS ({len(changes.added)})")
    for job in changes.added:
      location = f" — {job.location}" if job.location else ""
      lines.append(f"  + {job.title}{location}")
      lines.append(f"    {job.url}")
    lines.append("")

  if changes.changed:
    lines.append(f"UPDATED POSTINGS ({len(changes.changed)})")
    for change in changes.changed:
      lines.append(f"  ~ {change.after.title}")
      for label, old, new in change.fields_changed():
        lines.append(f"    {label}: {old or '(none)'} -> {new or '(none)'}")
      lines.append(f"    {change.after.url}")
    lines.append("")

  if changes.removed:
    lines.append(f"REMOVED POSTINGS ({len(changes.removed)})")
    for job in changes.removed:
      location = f" — {job.location}" if job.location else ""
      lines.append(f"  - {job.title}{location}")
    lines.append("")

  return "\n".join(lines).rstrip() + "\n"


def render_html(board: str, changes: JobChanges) -> str:
  sections = [f"<h2>Changes on the {escape(board)} job board</h2>"]

  if changes.added:
    items = "".join(
      f'<li><a href="{escape(job.url)}">{escape(job.title)}</a>'
      f'{" — " + escape(job.location) if job.location else ""}</li>'
      for job in changes.added
    )
    sections.append(f"<h3>New postings ({len(changes.added)})</h3><ul>{items}</ul>")

  if changes.changed:
    items = []
    for change in changes.changed:
      detail = "".join(
        f"<li>{escape(label)}: <s>{escape(old) or '(none)'}</s> &rarr; "
        f"<strong>{escape(new) or '(none)'}</strong></li>"
        for label, old, new in change.fields_changed()
      )
      items.append(
        f'<li><a href="{escape(change.after.url)}">{escape(change.after.title)}</a>'
        f"<ul>{detail}</ul></li>"
      )
    sections.append(f"<h3>Updated postings ({len(changes.changed)})</h3><ul>{''.join(items)}</ul>")

  if changes.removed:
    items = "".join(
      f"<li>{escape(job.title)}{' — ' + escape(job.location) if job.location else ''}</li>"
      for job in changes.removed
    )
    sections.append(f"<h3>Removed postings ({len(changes.removed)})</h3><ul>{items}</ul>")

  return (
    '<!doctype html><html><body style="font-family:system-ui,sans-serif;">'
    + "".join(sections)
    + "</body></html>"
  )


def build_message(config: Config, changes: JobChanges) -> EmailMessage:
  message = EmailMessage()
  message["Subject"] = build_subject(config.board, changes)
  message["From"] = config.email_from
  message["To"] = config.email_to
  message["Date"] = formatdate(localtime=True)
  message.set_content(render_text(config.board, changes))
  message.add_alternative(render_html(config.board, changes), subtype="html")
  return message


def _smtp_send(message: EmailMessage, config: Config) -> None:
  with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
    if config.smtp_use_tls:
      server.starttls()
    if config.smtp_user:
      server.login(config.smtp_user, config.smtp_password)
    server.send_message(message)


def send_changes(config: Config, changes: JobChanges, sender: Optional[Sender] = None) -> EmailMessage:
  """Build and deliver the change email, returning the message that was sent."""

  message = build_message(config, changes)
  send = sender or _smtp_send
  send(message, config)
  return message
