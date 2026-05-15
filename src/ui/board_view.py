# src/ui/board_view.py
import pygame
from src.engine.board import BOARD_SIZE, P1, P2

# Global Constants
CELL_SIZE = 60
WALL_WIDTH = 12
BOARD_MARGIN = 50

class BoardView:
    def __init__(self):
        # ── Dimensions (Required by GameScene) ──
        self.cell_size = CELL_SIZE
        self.wall_width = WALL_WIDTH
        self.margin = BOARD_MARGIN

        # ── Colors ──
        self.cell_color = (200, 200, 200)
        self.p1_color = (0, 0, 255)
        self.p2_color = (255, 0, 0)
        self.wall_color = (239, 159, 39)
        self.highlight_color = (150, 255, 150)

    def cell_center(self, pos: tuple[int, int]) -> tuple[int, int]:
        """
        Calculates the (x, y) pixel center of a board cell at (row, col).
        Required for drawing animated auras and ghost pawns.
        """
        r, c = pos
        x = self.margin + c * (self.cell_size + self.wall_width) + self.cell_size // 2
        y = self.margin + r * (self.cell_size + self.wall_width) + self.cell_size // 2
        return (x, y)

    def draw(self, screen, board, valid_moves=[]):
        # 1. Draw Grid and Highlight Valid Moves
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = self.highlight_color if (r, c) in valid_moves else self.cell_color
                rect = pygame.Rect(
                    self.margin + c * (self.cell_size + self.wall_width),
                    self.margin + r * (self.cell_size + self.wall_width),
                    self.cell_size, self.cell_size
                )
                pygame.draw.rect(screen, color, rect)

        # 2. Draw Horizontal Walls
        for r, c in board.h_walls:
            rect = pygame.Rect(
                self.margin + c * (self.cell_size + self.wall_width),
                self.margin + (r + 1) * (self.cell_size + self.wall_width) - self.wall_width,
                self.cell_size * 2 + self.wall_width,
                self.wall_width
            )
            pygame.draw.rect(screen, self.wall_color, rect)

        # 3. Draw Vertical Walls
        for r, c in board.v_walls:
            rect = pygame.Rect(
                self.margin + (c + 1) * (self.cell_size + self.wall_width) - self.wall_width,
                self.margin + r * (self.cell_size + self.wall_width),
                self.wall_width,
                self.cell_size * 2 + self.wall_width
            )
            pygame.draw.rect(screen, self.wall_color, rect)

        # 4. Draw Pawns
        for player, color in [(P1, self.p1_color), (P2, self.p2_color)]:
            r, c = board.get_position(player)
            center = self.cell_center((r, c))
            pygame.draw.circle(screen, color, center, self.cell_size // 3)

    def identify_click(self, mouse_pos):
        """
        Determines if a click was on a cell or in a wall gutter.
        Returns: (type, data) where type is 'cell' or 'wall'
        """
        x, y = mouse_pos

        c = (x - self.margin) // (self.cell_size + self.wall_width)
        r = (y - self.margin) // (self.cell_size + self.wall_width)

        rel_x = (x - self.margin) % (self.cell_size + self.wall_width)
        rel_y = (y - self.margin) % (self.cell_size + self.wall_width)

        if rel_x > self.cell_size:
            return "wall", {"anchor": (r, c), "horizontal": False}
        if rel_y > self.cell_size:
            return "wall", {"anchor": (r, c), "horizontal": True}

        return "cell", (r, c)