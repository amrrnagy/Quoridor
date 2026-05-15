# src/ui/game_scene.py
from __future__ import annotations
import math
import threading
import time as _time
import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.ui.game_config import GameConfig, GameMode
from src.engine.board import Board, P1, P2
from src.engine.rules import apply_pawn_move, apply_wall, is_game_over, get_winner, get_valid_pawn_moves
from src.ai.agent import AIAgent
from src.ui.board_view import BoardView

# ── colour palette ──
BG_MAIN = (18, 17, 26)
BG_PANEL = (14, 13, 24)
BG_CARD = (30, 27, 46)
BG_CARD_A = (45, 40, 72)
BORDER = (58, 53, 85)
BORDER_A = (127, 119, 221)
TEXT_PRI = (240, 237, 248)
TEXT_SEC = (122, 117, 144)
TEXT_DIM = (90, 86, 112)
RED_PLAYER = (210, 40, 40)
BLUE_AI = (40, 80, 210)
RED_DARK = (163, 45, 45)
RED_LIGHT = (252, 235, 235)

SIDEBAR_W = 244
_BUDGET = {"Easy": 0.5, "Medium": 2.0, "Hard": 4.5}


def _make_aura_surface(radius: int, color: tuple, rings: int = 5) -> pygame.Surface:
    size = radius * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for i in range(rings, 0, -1):
        r = int(radius * i / rings)
        a = int(180 * (1 - i / rings))
        pygame.draw.circle(surf, (*color, a), (cx, cy), r, width=max(1, r // rings))
    return surf


class GameScene(Scene):
    W, H = 900, 750

    def __init__(self, manager: SceneManager, config: GameConfig) -> None:
        super().__init__(manager)
        self.config = config
        pygame.font.init()
        self._font_h2 = pygame.font.SysFont("segoeui", 20)
        self._font_body = pygame.font.SysFont("segoeui", 16)
        self._font_small = pygame.font.SysFont("segoeui", 14)
        self._font_sect = pygame.font.SysFont("segoeui", 12, bold=True)
        self._font_mono = pygame.font.SysFont("consolas", 14)

        self._invalid_msg = ""
        self._invalid_timer = 0.0
        self._anim_t = 0.0

        # UI Buttons (Increased padding and heights)
        bx = self.W - SIDEBAR_W + 16
        bw = SIDEBAR_W - 32
        btn_w = (bw - 8) // 2

        self._btn_undo = pygame.Rect(bx, self.H - 238, btn_w, 42)
        self._btn_redo = pygame.Rect(bx + btn_w + 8, self.H - 238, btn_w, 42)
        self._btn_reset_rect = pygame.Rect(bx, self.H - 180, bw, 48)
        self._btn_menu_rect = pygame.Rect(bx, self.H - 124, bw, 48)
        self._btn_exit_rect = pygame.Rect(bx, self.H - 68, bw, 48)

        self._hover_u, self._hover_r = False, False
        self._hover_res, self._hover_menu, self._hover_exit = False, False, False

        self._aura_blue = _make_aura_surface(28, BLUE_AI)
        self._init_engine()

    def _init_engine(self) -> None:
        self.board = Board()

        try:
            self.board_view = BoardView()
        except TypeError:
            self.board_view = BoardView(pygame.Rect(0, 0, self.W - SIDEBAR_W, self.H))

        self._undo_stack = []
        self._redo_stack = []

        if self.config.mode == GameMode.HUMAN_VS_AI:
            diff_str = self.config.difficulty.name.title()
            self.agent = AIAgent(player_id=P2, difficulty=diff_str)
            self._budget = _BUDGET.get(diff_str, 2.0)
        else:
            self.agent = None
            self._budget = 0.0

        self._ai_thinking = False
        self._ai_result = None
        self._turn_start = _time.monotonic()

    def on_enter(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_u = self._btn_undo.collidepoint(event.pos)
            self._hover_r = self._btn_redo.collidepoint(event.pos)
            self._hover_res = self._btn_reset_rect.collidepoint(event.pos)
            self._hover_menu = self._btn_menu_rect.collidepoint(event.pos)
            self._hover_exit = self._btn_exit_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_reset_rect.collidepoint(event.pos): self._init_engine()
            if self._btn_menu_rect.collidepoint(event.pos):  self._go_to_menu()
            if self._btn_exit_rect.collidepoint(event.pos):  self.manager.quit()

            if not self._ai_thinking:
                if self._btn_undo.collidepoint(event.pos):
                    self._undo_move()
                    return
                if self._btn_redo.collidepoint(event.pos):
                    self._redo_move()
                    return
                self._handle_board_click(event.pos)

    def _go_to_menu(self):
        from src.ui.menu_scene import MenuScene
        self.manager.switch(MenuScene(self.manager))

    def _undo_move(self):
        if self._undo_stack:
            self._redo_stack.append(self.board.copy())
            self.board = self._undo_stack.pop()
            if self.agent and self._undo_stack and self.board.current_player == P2:
                self._redo_stack.append(self.board.copy())
                self.board = self._undo_stack.pop()
            self._turn_start = _time.monotonic()

    def _redo_move(self):
        if self._redo_stack:
            self._undo_stack.append(self.board.copy())
            self.board = self._redo_stack.pop()
            self._turn_start = _time.monotonic()

    def update(self, dt: float) -> None:
        self._anim_t += dt / 1000.0
        if self._invalid_timer > 0: self._invalid_timer = max(0.0, self._invalid_timer - dt)
        if self._ai_thinking and self._ai_result is not None: self._apply_ai_result()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_MAIN)
        pygame.draw.rect(screen, BG_PANEL, pygame.Rect(0, 0, self.W - SIDEBAR_W, self.H))

        valid_moves = [] if self._ai_thinking else get_valid_pawn_moves(self.board, self.board.current_player)

        self._draw_aura_under_ai_pawn(screen)

        try:
            self.board_view.draw(screen, self.board, valid_moves)
        except TypeError:
            self.board_view.draw(screen, self.board, anim_t=self._anim_t, valid_moves=valid_moves,
                                 ai_thinking=self._ai_thinking)

        self._draw_ghost_pawns(screen, valid_moves)

        if self._invalid_timer > 0:
            self._draw_invalid_banner(screen, min(255, int(self._invalid_timer / 400 * 255)))

        self._draw_sidebar(screen)

    def _draw_aura_under_ai_pawn(self, screen: pygame.Surface) -> None:
        if not self._ai_thinking: return
        pawn_pos = self.board_view.cell_center(self.board.get_position(P2))
        pulse = (math.sin(self._anim_t * math.pi / 0.6) + 1) / 2
        alpha = int(60 + 180 * pulse)
        surf = self._aura_blue.copy()
        surf.set_alpha(alpha)
        size = self._aura_blue.get_width()
        screen.blit(surf, (pawn_pos[0] - size // 2, pawn_pos[1] - size // 2), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_ghost_pawns(self, screen, valid_moves):
        if not valid_moves: return
        pulse = (math.sin(self._anim_t * math.pi / 0.4) + 1) / 2
        alpha = int(80 + 100 * pulse)
        base_col = RED_PLAYER if self.board.current_player == P1 else BLUE_AI
        radius = self.board_view.cell_size // 2 - 4

        for pos in valid_moves:
            cx, cy = self.board_view.cell_center(pos)
            ghost = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*base_col, alpha), (radius, radius), radius)
            pygame.draw.circle(ghost, (*BG_PANEL, alpha), (radius, radius), max(2, radius - 4))
            screen.blit(ghost, (cx - radius, cy - radius))

    def _handle_board_click(self, pos: tuple) -> None:
        if self.agent and self.board.current_player == P2: return
        click_type, data = self.board_view.identify_click(pos)

        try:
            board_snapshot = self.board.copy()
            if click_type == "cell":
                apply_pawn_move(self.board, self.board.current_player, data)
            elif click_type == "wall":
                apply_wall(self.board, self.board.current_player, data["anchor"], data["horizontal"])

            self._undo_stack.append(board_snapshot)
            self._redo_stack.clear()
            self._turn_start = _time.monotonic()
            self._check_winner()

            if self.agent and not is_game_over(self.board) and self.board.current_player == P2:
                self._launch_ai_thread()
        except ValueError as e:
            self._flash_invalid(str(e))

    def _launch_ai_thread(self) -> None:
        self._ai_thinking = True
        self._ai_result = None
        self._ai_start_t = _time.monotonic()
        board_copy = self.board.copy()

        def _worker():
            action = self.agent.get_best_move(board_copy)
            self._ai_result = action

        self._ai_thread = threading.Thread(target=_worker, daemon=True)
        self._ai_thread.start()

    def _apply_ai_result(self) -> None:
        action = self._ai_result
        self._ai_thinking = False
        self._ai_result = None

        if action:
            self._undo_stack.append(self.board.copy())
            self._redo_stack.clear()
            if action["type"] == "move":
                apply_pawn_move(self.board, P2, action["target"])
            elif action["type"] == "wall":
                apply_wall(self.board, P2, action["anchor"], action["horizontal"])

        self._turn_start = _time.monotonic()
        self._check_winner()

    def _check_winner(self) -> None:
        if is_game_over(self.board):
            winner_idx = get_winner(self.board)
            name = "Player 1 (Red)" if winner_idx == P1 else "AI (Blue)"
            screenshot = pygame.display.get_surface().copy()
            from src.ui.game_over_scene import GameOverScene
            self.manager.switch(GameOverScene(self.manager, self.config, name, winner_idx, screenshot))

    def _flash_invalid(self, msg: str):
        self._invalid_msg = msg
        self._invalid_timer = 2000

    def _draw_invalid_banner(self, screen, alpha):
        surf = self._font_small.render(f"⚠ {self._invalid_msg}", True, RED_LIGHT)
        pad = pygame.Rect(0, 0, surf.get_width() + 28, surf.get_height() + 16)
        pad.centerx = (self.W - SIDEBAR_W) // 2
        pad.bottom = self.H - 20
        banner = pygame.Surface((pad.w, pad.h), pygame.SRCALPHA)
        banner.fill((*RED_DARK, alpha))
        screen.blit(banner, pad.topleft)
        screen.blit(surf, (pad.x + 14, pad.y + 8))

    def _draw_sidebar(self, screen: pygame.Surface) -> None:
        sx = self.W - SIDEBAR_W
        pygame.draw.rect(screen, BG_MAIN, pygame.Rect(sx, 0, SIDEBAR_W, self.H))
        pygame.draw.line(screen, BORDER, (sx, 0), (sx, self.H))

        x, y = sx + 16, 20
        bw = SIDEBAR_W - 32

        # 1. Turn Indicator Card
        card1 = pygame.Rect(x, y, bw, 96)
        pygame.draw.rect(screen, BG_CARD, card1, border_radius=10)
        screen.blit(self._font_sect.render("CURRENT TURN", True, TEXT_DIM), (x + 16, y + 14))

        current = self.board.current_player
        name = "Player 1 (Red)" if current == P1 else ("AI (Blue)" if self.agent else "Player 2 (Blue)")
        dot_col = RED_PLAYER if current == P1 else BLUE_AI

        # Simplified Player Icon
        self._draw_icon_player(screen, (x + 28, y + 62), dot_col, scale=1.2)
        screen.blit(self._font_h2.render(name, True, TEXT_PRI), (x + 50, y + 49))

        timer_str = f"{_time.monotonic() - self._turn_start:4.1f}s"
        ts = self._font_mono.render(timer_str, True, TEXT_DIM)
        screen.blit(ts, (card1.right - ts.get_width() - 16, y + 14))
        y += 112

        # 2. AI Progress Bar
        if self._ai_thinking:
            bar_card = pygame.Rect(x, y, bw, 64)
            pygame.draw.rect(screen, BG_CARD, bar_card, border_radius=10)
            screen.blit(self._font_sect.render("AI THINKING…", True, TEXT_DIM), (x + 16, y + 14))

            prog = min(1.0, (_time.monotonic() - self._ai_start_t) / max(0.1, self._budget))
            pygame.draw.rect(screen, BORDER, pygame.Rect(x + 16, y + 40, bw - 32, 6), border_radius=3)
            pygame.draw.rect(screen, BLUE_AI, pygame.Rect(x + 16, y + 40, max(4, int((bw - 32) * prog)), 6),
                             border_radius=3)
            y += 80

        # 3. Walls Remaining Card
        card2 = pygame.Rect(x, y, bw, 120)
        pygame.draw.rect(screen, BG_CARD, card2, border_radius=10)
        screen.blit(self._font_sect.render("WALLS REMAINING", True, TEXT_DIM), (x + 16, y + 14))

        walls = [self.board.get_walls_left(P1), self.board.get_walls_left(P2)]
        for i, (cnt, col, label) in enumerate(zip(walls, [RED_PLAYER, BLUE_AI], ["Red", "Blue"])):
            py = y + 44 + i * 42
            self._draw_icon_player(screen, (x + 24, py), col, scale=0.8)
            for w in range(10):
                wr = pygame.Rect(x + 44 + w * 14, py - 6, 10, 10)
                pygame.draw.rect(screen, col if w < cnt else BORDER, wr, border_radius=3)
        y += 136

        # 4. Action Buttons
        undo_ok = bool(self._undo_stack) and not self._ai_thinking
        redo_ok = bool(self._redo_stack) and not self._ai_thinking

        self._draw_btn(screen, self._btn_undo, "⮪ Undo", self._hover_u, undo_ok)
        self._draw_btn(screen, self._btn_redo, "⮫ Redo", self._hover_r, redo_ok)

        self._draw_action_btn(screen, self._btn_reset_rect, "⟳", "Reset Game", self._hover_res)
        self._draw_action_btn(screen, self._btn_menu_rect, "⌂", "Main Menu", self._hover_menu)
        self._draw_action_btn(screen, self._btn_exit_rect, "⮞", "Exit Game", self._hover_exit)

    def _draw_icon_player(self, screen, pos, color, scale=1.0):
        """Draws a clean, simple circular pawn with a specular highlight."""
        cx, cy = pos
        r = int(9 * scale)
        # Base pawn
        pygame.draw.circle(screen, color, (cx, cy), r)
        # Specular dot (shiny reflection)
        pygame.draw.circle(screen, (255, 255, 255), (cx - int(r * 0.3), cy - int(r * 0.3)), max(1, int(r * 0.3)))

    def _draw_btn(self, screen, rect, text, hover, enabled):
        col = BG_CARD_A if hover and enabled else BG_CARD
        bc = BORDER_A if hover and enabled else BORDER
        pygame.draw.rect(screen, col, rect, border_radius=8)
        pygame.draw.rect(screen, bc, rect, width=1, border_radius=8)
        lbl = self._font_body.render(text, True, TEXT_PRI if enabled else TEXT_DIM)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_action_btn(self, screen, rect, icon, text, hover):
        """Draws wide action buttons with dynamically centered text and icons."""
        bg = BG_CARD_A if hover else BG_CARD
        brd = BORDER_A if hover else BORDER
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, brd, rect, width=1, border_radius=10)

        icon_surf = self._font_h2.render(icon, True, TEXT_PRI)
        text_surf = self._font_body.render(text, True, TEXT_SEC if not hover else TEXT_PRI)

        # Calculate total width to perfectly center the group
        total_w = icon_surf.get_width() + 12 + text_surf.get_width()
        start_x = rect.x + (rect.width - total_w) // 2

        screen.blit(icon_surf, (start_x, rect.centery - icon_surf.get_height() // 2 - 2))
        screen.blit(text_surf, (start_x + icon_surf.get_width() + 12, rect.centery - text_surf.get_height() // 2))