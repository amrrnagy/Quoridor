# ai/minimax.py
import copy
from ..engine.board import Board
from ..engine.rules import get_all_legal_actions, apply_pawn_move, apply_wall, is_game_over
from ..ai.evaluation import evaluate_board


def get_best_move_minimax(board: Board, depth: int, ai_player: int, use_advanced_heuristic: bool) -> tuple:
    """
    Wrapper function to start the recursive minimax process with initial alpha/beta values.
    """
    return minimax(board, depth, float('-inf'), float('inf'), True, ai_player, use_advanced_heuristic)


def minimax(board: Board, depth: int, alpha: float, beta: float, maximizing_player: bool, ai_player: int,
            use_advanced_heuristic: bool) -> tuple:
    """
    The core recursive algorithm.
    """
    # BASE CASE: Stop searching if we hit depth 0 or the game is over
    if depth == 0 or is_game_over(board):
        # Call the evaluation file, passing the heuristic flag
        score = evaluate_board(board, ai_player, use_advanced_heuristic)
        return score, None

    actions = get_all_legal_actions(board)
    best_action = None

    if maximizing_player:
        max_eval = float('-inf')
        for action in actions:
            simulated_board = board.copy()

            # Apply the action to the simulated board
            if action["type"] == "move":
                apply_pawn_move(simulated_board, board.current_player, action["target"])
            elif action["type"] == "wall":
                apply_wall(simulated_board, board.current_player, action["anchor"], action["horizontal"])

            # Recurse one level deeper
            eval_score, _ = minimax(simulated_board, depth - 1, alpha, beta, False, ai_player, use_advanced_heuristic)

            if eval_score > max_eval:
                max_eval = eval_score
                best_action = action

            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Alpha-Beta Pruning

        return max_eval, best_action

    else:
        # Opponent's turn (Minimizing player)
        min_eval = float('inf')
        for action in actions:
            simulated_board = board.copy()

            if action["type"] == "move":
                apply_pawn_move(simulated_board, board.current_player, action["target"])
            elif action["type"] == "wall":
                apply_wall(simulated_board, board.current_player, action["anchor"], action["horizontal"])

            eval_score, _ = minimax(simulated_board, depth - 1, alpha, beta, True, ai_player, use_advanced_heuristic)

            if eval_score < min_eval:
                min_eval = eval_score
                best_action = action

            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha-Beta Pruning

        return min_eval, best_action