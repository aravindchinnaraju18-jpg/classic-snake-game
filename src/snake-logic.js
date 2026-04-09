export const GRID_SIZE = 16;
export const INITIAL_DIRECTION = "right";
export const TICK_MS = 140;

const coverageState = {
  functions: {},
  branches: {},
};

function coverFunction(name) {
  coverageState.functions[name] = (coverageState.functions[name] ?? 0) + 1;
}

function coverBranch(name, branch) {
  const entry = (coverageState.branches[name] ??= { true: 0, false: 0 });
  entry[branch] += 1;
}

export function getCoverageSnapshot() {
  return {
    functions: { ...coverageState.functions },
    branches: Object.fromEntries(
      Object.entries(coverageState.branches).map(([key, value]) => [key, { ...value }])
    ),
  };
}

export function resetCoverage() {
  for (const key of Object.keys(coverageState.functions)) {
    coverageState.functions[key] = 0;
  }

  for (const key of Object.keys(coverageState.branches)) {
    coverageState.branches[key] = { true: 0, false: 0 };
  }
}

const DIRECTION_VECTORS = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
};

const OPPOSITE_DIRECTIONS = {
  up: "down",
  down: "up",
  left: "right",
  right: "left",
};

export function createInitialState(random = Math.random) {
  coverFunction("createInitialState");
  const snake = [
    { x: 2, y: 8 },
    { x: 1, y: 8 },
    { x: 0, y: 8 },
  ];

  return {
    gridSize: GRID_SIZE,
    snake,
    direction: INITIAL_DIRECTION,
    queuedDirection: INITIAL_DIRECTION,
    food: placeFood(snake, GRID_SIZE, random),
    score: 0,
    isGameOver: false,
    isWin: false,
    hasStarted: false,
    isPaused: false,
  };
}

export function queueDirection(state, nextDirection) {
  coverFunction("queueDirection");
  const isInvalidDirection = !DIRECTION_VECTORS[nextDirection];
  coverBranch("queueDirection.invalidDirection", isInvalidDirection ? "true" : "false");
  if (isInvalidDirection) {
    return state;
  }

  const isOppositeDirection =
    state.hasStarted && nextDirection === OPPOSITE_DIRECTIONS[state.direction];
  coverBranch("queueDirection.oppositeDirection", isOppositeDirection ? "true" : "false");
  if (isOppositeDirection) {
    return state;
  }

  return {
    ...state,
    hasStarted: true,
    queuedDirection: nextDirection,
    isPaused: false,
  };
}

export function togglePause(state) {
  coverFunction("togglePause");
  const cannotTogglePause = state.isGameOver || !state.hasStarted;
  coverBranch("togglePause.cannotToggle", cannotTogglePause ? "true" : "false");
  if (cannotTogglePause) {
    return state;
  }

  return {
    ...state,
    isPaused: !state.isPaused,
  };
}

export function tickState(state, random = Math.random) {
  coverFunction("tickState");
  const shouldSkipTick = state.isGameOver || state.isPaused || !state.hasStarted;
  coverBranch("tickState.skip", shouldSkipTick ? "true" : "false");
  if (shouldSkipTick) {
    return state;
  }

  const direction = state.queuedDirection;
  const vector = DIRECTION_VECTORS[direction];
  const head = state.snake[0];
  const nextHead = { x: head.x + vector.x, y: head.y + vector.y };

  const hitWall = isWallCollision(nextHead, state.gridSize);
  coverBranch("tickState.wallCollision", hitWall ? "true" : "false");
  if (hitWall) {
    return {
      ...state,
      direction,
      isGameOver: true,
    };
  }

  const willGrow =
    state.food !== null && nextHead.x === state.food.x && nextHead.y === state.food.y;
  coverBranch("tickState.willGrow", willGrow ? "true" : "false");
  const nextSnake = [nextHead, ...state.snake];

  if (!willGrow) {
    nextSnake.pop();
  }

  const hitSelf = isSelfCollision(nextHead, nextSnake);
  coverBranch("tickState.selfCollision", hitSelf ? "true" : "false");
  if (hitSelf) {
    return {
      ...state,
      direction,
      snake: nextSnake,
      isGameOver: true,
    };
  }

  const nextFood = willGrow ? placeFood(nextSnake, state.gridSize, random) : state.food;
  const isWin = willGrow && nextFood === null;
  coverBranch("tickState.win", isWin ? "true" : "false");

  return {
    ...state,
    direction,
    snake: nextSnake,
    food: nextFood,
    score: willGrow ? state.score + 1 : state.score,
    isGameOver: isWin,
    isWin,
  };
}

export function placeFood(snake, gridSize, random = Math.random) {
  coverFunction("placeFood");
  const occupied = new Set(snake.map(({ x, y }) => `${x},${y}`));
  const available = [];

  for (let y = 0; y < gridSize; y += 1) {
    for (let x = 0; x < gridSize; x += 1) {
      const key = `${x},${y}`;
      if (!occupied.has(key)) {
        available.push({ x, y });
      }
    }
  }

  const isBoardFull = available.length === 0;
  coverBranch("placeFood.boardFull", isBoardFull ? "true" : "false");
  if (isBoardFull) {
    return null;
  }

  const index = Math.floor(random() * available.length);
  return available[index];
}

export function isWallCollision(position, gridSize) {
  coverFunction("isWallCollision");
  const collision =
    position.x < 0 ||
    position.y < 0 ||
    position.x >= gridSize ||
    position.y >= gridSize;
  coverBranch("isWallCollision.result", collision ? "true" : "false");
  return collision;
}

export function isSelfCollision(head, snake) {
  coverFunction("isSelfCollision");
  const collision = snake
    .slice(1)
    .some((segment) => segment.x === head.x && segment.y === head.y);
  coverBranch("isSelfCollision.result", collision ? "true" : "false");
  return collision;
}
