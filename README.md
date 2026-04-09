# Snake

A minimal classic Snake implementation built with plain HTML, CSS, and JavaScript.

## Run locally

From the repo root, start a simple static server:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Files

- `index.html`: game page
- `styles.css`: minimal app styling
- `src/snake-logic.js`: deterministic game rules
- `src/snake-game.js`: DOM rendering and controls

## Manual verification

- Movement works with arrow keys and `W`, `A`, `S`, `D`
- Snake grows by one segment after eating food
- Score increments after eating food
- Hitting a wall ends the game
- Running into the snake body ends the game
- Pause toggles with `Space`, `P`, and the pause button
- Restart resets the board and score
