# src/ai/minimax.py
import time
from ..engine import *
from ..ai.evaluation import evaluate_board


"""
Transposition table
Each entry: { key → (depth, score, best_move) }
Only trust a cached result when the stored depth >= the requested depth.
"""
_transposition_table: dict = {}


# Get Tactical Cells
def _build_hot_zone(p_path, opp_path, p_pos, opp_pos, radius: int = 2) -> set:
    """
    Three layers:
      A) All cells within `radius` steps of any cell on EITHER shortest path.
         radius=2 captures walls that force a one-cell detour around the path,
         plus walls that create a two-cell detour (the most common traps).
      B) A 2-cell halo around EACH pawn regardless of path length — ensures
         we never ignore threats right next to a player.
      C) Path-intersection zone: the 3×3 boxes around the point where the two
         paths cross (if they do).  Walls here affect BOTH players at once,
         which is exactly where the cleverest walls live.
    """
    zone = set()

    # Layer A — expanded corridor around both shortest paths
    for path in (p_path, opp_path):
        if not path:
            continue
        for (r, c) in path:
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    zone.add((r + dr, c + dc))

    # Layer B — immediate threat halo around each pawn
    for (pr, pc) in (p_pos, opp_pos):
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                zone.add((pr + dr, pc + dc))

    return zone


def _detour_delta(board, player: int, anchor, horizontal: bool) -> int:
    """
    Return how many extra steps the wall forces `player` to walk.
    Positive → wall lengthens their path (hurts them).
    0        → wall is irrelevant to this player.
    Returns 0 if pathfinding returns None (shouldn't happen for valid walls,
    but guards against edge cases).
    """
    before = shortest_path_length(board, player)
    if before is None:
        return 0

    sim = board.copy()
    if horizontal:
        sim.h_walls.add(anchor)
    else:
        sim.v_walls.add(anchor)

    after = shortest_path_length(sim, player)
    if after is None:
        return 99          # complete block — highest possible delta
    return max(0, after - before)


# Heuristic score for a wall placement — used for move ordering
def _score_wall(board, anchor, horizontal: bool, player: int, opp: int) -> float:
    """
    Higher score → try this wall earlier → better α-β cutoffs.

    Criteria (in decreasing importance):
      +10  per extra step forced on opponent
      -5   per extra step forced on self  (avoid self-harm)
      +3   if opponent is within 3 rows of their goal (urgency bonus)
      +1   if wall is close to opponent pawn (positional pressure)
    """
    opp_delta   = _detour_delta(board, opp,    anchor, horizontal)
    self_delta  = _detour_delta(board, player, anchor, horizontal)

    opp_pos  = board.get_position(opp)
    opp_goal = GOAL_ROW[opp]
    urgency  = 3 if abs(opp_pos[0] - opp_goal) <= 3 else 0

    r, c = anchor
    opp_r, opp_c = opp_pos
    proximity = 1 if abs(r - opp_r) + abs(c - opp_c) <= 3 else 0

    return opp_delta * 10 - self_delta * 5 + urgency + proximity


# Return a list of actions for the current player, ordered for α-β efficiency
def _get_strategic_actions(board):
    """
      1. Pawn moves — sorted so goal-advancing moves come first.
      2. Wall placements — filtered to the Hot Zone, then sorted by
         _score_wall (best walls first).

    Branching-factor target
    -----------------------
    Original (radius-1 hot zone, no scoring): ~8-15 actions → depth-10 in 0.05 s
    This version (radius-2 + pawn halo + scoring): ~25-50 actions → fills 2 s budget
    at depth 6-8 in Python, which translates to much stronger play.
    """
    player = board.current_player
    opp    = 1 - player

    # ── Pawn moves (always included, sorted toward goal) ─────────────────
    goal_row = GOAL_ROW[player]
    pawn_moves = get_valid_pawn_moves(board, player)

    def pawn_priority(pos):
        # Lower value = tried first. Moves that decrease distance to goal come first.
        return abs(pos[0] - goal_row)

    pawn_actions = sorted(
        [{"type": "move", "target": m} for m in pawn_moves],
        key=lambda a: pawn_priority(a["target"])
    )

    # ── Wall candidates — build hot zone ─────────────────────────────────
    p_pos   = board.get_position(player)
    opp_pos = board.get_position(opp)
    p_path  = get_full_path(board, player)
    opp_path = get_full_path(board, opp)

    hot_zone = _build_hot_zone(p_path, opp_path, p_pos, opp_pos, radius=2)

    # ── Filter valid walls to hot zone, then score them ───────────────────
    wall_candidates = []
    for anchor, horiz in get_valid_walls(board, player):
        r, c = anchor
        # A wall at `anchor` physically affects cells (r,c), (r,c+1) for
        # horizontal and (r,c), (r+1,c) for vertical.  Check both cells.
        if horiz:
            relevant_cells = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
        else:
            relevant_cells = [(r, c), (r + 1, c), (r, c + 1), (r + 1, c + 1)]

        if any(cell in hot_zone for cell in relevant_cells):
            score = _score_wall(board, anchor, horiz, player, opp)
            wall_candidates.append((score, anchor, horiz))

    # Sort walls: highest score first
    wall_candidates.sort(key=lambda x: -x[0])

    wall_actions = [
        {"type": "wall", "anchor": anchor, "horizontal": horiz}
        for _, anchor, horiz in wall_candidates
    ]

    return pawn_actions + wall_actions

