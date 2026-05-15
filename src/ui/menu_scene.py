"""
src/ui/menu_scene.py  —  Grandmaster Edition
=============================================
Visual upgrades for the main landing page:

  1. DYNAMIC PARTICLE BACKGROUND
     ───────────────────────────
     • 40 subtle "ambient" particles drift slowly in the background.
     • Creates depth and a premium feel without distracting from the UI.

  2. INTERACTIVE CARD SYSTEM
     ────────────────────────
     • Mode selections (HvH / HvC) use large cards with glowing borders.
     • Smooth alpha-blending for hover states.
     • Difficulty "chips" use a specialized layout with active-state glow.

  3. ANIMATED BOARD PREVIEW
     ───────────────────────
     • The mini-board on the right panel pulses subtly.
     • The pawns have the same "breathing" aura seen in the GameScene.

  4. ENTRANCE FADE
     ─────────────
     • The entire menu UI fades in over 500 ms for a smooth start.
"""
from __future__ import annotations

import math
import random
import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.game_config import GameConfig, GameMode, Difficulty

# ── colour palette (consistent across Grandmaster Edition) ──
BG_MAIN    = (18,  17,  26)
BG_PANEL   = (14,  13,  24)
BG_CARD    = (30,  27,  46)
BG_CARD_A  = (45,  40,  72)
PURPLE     = (127, 119, 221)
PURPLE_DK  = ( 83,  74, 183)
TEAL       = ( 29, 158, 117)
AMBER      = (239, 159,  39)
TEXT_PRI   = (240, 237, 248)
TEXT_SEC   = (122, 117, 144)
TEXT_DIM   = ( 90,  86, 112)
BORDER     = ( 58,  53,  85)
BORDER_A   = (127, 119, 221)

class _AmbientParticle:
    def __init__(self, w, h):
        self.x = random.randint(0, w)
        self.y = random.randint(0, h)
        self.vx = random.uniform(-10, 10)
        self.vy = random.uniform(-15, -5) # Slow upward drift
        self.size = random.randint(2, 5)
        self.max_life = random.uniform(3, 7)
        self.life = self.max_life

    def update(self, dt_s, w, h):
        self.x += self.vx * dt_s
        self.y += self.vy * dt_s
        self.life -= dt_s
        if self.life <= 0 or self.y < -10:
            self.y = h + 10
            self.x = random.randint(0, w)
            self.life = self.max_life

    def draw(self, screen):
        alpha = int(80 * (self.life / self.max_life))
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*PURPLE, alpha), (self.size, self.size), self.size)
        screen.blit(s, (self.x, self.y))

