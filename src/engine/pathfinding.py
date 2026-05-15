# src/engine/pathfinding.py
from .board import Board, Position, GOAL_ROW, P1, P2
from collections import deque
from typing import List, Optional

# Core BFS
def _bfs(board: Board, start: Position, goal_row: int) -> Optional[List[Position]]:
    """
    Returns the full path as a list of positions [start, ..., goal],
    or None if no path exists (player is completely blocked).

    How it works:
      1. Start from the pawn's current cell.
      2. Expand outward one step at a time (BFS = shortest path guaranteed).
      3. For each neighbor: check in-bounds, not visited, no wall between.
      4. If we reach goal_row → reconstruct and return the path.
      5. If queue empties with no goal found → return None (blocked).
    """
    # Edge case: pawn already on goal row
    if start[0] == goal_row:
        return [start]

    # parent[pos] = which cell we came from (used to reconstruct path)
    parent: dict = {start: None}
    queue: deque = deque([start])

    while queue:
        r, c = queue.popleft()

        # Try all 4 directions: up, down, left, right
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc

            # Skip if out of bounds
            if not board.is_inside(nr, nc):
                continue

            # Skip if already visited
            if (nr, nc) in parent:
                continue

            # Skip if there is a wall between current cell and neighbor
            if board.has_wall_between(r, c, nr, nc):
                continue

            # Mark as visited with parent pointer
            parent[(nr, nc)] = (r, c)

            # Goal check
            if nr == goal_row:
                return _reconstruct_path(parent, start, (nr, nc))

            queue.append((nr, nc))

    # Queue exhausted — no path exists
    return None


def _reconstruct_path(
    parent: dict,
    start: Position,
    end: Position,
) -> List[Position]:
    """
    Walk the parent pointers from end back to start, then reverse.
    This gives us the path in the correct order: [start, ..., end].
    """
    path = []
    node = end
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path


# ─────────────────────────────────────────────────────────────
# APIs (what everyone else imports from this file)
# ─────────────────────────────────────────────────────────────

def has_path(board: Board, player: int) -> bool:
    """
    Return True if `player` has at least one path to their goal row.

    Called per-player when you only need a yes/no answer.

    Usage example:
        from engine.pathfinding import has_path
        if not has_path(board, P1):
            print("P1 is completely blocked!")
    """
    start    = board.get_position(player)
    goal_row = GOAL_ROW[player]
    return _bfs(board, start, goal_row) is not None


def both_players_have_path(board: Board) -> bool:
    """
    Return True only if BOTH players can still reach their goal row.

    This is the most important function in this file.
    It is called inside is_valid_wall() in rules.py every time
    a player tries to place a wall:

        test_board = board.copy()
        test_board.h_walls.add(anchor)
        if not both_players_have_path(test_board):
            return False   # wall would trap someone — illegal

    P1 must be able to reach row 8.
    P2 must be able to reach row 0.
    Both must be reachable for the wall to be legal.
    """
    return has_path(board, P1) and has_path(board, P2)


def shortest_path_length(board: Board, player: int) -> Optional[int]:
    """
    Return the number of steps in the shortest path for `player`,
    or None if the player is completely blocked.

    This is what AI uses in the evaluation function:

        ai_dist  = shortest_path_length(board, ai_player)
        opp_dist = shortest_path_length(board, opponent)
        score    = opp_dist - ai_dist
        # positive score = AI is closer to winning = good

    Steps = number of cells to cross = len(path) - 1
    Example: path [(0,4),(1,4),(2,4)] has length 3 nodes = 2 steps
    """
    start    = board.get_position(player)
    goal_row = GOAL_ROW[player]
    path = _bfs(board, start, goal_row)
    if path is None:
        return None
    return len(path) - 1   # nodes - 1 = steps


def get_full_path(board: Board, player: int) -> Optional[List[Position]]:
    """
    Return the full shortest path for `player` as a list of positions,
    or None if blocked.

    Example output for P1 on a clear board:
        [(0,4), (1,4), (2,4), (3,4), (4,4), (5,4), (6,4), (7,4), (8,4)]

    Useful for:
      - UI: highlight the shortest path on the board in green
      - Debugging: see exactly which route is being used
      - Testing: verify walls are correctly blocking expected paths
    """
    start    = board.get_position(player)
    goal_row = GOAL_ROW[player]
    return _bfs(board, start, goal_row)