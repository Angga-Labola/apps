"""Bounded Sokoban search used to check levels and produce move sequences.

The search operates on box pushes rather than every player step. Lowercase
letters in a returned path are player walks; uppercase letters are pushes.
"""

from collections import deque
import re
import time
from typing import Literal


SolveStatus = Literal["solvable", "unsolvable", "unknown"]
_DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))
_OPPOSITE = (1, 0, 3, 2)
_MOVE_CHARS = "UDLR"
# Return "unknown" rather than claiming a result when either safety budget is hit.
_MAX_SEARCH_STATES = 1000000
_MAX_SEARCH_SECONDS = 20.0


def _level_map(level: object) -> str | None:
    if isinstance(level, str):
        return level
    if not isinstance(level, dict):
        return None

    value = next(
        (level[key] for key in ("map", "level", "layout", "board", "data") if key in level),
        None,
    )
    if isinstance(value, str):
        width = level.get("width")
        height = level.get("height")
        if (
            re.fullmatch(r"[0-7]+", value)
            and isinstance(width, int)
            and isinstance(height, int)
            and width > 0
            and height > 0
            and len(value) == width * height
        ):
            tiles = " #@$.*+#"
            return "\n".join(
                "".join(tiles[int(tile)] for tile in value[row * width:(row + 1) * width])
                for row in range(height)
            )
        if "\n" in value or "\r" in value or ("@" in value and "$" in value):
            return value
    if isinstance(value, list) and all(isinstance(row, str) for row in value):
        return "\n".join(value)
    return None


def _parse_board(level: object):
    map_text = _level_map(level)
    if map_text is None:
        return None

    rows = [row.rstrip() for row in map_text.replace("\r", "").split("\n")]
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    if not rows:
        return None

    width = max(map(len, rows))
    height = len(rows)
    player = None
    boxes = set()
    goals = set()
    floor = set()
    for y, row in enumerate(rows):
        for x in range(width):
            tile = row[x] if x < len(row) else " "
            position = y * width + x
            if tile == "#":
                continue
            floor.add(position)
            if tile == "$" or tile == "*":
                boxes.add(position)
            if tile == "." or tile == "*" or tile == "+":
                goals.add(position)
            if tile == "@" or tile == "+":
                if player is not None:
                    return None
                player = position

    if player is None or not boxes or not goals:
        return None
    return width, height, floor, player, boxes, goals


def _neighbors(width: int, height: int, floor: set[int]) -> list[tuple[int, ...]]:
    result = []
    for position in range(width * height):
        x, y = position % width, position // width
        result.append(tuple(
            (y + dy) * width + x + dx
            if 0 <= x + dx < width and 0 <= y + dy < height
            and (y + dy) * width + x + dx in floor
            else -1
            for dx, dy in _DIRECTIONS
        ))
    return result


def _reachable(start: int, boxes: set[int], neighbors: list[tuple[int, ...]]):
    # Any player position in this connected region is equivalent until a box
    # is pushed, so the smallest reachable tile is a stable state key.
    seen = 1 << start
    pending = [start]
    while pending:
        position = pending.pop()
        for neighbor in neighbors[position]:
            if neighbor >= 0 and neighbor not in boxes and not (seen >> neighbor) & 1:
                seen |= 1 << neighbor
                pending.append(neighbor)
    return seen, (seen & -seen).bit_length() - 1


def _walking_predecessors(
    start: int,
    boxes: set[int],
    neighbors: list[tuple[int, ...]],
) -> dict[int, tuple[int, str] | None]:
    previous = {start: None}
    pending = deque([start])
    while pending:
        position = pending.popleft()
        for direction, neighbor in enumerate(neighbors[position]):
            if neighbor >= 0 and neighbor not in boxes and neighbor not in previous:
                previous[neighbor] = (position, _MOVE_CHARS[direction].lower())
                pending.append(neighbor)
    return previous


def _walking_path(previous: dict[int, tuple[int, str] | None], destination: int) -> str:
    moves = []
    while previous[destination] is not None:
        parent, move = previous[destination]
        moves.append(move)
        destination = parent
    return "".join(reversed(moves))


def _solution_to_state(
    parents: dict[tuple[tuple[int, ...], int], tuple[tuple[tuple[int, ...], int] | None, str]],
    state: tuple[tuple[int, ...], int],
    final_segment: str = "",
) -> str:
    segments = [final_segment]
    while parents[state][0] is not None:
        parent, segment = parents[state]
        segments.append(segment)
        state = parent
    return "".join(reversed(segments))


