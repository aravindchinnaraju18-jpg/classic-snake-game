import {
  GRID_SIZE,
  TICK_MS,
  createInitialState,
  queueDirection,
  tickState,
  togglePause,
} from "./snake-logic.js";

const boardElement = document.querySelector("#board");
const scoreElement = document.querySelector("#score");
const bestScoreElement = document.querySelector("#best-score");
const statusElement = document.querySelector("#status");
const restartButton = document.querySelector("#restart-button");
const pauseButton = document.querySelector("#pause-button");
const controlButtons = document.querySelectorAll("[data-direction]");

const bestScoreKey = "snake-best-score";
let state = createInitialState();
let bestScore = Number.parseInt(window.localStorage.getItem(bestScoreKey) ?? "0", 10) || 0;

const cells = Array.from({ length: GRID_SIZE * GRID_SIZE }, () => {
  const cell = document.createElement("div");
  cell.className = "cell";
  boardElement.appendChild(cell);
  return cell;
});

function random() {
  return Math.random();
}

function setState(nextState) {
  state = nextState;

  if (state.score > bestScore) {
    bestScore = state.score;
    window.localStorage.setItem(bestScoreKey, String(bestScore));
  }

  render();
}

function restartGame() {
  setState(createInitialState(random));
  boardElement.focus();
}

function handleDirectionInput(direction) {
  setState(queueDirection(state, direction));
  boardElement.focus();
}

function updateStatus() {
  if (state.isWin) {
    statusElement.textContent = "You filled the board. Restart to play again.";
    pauseButton.textContent = "Pause";
    return;
  }

  if (state.isGameOver) {
    statusElement.textContent = "Game over. Restart to play again.";
    pauseButton.textContent = "Pause";
    return;
  }

  if (!state.hasStarted) {
    statusElement.textContent = "Press any arrow key or WASD to start.";
    pauseButton.textContent = "Pause";
    return;
  }

  if (state.isPaused) {
    statusElement.textContent = "Paused.";
    pauseButton.textContent = "Resume";
    return;
  }

  statusElement.textContent = "Playing.";
  pauseButton.textContent = "Pause";
}

function render() {
  scoreElement.textContent = String(state.score);
  bestScoreElement.textContent = String(bestScore);
  updateStatus();

  for (const cell of cells) {
    cell.className = "cell";
  }

  if (state.food) {
    const foodIndex = state.food.y * GRID_SIZE + state.food.x;
    cells[foodIndex].classList.add("food");
  }

  state.snake.forEach((segment, index) => {
    const cellIndex = segment.y * GRID_SIZE + segment.x;
    cells[cellIndex].classList.add(index === 0 ? "snake-head" : "snake");
  });
}

function handleKeydown(event) {
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  const keyMap = {
    ArrowUp: "up",
    ArrowDown: "down",
    ArrowLeft: "left",
    ArrowRight: "right",
    w: "up",
    a: "left",
    s: "down",
    d: "right",
  };

  const direction = keyMap[key];
  if (direction) {
    event.preventDefault();
    handleDirectionInput(direction);
    return;
  }

  if (key === " " || key === "p") {
    event.preventDefault();
    setState(togglePause(state));
  }
}

document.addEventListener("keydown", handleKeydown);
restartButton.addEventListener("click", restartGame);
pauseButton.addEventListener("click", () => {
  setState(togglePause(state));
  boardElement.focus();
});

controlButtons.forEach((button) => {
  button.addEventListener("click", () => {
    handleDirectionInput(button.dataset.direction);
  });
});

window.setInterval(() => {
  setState(tickState(state, random));
}, TICK_MS);

render();
