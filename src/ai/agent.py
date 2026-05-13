# ai/agent.py

# from engine.board import Board
# from ai.minimax import minimax


class AIAgent:
    def __init__(self, player_id: int, difficulty: str = "Medium"):
        """
        Initialize the AI with its player ID (P1 or P2) and difficulty level.
        """
        self.player_id = player_id
        self.difficulty = difficulty

        # Determine the search depth based on difficulty
        if self.difficulty == "Easy":
            self.depth = 1  # Very short-sighted
        elif self.difficulty == "Medium":
            self.depth = 3  # Looks ahead a little bit
        elif self.difficulty == "Hard":
            self.depth = 4  # Looks deep, might take a couple of seconds to compute
        else:
            self.depth = 3

    def get_best_move(self, board: Board) -> dict:
        """
        Calls the minimax algorithm to figure out the best move.
        Returns the action dictionary (e.g., {"type": "move", "target": (r, c)}).
        """

        # Initial alpha and beta values for pruning
        alpha = float('-inf')
        beta = float('inf')

        # Call the minimax function
        best_score, best_action = minimax(
            board=board,
            depth=self.depth,
            alpha=alpha,
            beta=beta,
            maximizing_player=True,
            ai_player=self.player_id
        )

        return best_action