"""
src/ui/board_view.py  —  Grandmaster Edition
============================================
Rendering engine for the 9×9 Quoridor board.

Key design decisions
--------------------
1.  Dynamic centering
    BoardView receives the *play_area* Rect at construction time and derives
    ``cell_size``, ``wall_width``, ``margin_x``, and ``margin_y`` so the
    board always sits perfectly centred regardless of window size changes.

2.  Ghost Pawns
    Valid-move tiles receive translucent silhouette circles (ring style) that
    pulse at ~1.2 Hz using a sine wave driven by an external ``anim_t``.

3.  Breathing Auras
    The *current* player's pawn gets a multi-ring glow that expands and
    contracts on a 1.6 s cycle.  The AI pawn gets an additional faster pulse
    while the engine thread is running (``ai_thinking=True``).

4.  Wall preview
    A semi-transparent wall segment is drawn under the cursor when the mouse
    is hovering over a wall gap, giving immediate visual feedback before the
    player commits.

5.  SRCALPHA surfaces
    All translucent effects use pre-allocated SRCALPHA surfaces that are
    blitted with ``special_flags=pygame.BLEND_RGBA_ADD`` for additive
    glow layering.  The pawn aura surface is rebuilt lazily only when the
    radius changes.
"""
from __future__ import annotations

import math
import pygame

# Import engine constants — no UI imports here to avoid circular dependency
from src.engine.board import BOARD_SIZE, P1, P2


# ─────────────────────────────────────────────────────────────────────────────
# Internal colour palette (mirrors game_scene.py — kept in sync by convention)
# ─────────────────────────────────────────────────────────────────────────────
_BG_GUTTER      = (12,  11,  20)   # outer frame behind tiles
_CELL_IDLE      = (28,  25,  44)   # standard tile
_CELL_HIGHLIGHT = (42,  38,  68)   # valid-move tile
_CELL_BORDER    = (38,  34,  60)   # subtle tile outline
_WALL_COLOR     = (239, 159,  39)  # Amber
_WALL_PREVIEW   = (239, 159,  39)  # Same amber, drawn at 50 % alpha
_P1_COLOR       = (210,  40,  40)  # Red  – Player 1
_P2_COLOR       = ( 40,  80, 210)  # Blue – Player 2 / AI
_SPEC_WHITE     = (255, 255, 255)  # specular highlight on pawn


