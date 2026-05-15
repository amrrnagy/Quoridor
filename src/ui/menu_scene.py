"""
src/ui/menu_scene.py  —  Grandmaster Edition
============================================
Main landing page / configuration selector.

Visual Features
───────────────
1.  ENTRANCE FADE
    The entire scene fades in over 500 ms using a black overlay whose alpha
    decreases from 255 → 0.  Powered by on_enter() timestamp + draw().

2.  DYNAMIC PARTICLE BACKGROUND
    40 ambient particles drift slowly upward.  Each has a random velocity,
    lifetime, and size.  They are rendered with SRCALPHA for soft blending.

3.  INTERACTIVE CARD SYSTEM
    Mode cards (HvH / HvC) glow on hover and selection using a BORDER_A
    outline.  Difficulty chips use the same system with a pill shape.

4.  ANIMATED BOARD PREVIEW
    The mini 9×9 grid on the right panel shows pulsing pawns with a
    "breathing" aura — a preview of the in-game aesthetic.

5.  GRADIENT TITLE
    The title "QUORIDOR" is rendered in a layered tint (TEXT_PRI + PURPLE)
    for a subtle colour wash effect.

6.  KEYBOARD SHORTCUT
    Pressing Enter starts the game immediately.
"""
from __future__ import annotations

import math
import random
import time as _time

import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.ui.game_config import GameConfig, GameMode, Difficulty


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette  (consistent across Grandmaster Edition)
# ─────────────────────────────────────────────────────────────────────────────
BG_MAIN    = ( 18,  17,  26)
BG_PANEL   = ( 14,  13,  24)
BG_CARD    = ( 30,  27,  46)
BG_CARD_A  = ( 45,  40,  72)
PURPLE     = (127, 119, 221)
PURPLE_DK  = ( 83,  74, 183)
TEAL       = ( 29, 158, 117)
AMBER      = (239, 159,  39)
TEXT_PRI   = (240, 237, 248)
TEXT_SEC   = (122, 117, 144)
TEXT_DIM   = ( 90,  86, 112)
BORDER     = ( 58,  53,  85)
BORDER_A   = (127, 119, 221)

# Entrance-fade duration in seconds
_FADE_IN_DURATION = 0.45


# ─────────────────────────────────────────────────────────────────────────────
# Ambient particle
# ─────────────────────────────────────────────────────────────────────────────
class _AmbientParticle:
    """
    A single slowly drifting background particle.

    Particles move upward with slight horizontal drift and fade out as
    their lifetime expires, then respawn at a random bottom position.
    """

    __slots__ = ("x", "y", "vx", "vy", "size", "max_life", "life")

    def __init__(self, w: int, h: int) -> None:
        self.x        = random.randint(0, w)
        self.y        = float(random.randint(0, h))
        self.vx       = random.uniform(-8.0, 8.0)
        self.vy       = random.uniform(-18.0, -5.0)  # upward drift
        self.size     = random.randint(2, 4)
        self.max_life = random.uniform(3.5, 7.0)
        self.life     = random.uniform(0.0, self.max_life)  # stagger starts

    def update(self, dt_s: float, w: int, h: int) -> None:
        self.x    += self.vx * dt_s
        self.y    += self.vy * dt_s
        self.life -= dt_s
        # Respawn at bottom when lifetime expires or particle exits top
        if self.life <= 0 or self.y < -10:
            self.y    = float(h + random.randint(0, 40))
            self.x    = random.randint(0, w)
            self.life = self.max_life

    def draw(self, screen: pygame.Surface) -> None:
        alpha = int(90 * (self.life / self.max_life))
        if alpha <= 0:
            return
        s = self.size
        surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*PURPLE, alpha), (s, s), s)
        screen.blit(surf, (int(self.x) - s, int(self.y) - s))


