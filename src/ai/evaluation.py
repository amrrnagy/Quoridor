# ai/evaluation.py
from engine.board import Board, P1, P2
from engine.pathfinding import shortest_path_length


def evaluate_board(board: Board, ai_player: int, use_advanced_heuristic: bool) -> float:
    """
    Calculates the score of the board. Positive means AI is winning.
    """
    opponent = P2 if ai_player == P1 else P1

    # 1. Base metric: Distance to goal (Needed for all difficulties)
    ai_distance = shortest_path_length(board, ai_player)
    opp_distance = shortest_path_length(board, opponent)

    # Base score: If opponent is 8 steps away and AI is 3, score is +5
    score = opp_distance - ai_distance

    # 2. Advanced metric: Only used for "Hard" mode
    if use_advanced_heuristic:
        ai_walls = board.get_walls_left(ai_player)
        opp_walls = board.get_walls_left(opponent)

        # Example formula: Give a small point bonus for hoarding walls
        # Adjust this multiplier (0.5) through testing!
        wall_advantage = (ai_walls - opp_walls) * 0.5
        score += wall_advantage

    return score