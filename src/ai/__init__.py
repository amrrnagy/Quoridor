# ai/__init__.py

from .agent import AIAgent
from .evaluation import evaluate_board
from .minimax import minimax

# The __all__ list defines the public API of this package.
# It tells Python exactly what gets imported if someone runs: from ai import *
__all__ = [
    "AIAgent",
    "evaluate_board",
    "minimax",
]