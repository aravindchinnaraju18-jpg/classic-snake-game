# Aravind's Snake App

A minimal classic Snake implementation built with plain HTML, CSS, and JavaScript.

## Run locally

From the repo root, start a simple static server:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Run unit tests

The project uses a tiny dependency-free browser test runner for the pure game logic.

1. Start the same local server:

```powershell
python -m http.server 8000
```

2. Open `http://localhost:8000/tests/`
3. Confirm the page reports all tests as passing and shows function and branch coverage percentages for `src/snake-logic.js`

## Run tests in PowerShell

If you want to see the test results directly in PowerShell before committing, run:

```powershell
.\scripts\run-tests.ps1
```

This starts a temporary local server, opens the browser tests headlessly, and prints the summary plus each pass/fail line in the terminal.

## Files

- `index.html`: game page
- `styles.css`: minimal app styling
- `src/snake-logic.js`: deterministic game rules
- `src/snake-game.js`: DOM rendering and controls
- `scripts/run-tests.ps1`: PowerShell runner for terminal test output
- `tests/snake-logic.test.js`: unit tests for core game rules
- `tests/test-runner.js`: browser-based test harness

## Manual verification

- Movement works with arrow keys and `W`, `A`, `S`, `D`
- Snake grows by one segment after eating food
- Score increments after eating food
- Hitting a wall ends the game
- Running into the snake body ends the game
- Pause toggles with `Space`, `P`, and the pause button
- Restart resets the board and score
