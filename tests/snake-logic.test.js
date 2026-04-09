import {
  GRID_SIZE,
  createInitialState,
  getCoverageSnapshot,
  isSelfCollision,
  isWallCollision,
  placeFood,
  queueDirection,
  resetCoverage,
  tickState,
  togglePause,
} from "../src/snake-logic.js?v=20260409";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(`${message} Expected ${expected}, received ${actual}.`);
  }
}

function assertPosition(actual, expected, message) {
  const matches = actual && actual.x === expected.x && actual.y === expected.y;
  assert(matches, `${message} Expected (${expected.x}, ${expected.y}).`);
}

function withState(overrides) {
  return {
    gridSize: GRID_SIZE,
    snake: [
      { x: 2, y: 8 },
      { x: 1, y: 8 },
      { x: 0, y: 8 },
    ],
    direction: "right",
    queuedDirection: "right",
    food: { x: 6, y: 8 },
    score: 0,
    isGameOver: false,
    isWin: false,
    hasStarted: true,
    isPaused: false,
    ...overrides,
  };
}

export const tests = [
  {
    name: "resetCoverage clears the existing coverage counters",
    run() {
      createInitialState(() => 0);
      resetCoverage();
      const snapshot = getCoverageSnapshot();
      assertEqual(snapshot.functions.createInitialState, 0, "Function coverage should reset to zero.");
      assertEqual(snapshot.functions.placeFood, 0, "Nested function coverage should reset to zero.");
    },
  },
  {
    name: "createInitialState places food away from the snake",
    run() {
      const state = createInitialState(() => 0);
      assertEqual(state.snake.length, 3, "Initial snake should have three segments.");
      assertPosition(state.food, { x: 0, y: 0 }, "Initial food should use the first free cell.");
      assert(!state.snake.some((segment) => segment.x === state.food.x && segment.y === state.food.y), "Food should not overlap the snake.");
    },
  },
  {
    name: "queueDirection starts the game and changes direction",
    run() {
      const state = withState({ hasStarted: false });
      const nextState = queueDirection(state, "up");
      assertEqual(nextState.hasStarted, true, "Direction input should start the game.");
      assertEqual(nextState.queuedDirection, "up", "Queued direction should update.");
    },
  },
  {
    name: "queueDirection blocks reversing into the opposite direction",
    run() {
      const state = withState({ direction: "right", queuedDirection: "right", hasStarted: true });
      const nextState = queueDirection(state, "left");
      assertEqual(nextState.queuedDirection, "right", "Opposite direction should be ignored.");
    },
  },
  {
    name: "queueDirection ignores invalid directions",
    run() {
      const state = withState({});
      const nextState = queueDirection(state, "northwest");
      assertEqual(nextState, state, "Unknown directions should return the original state.");
    },
  },
  {
    name: "tickState moves the snake one cell in the queued direction",
    run() {
      const state = withState({ queuedDirection: "down" });
      const nextState = tickState(state, () => 0);
      assertPosition(nextState.snake[0], { x: 2, y: 9 }, "Head should move one cell down.");
      assertEqual(nextState.snake.length, 3, "Snake length should remain constant without food.");
    },
  },
  {
    name: "tickState does nothing when the game is paused",
    run() {
      const state = withState({ isPaused: true });
      const nextState = tickState(state, () => 0);
      assertEqual(nextState, state, "Paused games should not advance.");
    },
  },
  {
    name: "tickState grows the snake and increments the score after eating food",
    run() {
      const state = withState({ food: { x: 3, y: 8 } });
      const nextState = tickState(state, () => 0);
      assertEqual(nextState.score, 1, "Score should increment after food is eaten.");
      assertEqual(nextState.snake.length, 4, "Snake should grow by one segment.");
      assertPosition(nextState.snake[0], { x: 3, y: 8 }, "Head should move onto the food cell.");
      assertPosition(nextState.food, { x: 0, y: 0 }, "Next food should be placed on the first open cell.");
    },
  },
  {
    name: "tickState marks game over on wall collision",
    run() {
      const state = withState({
        snake: [{ x: GRID_SIZE - 1, y: 4 }, { x: GRID_SIZE - 2, y: 4 }, { x: GRID_SIZE - 3, y: 4 }],
        direction: "right",
        queuedDirection: "right",
      });
      const nextState = tickState(state, () => 0);
      assertEqual(nextState.isGameOver, true, "Crossing the boundary should end the game.");
    },
  },
  {
    name: "tickState marks game over on self collision",
    run() {
      const state = withState({
        snake: [
          { x: 4, y: 4 },
          { x: 4, y: 5 },
          { x: 3, y: 5 },
          { x: 3, y: 4 },
          { x: 3, y: 3 },
          { x: 4, y: 3 },
        ],
        direction: "up",
        queuedDirection: "left",
        food: { x: 10, y: 10 },
      });
      const nextState = tickState(state, () => 0);
      assertEqual(nextState.isGameOver, true, "Running into the body should end the game.");
    },
  },
  {
    name: "tickState marks a win when the final food fills the board",
    run() {
      const state = {
        gridSize: 2,
        snake: [
          { x: 0, y: 0 },
          { x: 1, y: 0 },
          { x: 1, y: 1 },
        ],
        direction: "left",
        queuedDirection: "down",
        food: { x: 0, y: 1 },
        score: 0,
        isGameOver: false,
        isWin: false,
        hasStarted: true,
        isPaused: false,
      };
      const nextState = tickState(state, () => 0);
      assertEqual(nextState.isWin, true, "Eating the last available food should mark a win.");
      assertEqual(nextState.isGameOver, true, "Winning should also end the game.");
      assertEqual(nextState.food, null, "No food should remain once the board is full.");
    },
  },
  {
    name: "togglePause only works after the game has started",
    run() {
      const notStarted = withState({ hasStarted: false, isPaused: false });
      const unchanged = togglePause(notStarted);
      assertEqual(unchanged.isPaused, false, "Pause should not toggle before the game starts.");

      const playing = withState({ hasStarted: true, isPaused: false });
      const paused = togglePause(playing);
      assertEqual(paused.isPaused, true, "Pause should toggle during play.");
    },
  },
  {
    name: "togglePause does nothing after game over",
    run() {
      const state = withState({ isGameOver: true, isPaused: false });
      const nextState = togglePause(state);
      assertEqual(nextState, state, "Pause should not toggle after the game ends.");
    },
  },
  {
    name: "placeFood returns null when the board is full",
    run() {
      const snake = [];
      for (let y = 0; y < 2; y += 1) {
        for (let x = 0; x < 2; x += 1) {
          snake.push({ x, y });
        }
      }
      const food = placeFood(snake, 2, () => 0);
      assertEqual(food, null, "No food should be placed on a full board.");
    },
  },
  {
    name: "collision helpers detect expected cases",
    run() {
      assertEqual(isWallCollision({ x: -1, y: 0 }, GRID_SIZE), true, "Negative X should collide with the wall.");
      assertEqual(isWallCollision({ x: 0, y: 0 }, GRID_SIZE), false, "In-bounds positions should not collide with the wall.");
      assertEqual(
        isSelfCollision(
          { x: 2, y: 2 },
          [{ x: 2, y: 2 }, { x: 2, y: 3 }, { x: 2, y: 2 }]
        ),
        true,
        "Matching a later segment should count as self collision."
      );
      assertEqual(
        isSelfCollision(
          { x: 1, y: 1 },
          [{ x: 1, y: 1 }, { x: 1, y: 2 }, { x: 2, y: 2 }]
        ),
        false,
        "Non-matching segments should not count as self collision."
      );
    },
  },
];
