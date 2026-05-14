# ai/minimax.py
from functools import lru_cache
from ..engine.board import Board
from ..engine.rules import get_all_legal_actions, apply_pawn_move, apply_wall, is_game_over
from ..ai.evaluation import evaluate_board

# ── OPTIMIZATION 1: Transposition Table ──────────────────────────────────────
# Quoridor often reaches the same board state via different move orders.
# Instead of re-evaluating a state we've already seen, we cache it here.
# Key   → a hashable snapshot of the board (positions + walls + current player)
# Value → (score, best_action) already computed at that state
_transposition_table: dict = {}


def get_best_move_minimax(board: Board, depth: int, ai_player: int, use_advanced_heuristic: bool) -> tuple:
    """
    Wrapper function to start the recursive minimax process.
    Clears the transposition table at the start of each new top-level search
    so stale entries from the previous turn don't pollute results.
    """
    # ── OPTIMIZATION 2: Clear stale cache each new turn ──────────────────────
    _transposition_table.clear()
    return minimax(board, depth, float('-inf'), float('inf'), True, ai_player, use_advanced_heuristic)


# Inside src/ai/minimax.py

def _board_key(board):
    """
    Creates a unique, hashable representation of the current board state.
    Used for memoization in the transposition table.
    """
    return (
        # 1. Pawn positions (converted to a sorted tuple of items)
        tuple(sorted(board.positions.items())),

        # 2. Horizontal walls (converted to a frozenset for hashing)
        frozenset(board.h_walls),

        # 3. Vertical walls (converted to a frozenset for hashing)
        frozenset(board.v_walls),

        # 4. The current player's turn
        board.current_player
    )

def _sort_actions(actions: list) -> list:
    """
    ── OPTIMIZATION 3: Move Ordering ────────────────────────────────────────
    Alpha-beta pruning is most effective when the best moves are searched first.
    Simple heuristic: explore pawn moves before wall placements.
    Pawn moves are cheap, often best, and cause pruning early — reducing the
    number of wall placements (expensive) that need to be evaluated at all.
    """
    return sorted(actions, key=lambda a: 0 if a["type"] == "move" else 1)


def minimax(board: Board, depth: int, alpha: float, beta: float,
            maximizing_player: bool, ai_player: int, use_advanced_heuristic: bool) -> tuple:
    """
    Core recursive minimax with alpha-beta pruning + transposition table.
    """
    # ── OPTIMIZATION 4: Transposition Table Lookup ────────────────────────────
    # Before doing any work, check if this exact board state was already solved.
    key = _board_key(board)
    if key in _transposition_table:
        return _transposition_table[key]

    # BASE CASE
    if depth == 0 or is_game_over(board):
        score = evaluate_board(board, ai_player, use_advanced_heuristic)
        result = (score, None)
        _transposition_table[key] = result      # cache leaf nodes too
        return result

    # Move ordering: pawn moves first for better pruning
    actions = _sort_actions(get_all_legal_actions(board))
    best_action = None

    if maximizing_player:
        max_eval = float('-inf')
        for action in actions:
            simulated_board = board.copy()
            _apply_action(simulated_board, board.current_player, action)

            eval_score, _ = minimax(simulated_board, depth - 1, alpha, beta,
                                    False, ai_player, use_advanced_heuristic)

            if eval_score > max_eval:
                max_eval = eval_score
                best_action = action

            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Pruned

        result = (max_eval, best_action)

    else:
        min_eval = float('inf')
        for action in actions:
            simulated_board = board.copy()
            _apply_action(simulated_board, board.current_player, action)

            eval_score, _ = minimax(simulated_board, depth - 1, alpha, beta,
                                    True, ai_player, use_advanced_heuristic)

            if eval_score < min_eval:
                min_eval = eval_score
                best_action = action

            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Pruned

        result = (min_eval, best_action)

    # ── Cache the result before returning ────────────────────────────────────
    _transposition_table[key] = result
    return result


def _apply_action(board: Board, player: int, action: dict) -> None:
    """
    ── OPTIMIZATION 5: DRY helper ───────────────────────────────────────────
    Removes the duplicated if/elif block that existed in both the maximizer
    and minimizer branches — cuts 8 lines of repeated logic down to 1 call.
    """
    if action["type"] == "move":
        apply_pawn_move(board, player, action["target"])
    elif action["type"] == "wall":
        apply_wall(board, player, action["anchor"], action["horizontal"])