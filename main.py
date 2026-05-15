# main.py
import pygame
from src.ui.scene_manager import SceneManager
from src.ui.menu_scene import MenuScene


def main() -> None:
    pygame.init()

    WINDOW_TITLE = "Quoridor AI"
    W, H = 900, 750

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(WINDOW_TITLE)

    # Initialize the Scene Manager and push the Main Menu as the first state
    manager = SceneManager(screen)
    manager.push(MenuScene(manager))

    # This will block and run the game loop until the window is closed
    manager.run()

    pygame.quit()


if __name__ == "__main__":
    main()