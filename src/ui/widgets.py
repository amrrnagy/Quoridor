# src/ui/widgets.py
import pygame


def draw_sidebar(screen, board):
    font = pygame.font.SysFont("Verdana", 22, bold=True)
    small_font = pygame.font.SysFont("Verdana", 18)

    # Position sidebar at x=700
    sidebar_x = 720

    # 1. Title
    title = font.render("QUORIDOR AI", True, (50, 50, 50))
    screen.blit(title, (sidebar_x, 50))

    # 2. Turn Indicator
    color = (0, 0, 255) if board.current_player == 0 else (255, 0, 0)
    turn_label = small_font.render(f"Current Turn:", True, (0, 0, 0))
    turn_val = font.render(f"PLAYER {board.current_player + 1}", True, color)
    screen.blit(turn_label, (sidebar_x, 120))
    screen.blit(turn_val, (sidebar_x, 150))

    # 3. Wall Counts
    p1_walls = small_font.render(f"P1 (Blue) Walls: {board.get_walls_left(0)}", True, (0, 0, 255))
    p2_walls = small_font.render(f"P2 (Red) Walls: {board.get_walls_left(1)}", True, (255, 0, 0))
    screen.blit(p1_walls, (sidebar_x, 250))
    screen.blit(p2_walls, (sidebar_x, 280))

    # 4. Instructions
    hint = small_font.render("Click cell to move", True, (100, 100, 100))
    hint2 = small_font.render("Click gutter to block", True, (100, 100, 100))
    screen.blit(hint, (sidebar_x, 500))
    screen.blit(hint2, (sidebar_x, 530))