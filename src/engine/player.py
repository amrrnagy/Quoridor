# src/engine/player.py

"""
Member 2 — Player module (small helper, required by __init__.py)

Defines the Player type and two factory functions:
  make_human(name) → a human player
  make_ai(name)    → an AI player

The board and rules modules use player *indices* (P1=0, P2=1) everywhere,
so this class is lightweight — it just carries metadata used by the UI
and the main game loop.
"""

from dataclasses import dataclass


@dataclass
class Player:
    """
    Represents one participant in the game.

    Attributes:
        name    : display name shown in the UI ("Player 1", "Computer", etc.)
        is_ai   : True if this player is controlled by the AI engine,
                  False if controlled by a human via the UI
        index   : board index — must be P1 (0) or P2 (1) from board.py
    """
    name:   str
    is_ai:  bool
    index:  int


def make_human(name: str, index: int) -> Player:
    """
    Create a human-controlled player.

    Usage:
        from engine.player import make_human
        from engine.board  import P1
        player1 = make_human("Player 1", P1)
    """
    return Player(name=name, is_ai=False, index=index)


def make_ai(name: str, index: int) -> Player:
    """
    Create an AI-controlled player.

    Usage:
        from engine.player import make_ai
        from engine.board  import P2
        computer = make_ai("Computer", P2)
    """
    return Player(name=name, is_ai=True, index=index)