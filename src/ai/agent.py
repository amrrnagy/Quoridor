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

    # An API that applies the iterative deepening with a time limit
    def get_best_move(self, board) -> dict:
        return get_best_move_iterative(
            board,
            self.cfg["depth"],
            self.player_id,
            self.cfg["adv"],
            self.cfg["time"]
        )