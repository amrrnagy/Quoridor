# ai/minimax.py

# from engine.board import Board
# from engine.rules import get_all_legal_actions, apply_pawn_move, apply_wall, is_game_over
# from ai.evaluation import evaluate_board
import copy


def minimax(board: Board, depth: int, alpha: float, beta: float, maximizing_player: bool, ai_player: int) -> tuple:
    """
    Returns a tuple containing: (best_score, best_action_dict)

    Logic Steps:
    1. Base Case: If depth == 0 or is_game_over(board), return the score from
       evaluate_board() and None for the action.
    2. Get all possible actions using get_all_legal_actions(board).
    3. If maximizing_player (It is the AI's turn):
        a. Set max_eval to -infinity.
        b. Loop through every action:
            - Make a deep copy of the board.
            - Apply the action to the copied board.
            - Recursively call minimax() with depth - 1 and maximizing_player = False.
            - Update max_eval, alpha, and the best_action.
            - If beta <= alpha, break (Pruning!).
        c. Return (max_eval, best_action).
    4. If not maximizing_player (It is the Opponent's turn):
        - Do the exact same thing as above, but look for the min_eval,
          update beta, and break if beta <= alpha.
    """

    # TODO: Implement the recursive Alpha-Beta Minimax logic here
    pass