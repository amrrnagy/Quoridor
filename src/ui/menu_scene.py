"""
src/ui/menu_scene.py  —  Grandmaster Edition
"""
from __future__ import annotations
import math
import random
import time as _time
import pygame

from src.ui.scene_manager import Scene, SceneManager
from src.ui.game_config import GameConfig, GameMode, Difficulty

# ── colour palette ──
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
        self.vy = random.uniform(-15, -5)
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


class _TextBox:
    """Interactive text input box for player names."""
    def __init__(self, rect, default_text=""):
        self.rect = rect
        self.text = default_text
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            elif len(self.text) < 14 and event.unicode.isprintable():
                self.text += event.unicode

    def draw(self, screen, font):
        bg = BG_CARD_A if self.active else BG_CARD
        brd = BORDER_A if self.active else BORDER
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, brd, self.rect, width=1, border_radius=8)

        # Blinking cursor effect
        cursor = "|" if self.active and int(_time.time() * 2) % 2 == 0 else ""
        txt_surf = font.render(self.text + cursor, True, TEXT_PRI)
        screen.blit(txt_surf, (self.rect.x + 16, self.rect.centery - txt_surf.get_height() // 2))


class MenuScene(Scene):
    W, H = 1000, 750

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

        # Interactive Text Boxes (This was missing!)
        self._tb_p1 = _TextBox(pygame.Rect(60, 445, 200, 44), "You")
        self._tb_p2 = _TextBox(pygame.Rect(280, 445, 200, 44), "Player 2")

        self._init_buttons()

    def _init_buttons(self) -> None:
        self._rect_hvh = pygame.Rect(60, 250, 440, 64)
        self._rect_hvc = pygame.Rect(60, 326, 440, 64)
        self._rect_start = pygame.Rect(60, 620, 440, 60)

        # Difficulty chips
        self._chip_rects = []
        for i in range(3):
            self._chip_rects.append(pygame.Rect(60 + i*146, 545, 136, 44))

    def handle_event(self, event: pygame.event.Event) -> None:
        # Route events to the text boxes so you can type
        self._tb_p1.handle_event(event)
        self._tb_p2.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect_hvh.collidepoint(event.pos):
                self.config.mode = GameMode.HUMAN_VS_HUMAN
            elif self._rect_hvc.collidepoint(event.pos):
                self.config.mode = GameMode.HUMAN_VS_AI

            if self.config.mode == GameMode.HUMAN_VS_AI:
                for i, r in enumerate(self._chip_rects):
                    if r.collidepoint(event.pos):
                        self.config.difficulty = list(Difficulty)[i]

            if self._rect_start.collidepoint(event.pos):
                # Save the names into the config before leaving
                self.config.p1_name = self._tb_p1.text.strip() or "You"
                self.config.p2_name = self._tb_p2.text.strip() or "Player 2"

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
        right_w = 400
        right_x = self.W - right_w
        pygame.draw.rect(screen, BG_PANEL, (right_x, 0, right_w, self.H))
        pygame.draw.line(screen, BORDER, (right_x, 0), (right_x, self.H))
        self._draw_board_preview(screen, right_x + (right_w // 2), self.H // 2)

        # ── Left Content ──
        title = self._font_title.render("QUORIDOR", True, TEXT_PRI)
        screen.blit(title, (60, 80))
        sub = self._font_sub.render("CSE472s · AI Project", True, TEXT_DIM)
        screen.blit(sub, (64, 160))

        # ── Mode Selection ──
        self._draw_sect_label(screen, "GAME MODE", 60, 225)
        self._draw_mode_card(screen, self._rect_hvh, "Human vs. Human", self.config.mode == GameMode.HUMAN_VS_HUMAN)
        self._draw_mode_card(screen, self._rect_hvc, "Human vs. Computer", self.config.mode == GameMode.HUMAN_VS_AI)

        # ── Names & Difficulty ──
        ai_active = self.config.mode == GameMode.HUMAN_VS_AI

        if not ai_active:
            self._draw_sect_label(screen, "PLAYER 1 NAME", 60, 420)
            self._tb_p1.draw(screen, self._font_btn)
            self._draw_sect_label(screen, "PLAYER 2 NAME", 280, 420)
            self._tb_p2.draw(screen, self._font_btn)
        else:
            self._draw_sect_label(screen, "YOUR NAME", 60, 420)
            self._tb_p1.draw(screen, self._font_btn)
            self._draw_sect_label(screen, "OPPONENT", 60, 520)

            # Pure UI display names (Engine still safely uses 1, 2, 3 internally)
            diff_names = ["Easy (Ashraf)", "Medium (Yahia)", "Hard (Amr)"]
            for i, r in enumerate(self._chip_rects):
                is_sel = (self.config.difficulty.value == (i + 1))
                self._draw_chip(screen, r, diff_names[i], is_sel)

        # ── Start Button ──
        hover = self._rect_start.collidepoint(pygame.mouse.get_pos())
        self._draw_start_btn(screen, self._rect_start, hover)

    def _draw_mode_card(self, screen, rect, label, active):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        bg = BG_CARD_A if (active or hover) else BG_CARD
        brd = BORDER_A if (active or hover) else BORDER
        pygame.draw.rect(screen, bg, rect, border_radius=12)
        pygame.draw.rect(screen, brd, rect, width=1, border_radius=12)

        txt_col = TEXT_PRI if active else (TEXT_SEC if hover else TEXT_DIM)
        lbl = self._font_btn.render(label, True, txt_col)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_chip(self, screen, rect, label, selected):
        bg = BG_CARD_A if selected else BG_CARD
        brd = BORDER_A if selected else BORDER

        pygame.draw.rect(screen, bg, rect, border_radius=20)
        pygame.draw.rect(screen, brd, rect, width=1, border_radius=20)

        txt_col = TEXT_PRI if selected else TEXT_DIM
        lbl = self._font_sect.render(label.upper(), True, txt_col)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_start_btn(self, screen, rect, hover):
        color = PURPLE if hover else PURPLE_DK
        pygame.draw.rect(screen, color, rect, border_radius=12)
        lbl = self._font_btn.render("START →", True, (255,255,255))
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_sect_label(self, screen, text, x, y, alpha=255):
        lbl = self._font_sect.render(text, True, TEXT_DIM)
        lbl.set_alpha(alpha)
        screen.blit(lbl, (x, y))

    def _draw_board_preview(self, screen, cx, cy):
        """Draws the animated mini 9x9 grid, matching the real board UI."""
        cell, wall = 30, 8
        step = cell + wall
        total_size = 9 * cell + 8 * wall
        ox, oy = cx - total_size // 2, cy - total_size // 2

        _BG_GUTTER, _CELL_IDLE, _CELL_BORDER = (12, 11, 20), (28, 25, 44), (38, 34, 60)
        _WALL_COLOR, _SPEC_WHITE = (239, 159, 39), (255, 255, 255)
        _P1_COLOR, _P2_COLOR = (210, 40, 40), (40, 80, 210)

        gutter = pygame.Rect(ox - 3, oy - 3, total_size + 6, total_size + 6)
        pygame.draw.rect(screen, _BG_GUTTER, gutter, border_radius=8)

        frame = pygame.Rect(ox - 12, oy - 12, total_size + 24, total_size + 24)
        pygame.draw.rect(screen, _CELL_BORDER, frame, width=2, border_radius=12)

        for r in range(9):
            for c in range(9):
                rect = pygame.Rect(ox + c * step, oy + r * step, cell, cell)
                pygame.draw.rect(screen, _CELL_IDLE, rect, border_radius=4)
                pygame.draw.rect(screen, _CELL_BORDER, rect, width=1, border_radius=4)

        for r, c in [(6, 3)]:
            wr = pygame.Rect(ox + c * step, oy + (r + 1) * step - wall, cell * 2 + wall, wall)
            pygame.draw.rect(screen, _WALL_COLOR, wr, border_radius=3)
        for r, c in [(2, 2)]:
            wr = pygame.Rect(ox + (c + 1) * step - wall, oy + r * step, wall, cell * 2 + wall)
            pygame.draw.rect(screen, _WALL_COLOR, wr, border_radius=3)

        pulse = (math.sin(self._anim_t * 2) + 1) / 2
        aura_r, pr = int(cell // 2 + 3 + 5 * pulse), cell // 3

        for centre, col in (((ox + 4 * step + cell // 2, oy + 7 * step + cell // 2), _P1_COLOR),
                            ((ox + 4 * step + cell // 2, oy + 1 * step + cell // 2), _P2_COLOR)):
            s = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, int(40 + 60 * pulse)), (aura_r, aura_r), aura_r)
            screen.blit(s, (centre[0] - aura_r, centre[1] - aura_r))
            pygame.draw.circle(screen, col, centre, pr)
            pygame.draw.circle(screen, _SPEC_WHITE, centre, max(2, pr // 4))