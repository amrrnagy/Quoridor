from dataclasses import dataclass, field
from typing import Set, Tuple, Optional


Position = Tuple[int, int]   
Wall     = Tuple[int, int]   


BOARD_SIZE    = 9
WALLS_PER_PLAYER = 10

# Player indices
P1 = 0   
P2 = 1   

START_POSITIONS = {
    P1: (0, 4),   # top-center
    P2: (8, 4),   # bottom-center
}

GOAL_ROW = {
    P1: 8,
    P2: 0,
}


@dataclass
class Board:

    # Pawn positions
    positions: dict = field(default_factory=lambda: dict(START_POSITIONS))

    # Walls on the board
    h_walls: Set[Wall] = field(default_factory=set)   # horizontal
    v_walls: Set[Wall] = field(default_factory=set)   # vertical

    # Remaining wall counts
    walls_left: dict = field(default_factory=lambda: {P1: WALLS_PER_PLAYER,
                                                       P2: WALLS_PER_PLAYER})

    # Whose turn is it?
    current_player: int = P1

    # Winner (None until the game ends)
    winner: Optional[int] = None

# Helper methods for querying the board state
    def get_position(self, player: int) -> Position:
        return self.positions[player]

    def get_walls_left(self, player: int) -> int:
        return self.walls_left[player]

    def is_inside(self, row: int, col: int) -> bool:
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def is_occupied(self, row: int, col: int) -> bool:
        return (row, col) in self.positions.values()

    def get_player_at(self, row: int, col: int):
        for player, pos in self.positions.items():
            if pos == (row, col):
                return player
        return None


    def has_wall_between(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        dr = r2 - r1
        dc = c2 - c1

        if dr == 1 and dc == 0:
            # Moving DOWN (r1 → r1+1): blocked by h_wall at (r1, c1) or (r1, c1-1)
            return (r1, c1) in self.h_walls or (r1, c1 - 1) in self.h_walls

        if dr == -1 and dc == 0:
            # Moving UP (r1 → r1-1): blocked by h_wall at (r1-1, c1) or (r1-1, c1-1)
            return (r1 - 1, c1) in self.h_walls or (r1 - 1, c1 - 1) in self.h_walls

        if dr == 0 and dc == 1:
            # Moving RIGHT (c1 → c1+1): blocked by v_wall at (r1, c1) or (r1-1, c1)
            return (r1, c1) in self.v_walls or (r1 - 1, c1) in self.v_walls

        if dr == 0 and dc == -1:
            # Moving LEFT (c1 → c1-1): blocked by v_wall at (r1, c1-1) or (r1-1, c1-1)
            return (r1, c1 - 1) in self.v_walls or (r1 - 1, c1 - 1) in self.v_walls

        raise ValueError(f"Cells ({r1},{c1}) and ({r2},{c2}) are not adjacent")

    def move_pawn(self, player: int, target: Position) -> None:
        self.positions[player] = target
        self._check_winner(player, target)
        self._advance_turn()

    def place_wall(self, player: int, anchor: Wall, horizontal: bool) -> None:
        if horizontal:
            self.h_walls.add(anchor)
        else:
            self.v_walls.add(anchor)
        self.walls_left[player] -= 1
        self._advance_turn()

    def _advance_turn(self) -> None:
        if self.winner is None:
            self.current_player = P2 if self.current_player == P1 else P1

    def _check_winner(self, player: int, pos: Position) -> None:
        if pos[0] == GOAL_ROW[player]:
            self.winner = player

#will be checked when ai module is implemented
    def copy(self) -> "Board":
        """Return a deep copy (useful for AI look-ahead)."""
        import copy
        return copy.deepcopy(self)
    

# helper methods for visualization 
    def __repr__(self) -> str:
        p1 = self.positions[P1]
        p2 = self.positions[P2]
        return (
            f"Board(P1={p1} walls={self.walls_left[P1]}, "
            f"P2={p2} walls={self.walls_left[P2]}, "
            f"h_walls={len(self.h_walls)}, v_walls={len(self.v_walls)}, "
            f"turn=P{self.current_player + 1})"
        )


# method to print the board in terminal for testing before GUI
    def pretty_print(self) -> None:
        """ASCII render — handy for debugging in a terminal."""
        # Column header
        print("   " + " ".join(str(c) for c in range(BOARD_SIZE)))
        for r in range(BOARD_SIZE):
            row_str = f"{r}  "
            for c in range(BOARD_SIZE):
                if self.positions[P1] == (r, c):
                    row_str += "1"
                elif self.positions[P2] == (r, c):
                    row_str += "2"
                else:
                    row_str += "."

                # Vertical wall to the right?
                if c < BOARD_SIZE - 1:
                    if self.has_wall_between(r, c, r, c + 1):
                        row_str += "|"
                    else:
                        row_str += " "
            print(row_str)

            # Horizontal walls below this row
            if r < BOARD_SIZE - 1:
                wall_str = "   "
                for c in range(BOARD_SIZE):
                    if self.has_wall_between(r, c, r + 1, c):
                        wall_str += "-"
                    else:
                        wall_str += " "
                    if c < BOARD_SIZE - 1:
                        wall_str += " "
                print(wall_str)
                
