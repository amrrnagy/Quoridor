"""
src/ui/game_config.py  —  Grandmaster Edition
==============================================
Immutable-ish data carrier for user-selected settings.

Travels from MenuScene → GameScene → GameOverScene without mutation.
GameScene reads ``mode`` and ``difficulty`` but never writes back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class GameMode(Enum):
    """Which players are in the game."""
    HUMAN_VS_HUMAN = auto()
    HUMAN_VS_AI    = auto()


class Difficulty(Enum):
    """AI search time budget, increasing from EASY → HARD."""
    EASY   = auto()
    MEDIUM = auto()
    HARD   = auto()


# ─────────────────────────────────────────────────────────────────────────────
# Config dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GameConfig:
    """
    Plain data object carrying all user-configurable settings.

    Attributes
    ----------
    mode:
        HUMAN_VS_HUMAN or HUMAN_VS_AI.
    difficulty:
        Only relevant when mode == HUMAN_VS_AI.
        Controls the AI agent's time budget via ``_AI_BUDGETS``.
    """

    mode:       GameMode   = field(default=GameMode.HUMAN_VS_AI)
    difficulty: Difficulty = field(default=Difficulty.MEDIUM)

    # ── computed helpers ───────────────────────────────────────────────────

    @property
    def ai_budget(self) -> float:
        """Return the AI search time-budget (seconds) for the chosen difficulty."""
        return _AI_BUDGETS[self.difficulty]

    @property
    def difficulty_label(self) -> str:
        """Human-readable difficulty string, e.g. ``'Medium'``."""
        return self.difficulty.name.title()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"GameConfig(mode={self.mode.name}, "
            f"difficulty={self.difficulty.name}, "
            f"budget={self.ai_budget}s)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Lookup table – kept here so GameConfig is the single source of truth
# ─────────────────────────────────────────────────────────────────────────────

_AI_BUDGETS: dict[Difficulty, float] = {
    Difficulty.EASY:   0.5,
    Difficulty.MEDIUM: 2.0,
    Difficulty.HARD:   4.5,
}
