"""Fetch and normalise job postings from a Greenhouse job board.

Greenhouse exposes every public board through a JSON API, which is far more
reliable than scraping the rendered HTML page. The board at
``https://job-boards.greenhouse.io/pokemoncareers`` maps to the board token
``pokemoncareers`` and is served from::

    https://boards-api.greenhouse.io/v1/boards/pokemoncareers/jobs

The response looks roughly like::

    {
      "jobs": [
        {
          "id": 1234567,
          "title": "Software Engineer",
          "updated_at": "2026-01-01T00:00:00-05:00",
          "absolute_url": "https://job-boards.greenhouse.io/pokemoncareers/jobs/1234567",
          "location": {"name": "Bellevue, WA"}
        }
      ],
      "meta": {"total": 1}
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Callable, Dict, List
import urllib.parse
import urllib.request

BOARDS_API_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

# A plain identifier keeps us off Greenhouse's generic-bot blocklist without
# pretending to be a real browser.
USER_AGENT = "job-watcher/1.0 (+https://github.com/)"

# A sensible ceiling so a wedged connection can never hang the watcher loop.
DEFAULT_TIMEOUT = 30.0

# A callable that takes a URL and returns the raw response body as text. Made
# injectable so tests can exercise the parser without any network access.
Fetcher = Callable[[str], str]


@dataclass(frozen=True)
class Job:
  """A single normalised job posting.

  ``fingerprint`` captures the fields we treat as "the posting" for
  change-detection purposes, so an edited title, a relocation, or a content
  update (reflected in ``updated_at``) all register as a change.
  """

  id: str
  title: str
  location: str
  url: str
  updated_at: str

  @property
  def fingerprint(self) -> str:
    return "\x1f".join((self.title, self.location, self.updated_at))

  def to_dict(self) -> Dict[str, str]:
    return {
      "id": self.id,
      "title": self.title,
      "location": self.location,
      "url": self.url,
      "updated_at": self.updated_at,
    }

  @classmethod
  def from_dict(cls, data: Dict[str, str]) -> "Job":
    return cls(
      id=str(data.get("id", "")),
      title=str(data.get("title", "")),
      location=str(data.get("location", "")),
      url=str(data.get("url", "")),
      updated_at=str(data.get("updated_at", "")),
    )


@dataclass
class JobBoard:
  """The set of jobs fetched at one moment, keyed by job id."""

  board: str
  jobs: List[Job] = field(default_factory=list)

  def as_map(self) -> Dict[str, Job]:
    return {job.id: job for job in self.jobs}


def board_api_url(board: str) -> str:
  return BOARDS_API_TEMPLATE.format(board=board)


def _default_fetcher(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
  # Only ever fetch over HTTPS. Validating the scheme before opening the URL
  # means a misconfigured board token can never turn this into a local-file
  # read (file://) or a request to an unexpected protocol (ftp://, etc.).
  if urllib.parse.urlsplit(url).scheme != "https":
    raise ValueError(f"Refusing to fetch non-HTTPS URL: {url!r}")
  request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
  with urllib.request.urlopen(request, timeout=timeout) as response:
    charset = response.headers.get_content_charset() or "utf-8"
    return response.read().decode(charset)


def parse_jobs(board: str, payload: str) -> JobBoard:
  """Turn a raw Greenhouse API response body into a :class:`JobBoard`."""

  data = json.loads(payload)
  raw_jobs = data.get("jobs", [])
  if not isinstance(raw_jobs, list):
    raise ValueError("Unexpected Greenhouse response: 'jobs' is not a list")

  jobs: List[Job] = []
  for raw in raw_jobs:
    location = raw.get("location") or {}
    jobs.append(
      Job(
        id=str(raw.get("id", "")),
        title=(raw.get("title") or "").strip(),
        location=(location.get("name") or "").strip() if isinstance(location, dict) else "",
        url=raw.get("absolute_url") or "",
        updated_at=raw.get("updated_at") or "",
      )
    )

  # Sorting by title keeps email output and stored state stable regardless of
  # the order Greenhouse happens to return postings in.
  jobs.sort(key=lambda job: (job.title.lower(), job.id))
  return JobBoard(board=board, jobs=jobs)


def fetch_jobs(board: str, fetcher: Fetcher | None = None) -> JobBoard:
  """Fetch the live postings for ``board`` and return them normalised."""

  fetch = fetcher or _default_fetcher
  payload = fetch(board_api_url(board))
  return parse_jobs(board, payload)
