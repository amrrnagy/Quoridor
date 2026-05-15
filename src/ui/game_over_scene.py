"""
src/ui/game_over_scene.py  —  Grandmaster Edition
==================================================
Visual upgrades over the original:

  ENTRANCE ANIMATION
  ──────────────────
  • The card slides down from y=-ch to its final position over 400 ms
    using an ease-out cubic curve.  Feels weighty and deliberate.

  PARTICLE BURST
  ──────────────
  • On enter, 60 particles are spawned from the card centre.
  • Each particle is a small coloured circle with a random velocity,
    gravity, and lifetime (0.6–1.4 s).
  • Particle colours cycle through the palette: Purple, Teal, Amber,
    and a soft lavender — giving a confetti feel without external libs.
  • All particle logic is pure Python + Pygame; zero extra dependencies.

  ANIMATED CROWN
  ──────────────
  • The crown emoji pulses on a gentle sine wave (scale ±8 %).
    Implemented by pre-rendering the glyph then scaling the surface
    each frame (cheap: glyph is small, ~52 px).

  GRADIENT WINNER NAME
  ────────────────────
  • The winner name is rendered twice: once in TEXT_PRI and once in
    PURPLE, then blended via BLEND_RGBA_MULT for a subtle colour wash.

  FROSTED CARD
  ────────────
  • The card uses a blurred copy of the screenshot behind it (via
    a pixel-downscale trick) to approximate a frosted-glass look
    without requiring pygame.transform.box_blur (added in 2.1.3).

API change: __init__ now accepts `winner_idx` (int) for colour theming.
Pass P1 → purple crown, P2 (AI) → teal crown.
"""
from __future__ import annotations

import math
import random
import time as _time

import pygame
from src.ui.scene_manager import Scene, SceneManager
from src.game_config import GameConfig
from src.engine.board import P1, P2

# ── palette ───────────────────────────────────────────────────────────────
BG_MAIN    = (18,  17,  26)
BG_CARD    = (30,  27,  46)
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
OVERLAY    = (8,    7,  18, 200)

# Particle colours (RGBA)
_PARTICLE_COLORS = [
    (127, 119, 221, 255),  # purple
    ( 29, 158, 117, 255),  # teal
    (239, 159,  39, 255),  # amber
    (186, 175, 242, 255),  # lavender
    (255, 255, 255, 200),  # white sparkle
]

_SLIDE_DURATION = 0.38     # seconds for card slide-in
_GRAVITY        = 320.0    # pixels/s² for particles


# ─────────────────────────────────────────────────────────────────────────────
# Particle
# ─────────────────────────────────────────────────────────────────────────────
class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color")

    def __init__(self, cx: float, cy: float) -> None:
        angle   = random.uniform(0, math.tau)
        speed   = random.uniform(80, 340)
        self.x  = cx
        self.y  = cy
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(40, 120)  # upward bias
        self.max_life = random.uniform(0.6, 1.4)
        self.life     = self.max_life
        self.radius   = random.randint(3, 7)
        self.color    = random.choice(_PARTICLE_COLORS)

    def update(self, dt: float) -> None:
        self.vy += _GRAVITY * dt
        self.x  += self.vx  * dt
        self.y  += self.vy  * dt
        self.life = max(0.0, self.life - dt)

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def draw(self, screen: pygame.Surface) -> None:
        alpha   = int(255 * (self.life / self.max_life))
        r, g, b, _ = self.color
        surf    = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (r, g, b, alpha),
                           (self.radius, self.radius), self.radius)
        screen.blit(surf, (int(self.x) - self.radius,
                           int(self.y) - self.radius))


