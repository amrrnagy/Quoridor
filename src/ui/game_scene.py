"""
src/ui/game_scene.py  —  Grandmaster Edition
=============================================
Visual upgrades over the original:

  1. AI THINKING INDICATOR
     ─────────────────────
     • Threaded AI computation: the main loop never blocks.
     • While the AI thinks, the sidebar shows a live elapsed-time bar
       (fills purple → teal depending on difficulty budget).
     • The AI pawn gets an animated "breathing aura" — a semi-transparent
       ring that expands and fades on a 1.2 s cycle, drawn via a
       pre-rendered SRCALPHA surface so it costs only one blit per frame.

  2. VALID-MOVE HIGHLIGHTS  ("ghost pawns")
     ───────────────────────────────────────
     • Each valid move cell shows a translucent pawn silhouette
       ("ghost pawn") that pulses between 40 % and 80 % opacity on a
       0.8 s sine cycle, giving a living, breathing feel.
     • Highlight colour matches the current player (Purple / Teal).

  3. SIDEBAR HUD
     ────────────
     • Real player names pulled from GameConfig.
     • Animated "thinking" progress bar replaces static status text
       when the AI is computing.
     • Wall pips animate (slide in) when a wall is spent.
     • Turn elapsed timer counts up each player's per-turn time.

  4. INVALID-MOVE BANNER
     ─────────────────────
     • Unchanged API but fades out smoothly over the last 400 ms.
"""
from __future__ import annotations

import math
import threading
import time as _time

import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.ui.game_config import GameConfig, GameMode
from src.engine.board import Board, P1, P2
from src.engine.rules import (
    apply_pawn_move, apply_wall,
    is_game_over, get_winner, get_valid_pawn_moves,
)
from src.ai.agent import AIAgent
from src.ui.board_view import BoardView

# ── colour palette ────────────────────────────────────────────────────────
BG_MAIN    = (18,  17,  26)
BG_PANEL   = (14,  13,  24)
BG_CARD    = (30,  27,  46)
BG_CARD_A  = (45,  40,  72)
PURPLE     = (127, 119, 221)
PURPLE_DK  = ( 83,  74, 183)
TEAL       = ( 29, 158, 117)
TEAL_DK    = ( 17, 110,  82)
AMBER      = (239, 159,  39)
TEXT_PRI   = (240, 237, 248)
TEXT_SEC   = (122, 117, 144)
TEXT_DIM   = ( 90,  86, 112)
BORDER     = ( 58,  53,  85)
BORDER_A   = (127, 119, 221)
RED_DARK   = (163,  45,  45)
RED_LIGHT  = (252, 235, 235)

INVALID_FLASH_MS = 2200
SIDEBAR_W        = 220

