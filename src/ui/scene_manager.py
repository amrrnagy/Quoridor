"""
src/ui/scene_manager.py
-----------------------
Scene Manager pattern for Pygame.

Usage in main.py
----------------
    from src.ui.scene_manager import SceneManager
    from src.ui.menu_scene    import MenuScene

    manager = SceneManager(screen)
    manager.push(MenuScene(manager))
    manager.run()
"""
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.game_config import GameConfig


# ─────────────────────────────────────────────
# Base Scene  (all scenes inherit from this)
# ─────────────────────────────────────────────
class Scene:
    """
    Every scene gets a reference to the manager so it can
    call manager.switch(NextScene(...)) to navigate.
    """
    def __init__(self, manager: SceneManager) -> None:
        self.manager = manager

    # Called once when this scene becomes active
    def on_enter(self) -> None:
        pass

    # Called once when this scene is replaced
    def on_exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        """dt = milliseconds since last frame."""
        raise NotImplementedError

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError


# ─────────────────────────────────────────────
# Scene Manager
# ─────────────────────────────────────────────
class SceneManager:
    """
    Owns the Pygame clock and the active scene.

    One scene is active at a time.  Scenes call
    self.manager.switch(new_scene) to transition.
    """
    TARGET_FPS = 60

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen  = screen
        self.clock   = pygame.time.Clock()
        self._scene: Scene | None = None
        self._running = False

    # ── navigation ────────────────────────────
    def push(self, scene: Scene) -> None:
        """Set the very first scene (call once before run())."""
        self._scene = scene
        scene.on_enter()

    def switch(self, scene: Scene) -> None:
        """Replace the current scene with a new one."""
        if self._scene:
            self._scene.on_exit()
        self._scene = scene
        scene.on_enter()

    def quit(self) -> None:
        self._running = False

    # ── main loop ─────────────────────────────
    def run(self) -> None:
        self._running = True
        while self._running:
            dt = self.clock.tick(self.TARGET_FPS)   # ms

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif self._scene:
                    self._scene.handle_event(event)

            if self._scene:
                self._scene.update(dt)
                self._scene.draw(self.screen)

            pygame.display.flip()
