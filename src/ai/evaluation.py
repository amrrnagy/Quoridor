# src/ai/evaluation.py
from ..engine.board import Board, BOARD_SIZE, GOAL_ROW
from ..engine.pathfinding import shortest_path_length

# ── Score constants ────────────────────────────────────────────────────────
WIN_SCORE  =  10_000.0
LOSS_SCORE = -10_000.0

# ── Tunable weights ────────────────────────────────────────────────────────
# Each unit of path-length difference = 1.0 (baseline)
WALL_WEIGHT         = 0.7   # walls are worth more than "slightly nice to have"
TEMPO_WEIGHT        = 0.15  # having more reserve walls = options (small but consistent bonus)
CENTRALISATION_WEIGHT = 0.08  # column 4 is hardest to wall off; columns 0/8 are easiest
PROXIMITY_WEIGHT    = 0.02  # tiny nudge toward goal when everything else ties
END_GAME_MULTIPLIER = 2.0   # path difference is doubled in end-game situations
END_GAME_THRESHOLD  = 2     # opponent steps-to-goal ≤ this → end-game urgency active


def _centralisation(col: int) -> float:
    centre = BOARD_SIZE // 2          # = 4 on a 9×9 board
    return 1.0 - abs(col - centre) / centre

def evaluate_board(board: Board, ai_player: int,
                   use_advanced_heuristic: bool, game_history: list = None) -> float:

    # Returns a score from the AI's perspective.
    # Positive  → AI is winning.
    # Negative  → Opponent is winning.

    opponent = 1 - ai_player

    # ── Terminal states ───────────────────────────────────────────────────
    if board.winner == ai_player:
        return WIN_SCORE
    if board.winner is not None:
        return LOSS_SCORE

    # ── Path lengths ──────────────────────────────────────────────────────
    ai_dist  = shortest_path_length(board, ai_player)
    opp_dist = shortest_path_length(board, opponent)

    if ai_dist  is None: return LOSS_SCORE   # AI is completely blocked
    if opp_dist is None: return WIN_SCORE    # Opponent is completely blocked

    # ── Core race score ───────────────────────────────────────────────────

    # Positive when opponent needs more steps than AI.
    path_diff = float(opp_dist - ai_dist)

    # End-game urgency: amplify the race score when the opponent is close
    if opp_dist <= END_GAME_THRESHOLD:
        path_diff *= END_GAME_MULTIPLIER

    score = path_diff

    # ── Advanced heuristic block (Hard Level) ────────────────────────────
    if use_advanced_heuristic:
        ai_walls  = board.get_walls_left(ai_player)
        opp_walls = board.get_walls_left(opponent)

        # Wall advantage — re-weighted upward
        score += (ai_walls - opp_walls) * WALL_WEIGHT

        # Tempo — just having walls available (option value)
        # Both players' wall counts are normalized to [0,1] relative to
        # the starting count (10 walls each).
        score += (ai_walls - opp_walls) * TEMPO_WEIGHT

        # Tie-breaking positional sub-scores
        if abs(path_diff) < 1.5:
            ai_pos = board.get_position(ai_player)
            opp_pos = board.get_position(opponent)

            # Centralisation: prefer central columns
            central_bonus = (
                            _centralisation(ai_pos[1]) - _centralisation(opp_pos[1])
                            ) * CENTRALISATION_WEIGHT
            score += central_bonus

            # Proximity to own goal: tiny forward-progress nudge
            ai_goal_dist = abs(ai_pos[0] - GOAL_ROW[ai_player])
            opp_goal_dist = abs(opp_pos[0] - GOAL_ROW[opponent])
            proximity_bonus = (opp_goal_dist - ai_goal_dist) * PROXIMITY_WEIGHT
            score += proximity_bonus

            # Asymmetric Tie-Breaker
            score += (ai_pos[1] * 0.0001)

    # THE LOOP KILLER: Position History Penalty
    if game_history:
        ai_pos = board.get_position(ai_player)
        occurrences = game_history.count(ai_pos)
        if occurrences > 0:
            score -= (5.0 * occurrences)

    return score