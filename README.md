Quoridor: AI Board Game Implementation
CSE472s: Artificial Intelligence Course – Spring 2026
Ain Shams University - Faculty of Engineering

📖 Game Description
Quoridor is an award-winning abstract strategy board game invented by Mirko Marchesi. Played on a 9x9 grid, the objective is to be the first player to move your pawn to any square on the opposite base line.

On each turn, players must choose to either:

Move their pawn one step orthogonally.

Place a two-square-long wall to block their opponent's path.

The Catch: Walls cannot be placed to completely block a player from reaching their goal. A valid path must always exist.

✨ Features
Game Modes: Play Human vs. Human locally, or test your skills in Human vs. Computer mode.

Intelligent AI Opponent: The computer opponent is powered by a Minimax algorithm with Alpha-Beta Pruning, evaluating board states using custom pathfinding heuristics.

Interactive GUI: Built natively with PyQt6, featuring responsive click-to-move mechanics, valid move highlighting, turn indicators, and real-time wall counters.

Robust Game Engine: Strictly enforces all official rules, including orthogonal movement, pawn jumping mechanics, and wall collision detection.

Real-time Pathfinding: Automatically validates wall placements using Breadth-First Search (BFS) to prevent illegal trap placements.

📂 Project Structure
Plaintext
├── src/
│   ├── ai/               # Minimax algorithm and heuristic evaluations
│   ├── engine/           # Core game logic, state management, and rules validation
│   ├── ui/               # PyQt6 interface, board views, and window management
│   └── main.py           # Application entry point
├── .gitignore            # Excludes IDE metadata (e.g., .qtcreator, cmake-build)
└── README.md
📸 Screenshots
Main Menu: [Insert screenshot here]

Active Gameplay: [Insert screenshot showing valid move dots and wall placement]

End Game / Win Screen: [Insert screenshot here]


Bash
python src/main.py
🎮 Controls
Movement: Click on a highlighted adjacent square to move your pawn. If adjacent to an opponent, clicking the square behind them will execute a jump.

Wall Placement: Click on the edges or intersections between squares to place a horizontal or vertical wall.

Game Reset: Click the "Restart Game" button in the side control panel to clear the board and reset wall counts.

🎥 Demo Video
Watch the 3-5 minute Gameplay Demo Here (Insert YouTube/Drive Link)



[Team Member 6 Name] (ID: [Number])

Developed as the final term project for CSE472s.
