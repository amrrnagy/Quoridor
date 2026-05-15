"""
src/game_config.py
------------------
A plain dataclass that carries the user's menu selections from
MenuScene → GameScene → GameOverScene.  No Pygame dependency.
"""
from dataclasses import dataclass
from enum import Enum, auto


class GameMode(Enum):
    HUMAN_VS_HUMAN = auto()
    HUMAN_VS_AI    = auto()


class Difficulty(Enum):
    EASY   = 1   # minimax depth 1
    MEDIUM = 2   # minimax depth 2
    HARD   = 3   # minimax depth 3


@dataclass
class GameConfig:
    mode:       GameMode  = GameMode.HUMAN_VS_AI
    difficulty: Difficulty = Difficulty.MEDIUM

    @property
    def ai_depth(self) -> int:
        return self.difficulty.value
