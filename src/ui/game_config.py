# src/ui/game_config.py
from dataclasses import dataclass
from enum import Enum, auto

# carries the user's menu selections from
# MenuScene → GameScene → GameOverScene

class GameMode(Enum):
    HUMAN_VS_HUMAN = auto()
    HUMAN_VS_AI    = auto()


class Difficulty(Enum):
    EASY   = auto()
    MEDIUM = auto()
    HARD   = auto()


@dataclass
class GameConfig:
    mode:       GameMode   = GameMode.HUMAN_VS_AI
    difficulty: Difficulty = Difficulty.MEDIUM