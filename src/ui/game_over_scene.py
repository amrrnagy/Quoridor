# src/ui/game_over_scene.py
from __future__ import annotations
import math
import random
import time as _time
from typing import Optional
import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.ui.game_config import GameConfig
from src.engine.board import P1, P2

BG_MAIN    = ( 18,  17,  26)
BG_CARD    = ( 30,  27,  46)
PURPLE     = (127, 119, 221)
PURPLE_DK  = ( 83,  74, 183)
TEAL       = ( 29, 158, 117)
LAVENDER   = (186, 175, 242)
BORDER     = ( 58,  53,  85)
BORDER_A   = (127, 119, 221)
TEXT_PRI   = (240, 237, 248)
TEXT_SEC   = (122, 117, 144)
TEXT_DIM   = ( 90,  86, 112)
RED_PLAYER = (210,  40,  40)
BLUE_AI    = ( 40,  80, 210)
OVERLAY    = (  8,   7,  18, 210)   

_PARTICLE_PALETTE = [
    (127, 119, 221, 255),  
    ( 29, 158, 117, 255),  
    (239, 159,  39, 255),  
    (186, 175, 242, 255),  
    (255, 255, 255, 210),  
]

_SLIDE_DURATION_S = 0.38    
_GRAVITY_PX_S2    = 300.0   

