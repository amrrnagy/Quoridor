# ai/evaluation.py
from ..engine.board import Board, P1, P2
from ..engine.pathfinding import shortest_path_length

# ── OPTIMIZATION 1: Win/Loss constants ───────────────────────────────────────
# Using concrete large numbers instead of float('inf') is safer for arithmetic
# and prevents accidental NaN or overflow when scores are combined.
WIN_SCORE  =  10_000.0
LOSS_SCORE = -10_000.0

WALL_WEIGHT = 0.5   # Easy to tune in one place


def evaluate_board(board: Board, ai_player: int, use_advanced_heuristic: bool) -> float:
    """
    Calculates the score of the board. Positive means AI is winning.
    """
    opponent = P2 if ai_player == P1 else P1

    # If a player has already won, return immediately without computing BFS.
    # This is the cheapest possible evaluation — O(1) vs O(n²) for BFS.
    if board.winner == ai_player:
        return float('inf')
    elif board.winner is not None:  # Someone else won
        return float('-inf')

    # BFS distances (only called on non-terminal boards)
    ai_distance  = shortest_path_length(board, ai_player)
    opp_distance = shortest_path_length(board, opponent)

    # ── OPTIMIZATION 3: Unreachable path guard ────────────────────────────────
    # shortest_path_length returns -1 (or None) when no path exists.
    # Treat that as a guaranteed win/loss rather than crashing on arithmetic.
    if ai_distance  <= 0: return WIN_SCORE
    if opp_distance <= 0: return LOSS_SCORE

    score = opp_distance - ai_distance

    if use_advanced_heuristic:
        ai_walls  = board.get_walls_left(ai_player)
        opp_walls = board.get_walls_left(opponent)
        score += (ai_walls - opp_walls) * WALL_WEIGHT

    return score