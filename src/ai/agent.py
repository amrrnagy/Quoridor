# ai/agent.py
from engine.board import Board
from ai.minimax import get_best_move_minimax


class AIAgent:
    def __init__(self, player_id: int, difficulty: str = "Medium"):
        self.player_id = player_id
        self.difficulty = difficulty

        # Configure settings based on difficulty
        if self.difficulty == "Easy":
            self.depth = 1
            self.use_advanced_heuristic = False
        elif self.difficulty == "Medium":
            self.depth = 3
            self.use_advanced_heuristic = False
        elif self.difficulty == "Hard":
            self.depth = 4  # Increase if performance allows
            self.use_advanced_heuristic = True
        else:
            self.depth = 3
            self.use_advanced_heuristic = False

    def get_best_move(self, board: Board) -> dict:
        """
        Kicks off the Minimax search with the specific difficulty parameters.
        """
        # We start Minimax and pass the heuristic flag so the engine knows how to score
        best_score, best_action = get_best_move_minimax(
            board=board,
            depth=self.depth,
            ai_player=self.player_id,
            use_advanced_heuristic=self.use_advanced_heuristic
        )
        return best_action