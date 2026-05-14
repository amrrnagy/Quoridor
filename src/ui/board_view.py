# src/ui/board_view.py
import pygame
from src.engine.board import BOARD_SIZE, P1, P2

CELL_SIZE = 60
WALL_WIDTH = 12
BOARD_MARGIN = 50


class BoardView:
    def __init__(self):
        self.cell_color = (200, 200, 200)
        self.p1_color = (0, 0, 255)
        self.p2_color = (255, 0, 0)
        self.wall_color = (40, 40, 40)  # Darker wall color
        self.highlight_color = (150, 255, 150)  # Light Green for valid moves

    def draw(self, screen, board, valid_moves=[]):
        # 1. Draw Grid and Highlight Valid Moves
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = self.highlight_color if (r, c) in valid_moves else self.cell_color
                rect = pygame.Rect(
                    BOARD_MARGIN + c * (CELL_SIZE + WALL_WIDTH),
                    BOARD_MARGIN + r * (CELL_SIZE + WALL_WIDTH),
                    CELL_SIZE, CELL_SIZE
                )
                pygame.draw.rect(screen, color, rect)

        # 2. Draw Horizontal Walls
        for r, c in board.h_walls:
            rect = pygame.Rect(
                BOARD_MARGIN + c * (CELL_SIZE + WALL_WIDTH),
                BOARD_MARGIN + (r + 1) * (CELL_SIZE + WALL_WIDTH) - WALL_WIDTH,
                CELL_SIZE * 2 + WALL_WIDTH,
                WALL_WIDTH
            )
            pygame.draw.rect(screen, self.wall_color, rect)

        # 3. Draw Vertical Walls
        for r, c in board.v_walls:
            rect = pygame.Rect(
                BOARD_MARGIN + (c + 1) * (CELL_SIZE + WALL_WIDTH) - WALL_WIDTH,
                BOARD_MARGIN + r * (CELL_SIZE + WALL_WIDTH),
                WALL_WIDTH,
                CELL_SIZE * 2 + WALL_WIDTH
            )
            pygame.draw.rect(screen, self.wall_color, rect)

        # 4. Draw Pawns
        for player, color in [(P1, self.p1_color), (P2, self.p2_color)]:
            r, c = board.get_position(player)
            center = (
                BOARD_MARGIN + c * (CELL_SIZE + WALL_WIDTH) + CELL_SIZE // 2,
                BOARD_MARGIN + r * (CELL_SIZE + WALL_WIDTH) + CELL_SIZE // 2
            )
            pygame.draw.circle(screen, color, center, CELL_SIZE // 3)

    def identify_click(self, mouse_pos):
        """
        Determines if a click was on a cell or in a wall gutter.
        Returns: (type, data) where type is 'cell' or 'wall'
        """
        x, y = mouse_pos

        # Calculate approximate grid coordinates
        c = (x - BOARD_MARGIN) // (CELL_SIZE + WALL_WIDTH)
        r = (y - BOARD_MARGIN) // (CELL_SIZE + WALL_WIDTH)

        # Relative position within the cell+gutter block
        rel_x = (x - BOARD_MARGIN) % (CELL_SIZE + WALL_WIDTH)
        rel_y = (y - BOARD_MARGIN) % (CELL_SIZE + WALL_WIDTH)

        # Click is in the vertical gutter (between columns)
        if rel_x > CELL_SIZE:
            return "wall", {"anchor": (r, c), "horizontal": False}

        # Click is in the horizontal gutter (between rows)
        if rel_y > CELL_SIZE:
            return "wall", {"anchor": (r, c), "horizontal": True}

        # Click is inside a cell
        return "cell", (r, c)