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

SIDEBAR_W = 250


def _make_aura_surface(radius: int, color: tuple, rings: int = 5) -> pygame.Surface:
    size = radius * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for i in range(rings, 0, -1):
        r = int(radius * i / rings)
        a = int(180 * (1 - i / rings))
        pygame.draw.circle(surf, (*color, a), (cx, cy), r, width=max(1, r // rings))
    return surf


def _draw_icon_undo(screen, color, cx, cy):
    pygame.draw.line(screen, color, (cx + 3, cy + 3), (cx + 3, cy - 2), 2)
    pygame.draw.line(screen, color, (cx + 3, cy - 2), (cx - 2, cy - 2), 2)
    pygame.draw.polygon(screen, color, [(cx - 2, cy - 2), (cx + 1, cy - 6), (cx + 1, cy + 2)])


def _draw_icon_redo(screen, color, cx, cy):
    pygame.draw.line(screen, color, (cx - 3, cy + 3), (cx - 3, cy - 2), 2)
    pygame.draw.line(screen, color, (cx - 3, cy - 2), (cx + 2, cy - 2), 2)
    pygame.draw.polygon(screen, color, [(cx + 2, cy - 2), (cx - 1, cy - 6), (cx - 1, cy + 2)])


def _draw_icon_reset(screen, color, cx, cy):
    pygame.draw.arc(screen, color, (cx - 6, cy - 6, 12, 12), math.radians(45), math.radians(315), 2)
    pygame.draw.polygon(screen, color, [(cx + 5, cy - 5), (cx + 5, cy - 10), (cx, cy - 5)])


def _draw_icon_home(screen, color, cx, cy):
    pygame.draw.polygon(screen, color,
                        [(cx, cy - 6), (cx - 6, cy), (cx - 4, cy), (cx - 4, cy + 6), (cx + 4, cy + 6), (cx + 4, cy),
                         (cx + 6, cy)], 2)
    pygame.draw.rect(screen, color, (cx - 1, cy + 2, 3, 4))


def _draw_icon_exit(screen, color, cx, cy):
    pygame.draw.rect(screen, color, (cx - 5, cy - 5, 6, 10), 2)
    pygame.draw.line(screen, color, (cx - 1, cy), (cx + 4, cy), 2)
    pygame.draw.polygon(screen, color, [(cx + 4, cy), (cx + 1, cy - 3), (cx + 1, cy + 3)])


class GameScene(Scene):
    W, H = 1000, 750

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

        # Delay Timers for Game Over
        self._game_over_timer = -1.0
        self._pending_winner_name = ""
        self._pending_winner_idx = None

        self._active_dialog = None
        self._hover_dialog_yes = False
        self._hover_dialog_no = False
        self._rect_dialog_yes = pygame.Rect(0, 0, 0, 0)
        self._rect_dialog_no = pygame.Rect(0, 0, 0, 0)

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
            self.agent = AIAgent(player_id=P2, difficulty=self.config.difficulty_label)
            self._budget = self.config.ai_budget
        else:
            self.agent = None
            self._budget = 0.0

        self._ai_thinking = False
        self._ai_result = None
        self._turn_start = _time.monotonic()

        self._game_over_timer = -1.0

    def on_enter(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        # Ignore clicks if the game is over and we are waiting for the transition
        if self._game_over_timer > 0:
            return

        if self._active_dialog:
            if event.type == pygame.MOUSEMOTION:
                self._hover_dialog_yes = self._rect_dialog_yes.collidepoint(event.pos)
                self._hover_dialog_no = self._rect_dialog_no.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._rect_dialog_yes.collidepoint(event.pos):
                    if self._active_dialog == "reset":
                        self._init_engine()
                    elif self._active_dialog == "menu":
                        self._go_to_menu()
                    self._active_dialog = None
                elif self._rect_dialog_no.collidepoint(event.pos):
                    self._active_dialog = None
            return

        if event.type == pygame.MOUSEMOTION:
            self._hover_u = self._btn_undo.collidepoint(event.pos)
            self._hover_r = self._btn_redo.collidepoint(event.pos)
            self._hover_res = self._btn_reset_rect.collidepoint(event.pos)
            self._hover_menu = self._btn_menu_rect.collidepoint(event.pos)
            self._hover_exit = self._btn_exit_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_reset_rect.collidepoint(event.pos):
                if self._undo_stack or self._redo_stack:
                    self._active_dialog = "reset"
                return
            if self._btn_menu_rect.collidepoint(event.pos):
                if self._undo_stack or self._redo_stack:
                    self._active_dialog = "menu"
                else:
                    self._go_to_menu()
                return
            if self._btn_exit_rect.collidepoint(event.pos):
                self.manager.quit()
                return

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
            if self.agent and self._redo_stack and self.board.current_player == P2:
                self._undo_stack.append(self.board.copy())
                self.board = self._redo_stack.pop()
            self._turn_start = _time.monotonic()

    def update(self, dt: float) -> None:
        self._anim_t += dt / 1000.0

        # Countdown the Game Over delay if a player won
        if self._game_over_timer > 0:
            self._game_over_timer -= dt / 1000.0
            if self._game_over_timer <= 0:
                screenshot = pygame.display.get_surface().copy()
                from src.ui.game_over_scene import GameOverScene
                self.manager.switch(
                    GameOverScene(self.manager, self.config, self._pending_winner_name, self._pending_winner_idx,
                                  screenshot))
                self._game_over_timer = -1.0  # Safe reset

        if self._invalid_timer > 0: self._invalid_timer = max(0.0, self._invalid_timer - dt)
        if self._ai_thinking and self._ai_result is not None: self._apply_ai_result()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_MAIN)
        pygame.draw.rect(screen, BG_PANEL, pygame.Rect(0, 0, self.W - SIDEBAR_W, self.H))

        valid_moves = [] if self._ai_thinking or self._game_over_timer > 0 else get_valid_pawn_moves(self.board,
                                                                                                     self.board.current_player)
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
        if self._active_dialog: self._draw_dialog(screen)

    def _draw_dialog(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        dw, dh = 400, 210
        dx = (self.W - dw) // 2
        dy = (self.H - dh) // 2
        dialog = pygame.Rect(dx, dy, dw, dh)

        pygame.draw.rect(screen, BG_PANEL, dialog, border_radius=12)
        pygame.draw.rect(screen, BORDER_A, dialog, width=2, border_radius=12)

        if self._active_dialog == "reset":
            title, sub1, sub2, btn_yes, icon_yes = "Reset Game?", "Are you sure you want to restart?", "All history and undo/redo will be cleared.", "Yes, Reset", _draw_icon_reset
        else:
            title, sub1, sub2, btn_yes, icon_yes = "Main Menu?", "Are you sure you want to leave?", "Current game progress will be lost.", "Yes, Leave", _draw_icon_home

        lbl_title = self._font_h2.render(title, True, TEXT_PRI)
        screen.blit(lbl_title, lbl_title.get_rect(centerx=dialog.centerx, top=dy + 24))
        lbl_sub1 = self._font_body.render(sub1, True, TEXT_SEC)
        screen.blit(lbl_sub1, lbl_sub1.get_rect(centerx=dialog.centerx, top=dy + 64))
        lbl_sub2 = self._font_body.render(sub2, True, TEXT_SEC)
        screen.blit(lbl_sub2, lbl_sub2.get_rect(centerx=dialog.centerx, top=dy + 88))

        bw, bh, gap = 150, 44, 20
        self._rect_dialog_yes = pygame.Rect(dialog.centerx - bw - gap // 2, dy + 140, bw, bh)
        self._rect_dialog_no = pygame.Rect(dialog.centerx + gap // 2, dy + 140, bw, bh)

        self._draw_btn(screen, self._rect_dialog_yes, icon_yes, btn_yes, self._hover_dialog_yes, True)
        self._draw_btn(screen, self._rect_dialog_no, _draw_icon_exit, "Cancel", self._hover_dialog_no, True)

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

    def _get_friendly_error(self, raw_msg: str) -> str:
        msg = raw_msg.lower()
        if "pawn move" in msg: return "Invalid move: You cannot move your pawn there."
        if "block" in msg or "path" in msg: return "Invalid wall: This completely blocks a player's path."
        if "no walls" in msg or "out of walls" in msg: return "Invalid wall: You have no walls left to place."
        if "wall placement" in msg or "overlap" in msg or "intersect" in msg: return "Invalid wall: You cannot place a wall there."
        return "Invalid move: Action not allowed."

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
            self._flash_invalid(self._get_friendly_error(str(e)))

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
        # Instead of instantly switching, we queue up the winner and start a delay timer!
        if self._game_over_timer < 0 and is_game_over(self.board):
            winner_idx = get_winner(self.board)
            if winner_idx == P1:
                self._pending_winner_name = f"{self.config.p1_name} (Red)"
            else:
                ai_names = {"Easy": "Ashraf", "Medium": "Yahia", "Hard": "Amr"}
                ai_disp = ai_names.get(self.config.difficulty_label, "AI")
                self._pending_winner_name = f"{ai_disp} (Blue)" if self.agent else f"{self.config.p2_name} (Blue)"

            self._pending_winner_idx = winner_idx
            self._game_over_timer = 0.3  # Wait before the popup!

    def _flash_invalid(self, msg: str):
        self._invalid_msg = msg
        self._invalid_timer = 2000

    def _draw_invalid_banner(self, screen, alpha):
        surf = self._font_small.render(self._invalid_msg, True, RED_LIGHT)
        pad_w = surf.get_width() + 44
        pad_h = surf.get_height() + 16
        pad = pygame.Rect(0, 0, pad_w, pad_h)
        pad.centerx = (self.W - SIDEBAR_W) // 2
        pad.bottom = self.H - 24

        banner = pygame.Surface((pad.w, pad.h), pygame.SRCALPHA)
        pygame.draw.rect(banner, (*RED_DARK, alpha), (0, 0, pad.w, pad.h), border_radius=6)
        pygame.draw.rect(banner, (*RED_LIGHT, alpha), (0, 0, pad.w, pad.h), width=1, border_radius=6)

        cx, cy = 18, pad.h // 2
        pygame.draw.polygon(banner, (*RED_LIGHT, alpha), [(cx, cy - 6), (cx - 7, cy + 6), (cx + 7, cy + 6)], 2)
        pygame.draw.rect(banner, (*RED_LIGHT, alpha), (cx - 1, cy - 2, 2, 4))
        pygame.draw.rect(banner, (*RED_LIGHT, alpha), (cx - 1, cy + 4, 2, 2))

        screen.blit(banner, pad.topleft)
        txt_surf = surf.copy()
        txt_surf.set_alpha(alpha)
        screen.blit(txt_surf, (pad.x + 32, pad.y + 8))

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
        ai_names = {"Easy": "Ashraf", "Medium": "Yahia", "Hard": "Amr"}
        if current == P1:
            name = f"{self.config.p1_name} (Red)"
        else:
            ai_disp = ai_names.get(self.config.difficulty_label, "AI")
            name = f"{ai_disp} (Blue)" if self.agent else f"{self.config.p2_name} (Blue)"

        dot_col = RED_PLAYER if current == P1 else BLUE_AI
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

            ai_disp = ai_names.get(self.config.difficulty_label, "AI").upper()
            screen.blit(self._font_sect.render(f"{ai_disp} THINKING…", True, TEXT_DIM), (x + 16, y + 14))

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
            py = y + 56 + i * 42
            self._draw_icon_player(screen, (x + 24, py), col, scale=0.8)
            for w in range(10):
                wr = pygame.Rect(x + 44 + w * 14, py - 6, 10, 10)
                pygame.draw.rect(screen, col if w < cnt else BORDER, wr, border_radius=3)

            lbl_count = self._font_body.render(str(cnt), True, TEXT_PRI)
            screen.blit(lbl_count, (x + 192, py - lbl_count.get_height() // 2))
        y += 136

        # 4. Action Buttons
        undo_ok = bool(self._undo_stack) and not self._ai_thinking
        redo_ok = bool(self._redo_stack) and not self._ai_thinking

        self._draw_btn(screen, self._btn_undo, _draw_icon_undo, "Undo", self._hover_u, undo_ok)
        self._draw_btn(screen, self._btn_redo, _draw_icon_redo, "Redo", self._hover_r, redo_ok)
        self._draw_action_btn(screen, self._btn_reset_rect, _draw_icon_reset, "Reset Game", self._hover_res)
        self._draw_action_btn(screen, self._btn_menu_rect, _draw_icon_home, "Main Menu", self._hover_menu)

    def _draw_icon_player(self, screen, pos, color, scale=1.0):
        cx, cy = pos
        r = int(9 * scale)
        pygame.draw.circle(screen, color, (cx, cy), r)
        pygame.draw.circle(screen, (255, 255, 255), (cx - int(r * 0.3), cy - int(r * 0.3)), max(1, int(r * 0.3)))

    def _draw_btn(self, screen, rect, icon_func, text, hover, enabled):
        col = BG_CARD_A if hover and enabled else BG_CARD
        bc = BORDER_A if hover and enabled else BORDER
        pygame.draw.rect(screen, col, rect, border_radius=8)
        pygame.draw.rect(screen, bc, rect, width=1, border_radius=8)

        txt_col = TEXT_PRI if enabled else TEXT_DIM
        lbl = self._font_body.render(text, True, txt_col)
        total_w = 16 + 8 + lbl.get_width()
        start_x = rect.x + (rect.w - total_w) // 2

        icon_func(screen, txt_col, start_x + 6, rect.centery)
        screen.blit(lbl, (start_x + 20, rect.centery - lbl.get_height() // 2))

    def _draw_action_btn(self, screen, rect, icon_func, text, hover):
        bg = BG_CARD_A if hover else BG_CARD
        brd = BORDER_A if hover else BORDER
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, brd, rect, width=1, border_radius=10)

        txt_col = TEXT_PRI if hover else TEXT_SEC
        lbl = self._font_body.render(text, True, txt_col)
        total_w = 16 + 12 + lbl.get_width()
        start_x = rect.x + (rect.w - total_w) // 2

        icon_func(screen, txt_col, start_x + 6, rect.centery)
        screen.blit(lbl, (start_x + 24, rect.centery - lbl.get_height() // 2))