export const GRID_SIZE = 16;
export const INITIAL_DIRECTION = "right";
export const TICK_MS = 140;

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
  if (!DIRECTION_VECTORS[nextDirection]) {
    return state;
  }

  if (state.hasStarted && nextDirection === OPPOSITE_DIRECTIONS[state.direction]) {
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
  if (state.isGameOver || !state.hasStarted) {
    return state;
  }

  return {
    ...state,
    isPaused: !state.isPaused,
  };
}

export function tickState(state, random = Math.random) {
  if (state.isGameOver || state.isPaused || !state.hasStarted) {
    return state;
  }

  const direction = state.queuedDirection;
  const vector = DIRECTION_VECTORS[direction];
  const head = state.snake[0];
  const nextHead = { x: head.x + vector.x, y: head.y + vector.y };

  if (isWallCollision(nextHead, state.gridSize)) {
    return {
      ...state,
      direction,
      isGameOver: true,
    };
  }

  const willGrow =
    state.food !== null && nextHead.x === state.food.x && nextHead.y === state.food.y;
  const nextSnake = [nextHead, ...state.snake];

  if (!willGrow) {
    nextSnake.pop();
  }

  if (isSelfCollision(nextHead, nextSnake)) {
    return {
      ...state,
      direction,
      snake: nextSnake,
      isGameOver: true,
    };
  }

  const nextFood = willGrow ? placeFood(nextSnake, state.gridSize, random) : state.food;
  const isWin = willGrow && nextFood === null;

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

  if (available.length === 0) {
    return null;
  }

  const index = Math.floor(random() * available.length);
  return available[index];
}

export function isWallCollision(position, gridSize) {
  return (
    position.x < 0 ||
    position.y < 0 ||
    position.x >= gridSize ||
    position.y >= gridSize
  );
}

export function isSelfCollision(head, snake) {
  return snake.slice(1).some((segment) => segment.x === head.x && segment.y === head.y);
}
