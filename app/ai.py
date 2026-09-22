"""
AI engines for all three difficulty levels.

All public functions accept a board (list of 9 items, each None | 'X' | 'O')
and the AI's symbol, and return the chosen cell index (0–8).
"""

import random

from django.conf import settings

from .game_logic import (
    check_winner,
    get_empty_cells,
    apply_move,
    is_draw,
)


# ---------------------------------------------------------------------------
# Easy AI — fully random
# ---------------------------------------------------------------------------

def easy_move(board: list, ai_symbol: str) -> int:
    """Pick a random empty cell."""
    return random.choice(get_empty_cells(board))


# ---------------------------------------------------------------------------
# Medium AI — heuristic + tunable randomness
# ---------------------------------------------------------------------------

def _opponent(symbol: str) -> str:
    return "O" if symbol == "X" else "X"


def _find_winning_move(board: list, symbol: str) -> int | None:
    """Return the index that gives `symbol` an immediate win, or None."""
    for pos in get_empty_cells(board):
        if check_winner(apply_move(board, pos, symbol)):
            return pos
    return None


def medium_move(board: list, ai_symbol: str, skill: float | None = None) -> int:
    """
    With probability `skill` (default: Config.MEDIUM_AI_SKILL) play the
    "smart" heuristic move; otherwise play randomly.

    Heuristic priority:
      1. Win immediately if possible.
      2. Block the opponent's immediate win.
      3. Otherwise play randomly.
    """
    if skill is None:
        skill = getattr(settings, "MEDIUM_AI_SKILL", 0.7)

    if random.random() < skill:
        # Try to win
        move = _find_winning_move(board, ai_symbol)
        if move is not None:
            return move
        # Try to block
        move = _find_winning_move(board, _opponent(ai_symbol))
        if move is not None:
            return move

    # Fall back to random
    return random.choice(get_empty_cells(board))


# ---------------------------------------------------------------------------
# Hard AI — perfect play via Minimax with alpha-beta pruning
# ---------------------------------------------------------------------------

def _minimax(board: list, ai_symbol: str, human_symbol: str,
             is_maximizing: bool, alpha: float, beta: float) -> int:
    winner = check_winner(board)
    if winner == ai_symbol:
        return 10
    if winner == human_symbol:
        return -10
    if is_draw(board):
        return 0

    empty = get_empty_cells(board)

    if is_maximizing:
        best = -1000
        for pos in empty:
            score = _minimax(
                apply_move(board, pos, ai_symbol),
                ai_symbol, human_symbol, False, alpha, beta
            )
            best = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 1000
        for pos in empty:
            score = _minimax(
                apply_move(board, pos, human_symbol),
                ai_symbol, human_symbol, True, alpha, beta
            )
            best = min(best, score)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def hard_move(board: list, ai_symbol: str) -> int:
    """Return the optimal move index via Minimax with alpha-beta pruning."""
    human_symbol = _opponent(ai_symbol)
    best_score = -1000
    best_pos = None

    for pos in get_empty_cells(board):
        score = _minimax(
            apply_move(board, pos, ai_symbol),
            ai_symbol, human_symbol, False, -1000, 1000
        )
        if score > best_score:
            best_score = score
            best_pos = pos

    return best_pos


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def get_ai_move(board: list, ai_symbol: str, level: str) -> int:
    """Route to the correct AI engine based on `level`."""
    level = level.lower()
    if level == "easy":
        return easy_move(board, ai_symbol)
    elif level == "medium":
        return medium_move(board, ai_symbol)
    elif level == "hard":
        return hard_move(board, ai_symbol)
    else:
        raise ValueError(f"Unknown AI level: {level!r}")
