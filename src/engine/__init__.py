"""
engine/__init__.py
------------------
Public interface for the Quoridor game engine.
Import from here rather than from individual modules.
"""

from .board       import Board, P1, P2, BOARD_SIZE, WALLS_PER_PLAYER, GOAL_ROW
from .player      import Player, make_human, make_ai
from .pathfinding import (
    has_path,
    both_players_have_path,
    shortest_path_length,
    get_full_path,
)
from .rules       import (
    get_valid_pawn_moves,
    is_valid_pawn_move,
    is_valid_wall,
    get_valid_walls,
    apply_pawn_move,
    apply_wall,
    is_game_over,
    get_winner,
    get_all_legal_actions,
)

__all__ = [
    # board
    "Board", "P1", "P2", "BOARD_SIZE", "WALLS_PER_PLAYER", "GOAL_ROW",
    # player
    "Player", "make_human", "make_ai",
    # pathfinding
    "has_path", "both_players_have_path", "shortest_path_length", "get_full_path",
    # rules
    "get_valid_pawn_moves", "is_valid_pawn_move",
    "is_valid_wall", "get_valid_walls",
    "apply_pawn_move", "apply_wall",
    "is_game_over", "get_winner",
    "get_all_legal_actions",
]