def _has_filled_2x2(
    moved_box: int,
    width: int,
    height: int,
    floor: set[int],
    boxes: set[int],
    goals: set[int],
) -> bool:
    x, y = moved_box % width, moved_box // width
    for left in (x - 1, x):
        for top in (y - 1, y):
            square = tuple(
                row * width + column
                if 0 <= column < width and 0 <= row < height
                else -1
                for row, column in (
                    (top, left),
                    (top, left + 1),
                    (top + 1, left),
                    (top + 1, left + 1),
                )
            )
            if all(position not in floor or position in boxes for position in square):
                if any(position in boxes and position not in goals for position in square):
                    return True
    return False


def _search_sokoban_level(level: object, include_solution: bool) -> tuple[SolveStatus, str | None]:
    started_at = time.monotonic()
    board = _parse_board(level)
    if board is None:
        return "unknown", None
    width, height, floor, player, boxes, goals = board
    if len(boxes) != len(goals):
        return "unsolvable", None
    if boxes <= goals:
        return "solvable", ""

    neighbors = _neighbors(width, height, floor)
    can_reach_goal = set()
    for goal in goals:
        reachable = {goal}
        pending = deque([goal])
        while pending:
            position = pending.popleft()
            for opposite in _OPPOSITE:
                previous_box = neighbors[position][opposite]
                if previous_box < 0:
                    continue
                player_stand = neighbors[previous_box][opposite]
                if player_stand >= 0 and previous_box not in reachable:
                    reachable.add(previous_box)
                    pending.append(previous_box)
        can_reach_goal.update(reachable)

    if any(box not in can_reach_goal for box in boxes):
        return "unsolvable", None

    initial_boxes = tuple(sorted(boxes))
    initial_reachable, initial_anchor = _reachable(player, boxes, neighbors)
    # Deduplicate box layouts plus the player's reachable region, not each
    # individual player step; this keeps the push search much smaller.
    initial_state = (initial_boxes, initial_anchor)
    pending_states = deque([(initial_boxes, player, initial_reachable, initial_anchor)])
    visited = {initial_state}
    parents = {initial_state: (None, "")} if include_solution else {}
    explored = 0

    while pending_states:
        current_boxes, current_player, reachable, current_anchor = pending_states.popleft()
        explored += 1
        if explored > _MAX_SEARCH_STATES or time.monotonic() - started_at > _MAX_SEARCH_SECONDS:
            return "unknown", None

        current_state = (current_boxes, current_anchor)
        box_positions = set(current_boxes)
        if box_positions <= goals:
            solution = _solution_to_state(parents, current_state) if include_solution else None
            return "solvable", solution

        walk_previous = (
            _walking_predecessors(current_player, box_positions, neighbors)
            if include_solution
            else None
        )
        for box in current_boxes:
            for direction, opposite in enumerate(_OPPOSITE):
                stand = neighbors[box][opposite]
                destination = neighbors[box][direction]
                if (
                    stand < 0
                    or not (reachable >> stand) & 1
                    or destination < 0
                    or destination in box_positions
                    or destination not in can_reach_goal
                ):
                    continue

                next_boxes = tuple(sorted((box_positions - {box}) | {destination}))
                next_box_positions = set(next_boxes)
                if destination not in goals and _has_filled_2x2(
                    destination, width, height, floor, next_box_positions, goals
                ):
                    continue
                if next_box_positions <= goals:
                    if not include_solution:
                        return "solvable", None
                    segment = (
                        _walking_path(walk_previous, stand)
                        + _MOVE_CHARS[direction]
                    )
                    return "solvable", _solution_to_state(
                        parents,
                        current_state,
                        segment,
                    )

                next_player = box
                next_reachable, next_anchor = _reachable(
                    next_player,
                    next_box_positions,
                    neighbors,
                )
                next_state = (next_boxes, next_anchor)
                if next_state not in visited:
                    visited.add(next_state)
                    if include_solution:
                        segment = (
                            _walking_path(walk_previous, stand)
                            + _MOVE_CHARS[direction]
                        )
                        parents[next_state] = (current_state, segment)
                    pending_states.append((
                        next_boxes,
                        next_player,
                        next_reachable,
                        next_anchor,
                    ))

    return "unsolvable", None


def solve_sokoban_level(level: object) -> SolveStatus:
    """Check a level, trusting positive LetsLogic move counts when available."""
    if isinstance(level, dict):
        for key in ("blue_moves", "green_moves"):
            moves = level.get(key)
            if isinstance(moves, (int, float)) and moves > 0:
                return "solvable"
    return _search_sokoban_level(level, include_solution=False)[0]


def find_sokoban_solution(level: object) -> tuple[SolveStatus, str | None]:
    """Search locally for a walk-and-push sequence for browser playback."""
    return _search_sokoban_level(level, include_solution=True)