# ─────────────────────────────────────────────────────────────────────────────
# Frosted-glass helper
# ─────────────────────────────────────────────────────────────────────────────
def _frosted_crop(source: pygame.Surface, rect: pygame.Rect,
                  blur_factor: int = 6) -> pygame.Surface:
    """
    Crop `rect` from `source`, downscale by `blur_factor`, upscale back.
    This creates a cheap box-blur approximation.
    Returns a Surface sized rect.w × rect.h.
    """
    crop  = source.subsurface(rect).copy()
    small_w = max(1, rect.w // blur_factor)
    small_h = max(1, rect.h // blur_factor)
    small = pygame.transform.smoothscale(crop, (small_w, small_h))
    return pygame.transform.smoothscale(small, (rect.w, rect.h))


# ─────────────────────────────────────────────────────────────────────────────
# GameOverScene
# ─────────────────────────────────────────────────────────────────────────────
class GameOverScene(Scene):
    W, H = 900, 750

    def __init__(
        self,
        manager:    SceneManager,
        config:     GameConfig,
        winner:     str,
        winner_idx: int = P1,
        screenshot: pygame.Surface | None = None,
    ) -> None:
        super().__init__(manager)
        self.config     = config
        self.winner     = winner
        self.winner_idx = winner_idx
        self.screenshot = screenshot

        pygame.font.init()
        self._font_crown = pygame.font.SysFont("segoeui", 52)
        self._font_h1    = pygame.font.SysFont("segoeui", 36)
        self._font_sub   = pygame.font.SysFont("segoeui", 15)
        self._font_btn   = pygame.font.SysFont("segoeui", 17)

        # Card geometry
        self._cw, self._ch = 340, 310
        self._card_final_y = (self.H - self._ch) // 2
        self._card_x       = (self.W - self._cw) // 2

        # Buttons
        bx = self._card_x + 24
        bw = self._cw - 48
        self._btn_play_again = pygame.Rect(bx, 0, bw, 48)   # y set in draw
        self._btn_main_menu  = pygame.Rect(bx, 0, bw, 40)
        self._hover_play  = False
        self._hover_menu  = False

        # Overlay (built once)
        self._overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._overlay.fill(OVERLAY)

        # Frosted card background (built once from screenshot)
        card_rect = pygame.Rect(self._card_x, self._card_final_y,
                                self._cw, self._ch)
        if screenshot:
            self._frosted_bg = _frosted_crop(screenshot, card_rect)
        else:
            self._frosted_bg = None

        # Animation state
        self._enter_t  = _time.monotonic()    # scene enter time
        self._anim_t   = 0.0                  # seconds since enter

        # Particles
        cx = self.W // 2
        cy = self.H // 2
        self._particles: list[_Particle] = [
            _Particle(cx, cy) for _ in range(60)
        ]

        # Pre-render crown (scaled each frame)
        accent = TEAL if winner_idx == P2 else LAVENDER
        self._crown_base = self._font_crown.render("♛", True, accent)

    # ── Scene interface ───────────────────────────────────────────────────
    def on_enter(self) -> None:
        self._enter_t = _time.monotonic()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_play = self._btn_play_again.collidepoint(event.pos)
            self._hover_menu = self._btn_main_menu.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_play_again.collidepoint(event.pos):
                self._restart()
            elif self._btn_main_menu.collidepoint(event.pos):
                self._go_menu()

    def update(self, dt: float) -> None:
        self._anim_t += dt / 1000.0
        for p in self._particles:
            p.update(dt / 1000.0)
        self._particles = [p for p in self._particles if p.alive]

    def draw(self, screen: pygame.Surface) -> None:
        # Background
        if self.screenshot:
            screen.blit(self.screenshot, (0, 0))
        else:
            screen.fill(BG_MAIN)

        screen.blit(self._overlay, (0, 0))

        # Particles (drawn behind card)
        for p in self._particles:
            p.draw(screen)

        # Slide-in: ease-out cubic
        raw_progress  = min(1.0, self._anim_t / _SLIDE_DURATION)
        eased         = 1 - (1 - raw_progress) ** 3       # cubic ease-out
        card_y        = int(-self._ch + (self._card_final_y + self._ch) * eased)

        self._draw_card(screen, card_y)

    # ── card ─────────────────────────────────────────────────────────────
    def _draw_card(self, screen: pygame.Surface, card_y: int) -> None:
        card = pygame.Rect(self._card_x, card_y, self._cw, self._ch)

        # Frosted background layer
        if self._frosted_bg:
            fb = self._frosted_bg.copy()
            fb.set_alpha(160)
            screen.blit(fb, card.topleft)

        # Card fill
        card_surf = pygame.Surface((self._cw, self._ch), pygame.SRCALPHA)
        card_surf.fill((*BG_CARD, 230))
        screen.blit(card_surf, card.topleft)

        # Glowing border — accent colour for winner
        border_col = TEAL if self.winner_idx == P2 else PURPLE
        pygame.draw.rect(screen, border_col, card, width=1, border_radius=16)
        # Second, dimmer outer ring for depth
        outer = card.inflate(2, 2)
        pygame.draw.rect(screen, (*border_col, 60), outer, width=1, border_radius=17)

        cx = card.centerx
        ty = card.top + 22

        # Animated crown — pulses ±8% scale
        scale  = 1.0 + 0.08 * math.sin(self._anim_t * math.tau / 1.4)
        cw_b, ch_b = self._crown_base.get_size()
        nw, nh = int(cw_b * scale), int(ch_b * scale)
        crown  = pygame.transform.smoothscale(self._crown_base, (nw, nh))
        screen.blit(crown, crown.get_rect(centerx=cx, top=ty))

        # "WINNER" label
        sub = self._font_sub.render("W I N N E R", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, top=ty + 66))

        # Winner name with colour wash
        name_surf = self._font_h1.render(self.winner, True, TEXT_PRI)
        # Tint pass
        tint_col  = TEAL if self.winner_idx == P2 else PURPLE
        tint_surf = self._font_h1.render(self.winner, True, tint_col)
        tint_surf.set_alpha(90)
        name_pos  = name_surf.get_rect(centerx=cx, top=ty + 96)
        screen.blit(name_surf, name_pos)
        screen.blit(tint_surf, name_pos)

        # Divider
        dy = card.top + 200
        pygame.draw.line(screen, BORDER,
                         (card.left + 24, dy), (card.right - 24, dy))

        # Buttons (y relative to card so they animate with it)
        by = card.top + 212
        self._btn_play_again.y = by
        self._btn_main_menu.y  = by + 56

        # Play Again
        r1   = self._btn_play_again
        col1 = PURPLE if self._hover_play else PURPLE_DK
        pygame.draw.rect(screen, col1, r1, border_radius=10)
        lbl1 = self._font_btn.render("Play Again", True, (255, 255, 255))
        screen.blit(lbl1, lbl1.get_rect(center=r1.center))

        # Main Menu
        r2   = self._btn_main_menu
        col2 = (45, 40, 72) if self._hover_menu else BG_CARD
        bc2  = BORDER_A     if self._hover_menu else BORDER
        pygame.draw.rect(screen, col2, r2, border_radius=10)
        pygame.draw.rect(screen, bc2,  r2, width=1, border_radius=10)
        lbl2 = self._font_btn.render("Main Menu", True, TEXT_SEC)
        screen.blit(lbl2, lbl2.get_rect(center=r2.center))

    # ── navigation ────────────────────────────────────────────────────────
    def _restart(self) -> None:
        from src.ui.game_scene import GameScene
        self.manager.switch(GameScene(self.manager, self.config))

    def _go_menu(self) -> None:
        from src.ui.menu_scene import MenuScene
        self.manager.switch(MenuScene(self.manager))