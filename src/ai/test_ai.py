# test_ai.py\

import time
from src.engine.board import Board, P1, P2
from src.engine.rules import apply_pawn_move, apply_wall, is_game_over, get_winner
from src.ai.agent import AIAgent


def run_test_game():
    print("--- QUORIDOR AI TEST ---")

    # 1. Initialize the board and the AI
    board = Board()

    # Let's make the AI play as Player 2 on "Medium" difficulty
    ai = AIAgent(player_id=P2, difficulty="Easy")

    # 2. The Game Loop
    while not is_game_over(board):
        print("\n" + "=" * 30)
        board.pretty_print()
        print("=" * 30)

        if board.current_player == P1:
            print("\n--- HUMAN TURN (P1) ---")
            board.pretty_print()

            # Get input from the terminal
            try:
                move_input = input("Enter your move as 'row col' (e.g., 2 4): ")
                r_inp, c_inp = map(int, move_input.split())
                target = (r_inp, c_inp)

                # The engine already has validation logic in rules.py
                apply_pawn_move(board, P1, target)
                print(f"Human moved to {target}")
            except ValueError as e:
                print(f"Invalid input or illegal move: {e}. Try again.")
                continue  # This keeps the turn on P1 so you can retry

        else:
            print("\n--- AI TURN (P2) ---")
            start_time = time.time()

            # Ask the Agent for the best move
            best_action = ai.get_best_move(board)

            end_time = time.time()
            print(f"AI took {end_time - start_time:.4f} seconds to think.")

            if best_action is None:
                print("AI gave up! No valid moves found.")
                break

            # Apply the AI's chosen move
            print(f"AI chose to: {best_action}")
            if best_action["type"] == "move":
                apply_pawn_move(board, P2, best_action["target"])
            elif best_action["type"] == "wall":
                apply_wall(board, P2, best_action["anchor"], best_action["horizontal"])

    # Game Over
    print("\n" + "=" * 30)
    board.pretty_print()
    winner = get_winner(board)
    print(f"GAME OVER! Winner is Player {winner + 1}")


if __name__ == "__main__":
    run_test_game()