"""
src/ui/game_over_scene.py  —  Grandmaster Edition
==================================================
Victory state scene with cinematic entrance and particle celebration.

Visual Features
───────────────
ENTRANCE ANIMATION
    The result card slides in from above using a cubic ease-out curve.
    Duration: 380 ms.  Feels weighty and deliberate.

PARTICLE BURST
    60 particles spawn from the card centre on enter.
    Colours: Purple, Teal, Amber, Lavender, White sparkle.
    Each particle has: random velocity, gravity, radius, alpha fade.

ANIMATED CROWN
    The ♛ glyph scales on a gentle sine wave (±8%) for a living feel.

WINNER NAME COLOUR WASH
    Rendered twice (TEXT_PRI + winner accent) for a subtle tint pass.

FROSTED CARD BACKGROUND
    A downscale→upscale trick approximates a Gaussian blur on the game
    screenshot, producing a frosted-glass card backing without
    requiring pygame ≥ 2.1.3.

BUTTON ICON GLYPH
    The 'Play Again' button shows a ↺ glyph prefix.
    The 'Main Menu' button shows a ⌂ glyph prefix.

API
───
    GameOverScene(manager, config, winner, winner_idx, screenshot)
      winner_idx: P1 → Lavender crown;  P2 (AI) → Teal crown
"""
from __future__ import annotations

import math
import random
import time as _time
from typing import Optional

import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.ui.game_config import GameConfig
from src.engine.board import P1, P2


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────────────────────────────────────
BG_MAIN    = ( 18,  17,  26)
BG_CARD    = ( 30,  27,  46)
PURPLE     = (127, 119, 221)
PURPLE_DK  = ( 83,  74, 183)
TEAL       = ( 29, 158, 117)
AMBER      = (239, 159,  39)
LAVENDER   = (186, 175, 242)
BORDER     = ( 58,  53,  85)
BORDER_A   = (127, 119, 221)
TEXT_PRI   = (240, 237, 248)
TEXT_SEC   = (122, 117, 144)
TEXT_DIM   = ( 90,  86, 112)
RED_PLAYER = (210,  40,  40)
BLUE_AI    = ( 40,  80, 210)
OVERLAY    = (  8,   7,  18, 210)   # RGBA: dark vignette over the screenshot

# Particle colour palette (RGBA)
_PARTICLE_PALETTE = [
    (127, 119, 221, 255),   # purple
    ( 29, 158, 117, 255),   # teal
    (239, 159,  39, 255),   # amber
    (186, 175, 242, 255),   # lavender
    (255, 255, 255, 210),   # white sparkle
]

_SLIDE_DURATION_S = 0.38    # seconds for the card slide-in
_GRAVITY_PX_S2    = 300.0   # particle gravity (pixels per second²)


# ─────────────────────────────────────────────────────────────────────────────
# Particle
# ─────────────────────────────────────────────────────────────────────────────
class _Particle:
    """Single confetti particle with velocity, gravity, and alpha fade."""

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color")

    def __init__(self, cx: float, cy: float) -> None:
        angle        = random.uniform(0, math.tau)
        speed        = random.uniform(70, 360)
        self.x       = cx
        self.y       = cy
        self.vx      = math.cos(angle) * speed
        self.vy      = math.sin(angle) * speed - random.uniform(30, 110)
        self.max_life = random.uniform(0.55, 1.45)
        self.life    = self.max_life
        self.radius  = random.randint(3, 7)
        self.color   = random.choice(_PARTICLE_PALETTE)

    def update(self, dt_s: float) -> None:
        self.vy  += _GRAVITY_PX_S2 * dt_s
        self.x   += self.vx * dt_s
        self.y   += self.vy * dt_s
        self.life = max(0.0, self.life - dt_s)

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def draw(self, screen: pygame.Surface) -> None:
        alpha        = int(255 * (self.life / self.max_life))
        r, g, b, _  = self.color
        s            = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (int(self.x) - self.radius, int(self.y) - self.radius))