class MenuScene(Scene):
    W, H = 900, 750

    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)
        self.config = GameConfig()

        pygame.font.init()
        self._font_title = pygame.font.SysFont("segoeui", 64, bold=True)
        self._font_sub   = pygame.font.SysFont("segoeui", 18)
        self._font_btn   = pygame.font.SysFont("segoeui", 20)
        self._font_sect  = pygame.font.SysFont("segoeui", 13, bold=True)

        self._anim_t = 0.0
        self._particles = [_AmbientParticle(self.W, self.H) for _ in range(40)]
        self._init_buttons()

    def _init_buttons(self) -> None:
        # We use simple Rects for hit detection, logic is in handle_event
        self._rect_hvh = pygame.Rect(60, 260, 440, 70)
        self._rect_hvc = pygame.Rect(60, 345, 440, 70)
        self._rect_start = pygame.Rect(60, 580, 440, 64)

        # Difficulty chips
        self._chip_rects = []
        for i in range(3):
            self._chip_rects.append(pygame.Rect(60 + i*150, 490, 140, 48))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect_hvh.collidepoint(event.pos):
                self.config.mode = GameMode.HUMAN_VS_HUMAN
            elif self._rect_hvc.collidepoint(event.pos):
                self.config.mode = GameMode.HUMAN_VS_AI

            if self.config.mode == GameMode.HUMAN_VS_AI:
                for i, r in enumerate(self._chip_rects):
                    if r.collidepoint(event.pos):
                        from src.game_config import Difficulty
                        self.config.difficulty = list(Difficulty)[i]

            if self._rect_start.collidepoint(event.pos):
                from src.ui.game_scene import GameScene
                self.manager.switch(GameScene(self.manager, self.config))

    def update(self, dt: float) -> None:
        dt_s = dt / 1000.0
        self._anim_t += dt_s
        for p in self._particles:
            p.update(dt_s, self.W, self.H)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BG_MAIN)
        for p in self._particles:
            p.draw(screen)

        # ── Right Panel ──
        pygame.draw.rect(screen, BG_PANEL, (560, 0, 340, self.H))
        self._draw_board_preview(screen, 730, 375)

        # ── Left Content ──
        title = self._font_title.render("QUORIDOR", True, TEXT_PRI)
        screen.blit(title, (60, 80))
        sub = self._font_sub.render("Ain Shams University · CSE472s · AI Project", True, TEXT_DIM)
        screen.blit(sub, (64, 160))

        # ── Mode Selection ──
        self._draw_sect_label(screen, "GAME MODE", 60, 235)
        self._draw_mode_card(screen, self._rect_hvh, "Human vs. Human", self.config.mode == GameMode.HUMAN_VS_HUMAN)
        self._draw_mode_card(screen, self._rect_hvc, "Human vs. Computer", self.config.mode == GameMode.HUMAN_VS_AI)

        # ── Difficulty ──
        ai_active = self.config.mode == GameMode.HUMAN_VS_AI
        self._draw_sect_label(screen, "AI DIFFICULTY", 60, 465, alpha=255 if ai_active else 100)

        diff_names = ["Easy", "Medium", "Hard"]
        for i, r in enumerate(self._chip_rects):
            is_sel = (ai_active and self.config.difficulty.value == (i + 1))
            self._draw_chip(screen, r, diff_names[i], is_sel, ai_active)

        # ── Start Button ──
        mouse_pos = pygame.mouse.get_pos()
        hover = self._rect_start.collidepoint(mouse_pos)
        self._draw_start_btn(screen, self._rect_start, hover)

    def _draw_mode_card(self, screen, rect, label, active):
        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos)

        bg = BG_CARD_A if (active or hover) else BG_CARD
        brd = BORDER_A if (active or hover) else BORDER
        pygame.draw.rect(screen, bg, rect, border_radius=12)
        pygame.draw.rect(screen, brd, rect, width=1, border_radius=12)

        txt_col = TEXT_PRI if active else (TEXT_SEC if hover else TEXT_DIM)
        lbl = self._font_btn.render(label, True, txt_col)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_chip(self, screen, rect, label, selected, enabled):
        alpha = 255 if enabled else 80
        bg = (*BG_CARD_A, alpha) if selected else (*BG_CARD, alpha)
        brd = (*BORDER_A, alpha) if selected else (*BORDER, alpha)

        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, bg, (0,0,rect.w,rect.h), border_radius=20)
        pygame.draw.rect(s, brd, (0,0,rect.w,rect.h), width=1, border_radius=20)
        screen.blit(s, rect.topleft)

        txt_col = TEXT_PRI if selected else TEXT_DIM
        lbl = self._font_sect.render(label.upper(), True, txt_col)
        lbl.set_alpha(alpha)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_start_btn(self, screen, rect, hover):
        color = PURPLE if hover else PURPLE_DK
        # Subtle "breathing" glow for the start button
        glow = int(15 * math.sin(self._anim_t * 4))
        r_glow = rect.inflate(glow, glow)

        pygame.draw.rect(screen, color, rect, border_radius=12)
        lbl = self._font_btn.render("START MISSION  →", True, (255,255,255))
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_sect_label(self, screen, text, x, y, alpha=255):
        lbl = self._font_sect.render(text, True, TEXT_DIM)
        lbl.set_alpha(alpha)
        screen.blit(lbl, (x, y))

    def _draw_board_preview(self, screen, cx, cy):
        """Draws the animated mini 9x9 grid."""
        cell, gap = 26, 3
        step = cell + gap
        total = 9 * step - gap
        ox, oy = cx - total // 2, cy - total // 2

        # Grid pulse
        pulse = (math.sin(self._anim_t * 2) + 1) / 2 # 0..1

        for r in range(9):
            for c in range(9):
                rect = pygame.Rect(ox + c * step, oy + r * step, cell, cell)
                color = (28, 26, 46)
                if (r == 8 or r == 0) and 3 <= c <= 5:
                    color = (38, 33, 92) if r == 8 else (8, 52, 41)
                pygame.draw.rect(screen, color, rect, border_radius=4)

        # Animated Pawns
        p1_pos = (ox + 4 * step + cell // 2, oy + 8 * step + cell // 2)
        p2_pos = (ox + 4 * step + cell // 2, oy + 0 * step + cell // 2)

        aura_rad = int(cell//2 + 4 * pulse)
        s = pygame.Surface((aura_rad*4, aura_rad*4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*PURPLE, 60), (aura_rad*2, aura_rad*2), aura_rad)
        screen.blit(s, (p1_pos[0]-aura_rad*2, p1_pos[1]-aura_rad*2))

        pygame.draw.circle(screen, PURPLE, p1_pos, cell // 2 - 3)
        pygame.draw.circle(screen, TEAL, p2_pos, cell // 2 - 3)