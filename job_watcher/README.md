# Job board watcher

Watches the Pokémon careers job board
(<https://job-boards.greenhouse.io/pokemoncareers>) and emails you whenever a
posting is **added**, **removed**, or **changed** since the last check.

It reads the board through Greenhouse's public JSON API
(`https://boards-api.greenhouse.io/v1/boards/pokemoncareers/jobs`) rather than
scraping HTML, so it is stable and fast. Everything is Python standard library —
no `pip install` required.

## How it works

1. **Fetch** the current postings from the Greenhouse board API.
2. **Compare** them against the snapshot saved from the previous run
   (title, location, and Greenhouse's `updated_at` make up each posting's
   fingerprint).
3. **Email** a summary of what changed (if anything).
4. **Save** the new snapshot for next time.

The first run just records a baseline and sends nothing (pass
`--notify-first-run` to change that).

## Configure email

Settings come from environment variables so secrets stay out of the command
line and the repo:

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `SMTP_HOST` | yes | — | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | no | `587` | |
| `SMTP_USER` | no | — | SMTP login (also the default `EMAIL_FROM`) |
| `SMTP_PASSWORD` | no | — | For Gmail, use an [App Password] |
| `SMTP_USE_TLS` | no | `true` | STARTTLS |
| `EMAIL_FROM` | yes | `SMTP_USER` | |
| `EMAIL_TO` | yes | — | where alerts are sent |
| `JOB_BOARD_TOKEN` | no | `pokemoncareers` | watch a different board |
| `JOB_STATE_FILE` | no | `data/job_state.json` | snapshot location |

[App Password]: https://support.google.com/accounts/answer/185833

## Run it

Preview changes without sending email (no SMTP settings needed):

```bash
python -m job_watcher --dry-run
```

Run once and email on changes:

```bash
export SMTP_HOST=smtp.gmail.com SMTP_USER=you@gmail.com \
       SMTP_PASSWORD="app-password" EMAIL_TO=you@gmail.com
python -m job_watcher
```

Run continuously, checking every 30 minutes:

```bash
python -m job_watcher --interval 1800
```

`python watch_jobs.py` is an equivalent entry point. Run `python -m job_watcher
--help` for all flags (`--board`, `--state-file`, `--to`, `--dry-run`,
`--notify-first-run`, `--interval`).

## Schedule it

- **cron** (checks every 6 hours):

  ```cron
  0 */6 * * * cd /path/to/repo && SMTP_HOST=... EMAIL_TO=... python -m job_watcher >> watch.log 2>&1
  ```

- **Built-in loop**: run with `--interval` under a process manager
  (`systemd`, `pm2`, `tmux`, …).

- **GitHub Actions (serverless)**: [`.github/workflows/job-watch.yml`](../.github/workflows/job-watch.yml)
  runs on a schedule and commits the snapshot back to the repo. Add `SMTP_HOST`,
  `SMTP_USER`, `SMTP_PASSWORD`, and `EMAIL_TO` as Actions secrets.

## Tests

```bash
python scripts/run-python-tests.py
```

Tests are fully offline — the Greenhouse fetch and the SMTP send are injected,
so nothing hits the network.