# ─────────────────────────────────────────────────────────────────────────────
# MenuScene
# ─────────────────────────────────────────────────────────────────────────────
class MenuScene(Scene):
    """
    Entry point for the Quoridor Grandmaster Edition.

    Layout
    ──────
    Left panel  (x: 0 … 560)   : Title, mode selection, difficulty, start
    Right panel (x: 560 … 900) : Animated board preview + info copy
    """

    W, H = 900, 750

    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        # Shared config object — mutated by UI and passed to GameScene
        self.config = GameConfig()

        # ── Fonts ─────────────────────────────────────────────────────────
        pygame.font.init()
        self._font_title = pygame.font.SysFont("segoeui", 64, bold=True)
        self._font_sub   = pygame.font.SysFont("segoeui", 16)
        self._font_btn   = pygame.font.SysFont("segoeui", 20)
        self._font_sect  = pygame.font.SysFont("segoeui", 12, bold=True)
        self._font_body  = pygame.font.SysFont("segoeui", 14)

        # ── Animation ─────────────────────────────────────────────────────
        self._anim_t   = 0.0
        self._enter_t  = 0.0   # set in on_enter()
        self._fade_surf = pygame.Surface((self.W, self.H))
        self._fade_surf.fill((0, 0, 0))

        # ── Particles ─────────────────────────────────────────────────────
        self._particles = [_AmbientParticle(self.W, self.H) for _ in range(45)]

        # ── Button rectangles ─────────────────────────────────────────────
        self._init_buttons()

    def _init_buttons(self) -> None:
        """Pre-compute all interactive element rects."""
        # Mode selection cards (left panel)
        self._rect_hvh   = pygame.Rect(60, 268, 450, 68)
        self._rect_hvc   = pygame.Rect(60, 350, 450, 68)

        # Difficulty chips
        self._chip_rects: list[pygame.Rect] = [
            pygame.Rect(60 + i * 152, 496, 142, 46)
            for i in range(3)
        ]

        # Start button
        self._rect_start = pygame.Rect(60, 596, 450, 64)

    # ── Scene lifecycle ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        """Record the entry timestamp for the fade-in animation."""
        self._enter_t = _time.monotonic()

    # ── Event handling ──────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._launch_game()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        # Mode selection
        if self._rect_hvh.collidepoint(pos):
            self.config.mode = GameMode.HUMAN_VS_HUMAN
        elif self._rect_hvc.collidepoint(pos):
            self.config.mode = GameMode.HUMAN_VS_AI

        # Difficulty chips (only interactive in HvAI mode)
        if self.config.mode == GameMode.HUMAN_VS_AI:
            for i, r in enumerate(self._chip_rects):
                if r.collidepoint(pos):
                    self.config.difficulty = list(Difficulty)[i]

        # Start button
        if self._rect_start.collidepoint(pos):
            self._launch_game()

    def _launch_game(self) -> None:
        """Transition to GameScene with the current config."""
        from src.ui.game_scene import GameScene  # deferred – avoids circular import
        self.manager.switch_fade(GameScene(self.manager, self.config))

    # ── Update ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        dt_s          = dt / 1000.0
        self._anim_t += dt_s
        for p in self._particles:
            p.update(dt_s, self.W, self.H)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_MAIN)

        # Ambient particles (behind everything)
        for p in self._particles:
            p.draw(screen)

        # Right panel
        pygame.draw.rect(screen, BG_PANEL, pygame.Rect(560, 0, 340, self.H))
        self._draw_right_panel(screen)

        # Left panel content
        self._draw_left_panel(screen)

        # Entrance fade-in overlay (drawn last so it dims everything)
        self._draw_entrance_fade(screen)

    # ── Panel renderers ──────────────────────────────────────────────────────

    def _draw_left_panel(self, screen: pygame.Surface) -> None:
        """Render the title, tagline, mode cards, difficulty chips, and start button."""
        mp = pygame.mouse.get_pos()

        # ── Title ─────────────────────────────────────────────────────────
        # Two-pass tint: base colour + translucent purple wash
        title_base = self._font_title.render("QUORIDOR", True, TEXT_PRI)
        title_tint = self._font_title.render("QUORIDOR", True, PURPLE)
        title_tint.set_alpha(55)
        screen.blit(title_base, (60, 80))
        screen.blit(title_tint, (60, 80))

        # Tagline
        tag = self._font_sub.render(
            "Grandmaster Edition  ·  Strategy Board Game", True, TEXT_DIM
        )
        screen.blit(tag, (62, 158))

        # Subtle separator
        pygame.draw.line(screen, BORDER, (60, 184), (510, 184), 1)

        # ── Mode label ────────────────────────────────────────────────────
        self._draw_sect_label(screen, "GAME MODE", 60, 238)
        self._draw_mode_card(
            screen, self._rect_hvh, "⚔   Human vs. Human",
            self.config.mode == GameMode.HUMAN_VS_HUMAN, mp,
        )
        self._draw_mode_card(
            screen, self._rect_hvc, "🤖  Human vs. Computer",
            self.config.mode == GameMode.HUMAN_VS_AI, mp,
        )

        # ── Difficulty chips ──────────────────────────────────────────────
        ai_active = (self.config.mode == GameMode.HUMAN_VS_AI)
        self._draw_sect_label(screen, "AI DIFFICULTY", 60, 468,
                              alpha=255 if ai_active else 80)

        diff_labels = ["Easy", "Medium", "Hard"]
        for i, (rect, label) in enumerate(zip(self._chip_rects, diff_labels)):
            selected = ai_active and (self.config.difficulty.value == i + 1)
            self._draw_chip(screen, rect, label, selected, ai_active)

        # ── Start button ──────────────────────────────────────────────────
        self._draw_start_btn(screen, self._rect_start, mp)

    def _draw_right_panel(self, screen: pygame.Surface) -> None:
        """Render the animated mini board and decorative copy text."""
        self._draw_board_preview(screen, cx=730, cy=340)

        # Panel heading
        h = self._font_sect.render("BOARD PREVIEW", True, TEXT_DIM)
        screen.blit(h, h.get_rect(centerx=730, top=130))

        # Short description paragraphs
        lines = [
            "Place walls to block",
            "your opponent.",
            "",
            "Be first to cross",
            "to the opposite side.",
        ]
        for i, line in enumerate(lines):
            t = self._font_body.render(line, True, TEXT_SEC)
            screen.blit(t, t.get_rect(centerx=730, top=540 + i * 22))

    def _draw_entrance_fade(self, screen: pygame.Surface) -> None:
        """Draw a black overlay that fades from opaque to transparent on entry."""
        elapsed = _time.monotonic() - self._enter_t
        t       = min(1.0, elapsed / _FADE_IN_DURATION)
        alpha   = int(255 * (1.0 - t))
        if alpha <= 0:
            return
        self._fade_surf.set_alpha(alpha)
        screen.blit(self._fade_surf, (0, 0))

    # ── Widget drawers ───────────────────────────────────────────────────────

    def _draw_mode_card(
        self,
        screen: pygame.Surface,
        rect:   pygame.Rect,
        label:  str,
        active: bool,
        mp:     tuple[int, int],
    ) -> None:
        """Render a mode selection card with hover + selection states."""
        hover   = rect.collidepoint(mp)
        bg      = BG_CARD_A if (active or hover) else BG_CARD
        brd     = BORDER_A  if (active or hover) else BORDER
        txt_col = TEXT_PRI  if active else (TEXT_SEC if hover else TEXT_DIM)

        pygame.draw.rect(screen, bg,  rect, border_radius=12)
        pygame.draw.rect(screen, brd, rect, width=1, border_radius=12)

        # Active: left-edge accent bar
        if active:
            bar = pygame.Rect(rect.x, rect.y + 12, 3, rect.h - 24)
            pygame.draw.rect(screen, PURPLE, bar, border_radius=2)

        lbl = self._font_btn.render(label, True, txt_col)
        screen.blit(lbl, lbl.get_rect(midleft=(rect.x + 24, rect.centery)))

    def _draw_chip(
        self,
        screen:   pygame.Surface,
        rect:     pygame.Rect,
        label:    str,
        selected: bool,
        enabled:  bool,
    ) -> None:
        """Render a pill-shaped difficulty selection chip."""
        alpha   = 255 if enabled else 70
        bg      = BG_CARD_A if selected else BG_CARD
        brd     = BORDER_A  if selected else BORDER
        txt_col = TEXT_PRI  if selected else TEXT_DIM

        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (*bg,  alpha), (0, 0, rect.w, rect.h), border_radius=23)
        pygame.draw.rect(s, (*brd, alpha), (0, 0, rect.w, rect.h),
                         width=1, border_radius=23)
        screen.blit(s, rect.topleft)

        lbl = self._font_sect.render(label.upper(), True, txt_col)
        lbl.set_alpha(alpha)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_start_btn(
        self,
        screen: pygame.Surface,
        rect:   pygame.Rect,
        mp:     tuple[int, int],
    ) -> None:
        """Render the primary 'Start Mission' button with a breathing glow."""
        hover   = rect.collidepoint(mp)
        pulse   = (math.sin(self._anim_t * 3.5) + 1) / 2   # 0..1

        # Outer glow ring (subtle pulsing)
        glow_r = int(4 + 6 * pulse)
        glow   = rect.inflate(glow_r, glow_r)
        glow_s = pygame.Surface((glow.w, glow.h), pygame.SRCALPHA)
        pygame.draw.rect(glow_s, (*PURPLE, int(40 * pulse)),
                         (0, 0, glow.w, glow.h), border_radius=14)
        screen.blit(glow_s, glow.topleft)

        # Button fill
        col = PURPLE if hover else PURPLE_DK
        pygame.draw.rect(screen, col, rect, border_radius=12)

        # Arrow shifts right on hover for a "press" feel
        arrow_offset = 4 if hover else 0
        lbl = self._font_btn.render("START MISSION", True, (255, 255, 255))
        arrow = self._font_btn.render("→", True, AMBER)

        total_w = lbl.get_width() + 14 + arrow.get_width()
        start_x = rect.centerx - total_w // 2
        lbl_y   = rect.centery - lbl.get_height() // 2
        screen.blit(lbl, (start_x, lbl_y))
        screen.blit(arrow, (start_x + lbl.get_width() + 14 + arrow_offset, lbl_y))

    def _draw_sect_label(
        self,
        screen: pygame.Surface,
        text:   str,
        x:      int,
        y:      int,
        alpha:  int = 255,
    ) -> None:
        """Render a small all-caps section header."""
        lbl = self._font_sect.render(text, True, TEXT_DIM)
        lbl.set_alpha(alpha)
        screen.blit(lbl, (x, y))

    def _draw_board_preview(
        self,
        screen: pygame.Surface,
        cx:     int,
        cy:     int,
    ) -> None:
        """
        Draw the animated mini 9×9 board preview on the right panel.

        Animated elements:
          • Grid cells pulse between two shades in a subtle wave pattern.
          • Player pawns have a breathing aura ring.
          • A few static amber walls are pre-placed for visual interest.
        """
        cell  = 26
        gap   = 3
        step  = cell + gap
        total = 9 * step - gap
        ox    = cx - total // 2
        oy    = cy - total // 2

        wave  = (math.sin(self._anim_t * 1.5) + 1) / 2  # 0..1 slow pulse

        # Draw grid cells
        for r in range(9):
            for c in range(9):
                # Goal rows get a faint tint
                if r == 0:
                    base = (8, 48, 38)   # teal tint for P2 goal
                elif r == 8:
                    base = (38, 16, 28)  # red tint for P1 goal
                else:
                    base = (26, 24, 42)

                rect = pygame.Rect(ox + c * step, oy + r * step, cell, cell)
                pygame.draw.rect(screen, base, rect, border_radius=3)

        # Static decorative walls
        for r, c in [(3, 2), (3, 3), (5, 5), (5, 6)]:
            # Horizontal wall stub
            wr = pygame.Rect(ox + c * step, oy + (r + 1) * step - gap,
                             cell * 2 + gap, gap + 2)
            if wr.right < ox + total and wr.bottom < oy + total:
                pygame.draw.rect(screen, AMBER, wr, border_radius=2)

        # Pawn positions
        p1_pos = (ox + 4 * step + cell // 2, oy + 8 * step + cell // 2)
        p2_pos = (ox + 4 * step + cell // 2, oy + 0 * step + cell // 2)

        # Aura rings (breathing)
        aura_r = int(cell // 2 + 3 + 4 * wave)
        for centre, col in ((p1_pos, (210, 40, 40)), (p2_pos, (40, 80, 210))):
            s = pygame.Surface((aura_r * 4, aura_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, int(50 + 40 * wave)),
                               (aura_r * 2, aura_r * 2), aura_r, width=2)
            screen.blit(s, (centre[0] - aura_r * 2, centre[1] - aura_r * 2))

        # Pawns
        pygame.draw.circle(screen, (210,  40,  40), p1_pos, cell // 2 - 2)
        pygame.draw.circle(screen, ( 40,  80, 210), p2_pos, cell // 2 - 2)

        # Specular dots
        for centre in (p1_pos, p2_pos):
            pygame.draw.circle(screen, (255, 255, 255),
                               (centre[0] - 3, centre[1] - 3), 2)
