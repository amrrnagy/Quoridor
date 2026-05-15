#src/ui/scene_manager.py
"""
================================================
Scene Manager + Fade Transition engine.

Usage in main.py
----------------
    from src.ui.scene_manager import SceneManager
    from src.ui.menu_scene    import MenuScene

    manager = SceneManager(screen)
    manager.push(MenuScene(manager))
    manager.run()

Architecture
------------
    SceneManager owns the Pygame clock, the currently active Scene, and an
    optional FadeTransition layer that is drawn on top of everything.  Scenes
    communicate with the manager through two public methods:

        manager.switch(new_scene)           – instant swap
        manager.switch_fade(new_scene)      – cross-fade (~400 ms)

    The FadeTransition drives a two-phase fade:
        Phase 1  FADE_OUT  – alpha 0 → 255  (current scene dims to black)
        Phase 2  FADE_IN   – alpha 255 → 0  (next scene reveals from black)

    The actual scene swap happens at the boundary between Phase 1 and Phase 2,
    so the new scene is never rendered while the screen is still partially
    showing the old scene.
"""
from __future__ import annotations

import pygame
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass  # forward-reference guard


# ─────────────────────────────────────────────────────────────────────────────
# Base Scene  (all scenes inherit from this)
# ─────────────────────────────────────────────────────────────────────────────
class Scene:
    """
    Abstract base class for all scenes.

    Every concrete scene receives a reference to the SceneManager so it can
    request navigation via ``self.manager.switch_fade(NextScene(...))``.
    """

    def __init__(self, manager: "SceneManager") -> None:
        self.manager = manager

    # ── lifecycle hooks ────────────────────────────────────────────────────

    def on_enter(self) -> None:
        """Called once, immediately after this scene becomes active."""

    def on_exit(self) -> None:
        """Called once, just before this scene is replaced."""

    # ── per-frame interface ────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a single Pygame event (keyboard, mouse, etc.)."""
        raise NotImplementedError(f"{type(self).__name__} must implement handle_event")

    def update(self, dt: float) -> None:
        """Advance game-state by ``dt`` **milliseconds**."""
        raise NotImplementedError(f"{type(self).__name__} must implement update")

    def draw(self, screen: pygame.Surface) -> None:
        """Render everything onto *screen* for this frame."""
        raise NotImplementedError(f"{type(self).__name__} must implement draw")


# ─────────────────────────────────────────────────────────────────────────────
# Fade Transition
# ─────────────────────────────────────────────────────────────────────────────
class _FadeTransition:
    """
    Two-phase cross-fade between scenes.

    State machine:
        IDLE  →  FADE_OUT  →  (scene swap)  →  FADE_IN  →  IDLE
    """

    _DURATION_MS = 220   # ms for each phase (total round-trip = 440 ms)
    _COLOR       = (0, 0, 0)

    # Internal states
    _IDLE     = 0
    _FADE_OUT = 1
    _FADE_IN  = 2

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self._overlay = pygame.Surface((screen_w, screen_h))
        self._overlay.fill(self._COLOR)

        self._state    = self._IDLE
        self._elapsed  = 0.0          # ms since phase start
        self._pending: Optional[Scene] = None  # scene waiting for swap

    @property
    def active(self) -> bool:
        """True while a transition is in progress."""
        return self._state != self._IDLE

    def start(self, next_scene: Scene) -> None:
        """Begin a fade-out / swap / fade-in sequence."""
        self._pending = next_scene
        self._state   = self._FADE_OUT
        self._elapsed = 0.0

    def update(self, dt: float) -> Optional[Scene]:
        """
        Advance the transition.

        Returns the scene to swap to when the mid-point is reached, else None.
        """
        if self._state == self._IDLE:
            return None

        self._elapsed += dt
        swap_target: Optional[Scene] = None

        if self._state == self._FADE_OUT:
            if self._elapsed >= self._DURATION_MS:
                # Mid-point: trigger the actual scene swap
                swap_target   = self._pending
                self._state   = self._FADE_IN
                self._elapsed = 0.0

        elif self._state == self._FADE_IN:
            if self._elapsed >= self._DURATION_MS:
                self._state  = self._IDLE
                self._elapsed = 0.0

        return swap_target

    def draw(self, screen: pygame.Surface) -> None:
        """Blit the black overlay at the appropriate alpha."""
        if self._state == self._IDLE:
            return

        if self._state == self._FADE_OUT:
            t = min(1.0, self._elapsed / self._DURATION_MS)
        else:  # FADE_IN
            t = 1.0 - min(1.0, self._elapsed / self._DURATION_MS)

        alpha = int(255 * t)
        self._overlay.set_alpha(alpha)
        screen.blit(self._overlay, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Scene Manager
# ─────────────────────────────────────────────────────────────────────────────
class SceneManager:
    """
    Owns the Pygame clock, the active scene, and the fade-transition layer.

    Public navigation API
    ─────────────────────
    push(scene)          – set the very first scene (call once before run())
    switch(scene)        – instant scene swap (no animation)
    switch_fade(scene)   – smooth alpha cross-fade swap
    quit()               – signal the main loop to exit
    """

    TARGET_FPS = 60

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen  = screen
        self.clock   = pygame.time.Clock()

        w, h = screen.get_size()
        self._fade   = _FadeTransition(w, h)
        self._scene: Optional[Scene]  = None
        self._running = False

    # ── navigation ─────────────────────────────────────────────────────────

    def push(self, scene: Scene) -> None:
        """Set the initial scene.  Must be called before ``run()``."""
        self._scene = scene
        scene.on_enter()

    def switch(self, scene: Scene) -> None:
        """Instantly swap to *scene* (no animation)."""
        if self._scene:
            self._scene.on_exit()
        self._scene = scene
        scene.on_enter()

    def switch_fade(self, scene: Scene) -> None:
        """
        Swap to *scene* through a smooth black cross-fade.

        If a transition is already in progress the request is silently
        ignored to prevent a race condition.
        """
        if not self._fade.active:
            self._fade.start(scene)

    def quit(self) -> None:
        """Signal the main loop to exit cleanly after the current frame."""
        self._running = False

    # ── main loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Blocking main-loop.  Runs at up to TARGET_FPS frames per second.

        Frame order:
            1. Collect and dispatch Pygame events (blocked during transitions)
            2. Update active scene
            3. Draw active scene
            4. Advance & draw transition overlay (drawn last, on top)
            5. pygame.display.flip()
        """
        self._running = True

        while self._running:
            dt = self.clock.tick(self.TARGET_FPS)  # actual ms this frame

            # ── events ────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif self._scene and not self._fade.active:
                    # Block scene input during transitions to avoid spurious clicks
                    self._scene.handle_event(event)

            # ── update ────────────────────────────────────────────────────
            if self._scene:
                self._scene.update(dt)

            # Advance transition; get pending scene swap at mid-point
            swap = self._fade.update(dt)
            if swap is not None:
                # Perform the actual swap at the blackest frame
                if self._scene:
                    self._scene.on_exit()
                self._scene = swap
                swap.on_enter()

            # ── draw ──────────────────────────────────────────────────────
            if self._scene:
                self._scene.draw(self.screen)

            # Transition overlay rendered on top of everything
            self._fade.draw(self.screen)

            pygame.display.flip()
