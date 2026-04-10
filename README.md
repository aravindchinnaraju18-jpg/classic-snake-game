# Aravind's Snake App

A small Python web app with registration, login, SQLite persistence, and a protected Snake dashboard. The frontend Snake game still uses plain HTML, CSS, and JavaScript, and the repo now includes a real build step that packages the app into `build/`.

## Run locally

From the repo root, start the app server:

```powershell
python app.py
```

Then open `http://127.0.0.1:8000`.

## Auth workflow

- Visit `/register` to create a user
- You are logged in automatically after registration
- The Snake dashboard is served at `/app`
- User accounts and sessions are stored in SQLite at `data/app.db`

## Build the app

Create a packaged build in `build/`:

```powershell
python scripts/build.py
```

Then run the built app:

```powershell
python build/app.py
```

## Run unit tests

The project uses Python `unittest` for the backend auth flow and a tiny dependency-free browser test runner for the Snake game logic.

1. Start the same local server:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-tests.ps1
```

The PowerShell script runs:

- Python auth and app tests
- Browser Snake logic tests with function and branch coverage

## Run tests in PowerShell

If you want to see the test results directly in PowerShell before committing, run:

```powershell
.\scripts\run-tests.ps1
```

This runs the Python backend tests first, then starts a temporary local server, opens the browser Snake tests headlessly, and prints the summary plus each pass/fail line in the terminal.

## Run tests automatically on commit

This repo can also run the same PowerShell tests automatically during `git commit` through a Git `pre-commit` hook.

If the hook is configured, Git will:

- run `.\scripts\run-tests.ps1`
- stop the commit if any test fails
- allow the commit only when the test run passes

## Files

- `app.py`: local development server entry point
- `snake_portal/`: Python app, auth, and rendering code
- `styles.css`: app and game styling
- `src/snake-logic.js`: deterministic Snake game rules
- `src/snake-game.js`: Snake DOM rendering and controls
- `scripts/build.py`: build step that packages the app into `build/`
- `scripts/run-tests.ps1`: PowerShell runner for terminal test output
- `tests/test_auth.py`: backend auth tests
- `tests/test_app.py`: backend route tests
- `tests/snake-logic.test.js`: unit tests for core game rules
- `tests/test-runner.js`: browser-based test harness

## Manual verification

- Register a new account and confirm you land on `/app`
- Log out and confirm `/app` redirects back to `/login`
- Log back in with the same credentials
- Movement works with arrow keys and `W`, `A`, `S`, `D`
- Snake grows by one segment after eating food
- Score increments after eating food
- Hitting a wall ends the game
- Running into the snake body ends the game
- Pause toggles with `Space`, `P`, and the pause button
- Restart resets the board and score