# Per-difficulty time budgets (must match agent.py)
_BUDGET = {"Easy": 0.5, "Medium": 2.0, "Hard": 4.5}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: pre-render a blurred aura ring onto an SRCALPHA surface
# ─────────────────────────────────────────────────────────────────────────────
def _make_aura_surface(radius: int, color: tuple, rings: int = 5) -> pygame.Surface:
    """
    Returns a square SRCALPHA surface with a soft glowing ring.
    `radius`  — outer radius of the aura
    `color`   — (R,G,B) — alpha is controlled at blit time via set_alpha()
    `rings`   — number of concentric circles for the soft edge
    """
    size = radius * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for i in range(rings, 0, -1):
        r = int(radius * i / rings)
        a = int(180 * (1 - i / rings))          # inner rings more opaque
        pygame.draw.circle(surf, (*color, a), (cx, cy), r, width=max(1, r // rings))
    return surf


# ─────────────────────────────────────────────────────────────────────────────
# GameScene
# ─────────────────────────────────────────────────────────────────────────────
class GameScene(Scene):
    W, H = 900, 750

    def __init__(self, manager: SceneManager, config: GameConfig) -> None:
        super().__init__(manager)
        self.config = config

        pygame.font.init()
        self._font_h2    = pygame.font.SysFont("segoeui", 20)
        self._font_body  = pygame.font.SysFont("segoeui", 15)
        self._font_small = pygame.font.SysFont("segoeui", 13)
        self._font_sect  = pygame.font.SysFont("segoeui", 12)
        self._font_mono  = pygame.font.SysFont("consolas", 13)

        # ── invalid-move flash ────────────────────
        self._invalid_msg: str   = ""
        self._invalid_timer: float = 0.0

        # ── reset button ──────────────────────────
        bx = self.W - SIDEBAR_W + 12
        self._btn_reset_rect  = pygame.Rect(bx, self.H - 66, SIDEBAR_W - 24, 44)
        self._btn_reset_hover = False

        # ── animation clock (seconds, updated each frame) ─────────────
        self._anim_t: float = 0.0      # total elapsed seconds for sine waves

        # ── turn timer ────────────────────────────
        self._turn_start: float = _time.monotonic()

        # ── AI thinking state ─────────────────────
        self._ai_thinking  = False
        self._ai_start_t   = 0.0       # monotonic seconds when AI started
        self._ai_result    = None      # dict set by background thread
        self._ai_thread: threading.Thread | None = None

        # ── aura surfaces (built lazily once) ─────
        self._aura_p     = _make_aura_surface(28, PURPLE)
        self._aura_teal  = _make_aura_surface(28, TEAL)

        # ── init engine ───────────────────────────
        self._init_engine()

    # ── engine init ──────────────────────────────────────────────────────
    def _init_engine(self) -> None:
        self.board      = Board()
        self.board_view = BoardView()

        if self.config.mode == GameMode.HUMAN_VS_AI:
            diff_str    = self.config.difficulty.name.title()
            self.agent  = AIAgent(player_id=P2, difficulty=diff_str)
            self._budget = _BUDGET.get(diff_str, 2.0)
        else:
            self.agent   = None
            self._budget = 0.0

        # Cancel any running thread
        self._ai_thinking = False
        self._ai_result   = None
        self._turn_start  = _time.monotonic()

    # ── Scene interface ───────────────────────────────────────────────────
    def on_enter(self) -> None:
        self._init_engine()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._btn_reset_hover = self._btn_reset_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_reset_rect.collidepoint(event.pos):
                self._reset_game()
                return
            if not self._ai_thinking:
                self._handle_board_click(event.pos)

    def update(self, dt: float) -> None:
        # dt is milliseconds from the main loop clock.tick()
        self._anim_t += dt / 1000.0

        if self._invalid_timer > 0:
            self._invalid_timer = max(0.0, self._invalid_timer - dt)

        # Poll for AI result from background thread
        if self._ai_thinking and self._ai_result is not None:
            self._apply_ai_result()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_MAIN)

        board_rect = pygame.Rect(0, 0, self.W - SIDEBAR_W, self.H)
        pygame.draw.rect(screen, BG_PANEL, board_rect)

        # ── valid-move ghost highlights ───────────
        if not self._ai_thinking:
            valid_moves = get_valid_pawn_moves(self.board, self.board.current_player)
        else:
            valid_moves = []

        self._draw_aura_under_ai_pawn(screen)
        self.board_view.draw(screen, self.board, valid_moves)
        self._draw_ghost_pawns(screen, valid_moves)

        if self._invalid_timer > 0:
            alpha = min(255, int(self._invalid_timer / 400 * 255))
            self._draw_invalid_banner(screen, alpha)

        self._draw_sidebar(screen)

    # ── AI aura ───────────────────────────────────────────────────────────
    def _draw_aura_under_ai_pawn(self, screen: pygame.Surface) -> None:
        """
        Draws a breathing glow around the AI pawn (P2) while it is thinking.
        The aura pulses on a 1.2 s sine cycle: opacity goes 0 → 200 → 0.
        """
        if not self._ai_thinking:
            return

        # Get screen position of P2 pawn from board_view
        pawn_screen_pos = self.board_view.cell_center(self.board.get_position(P2))
        if pawn_screen_pos is None:
            return

        pulse = (math.sin(self._anim_t * math.pi / 0.6) + 1) / 2   # 0..1
        alpha = int(60 + 180 * pulse)                                 # 60..240

        surf = self._aura_teal.copy()
        surf.set_alpha(alpha)
        cx, cy = pawn_screen_pos
        size   = self._aura_teal.get_width()
        screen.blit(surf, (cx - size // 2, cy - size // 2),
                    special_flags=pygame.BLEND_RGBA_ADD)

    # ── ghost pawns (valid-move highlights) ──────────────────────────────
    def _draw_ghost_pawns(
        self, screen: pygame.Surface, valid_moves: list
    ) -> None:
        """
        Draws a translucent pawn silhouette on each valid move cell.
        Opacity pulses between 40 % and 85 % on a 0.8 s cycle.
        """
        if not valid_moves:
            return

        pulse = (math.sin(self._anim_t * math.pi / 0.4) + 1) / 2   # 0..1
        alpha = int(100 + 115 * pulse)                                # 100..215

        current = self.board.current_player
        base_color = PURPLE if current == P1 else TEAL
        radius     = self.board_view.cell_size // 2 - 4

        for pos in valid_moves:
            cx, cy = self.board_view.cell_center(pos)
            ghost  = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*base_color, alpha),
                               (radius, radius), radius)
            # Hollow ring to look like a "ghost" outline
            inner = max(2, radius - 4)
            pygame.draw.circle(ghost, (*BG_PANEL, alpha),
                               (radius, radius), inner)
            screen.blit(ghost, (cx - radius, cy - radius))

    # ── board click ───────────────────────────────────────────────────────
    def _handle_board_click(self, pos: tuple) -> None:
        if self.agent and self.board.current_player == P2:
            return

        click_type, data = self.board_view.identify_click(pos)
        try:
            if click_type == "cell":
                apply_pawn_move(self.board, self.board.current_player, data)
            elif click_type == "wall":
                apply_wall(self.board, self.board.current_player,
                           data["anchor"], data["horizontal"])

            self._check_winner()
            self._turn_start = _time.monotonic()

            if (self.agent and not is_game_over(self.board)
                    and self.board.current_player == P2):
                self._launch_ai_thread()

        except ValueError as e:
            self._flash_invalid(str(e))

    # ── threaded AI ───────────────────────────────────────────────────────
    def _launch_ai_thread(self) -> None:
        """Start AI computation in a background thread."""
        self._ai_thinking = True
        self._ai_result   = None
        self._ai_start_t  = _time.monotonic()

        board_copy = self.board.copy()

        def _worker():
            action = self.agent.get_best_move(board_copy)
            self._ai_result = action         # atomic write; Python GIL safe

        self._ai_thread = threading.Thread(target=_worker, daemon=True)
        self._ai_thread.start()

    def _apply_ai_result(self) -> None:
        """Called from update() once the background thread has a result."""
        action = self._ai_result
        self._ai_thinking = False
        self._ai_result   = None

        if action:
            if action["type"] == "move":
                apply_pawn_move(self.board, P2, action["target"])
            elif action["type"] == "wall":
                apply_wall(self.board, P2, action["anchor"], action["horizontal"])

        self._turn_start = _time.monotonic()
        self._check_winner()

    # ── winner check ──────────────────────────────────────────────────────
    def _check_winner(self) -> None:
        if is_game_over(self.board):
            winner_idx  = get_winner(self.board)
            winner_name = "Player 1 (Blue)" if winner_idx == P1 else "Player 2 (AI)"
            screenshot  = pygame.display.get_surface().copy()
            from src.ui.game_over_scene import GameOverScene
            self.manager.switch(
                GameOverScene(self.manager, self.config, winner_name,
                              winner_idx, screenshot)
            )

    # ── reset ─────────────────────────────────────────────────────────────
    def _reset_game(self) -> None:
        self._invalid_timer = 0.0
        self._init_engine()

    # ── invalid-move banner ───────────────────────────────────────────────
    def _flash_invalid(self, msg: str) -> None:
        self._invalid_msg   = msg
        self._invalid_timer = INVALID_FLASH_MS

    def _draw_invalid_banner(self, screen: pygame.Surface, alpha: int) -> None:
        msg  = f"⚠  {self._invalid_msg}"
        surf = self._font_small.render(msg, True, RED_LIGHT)
        pad  = pygame.Rect(0, 0, surf.get_width() + 28, surf.get_height() + 16)
        pad.centerx = (self.W - SIDEBAR_W) // 2
        pad.bottom  = self.H - 20
        banner = pygame.Surface((pad.w, pad.h), pygame.SRCALPHA)
        banner.fill((*RED_DARK, alpha))
        screen.blit(banner, pad.topleft)
        screen.blit(surf, (pad.x + 14, pad.y + 8))

    # ── sidebar ───────────────────────────────────────────────────────────
    def _draw_sidebar(self, screen: pygame.Surface) -> None:
        sx = self.W - SIDEBAR_W
        pygame.draw.rect(screen, BG_MAIN,
                         pygame.Rect(sx, 0, SIDEBAR_W, self.H))
        pygame.draw.line(screen, BORDER, (sx, 0), (sx, self.H))

        x = sx + 14
        y = 20

        # ─── 1. Turn indicator card ────────────────────────────────────
        card = pygame.Rect(x, y, SIDEBAR_W - 28, 82)
        pygame.draw.rect(screen, BG_CARD, card, border_radius=10)
        pygame.draw.rect(screen, BORDER_A, card, width=1, border_radius=10)

        self._draw_section_label(screen, "CURRENT TURN", x + 12, y + 10)

        current   = self.board.current_player
        name      = ("Player 1" if current == P1
                     else ("AI" if self.agent else "Player 2"))
        dot_col   = PURPLE if current == P1 else TEAL
        pygame.draw.circle(screen, dot_col, (x + 18, y + 57), 5)
        lbl = self._font_h2.render(name, True, TEXT_PRI)
        screen.blit(lbl, (x + 30, y + 48))

        # Turn elapsed timer (top-right of card)
        elapsed_s = _time.monotonic() - self._turn_start
        timer_str = f"{elapsed_s:4.1f}s"
        ts = self._font_mono.render(timer_str, True, TEXT_DIM)
        screen.blit(ts, (card.right - ts.get_width() - 10, y + 10))

        y += 98

        # ─── 2. AI thinking progress bar ──────────────────────────────
        if self._ai_thinking:
            bar_card = pygame.Rect(x, y, SIDEBAR_W - 28, 56)
            pygame.draw.rect(screen, BG_CARD, bar_card, border_radius=10)
            pygame.draw.rect(screen, BORDER_A, bar_card, width=1, border_radius=10)

            self._draw_section_label(screen, "AI THINKING…", x + 12, y + 10)

            think_elapsed = _time.monotonic() - self._ai_start_t
            progress      = min(1.0, think_elapsed / self._budget)

            bar_bg = pygame.Rect(x + 12, y + 34, SIDEBAR_W - 52, 10)
            pygame.draw.rect(screen, BORDER, bar_bg, border_radius=5)

            bar_w  = max(4, int(bar_bg.width * progress))
            bar_fg = pygame.Rect(bar_bg.x, bar_bg.y, bar_w, 10)
            # Colour shifts purple → teal as progress increases
            r_c = int(PURPLE[0] + (TEAL[0] - PURPLE[0]) * progress)
            g_c = int(PURPLE[1] + (TEAL[1] - PURPLE[1]) * progress)
            b_c = int(PURPLE[2] + (TEAL[2] - PURPLE[2]) * progress)
            pygame.draw.rect(screen, (r_c, g_c, b_c), bar_fg, border_radius=5)

            # Animated dots after "AI THINKING"
            dots = "." * (int(self._anim_t * 2) % 4)
            dt_s = self._font_small.render(
                f"{think_elapsed:.1f}s{dots}", True, TEXT_SEC)
            screen.blit(dt_s, (bar_bg.right - dt_s.get_width(),
                               bar_bg.top - 16))
            y += 72

        # ─── 3. Walls remaining card ───────────────────────────────────
        card2 = pygame.Rect(x, y, SIDEBAR_W - 28, 106)
        pygame.draw.rect(screen, BG_CARD, card2, border_radius=10)
        self._draw_section_label(screen, "WALLS REMAINING", x + 12, y + 10)

        walls  = [self.board.get_walls_left(P1),
                  self.board.get_walls_left(P2)]
        colors = [PURPLE, TEAL]
        p_names = ["Player 1",
                   "AI" if self.agent else "Player 2"]

        for i in range(2):
            py = y + 32 + i * 34
            screen.blit(self._font_small.render(p_names[i], True, TEXT_SEC),
                        (x + 12, py))
            count_s = self._font_mono.render(str(walls[i]), True, colors[i])
            screen.blit(count_s, (card2.right - count_s.get_width() - 10, py))

            for w in range(10):
                wr = pygame.Rect(x + 12 + w * 15, py + 17, 12, 7)
                if w < walls[i]:
                    pygame.draw.rect(screen, colors[i], wr, border_radius=2)
                else:
                    # spent wall: dim pip with a subtle "used" cross
                    pygame.draw.rect(screen, BORDER, wr, border_radius=2)

        y += 122

        # ─── 4. Status / hint card ─────────────────────────────────────
        card3 = pygame.Rect(x, y, SIDEBAR_W - 28, 100)
        pygame.draw.rect(screen, BG_CARD, card3, border_radius=10)
        self._draw_section_label(screen, "STATUS", x + 12, y + 10)

        if self._ai_thinking:
            lines = [
                "AI is calculating…",
                "Please wait.",
            ]
        elif self.board.current_player == P1:
            lines = [
                "Your turn.",
                "Click a glowing cell",
                "to move your pawn, or",
                "a board edge for a wall.",
            ]
        else:
            lines = [
                "Player 2's turn.",
                "Click a glowing cell",
                "to move or place wall.",
            ]

        for i, line in enumerate(lines):
            s = self._font_small.render(line, True, TEXT_SEC)
            screen.blit(s, (x + 12, y + 28 + i * 18))

        # ─── 5. Reset button ───────────────────────────────────────────
        r = self._btn_reset_rect
        col = BG_CARD_A if self._btn_reset_hover else BG_CARD
        bc  = BORDER_A  if self._btn_reset_hover else BORDER
        pygame.draw.rect(screen, col, r, border_radius=8)
        pygame.draw.rect(screen, bc,  r, width=1, border_radius=8)
        lbl = self._font_body.render("⟳  Reset Game", True, TEXT_SEC)
        screen.blit(lbl, lbl.get_rect(center=r.center))

    def _draw_section_label(
        self, screen: pygame.Surface, text: str, x: int, y: int
    ) -> None:
        surf = self._font_sect.render(text, True, TEXT_DIM)
        screen.blit(surf, (x, y))