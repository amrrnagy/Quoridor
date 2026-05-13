# ♟️ Quoridor AI
 
**Course:** CSE472s - Artificial Intelligence
**Semester:** Spring 2026
**Department:** Computer and Systems Engineering Department
**Institution:** Ain Shams University - Faculty of Engineering, Specialized Programs
 
---
 
## 👥 Team Members
 
| # | Name | Student ID |
|---|------|------------|
| 1 |Amr Ahmed Nagy |2300162|
| 2 |Mohamed Ashraf Mohamed |2300475|
| 3 |Omar Ahmed Morshed|2300131|
| 4 |Ali Ahmed Ayman |2300346|
| 5 |Mohamed EHab Abdelbary|2300570|
 
---
 
## 📖 Project Description
 
Quoridor AI is a complete implementation of the abstract strategy board game **Quoridor**, originally invented by Mirko Marchesi (1997) and winner of the Mensa Mind Game award. The game is played on a 9×9 board where two players race to move their pawn to the opposite side while strategically placing walls to block their opponent. This project implements the full ruleset, a graphical user interface, and an AI opponent powered by the Minimax algorithm with Alpha-Beta pruning.
 
---
 
## ✨ Implemented Features
 
1. **Full Quoridor Ruleset:** Complete 2-player implementation including orthogonal pawn movement, wall placement, jump-over mechanics, and diagonal fallback moves.
2. **Wall Validation:** Walls cannot overlap, cross, or completely block a player's path — enforced via a pathfinding check on every placement attempt.
3. **Human vs. Human Mode:** Two players can play locally on the same machine.
4. **Human vs. Computer Mode:** Play against an AI opponent.
5. **AI Opponent:** A computer opponent that evaluates future game states and selects optimal moves.
6. **Valid Move Highlighting:** Legal moves are highlighted on the board to guide the player.
7. **Game State Visualization:** The board, pawns, walls, turn indicator, and wall counts are all displayed in real time.
8. **Winner Announcement & Game Reset:** The game detects win conditions and allows the player to restart.
---
 
## 🤖 AI Algorithm
 
The computer opponent uses the **Minimax algorithm with Alpha-Beta Pruning**:
 
- **Minimax** builds a game tree of possible future moves, assuming both players play optimally. The AI maximizes its own advantage while minimizing the opponent's.
- **Alpha-Beta Pruning** cuts off branches of the game tree that cannot influence the final decision, significantly reducing computation time and allowing a deeper search depth.
- **Heuristic Evaluation** uses the difference in shortest path lengths (via BFS/Dijkstra) between the two players as the board evaluation score — the AI favors positions where its path to the goal is shorter than the opponent's.
---
 
## 🏗️ Architecture & Design
 
The project is separated into three clean layers:
 
| Layer | Responsibility |
|---|---|
| **Game Logic** | Board state, move validation, wall placement, win detection |
| **AI Engine** | Minimax tree search, Alpha-Beta pruning, heuristic evaluation |
| **GUI / Presentation** | Board rendering, user input, game state display |
 
This separation ensures the AI and game logic can be tested independently of the interface.
 
---
 

 
## 🎮 Controls
 
| Action | Control |
|---|---|
| Move pawn | Click a highlighted square |
| Place wall | Click between two squares on the board edge |
| Reset game | Click the **Reset** button |
 
---
 
## 📥 How to Get the Project
 
Clone the repository using Git:
 
```bash
git clone https://github.com/amrrnagy/Quoridor_AI.git
cd Quoridor_AI
```
 
Or download it directly from GitHub:
[https://github.com/amrrnagy/Quoridor_AI](https://github.com/amrrnagy/Quoridor_AI)
 
---
 
## 🚀 How to Compile and Run
 
To compile and execute the game from the terminal, ensure you have a standard C++ compiler (like `g++`) and Qt6 installed.
 
1. **Navigate to the project directory:**
   ```bash
   cd Quoridor_AI
   ```
 
2. **Configure and build with CMake:**
   ```bash
   mkdir build && cd build
   cmake ..
   cmake --build . --parallel
   ```
 

 
---
 
## 🎬 Demo Video
 

 
---
 
## 🤖 AI Usage Declaration
 
In accordance with the course guidelines, we transparently declare our use of AI tools throughout this project.
 
### Tools Used
- **Claude ** — used for brainstorming architecture, improving documentation, and structuring the README.
- **Gemini ** — used for learning concepts related to Minimax, Alpha-Beta pruning, and pathfinding algorithms.
### What AI Was Used For
- Brainstorming the overall architecture and separation of concerns between game logic, AI, and GUI.
- Learning and clarifying AI concepts (Minimax depth limits, heuristic design, Alpha-Beta pruning efficiency).
- Debugging logic errors in wall validation and pathfinding.
- Improving the structure and wording of this README .
### What Was Modified or Rejected
- AI-suggested Minimax implementations were reviewed and rewritten to fit our specific board representation and heuristic scoring function.
- Some suggested heuristics (e.g., pure distance-to-goal) were replaced after testing showed they caused poor AI decisions near walls — we added a wall-count factor to the evaluation.
- README and report sections generated by AI were edited to reflect our actual implementation accurately.
### Example Where AI Output Was Not Fully Correct
When we asked an AI tool to generate the wall placement validation logic, it produced a check that only prevented walls from overlapping but did not verify that a valid path still existed for both players after placement. This is a core rule of Quoridor. We identified the gap ourselves, understood why the path-blocking check is necessary (a player must always have a route to their goal), and implemented a BFS-based reachability check that runs after every attempted wall placement.
 
### What the Group Understood and Implemented Themselves
The complete game ruleset, board representation, pathfinding, Minimax search tree, Alpha-Beta pruning, GUI rendering, and all integration between layers were designed, written, and debugged by the group. AI tools were used strictly as a learning and productivity aid — every line of submitted code was read, understood, and verified by a team member before inclusion.
 
---
 
*Computer and Systems Engineering Department — Ain Shams University — Spring 2026*