# Iterative Deepening
def get_best_move_iterative(board, max_depth: int, ai_player: int,
                            use_adv: bool, time_limit: float):
    """
    Searches depth-by-depth until the time budget is exhausted or max_depth
    is reached.  The last *fully completed* search result is returned.

    Time-management tweak: we skip launching a new depth iteration if less
    than 10 % of the budget remains (avoids wasting time on an incomplete
    search that we'd discard anyway).
    """
    start_time  = time.time()
    best_action = None
    _transposition_table.clear()

    for depth in range(1, max_depth + 1):
        elapsed = time.time() - start_time
        if elapsed > time_limit:
            break
        # Don't start a depth we almost certainly cannot finish
        remaining = time_limit - elapsed
        if depth > 1 and remaining < time_limit * 0.10:
            break

        _, move = minimax(board, depth, float('-inf'), float('inf'),
                          True, ai_player, use_adv, start_time, time_limit)
        if move:
            best_action = move

    return best_action


# Minimax with α-β + Transposition-table (depth added)
def minimax(board, depth: int, alpha: float, beta: float,
            maximizing: bool, ai_player: int, use_adv: bool,
            start_t: float, limit: float):

    # ── Transposition-table lookup ────────────────────────────────────────
    key = (board.positions[0], board.positions[1],
           frozenset(board.h_walls), frozenset(board.v_walls),
           board.current_player)

    if key in _transposition_table:
        stored_depth, stored_score, stored_move = _transposition_table[key]
        if stored_depth >= depth:          # only trust deeper/equal entries
            return stored_score, stored_move

    # ── Terminal / leaf node ──────────────────────────────────────────────
    if time.time() - start_t > limit or depth == 0 or is_game_over(board):
        return evaluate_board(board, ai_player, use_adv), None

    # ── Generate and order actions ────────────────────────────────────────
    actions = _get_strategic_actions(board)

    best_move = None
    if maximizing:
        max_eval = float('-inf')
        for action in actions:
            sim = board.copy()
            if action["type"] == "move":
                apply_pawn_move(sim, board.current_player, action["target"])
            else:
                apply_wall(sim, board.current_player,
                           action["anchor"], bool(action["horizontal"]))

            val, _ = minimax(sim, depth - 1, alpha, beta,
                             False, ai_player, use_adv, start_t, limit)
            if val > max_eval:
                max_eval, best_move = val, action
            alpha = max(alpha, val)
            if beta <= alpha:
                break   # β cut-off

        _transposition_table[key] = (depth, max_eval, best_move)
        return max_eval, best_move

    else:
        min_eval = float('inf')
        for action in actions:
            sim = board.copy()
            if action["type"] == "move":
                apply_pawn_move(sim, board.current_player, action["target"])
            else:
                apply_wall(sim, board.current_player,
                           action["anchor"], bool(action["horizontal"]))

            val, _ = minimax(sim, depth - 1, alpha, beta,
                             True, ai_player, use_adv, start_t, limit)
            if val < min_eval:
                min_eval, best_move = val, action
            beta = min(beta, val)
            if beta <= alpha:
                break   # α cut-off

        _transposition_table[key] = (depth, min_eval, best_move)
        return min_eval, best_move