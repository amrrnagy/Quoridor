# src/ui/main_window.py
import pygame
import time
from src.engine.board import Board, P1, P2
from src.engine.rules import apply_pawn_move, apply_wall, is_game_over, get_valid_pawn_moves
from src.ai.agent import AIAgent
from .board_view import BoardView
from .widgets import draw_sidebar


class QuoridorGUI:
    def __init__(self):
        pygame.init()
        # Set window size to accommodate board + sidebar
        self.screen = pygame.display.set_mode((900, 750))
        pygame.display.set_caption("Quoridor AI")

        self.board = Board()
        self.view = BoardView()
        self.ai = AIAgent(player_id=P2, difficulty="Easy")
        self.running = True

    def run(self):
        while self.running:
            self.handle_events()
            if not is_game_over(self.board) and self.board.current_player == P2:
                self.process_ai_turn()
            self.render()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.MOUSEBUTTONDOWN and self.board.current_player == P1:
                click_type, data = self.view.identify_click(event.pos)

                try:
                    if click_type == "cell":
                        apply_pawn_move(self.board, P1, data)
                    elif click_type == "wall":
                        apply_wall(self.board, P1, data["anchor"], data["horizontal"])
                except ValueError as e:
                    print(f"Illegal Move: {e}")

    def process_ai_turn(self):
        # Brief pause so the human can see what happened
        time.sleep(0.25)
        action = self.ai.get_best_move(self.board)
        if action:
            if action["type"] == "move":
                apply_pawn_move(self.board, P2, action["target"])
            elif action["type"] == "wall":
                apply_wall(self.board, P2, action["anchor"], action["horizontal"])

    def render(self):
        self.screen.fill((255, 255, 255))

        # Get valid moves to highlight them
        valid_moves = get_valid_pawn_moves(self.board, self.board.current_player)
        self.view.draw(self.screen, self.board, valid_moves)

        # Draw the status info (walls left, current turn)
        draw_sidebar(self.screen, self.board)

        pygame.display.flip()