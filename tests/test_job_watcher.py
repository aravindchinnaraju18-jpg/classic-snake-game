"""Tests for the Greenhouse job board watcher.

All tests run offline: the Greenhouse fetch and the SMTP send are both
injected, so no network or mail server is touched.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from job_watcher.config import Config
from job_watcher.diff import diff_jobs
from job_watcher.notifier import build_message, build_subject, render_text
from job_watcher.scraper import Job, _default_fetcher, parse_jobs
from job_watcher.watcher import run_once


def sample_payload(jobs):
  return json.dumps({"jobs": jobs, "meta": {"total": len(jobs)}})


SWE = {
  "id": 1,
  "title": "Software Engineer",
  "updated_at": "2026-01-01T00:00:00-05:00",
  "absolute_url": "https://job-boards.greenhouse.io/pokemoncareers/jobs/1",
  "location": {"name": "Bellevue, WA"},
}
DESIGNER = {
  "id": 2,
  "title": "Product Designer",
  "updated_at": "2026-01-02T00:00:00-05:00",
  "absolute_url": "https://job-boards.greenhouse.io/pokemoncareers/jobs/2",
  "location": {"name": "Remote"},
}


class ParseJobsTests(unittest.TestCase):
  def test_parses_and_normalises_fields(self):
    board = parse_jobs("pokemoncareers", sample_payload([SWE]))
    self.assertEqual(len(board.jobs), 1)
    job = board.jobs[0]
    self.assertEqual(job.id, "1")
    self.assertEqual(job.title, "Software Engineer")
    self.assertEqual(job.location, "Bellevue, WA")
    self.assertEqual(job.url, SWE["absolute_url"])

  def test_sorts_jobs_by_title(self):
    board = parse_jobs("pokemoncareers", sample_payload([SWE, DESIGNER]))
    self.assertEqual([job.title for job in board.jobs], ["Product Designer", "Software Engineer"])

  def test_missing_location_is_blank(self):
    raw = dict(SWE)
    raw.pop("location")
    board = parse_jobs("pokemoncareers", sample_payload([raw]))
    self.assertEqual(board.jobs[0].location, "")

  def test_non_list_jobs_raises(self):
    with self.assertRaises(ValueError):
      parse_jobs("pokemoncareers", json.dumps({"jobs": {}}))


class FetcherGuardTests(unittest.TestCase):
  def test_default_fetcher_refuses_non_https(self):
    for url in ("http://example.com", "file:///etc/passwd", "ftp://example.com"):
      with self.assertRaises(ValueError):
        _default_fetcher(url)


class DiffTests(unittest.TestCase):
  def _map(self, *jobs):
    return {job.id: job for job in jobs}

  def test_detects_added_and_removed(self):
    a = Job("1", "Software Engineer", "Bellevue", "u1", "t1")
    b = Job("2", "Designer", "Remote", "u2", "t2")
    changes = diff_jobs(self._map(a), self._map(b))
    self.assertEqual([j.id for j in changes.added], ["2"])
    self.assertEqual([j.id for j in changes.removed], ["1"])
    self.assertFalse(changes.changed)
    self.assertTrue(changes.has_changes)

  def test_detects_changed_fields(self):
    before = Job("1", "Software Engineer", "Bellevue", "u1", "t1")
    after = Job("1", "Senior Software Engineer", "Seattle", "u1", "t2")
    changes = diff_jobs(self._map(before), self._map(after))
    self.assertEqual(len(changes.changed), 1)
    labels = [label for label, _, _ in changes.changed[0].fields_changed()]
    self.assertEqual(labels, ["Title", "Location", "Last updated"])

  def test_identical_snapshots_have_no_changes(self):
    job = Job("1", "Software Engineer", "Bellevue", "u1", "t1")
    changes = diff_jobs(self._map(job), self._map(job))
    self.assertFalse(changes.has_changes)
    self.assertEqual(changes.total, 0)


class NotifierTests(unittest.TestCase):
  def test_subject_summarises_counts(self):
    changes = diff_jobs(
      {"1": Job("1", "Old", "", "u1", "t1")},
      {"2": Job("2", "New", "", "u2", "t2")},
    )
    subject = build_subject("pokemoncareers", changes)
    self.assertIn("1 new", subject)
    self.assertIn("1 removed", subject)

  def test_text_body_lists_new_jobs(self):
    changes = diff_jobs({}, {"2": Job("2", "Product Designer", "Remote", "https://x/2", "t2")})
    body = render_text("pokemoncareers", changes)
    self.assertIn("Product Designer", body)
    self.assertIn("https://x/2", body)

  def test_build_message_has_plain_and_html_parts(self):
    config = Config(board="pokemoncareers", email_from="a@b.com", email_to="c@d.com")
    changes = diff_jobs({}, {"2": Job("2", "Designer", "Remote", "https://x/2", "t2")})
    message = build_message(config, changes)
    self.assertEqual(message["To"], "c@d.com")
    self.assertTrue(message.is_multipart())
    subtypes = {part.get_content_subtype() for part in message.iter_parts()}
    self.assertEqual(subtypes, {"plain", "html"})


class RunOnceTests(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.state_file = Path(self.tmp.name) / "state.json"
    self.sent = []

  def _config(self, **overrides):
    defaults = dict(
      board="pokemoncareers",
      state_file=self.state_file,
      smtp_host="smtp.example.com",
      email_from="a@b.com",
      email_to="c@d.com",
    )
    defaults.update(overrides)
    return Config(**defaults)

  def _sender(self, message, config):
    self.sent.append(message)

  def test_first_run_records_baseline_without_email(self):
    fetcher = lambda url: sample_payload([SWE])
    result = run_once(self._config(), fetcher=fetcher, sender=self._sender)
    self.assertTrue(result.first_run)
    self.assertEqual(result.job_count, 1)
    self.assertFalse(result.notified)
    self.assertEqual(self.sent, [])
    self.assertTrue(self.state_file.exists())

  def test_first_run_can_email_when_opted_in(self):
    fetcher = lambda url: sample_payload([SWE])
    result = run_once(self._config(notify_on_first_run=True), fetcher=fetcher, sender=self._sender)
    self.assertTrue(result.notified)
    self.assertEqual(len(self.sent), 1)

  def test_second_run_emails_on_new_posting(self):
    run_once(self._config(), fetcher=lambda url: sample_payload([SWE]), sender=self._sender)
    result = run_once(
      self._config(),
      fetcher=lambda url: sample_payload([SWE, DESIGNER]),
      sender=self._sender,
    )
    self.assertFalse(result.first_run)
    self.assertTrue(result.notified)
    self.assertEqual(len(self.sent), 1)
    plain = self.sent[0].get_body(preferencelist=("plain",)).get_content()
    self.assertIn("Product Designer", plain)

  def test_no_email_when_board_unchanged(self):
    run_once(self._config(), fetcher=lambda url: sample_payload([SWE]), sender=self._sender)
    result = run_once(self._config(), fetcher=lambda url: sample_payload([SWE]), sender=self._sender)
    self.assertFalse(result.has_changes)
    self.assertEqual(self.sent, [])

  def test_dry_run_never_sends(self):
    run_once(self._config(), fetcher=lambda url: sample_payload([SWE]), sender=self._sender)
    result = run_once(
      self._config(dry_run=True),
      fetcher=lambda url: sample_payload([SWE, DESIGNER]),
      sender=self._sender,
    )
    self.assertTrue(result.has_changes)
    self.assertFalse(result.notified)
    self.assertEqual(self.sent, [])

  def test_email_failure_does_not_advance_snapshot(self):
    run_once(self._config(), fetcher=lambda url: sample_payload([SWE]), sender=self._sender)

    def failing_sender(message, config):
      raise RuntimeError("smtp down")

    with self.assertRaises(RuntimeError):
      run_once(
        self._config(),
        fetcher=lambda url: sample_payload([SWE, DESIGNER]),
        sender=failing_sender,
      )

    # Snapshot must still hold only the original posting, so the change is
    # re-detected (and re-sent) on the next successful run.
    result = run_once(
      self._config(),
      fetcher=lambda url: sample_payload([SWE, DESIGNER]),
      sender=self._sender,
    )
    self.assertTrue(result.notified)


if __name__ == "__main__":
  unittest.main()
