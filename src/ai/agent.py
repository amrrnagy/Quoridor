# ai/agent.py
from ..engine.board import Board
from ..ai.minimax import get_best_move_minimax

# ── OPTIMIZATION 1: Config table replaces if/elif chain ──────────────────────
# Adding a new difficulty = adding one line to the dict, not editing if/elif.
# Keeps __init__ from growing as the game expands.
_DIFFICULTY_CONFIG = {
    "Easy":   {"depth": 1, "use_advanced_heuristic": False},
    "Medium": {"depth": 3, "use_advanced_heuristic": False},
    "Hard":   {"depth": 4, "use_advanced_heuristic": True},
}
_DEFAULT_CONFIG = {"depth": 3, "use_advanced_heuristic": False}


class AIAgent:
    def __init__(self, player_id: int, difficulty: str = "Easy"):
        self.player_id  = player_id
        self.difficulty = difficulty

        # ── OPTIMIZATION 2: Single dict.get() lookup ──────────────────────────
        config = _DIFFICULTY_CONFIG.get(difficulty, _DEFAULT_CONFIG)
        self.depth                 = config["depth"]
        self.use_advanced_heuristic = config["use_advanced_heuristic"]

    def get_best_move(self, board: Board) -> dict:
        """Kicks off the minimax search with difficulty-specific parameters."""
        _, best_action = get_best_move_minimax(
            board=board,
            depth=self.depth,
            ai_player=self.player_id,
            use_advanced_heuristic=self.use_advanced_heuristic,
        )
        return best_action