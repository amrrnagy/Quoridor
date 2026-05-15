# src/ai/agent.py
from .minimax import get_best_move_iterative

class AIAgent:
    # Default is the Easy level
    def __init__(self, player_id: int, difficulty: str = "Easy"):
        self.player_id = player_id
        # Implements multiple AI difficulty levels (e.g., Easy, Medium, Hard)
        configs = {
            "Easy":   {"depth": 1, "adv": False, "time": 0.5},
            "Medium": {"depth": 6, "adv": False, "time": 2.0},
            "Hard":   {"depth": 10, "adv": True,  "time": 4.5}
        }
        self.cfg = configs.get(difficulty, configs["Easy"])

        # Memory of recent positions
        self.position_history = []

    # An API that applies the iterative deepening with a time limit
    def get_best_move(self, board) -> dict:
        # Record our current position before calculating the next move
        self.position_history.append(board.get_position(self.player_id))

        # Keep only the last 6 moves to prevent memory leaks and allow legitimate late-game backtracking
        if len(self.position_history) > 6:
            self.position_history.pop(0)

        return get_best_move_iterative(
            board,
            self.cfg["depth"],
            self.player_id,
            self.cfg["adv"],
            self.cfg["time"],
            self.position_history
        )