# ── Procedural Vector Icons ──
def _draw_icon_crown(screen, color, cx, cy, scale=1.0):
    w = 40 * scale
    h = 24 * scale
    pts = [
        (cx - w//2, cy + h//2),
        (cx + w//2, cy + h//2),
        (cx + w//2 + 6*scale, cy - h//2 + 6*scale),
        (cx + w//6, cy),
        (cx, cy - h//2 - 4*scale),
        (cx - w//6, cy),
        (cx - w//2 - 6*scale, cy - h//2 + 6*scale)
    ]
    pygame.draw.polygon(screen, color, pts)
    # Jewels on tips
    pygame.draw.circle(screen, color, (cx - w//2 - 6*scale, cy - h//2 + 6*scale), 5*scale)
    pygame.draw.circle(screen, color, (cx, cy - h//2 - 4*scale), 5*scale)
    pygame.draw.circle(screen, color, (cx + w//2 + 6*scale, cy - h//2 + 6*scale), 5*scale)
    # Inner base cutline
    pygame.draw.line(screen, BG_CARD, (cx - w//2 + 4*scale, cy + h//2 - 5*scale), (cx + w//2 - 4*scale, cy + h//2 - 5*scale), max(1, int(3*scale)))

def _draw_icon_reset(screen, color, cx, cy):
    pygame.draw.arc(screen, color, (cx-6, cy-6, 12, 12), math.radians(45), math.radians(315), 2)
    pygame.draw.polygon(screen, color, [(cx+5, cy-5), (cx+5, cy-10), (cx, cy-5)])

def _draw_icon_home(screen, color, cx, cy):
    pygame.draw.polygon(screen, color, [(cx, cy-6), (cx-6, cy), (cx-4, cy), (cx-4, cy+6), (cx+4, cy+6), (cx+4, cy), (cx+6, cy)], 2)
    pygame.draw.rect(screen, color, (cx-1, cy+2, 3, 4))


class _Particle:
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
    def alive(self) -> bool: return self.life > 0.0

    def draw(self, screen: pygame.Surface) -> None:
        alpha = int(255 * (self.life / self.max_life))
        r, g, b, _ = self.color
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (self.radius, self.radius), self.radius)
        screen.blit(s, (int(self.x) - self.radius, int(self.y) - self.radius))

def _frosted_crop(source: pygame.Surface, rect: pygame.Rect, blur_factor: int = 7) -> pygame.Surface:
    crop = source.subsurface(rect).copy()
    small_w = max(1, rect.w // blur_factor)
    small_h = max(1, rect.h // blur_factor)
    small = pygame.transform.smoothscale(crop, (small_w, small_h))
    return pygame.transform.smoothscale(small, (rect.w, rect.h))


class GameOverScene(Scene):
    W, H = 1000, 750

    def __init__(self, manager: SceneManager, config: GameConfig, winner: str, winner_idx: int = P1, screenshot: Optional[pygame.Surface] = None) -> None:
        super().__init__(manager)
        self.config = config
        self.winner = winner
        self.winner_idx = winner_idx
        self.screenshot = screenshot

        pygame.font.init()
        self._font_h1  = pygame.font.SysFont("segoeui", 32)
        self._font_sub = pygame.font.SysFont("segoeui", 14)
        self._font_btn = pygame.font.SysFont("segoeui", 17)

        self._cw = 360
        self._ch = 330
        self._card_x = (self.W - self._cw) // 2
        self._final_y = (self.H - self._ch) // 2 

        bx = self._card_x + 28
        bw = self._cw - 56
        self._btn_play = pygame.Rect(bx, 0, bw, 50) 
        self._btn_menu = pygame.Rect(bx, 0, bw, 42) 
        self._hover_play, self._hover_menu = False, False

        self._overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._overlay.fill(OVERLAY)

        card_rect = pygame.Rect(self._card_x, self._final_y, self._cw, self._ch)
        if screenshot and screenshot.get_size() == (self.W, self.H):
            safe_rect = card_rect.clip(screenshot.get_rect())
            self._frosted_bg: Optional[pygame.Surface] = (_frosted_crop(screenshot, safe_rect) if safe_rect.size == card_rect.size else None)
        else:
            self._frosted_bg = None

        self._enter_t = _time.monotonic()
        self._anim_t  = 0.0
        self._particles: list[_Particle] = [_Particle(self.W // 2, self.H // 2) for _ in range(70)]

    def on_enter(self) -> None:
        self._enter_t = _time.monotonic()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_play = self._btn_play.collidepoint(event.pos)
            self._hover_menu = self._btn_menu.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): self._restart()
            elif event.key == pygame.K_ESCAPE: self._go_menu()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_play.collidepoint(event.pos): self._restart()
            elif self._btn_menu.collidepoint(event.pos): self._go_menu()

    def update(self, dt: float) -> None:
        dt_s = dt / 1000.0
        self._anim_t += dt_s
        for p in self._particles: p.update(dt_s)
        self._particles = [p for p in self._particles if p.alive]

    def draw(self, screen: pygame.Surface) -> None:
        if self.screenshot: screen.blit(self.screenshot, (0, 0))
        else: screen.fill(BG_MAIN)
        screen.blit(self._overlay, (0, 0))

        for p in self._particles: p.draw(screen)

        raw = min(1.0, self._anim_t / _SLIDE_DURATION_S)
        eased = 1.0 - (1.0 - raw) ** 3
        card_y = int(-self._ch + (self._final_y + self._ch) * eased)
        self._draw_card(screen, card_y)

    def _draw_card(self, screen: pygame.Surface, card_y: int) -> None:
        card = pygame.Rect(self._card_x, card_y, self._cw, self._ch)

        if self._frosted_bg:
            fb = self._frosted_bg.copy()
            fb.set_alpha(150)
            screen.blit(fb, card.topleft)

        fill = pygame.Surface((self._cw, self._ch), pygame.SRCALPHA)
        fill.fill((*BG_CARD, 228))
        screen.blit(fill, card.topleft)

        border_col = TEAL if self.winner_idx == P2 else PURPLE
        pygame.draw.rect(screen, border_col, card, width=1, border_radius=18)
        
        outer = card.inflate(3, 3)
        outer_s = pygame.Surface((outer.w, outer.h), pygame.SRCALPHA)
        pygame.draw.rect(outer_s, (*border_col, 45), (0, 0, outer.w, outer.h), width=2, border_radius=19)
        screen.blit(outer_s, outer.topleft)

        cx, ty = card.centerx, card.top + 24

        # ── Procedural Crown ──
        scale = 1.0 + 0.08 * math.sin(self._anim_t * math.tau / 1.4)
        accent = TEAL if self.winner_idx == P2 else LAVENDER
        _draw_icon_crown(screen, accent, cx, ty + 20, scale)

        sub = self._font_sub.render("W I N N E R", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, top=ty + 70))

        name_surf  = self._font_h1.render(self.winner, True, TEXT_PRI)
        tint_surf  = self._font_h1.render(self.winner, True, accent)
        tint_surf.set_alpha(95)
        name_rect  = name_surf.get_rect(centerx=cx, top=ty + 102)
        screen.blit(name_surf, name_rect)
        screen.blit(tint_surf, name_rect)

        dot_col = RED_PLAYER if self.winner_idx == P1 else BLUE_AI
        pygame.draw.circle(screen, dot_col, (name_rect.left - 14, name_rect.centery), 5)

        div_y = card.top + 216
        pygame.draw.line(screen, BORDER, (card.left + 28, div_y), (card.right - 28, div_y))

        btn_y = div_y + 14
        self._btn_play.y = btn_y
        self._btn_menu.y = btn_y + 60

        self._draw_play_btn(screen, self._btn_play)
        self._draw_menu_btn(screen, self._btn_menu)

    def _draw_play_btn(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        col = PURPLE if self._hover_play else PURPLE_DK
        pygame.draw.rect(screen, col, rect, border_radius=10)
        
        if self._hover_play:
            glow = rect.inflate(4, 4)
            gs = pygame.Surface((glow.w, glow.h), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*PURPLE, 50), (0, 0, glow.w, glow.h), border_radius=12)
            screen.blit(gs, glow.topleft)
            
        lbl = self._font_btn.render("Play Again", True, (255, 255, 255))
        total_w = 16 + 12 + lbl.get_width()
        start_x = rect.x + (rect.w - total_w) // 2
        
        _draw_icon_reset(screen, (255, 255, 255), start_x + 8, rect.centery)
        screen.blit(lbl, (start_x + 28, rect.centery - lbl.get_height() // 2))

    def _draw_menu_btn(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        bg_col = BG_CARD + (0,) if not self._hover_menu else (45, 40, 72)
        brd_col = BORDER_A if self._hover_menu else BORDER
        
        if isinstance(bg_col, tuple) and len(bg_col) == 3:
            pygame.draw.rect(screen, bg_col, rect, border_radius=10)
        else:
            pygame.draw.rect(screen, BG_CARD, rect, border_radius=10)
            
        pygame.draw.rect(screen, brd_col, rect, width=1, border_radius=10)
        lbl = self._font_btn.render("Main Menu", True, TEXT_SEC)
        
        total_w = 16 + 12 + lbl.get_width()
        start_x = rect.x + (rect.w - total_w) // 2
        
        _draw_icon_home(screen, TEXT_SEC, start_x + 8, rect.centery)
        screen.blit(lbl, (start_x + 28, rect.centery - lbl.get_height() // 2))

    def _restart(self) -> None:
        from src.ui.game_scene import GameScene  
        self.manager.switch_fade(GameScene(self.manager, self.config))

    def _go_menu(self) -> None:
        from src.ui.menu_scene import MenuScene 
        self.manager.switch_fade(MenuScene(self.manager))