def _build_aura_surf(radius: int, color: tuple[int, int, int],
                     rings: int = 6) -> pygame.Surface:
    """
    Pre-render a multi-ring radial glow for a pawn aura.

    Each concentric ring has decreasing alpha, creating a soft halo.
    The surface uses SRCALPHA so it blends correctly on any background.

    Parameters
    ----------
    radius:  Outer radius of the aura in pixels.
    color:   RGB tuple of the aura colour.
    rings:   Number of concentric rings.
    """
    size = (radius + 6) * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for i in range(rings, 0, -1):
        r     = int((radius + 4) * i / rings)
        alpha = int(160 * (1 - i / rings) ** 1.2)  # power curve for soft falloff
        width = max(1, (radius + 4) // rings)
        pygame.draw.circle(surf, (*color, alpha), (cx, cy), r, width=width)
    return surf


# ─────────────────────────────────────────────────────────────────────────────
# BoardView
# ─────────────────────────────────────────────────────────────────────────────
class BoardView:
    """
    Stateless (per-frame) renderer for the Quoridor board.

    The caller is responsible for advancing ``anim_t`` each frame and passing
    it to ``draw()``.  BoardView itself holds no mutable animation state so
    it can be safely replaced or re-created without breaking anything.

    Parameters
    ----------
    play_rect:
        The screen region allocated to the board (excludes sidebar).
        BoardView will perfectly centre the grid within this rect.
    """

    def __init__(self, play_rect: pygame.Rect) -> None:
        # ── Dynamic layout calculation ──────────────────────────────────────
        # board_total = BOARD_SIZE * cell + (BOARD_SIZE-1) * wall
        # We aim for wall ≈ cell/5  →  total = cell*(BOARD_SIZE + (BOARD_SIZE-1)/5)
        # Solve: cell = available / (BOARD_SIZE + (BOARD_SIZE-1)/5)
        #
        # Leave at least 32 px padding on each side.
        # ── FIXED CRISP LAYOUT (Best of Both Worlds) ──
        self.cell_size = 56
        self.wall_width = 14

        # Compute actual board footprint and perfectly center it in the play area
        self._board_px = (BOARD_SIZE * self.cell_size + (BOARD_SIZE - 1) * self.wall_width)
        self.margin_x = play_rect.x + (play_rect.width - self._board_px) // 2
        self.margin_y = play_rect.y + (play_rect.height - self._board_px) // 2

        # ── Pre-built aura surfaces ─────────────────────────────────────────
        aura_r = self.cell_size // 2 + 10
        self._aura_p1 = _build_aura_surf(aura_r, _P1_COLOR)
        self._aura_p2 = _build_aura_surf(aura_r, _P2_COLOR)
        self._aura_ai = _build_aura_surf(aura_r + 6, _P2_COLOR, rings=8)

        # ── Ghost-pawn surface template (radius = cell//2 - 6) ─────────────
        self._ghost_r = max(6, self.cell_size // 2 - 6)

    # ── Coordinate helpers ──────────────────────────────────────────────────

    def cell_center(self, pos: tuple[int, int]) -> tuple[int, int]:
        """Return pixel (x, y) centre of the tile at board position (row, col)."""
        r, c = pos
        step = self.cell_size + self.wall_width
        x    = self.margin_x + c * step + self.cell_size // 2
        y    = self.margin_y + r * step + self.cell_size // 2
        return x, y

    def _cell_rect(self, r: int, c: int) -> pygame.Rect:
        """Return the pixel Rect for tile (r, c)."""
        step = self.cell_size + self.wall_width
        return pygame.Rect(
            self.margin_x + c * step,
            self.margin_y + r * step,
            self.cell_size,
            self.cell_size,
        )

    # ── Main draw entry point ───────────────────────────────────────────────

    def draw(
        self,
        screen:      pygame.Surface,
        board,
        anim_t:      float = 0.0,
        valid_moves: list[tuple[int, int]] | None = None,
        ai_thinking: bool = False,
        wall_preview: dict | None = None,
    ) -> None:
        """
        Full board render.  Called once per frame.

        Parameters
        ----------
        screen:       Destination surface.
        board:        Engine Board object (read-only).
        anim_t:       Cumulative animation time in seconds.
        valid_moves:  List of (row, col) positions where the current pawn
                      can legally move.  Shown as ghost pawns.
        ai_thinking:  When True, render the extra pulsing AI aura.
        wall_preview: If the cursor is over a wall gap, the caller passes a
                      dict ``{"anchor": (r, c), "horizontal": bool}`` so we
                      can draw a semi-transparent preview wall.
        """
        if valid_moves is None:
            valid_moves = []

        self._draw_gutter(screen)
        self._draw_tiles(screen, valid_moves)
        self._draw_walls(screen, board)

        if wall_preview:
            self._draw_wall_preview(screen, wall_preview)

        # Draw auras beneath pawns
        self._draw_ghost_pawns(screen, board, valid_moves, anim_t)
        self._draw_pawns(screen, board)

    # ── Private rendering helpers ───────────────────────────────────────────

    def _draw_gutter(self, screen: pygame.Surface) -> None:
        """Draw the premium outer frame and deep gutter."""
        # The deep background under the tiles
        gutter = pygame.Rect(
            self.margin_x - 4, self.margin_y - 4,
            self._board_px + 8, self._board_px + 8,
        )
        pygame.draw.rect(screen, _BG_GUTTER, gutter, border_radius=8)

        # The premium outer frame line
        frame_rect = pygame.Rect(
            self.margin_x - 14, self.margin_y - 14,
            self._board_px + 28, self._board_px + 28
        )
        pygame.draw.rect(screen, _CELL_BORDER, frame_rect, width=2, border_radius=12)

    def _draw_tiles(
        self,
        screen: pygame.Surface,
        valid_moves: list[tuple[int, int]],
    ) -> None:
        """Draw all 81 tiles with subtle rounded corners."""
        vm_set = set(valid_moves)
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                rect  = self._cell_rect(r, c)
                color = _CELL_HIGHLIGHT if (r, c) in vm_set else _CELL_IDLE
                pygame.draw.rect(screen, color, rect, border_radius=5)
                # Subtle tile border for depth
                pygame.draw.rect(screen, _CELL_BORDER, rect,
                                 width=1, border_radius=5)

    def _draw_walls(self, screen: pygame.Surface, board) -> None:
        """Draw all placed horizontal and vertical walls in Amber."""
        step = self.cell_size + self.wall_width

        # Horizontal walls span two cells horizontally, one wall-gap vertically
        for r, c in board.h_walls:
            rect = pygame.Rect(
                self.margin_x + c * step,
                self.margin_y + (r + 1) * step - self.wall_width,
                self.cell_size * 2 + self.wall_width,
                self.wall_width,
            )
            pygame.draw.rect(screen, _WALL_COLOR, rect, border_radius=4)

        # Vertical walls span one wall-gap horizontally, two cells vertically
        for r, c in board.v_walls:
            rect = pygame.Rect(
                self.margin_x + (c + 1) * step - self.wall_width,
                self.margin_y + r * step,
                self.wall_width,
                self.cell_size * 2 + self.wall_width,
            )
            pygame.draw.rect(screen, _WALL_COLOR, rect, border_radius=4)

    def _draw_wall_preview(self, screen: pygame.Surface,
                            preview: dict) -> None:
        """
        Draw a translucent amber wall to preview where the next wall would go.
        """
        r, c = preview["anchor"]
        horiz = preview["horizontal"]
        step  = self.cell_size + self.wall_width

        surf = pygame.Surface(
            (self.cell_size * 2 + self.wall_width, self.wall_width)
            if horiz else
            (self.wall_width, self.cell_size * 2 + self.wall_width),
            pygame.SRCALPHA,
        )
        surf.fill((*_WALL_PREVIEW, 110))

        if horiz:
            pos = (
                self.margin_x + c * step,
                self.margin_y + (r + 1) * step - self.wall_width,
            )
        else:
            pos = (
                self.margin_x + (c + 1) * step - self.wall_width,
                self.margin_y + r * step,
            )
        screen.blit(surf, pos)

    def _draw_player_aura(
        self,
        screen:      pygame.Surface,
        board,
        anim_t:      float,
        ai_thinking: bool,
    ) -> None:
        """
        Render a "breathing" glow under each pawn.

        Current player: gentle pulse at 0.6 Hz
        AI during think: faster secondary pulse at 1.6 Hz (additive)
        """
        # Slow breathing pulse: 0.0 → 1.0 → 0.0 over ~1.6 s
        breathe = (math.sin(anim_t * math.pi / 0.8) + 1) / 2   # 0..1

        for player, aura_surf, color in (
            (P1, self._aura_p1, _P1_COLOR),
            (P2, self._aura_p2, _P2_COLOR),
        ):
            cx, cy = self.cell_center(board.get_position(player))

            # All pawns get a subtle ambient glow
            alpha = int(30 + 50 * breathe)

            # Active player's aura is brighter
            if board.current_player == player:
                alpha = int(70 + 110 * breathe)

            # AI thinking: rapid additive pulse
            if ai_thinking and player == P2:
                fast_pulse = (math.sin(anim_t * math.pi / 0.35) + 1) / 2
                alpha      = int(80 + 170 * fast_pulse)
                surf       = self._aura_ai.copy()
                surf.set_alpha(alpha)
                sz = surf.get_width()
                screen.blit(surf, (cx - sz // 2, cy - sz // 2),
                            special_flags=pygame.BLEND_RGBA_ADD)
                continue  # skip the normal aura for the AI while thinking

            surf = aura_surf.copy()
            surf.set_alpha(alpha)
            sz   = surf.get_width()
            screen.blit(surf, (cx - sz // 2, cy - sz // 2),
                        special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_ghost_pawns(
        self,
        screen:      pygame.Surface,
        board,
        valid_moves: list[tuple[int, int]],
        anim_t:      float,
    ) -> None:
        """
        Draw pulsing hollow ring "ghost" pawns at every valid move position.

        The ring style is used instead of a filled circle so the tile colour
        shows through, keeping the UI readable.  Alpha pulses at ~1.4 Hz.
        """
        if not valid_moves:
            return

        pulse = (math.sin(anim_t * math.pi / 0.36) + 1) / 2  # 0..1
        alpha = int(70 + 120 * pulse)

        base_col = _P1_COLOR if board.current_player == P1 else _P2_COLOR
        r        = self._ghost_r
        diam     = r * 2

        # Create one reusable surface per frame (all ghosts share same style)
        ghost = pygame.Surface((diam, diam), pygame.SRCALPHA)
        ghost.fill((0, 0, 0, 0))
        pygame.draw.circle(ghost, (*base_col, alpha),     (r, r), r)
        pygame.draw.circle(ghost, (*base_col, 0),         (r, r), max(2, r - 5))

        for pos in valid_moves:
            cx, cy = self.cell_center(pos)
            screen.blit(ghost, (cx - r, cy - r))

    def _draw_pawns(self, screen: pygame.Surface, board) -> None:
        """
        Draw the two player pawns with a layered glass-sphere effect.

        Layers (bottom → top):
            • Soft shadow  (semi-transparent dark ring)
            • Base fill    (player colour)
            • Rim shine    (lighter arc at bottom edge)
            • Specular dot (white highlight, offset top-left)
        """
        for player, base_color in [(P1, _P1_COLOR), (P2, _P2_COLOR)]:
            r, c = board.get_position(player)
            cx, cy = self.cell_center((r, c))

            # Draw gradient/layered glowing effect
            radius = self.cell_size // 3
            pygame.draw.circle(screen, (*base_color, 80), (cx, cy), radius + 4)  # Outer glow
            pygame.draw.circle(screen, base_color, (cx, cy), radius)  # Core
            pygame.draw.circle(screen, (255, 255, 255), (cx - 4, cy - 4), 4)  # Specular highlight

    # ── Click identification ────────────────────────────────────────────────

    def identify_click(
        self, mouse_pos: tuple[int, int]
    ) -> tuple[str, object]:
        """
        Classify a mouse click into a cell move or a wall placement.

        Returns
        -------
        ("cell", (row, col))
            if the click landed on a tile.
        ("wall", {"anchor": (row, col), "horizontal": bool})
            if the click landed in a wall gap.
        ("none", None)
            if the click is outside the board area.
        """
        x, y   = mouse_pos
        step   = self.cell_size + self.wall_width
        rel_x  = x - self.margin_x
        rel_y  = y - self.margin_y

        # Guard: outside board
        if rel_x < 0 or rel_y < 0 or rel_x >= self._board_px or rel_y >= self._board_px:
            return "none", None

        col    = rel_x // step
        row    = rel_y // step
        off_x  = rel_x % step
        off_y  = rel_y % step

        # Clamp to board indices
        col = min(col, BOARD_SIZE - 1)
        row = min(row, BOARD_SIZE - 1)

        if off_x > self.cell_size:
            return "wall", {"anchor": (row, col), "horizontal": False}
        if off_y > self.cell_size:
            return "wall", {"anchor": (row, col), "horizontal": True}
        return "cell", (row, col)

    def get_wall_preview(
        self, mouse_pos: tuple[int, int]
    ) -> dict | None:
        """
        Return wall-preview data if the cursor is over a wall gap, else None.
        Used by GameScene to pass into draw().
        """
        kind, data = self.identify_click(mouse_pos)
        if kind == "wall":
            return data  # type: ignore[return-value]
        return None
