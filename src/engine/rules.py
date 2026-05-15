# src/engine/rules.py
from .board import Board, Position, Wall, BOARD_SIZE, GOAL_ROW, P1, P2
from .pathfinding import both_players_have_path
from typing import List, Optional, Tuple


def get_valid_pawn_moves(board: Board, player: int) -> List[Position]:
    r, c = board.get_position(player)
    opponent = P2 if player == P1 else P1
    opp_pos  = board.get_position(opponent)

    moves: List[Position] = []
    DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for dr, dc in DIRS:
        nr, nc = r + dr, c + dc
        if not board.is_inside(nr, nc):
            continue
        if board.has_wall_between(r, c, nr, nc):
            continue

        if (nr, nc) == opp_pos:
            # if opponent is adjacent, we may be able to jump over them (or diagonally if blocked)
            moves.extend(_jump_moves(board, r, c, dr, dc, opp_pos))
        else:
            # move to the empty cell
            moves.append((nr, nc))

    return moves


def _jump_moves(
    board: Board,
    r: int, c: int,
    dr: int, dc: int,
    opp_pos: Position,
) -> List[Position]:
    or_, oc = opp_pos          # opponent row, col
    jumps: List[Position] = []

    straight_r, straight_c = or_ + dr, oc + dc
    wall_behind = board.has_wall_between(or_, oc, straight_r, straight_c)
    straight_inside = board.is_inside(straight_r, straight_c)

    if straight_inside and not wall_behind:
        jumps.append((straight_r, straight_c))
    else:
        # ─ Diagonal jumps (wall or edge behind opponent)
        # Try the two perpendicular directions relative to the jump axis
        if dr == 0:   # jumping horizontally → diagonals are up/down
            side_dirs = [(-1, 0), (1, 0)]
        else:          # jumping vertically → diagonals are left/right
            side_dirs = [(0, -1), (0, 1)]

        for sdr, sdc in side_dirs:
            diag_r, diag_c = or_ + sdr, oc + sdc
            if board.is_inside(diag_r, diag_c):
                if not board.has_wall_between(or_, oc, diag_r, diag_c):
                    jumps.append((diag_r, diag_c))

    return jumps


def is_valid_pawn_move(board: Board, player: int, target: Position) -> bool:
    return target in get_valid_pawn_moves(board, player)

def is_valid_wall(
    board: Board,
    player: int,
    anchor: Wall,
    horizontal: bool,
) -> bool:
    
    # check that the player has walls left
    if board.walls_left[player] <= 0:
        return False

    ar, ac = anchor

    # check that the wall is within bounds
    if not (0 <= ar <= BOARD_SIZE - 2 and 0 <= ac <= BOARD_SIZE - 2):
        return False

    # Overlap (2 walls of the same orientation cannot share an anchor or be adjacent) and crossing (a horizontal and vertical wall cannot share an anchor)
    if horizontal:
        # Overlaps with adjacent horizontal walls sharing the same row
        if anchor in board.h_walls:
            return False
        if (ar, ac - 1) in board.h_walls:
            return False
        if (ar, ac + 1) in board.h_walls:
            return False
        # Crosses a vertical wall at the same anchor
        if anchor in board.v_walls:
            return False
    else:
        # Overlaps with adjacent vertical walls sharing the same column
        if anchor in board.v_walls:
            return False
        if (ar - 1, ac) in board.v_walls:
            return False
        if (ar + 1, ac) in board.v_walls:
            return False
        # Crosses a horizontal wall at the same anchor
        if anchor in board.h_walls:
            return False

    # Finally, check that the wall doesn't completely block player
    test_board = board.copy()
    if horizontal:
        test_board.h_walls.add(anchor)
    else:
        test_board.v_walls.add(anchor)

    return both_players_have_path(test_board)


def get_valid_walls(
    board: Board,
    player: int,
) -> List[Tuple[Wall, bool]]:
  
    if board.walls_left[player] <= 0:
        return []

    valid = []
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            anchor = (r, c)
            for horizontal in (True, False):
                if is_valid_wall(board, player, anchor, horizontal):
                    valid.append((anchor, horizontal))
    return valid



def apply_pawn_move(board: Board, player: int, target: Position) -> None:
    if not is_valid_pawn_move(board, player, target):
        raise ValueError(
            f"Illegal pawn move: player {player} cannot move to {target}"
        )
    board.move_pawn(player, target)


def apply_wall(
    board: Board,
    player: int,
    anchor: Wall,
    horizontal: bool,
) -> None:
    
    if not is_valid_wall(board, player, anchor, horizontal):
        raise ValueError(
            f"Illegal wall placement: player {player}, anchor={anchor}, "
            f"horizontal={horizontal}"
        )
    board.place_wall(player, anchor, horizontal)


# Return True once a player has reached their goal row
def is_game_over(board: Board) -> bool:
    return board.winner is not None

# Return Winner (None if the game is still ongoing)
def get_winner(board: Board) -> Optional[int]:
    return board.winner

# API to help iterate through legal actions only
def get_all_legal_actions(board: Board) -> List[dict]:
    """
    Return a unified list of legal actions for the current player.
    Each action is a dict:
      {"type": "move",  "target": (r, c)}
      {"type": "wall",  "anchor": (r, c), "horizontal": bool}

    Useful for the AI to iterate over actions in a uniform way.
    """
    player  = board.current_player
    actions = []

    for target in get_valid_pawn_moves(board, player):
        actions.append({"type": "move", "target": target})

    for anchor, horizontal in get_valid_walls(board, player):
        actions.append({"type": "wall", "anchor": anchor, "horizontal": horizontal})

    return actions