# ─────────────────────────────────────────────────────────────────────────────
# Frosted glass helper
# ─────────────────────────────────────────────────────────────────────────────
def _frosted_crop(
    source:      pygame.Surface,
    rect:        pygame.Rect,
    blur_factor: int = 7,
) -> pygame.Surface:
    """
    Approximate a box blur on the cropped region of *source*.

    Technique: downscale to (w/blur_factor, h/blur_factor) then upscale back.
    Works with all pygame versions (no pygame.transform.box_blur needed).
    """
    crop    = source.subsurface(rect).copy()
    small_w = max(1, rect.w // blur_factor)
    small_h = max(1, rect.h // blur_factor)
    small   = pygame.transform.smoothscale(crop, (small_w, small_h))
    return pygame.transform.smoothscale(small, (rect.w, rect.h))


# ─────────────────────────────────────────────────────────────────────────────
# GameOverScene
# ─────────────────────────────────────────────────────────────────────────────
class GameOverScene(Scene):
    """
    Victory / game-over scene.

    Parameters
    ----------
    manager:     SceneManager instance for navigation.
    config:      Carried game settings (used to re-create GameScene on replay).
    winner:      Display name of the winning player.
    winner_idx:  P1 or P2, used for colour theming (crown and border accents).
    screenshot:  Optional Surface captured just before this scene was entered.
                 Used as the blurred background behind the card.
    """

    W, H = 900, 750

    def __init__(
        self,
        manager:    SceneManager,
        config:     GameConfig,
        winner:     str,
        winner_idx: int = P1,
        screenshot: Optional[pygame.Surface] = None,
    ) -> None:
        super().__init__(manager)
        self.config     = config
        self.winner     = winner
        self.winner_idx = winner_idx
        self.screenshot = screenshot

        # ── Fonts ─────────────────────────────────────────────────────────
        pygame.font.init()
        self._font_crown = pygame.font.SysFont("segoeui", 52)
        self._font_h1    = pygame.font.SysFont("segoeui", 32)
        self._font_sub   = pygame.font.SysFont("segoeui", 14)
        self._font_btn   = pygame.font.SysFont("segoeui", 17)

        # ── Card geometry ─────────────────────────────────────────────────
        self._cw        = 360
        self._ch        = 330
        self._card_x    = (self.W - self._cw) // 2
        self._final_y   = (self.H - self._ch) // 2  # resting position

        # ── Buttons (y filled in draw so they animate with the card) ──────
        bx             = self._card_x + 28
        bw             = self._cw - 56
        self._btn_play = pygame.Rect(bx, 0, bw, 50)   # y set each frame
        self._btn_menu = pygame.Rect(bx, 0, bw, 42)   # y set each frame
        self._hover_play = False
        self._hover_menu = False

        # ── Dark overlay (constant alpha) ─────────────────────────────────
        self._overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._overlay.fill(OVERLAY)

        # ── Frosted background behind the card ───────────────────────────
        card_rect = pygame.Rect(self._card_x, self._final_y, self._cw, self._ch)
        if screenshot and screenshot.get_size() == (self.W, self.H):
            # Guard against out-of-bounds rect (e.g. during window resize)
            safe_rect = card_rect.clip(screenshot.get_rect())
            self._frosted_bg: Optional[pygame.Surface] = (
                _frosted_crop(screenshot, safe_rect) if safe_rect.size == card_rect.size
                else None
            )
        else:
            self._frosted_bg = None

        # ── Animation state ───────────────────────────────────────────────
        self._enter_t = _time.monotonic()
        self._anim_t  = 0.0

        # ── Particles ─────────────────────────────────────────────────────
        pcx = self.W // 2
        pcy = self.H // 2
        self._particles: list[_Particle] = [
            _Particle(pcx, pcy) for _ in range(70)
        ]

        # ── Crown surface (scaled each frame) ────────────────────────────
        accent           = TEAL if winner_idx == P2 else LAVENDER
        self._crown_base = self._font_crown.render("♛", True, accent)

    # ── Scene lifecycle ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        """Reset the entrance timer each time the scene becomes active."""
        self._enter_t = _time.monotonic()

    # ── Event handling ──────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_play = self._btn_play.collidepoint(event.pos)
            self._hover_menu = self._btn_menu.collidepoint(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._restart()
            elif event.key == pygame.K_ESCAPE:
                self._go_menu()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_play.collidepoint(event.pos):
                self._restart()
            elif self._btn_menu.collidepoint(event.pos):
                self._go_menu()

    # ── Update ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        dt_s          = dt / 1000.0
        self._anim_t += dt_s
        for p in self._particles:
            p.update(dt_s)
        self._particles = [p for p in self._particles if p.alive]

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        # Blurred game screenshot as background
        if self.screenshot:
            screen.blit(self.screenshot, (0, 0))
        else:
            screen.fill(BG_MAIN)

        # Dark vignette overlay
        screen.blit(self._overlay, (0, 0))

        # Particles erupt from behind the card
        for p in self._particles:
            p.draw(screen)

        # Slide-in card: cubic ease-out
        raw      = min(1.0, self._anim_t / _SLIDE_DURATION_S)
        eased    = 1.0 - (1.0 - raw) ** 3        # ease-out cubic
        card_y   = int(-self._ch + (self._final_y + self._ch) * eased)

        self._draw_card(screen, card_y)

    # ── Card rendering ───────────────────────────────────────────────────────

    def _draw_card(self, screen: pygame.Surface, card_y: int) -> None:
        """Render the result card at the given vertical position."""
        card = pygame.Rect(self._card_x, card_y, self._cw, self._ch)

        # ── Frosted background ────────────────────────────────────────────
        if self._frosted_bg:
            fb = self._frosted_bg.copy()
            fb.set_alpha(150)
            screen.blit(fb, card.topleft)

        # ── Card fill (semi-transparent) ──────────────────────────────────
        fill = pygame.Surface((self._cw, self._ch), pygame.SRCALPHA)
        fill.fill((*BG_CARD, 228))
        screen.blit(fill, card.topleft)

        # ── Glowing border ────────────────────────────────────────────────
        border_col = TEAL if self.winner_idx == P2 else PURPLE
        pygame.draw.rect(screen, border_col, card, width=1, border_radius=18)
        # Outer dim ring for depth
        outer = card.inflate(3, 3)
        outer_s = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
        pygame.draw.rect(outer_s, (*border_col, 45),
                         (0, 0, outer.w, outer.h), width=2, border_radius=19)
        screen.blit(outer_s, outer.topleft)

        cx = card.centerx
        ty = card.top + 24

        # ── Animated crown ────────────────────────────────────────────────
        # Scale ±8% on a 1.4 s sine cycle
        scale    = 1.0 + 0.08 * math.sin(self._anim_t * math.tau / 1.4)
        cw_b, ch_b = self._crown_base.get_size()
        nw       = int(cw_b * scale)
        nh       = int(ch_b * scale)
        crown    = pygame.transform.smoothscale(self._crown_base, (nw, nh))
        screen.blit(crown, crown.get_rect(centerx=cx, top=ty))

        # ── "WINNER" label ─────────────────────────────────────────────────
        sub = self._font_sub.render("W I N N E R", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, top=ty + 70))

        # ── Winner name with colour wash ──────────────────────────────────
        name_surf  = self._font_h1.render(self.winner, True, TEXT_PRI)
        tint_col   = TEAL if self.winner_idx == P2 else PURPLE
        tint_surf  = self._font_h1.render(self.winner, True, tint_col)
        tint_surf.set_alpha(95)
        name_rect  = name_surf.get_rect(centerx=cx, top=ty + 102)
        screen.blit(name_surf, name_rect)
        screen.blit(tint_surf, name_rect)

        # ── Winner colour dot accent ──────────────────────────────────────
        dot_col = RED_PLAYER if self.winner_idx == P1 else BLUE_AI
        pygame.draw.circle(screen, dot_col,
                           (name_rect.left - 14, name_rect.centery), 5)

        # ── Divider ───────────────────────────────────────────────────────
        div_y = card.top + 216
        pygame.draw.line(screen, BORDER,
                         (card.left + 28, div_y), (card.right - 28, div_y))

        # ── Buttons (animated with card) ──────────────────────────────────
        btn_y = div_y + 14
        self._btn_play.y = btn_y
        self._btn_menu.y = btn_y + 60

        self._draw_play_btn(screen, self._btn_play)
        self._draw_menu_btn(screen, self._btn_menu)

    def _draw_play_btn(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        """'Play Again' primary action button."""
        col = PURPLE if self._hover_play else PURPLE_DK
        pygame.draw.rect(screen, col, rect, border_radius=10)
        # Hover glow
        if self._hover_play:
            glow = rect.inflate(4, 4)
            gs   = pygame.Surface((glow.w, glow.h), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*PURPLE, 50),
                             (0, 0, glow.w, glow.h), border_radius=12)
            screen.blit(gs, glow.topleft)
        lbl = self._font_btn.render("↺  Play Again", True, (255, 255, 255))
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_menu_btn(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        """'Main Menu' secondary action button."""
        bg_col  = BG_CARD + (0,) if not self._hover_menu else (45, 40, 72)
        brd_col = BORDER_A if self._hover_menu else BORDER
        if isinstance(bg_col, tuple) and len(bg_col) == 3:
            pygame.draw.rect(screen, bg_col, rect, border_radius=10)
        else:
            pygame.draw.rect(screen, BG_CARD, rect, border_radius=10)
        pygame.draw.rect(screen, brd_col, rect, width=1, border_radius=10)
        lbl = self._font_btn.render("⌂  Main Menu", True, TEXT_SEC)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    # ── Navigation ───────────────────────────────────────────────────────────

    def _restart(self) -> None:
        from src.ui.game_scene import GameScene  # deferred – avoids circular import
        self.manager.switch_fade(GameScene(self.manager, self.config))

    def _go_menu(self) -> None:
        from src.ui.menu_scene import MenuScene  # deferred – avoids circular import
        self.manager.switch_fade(MenuScene(self.manager))
