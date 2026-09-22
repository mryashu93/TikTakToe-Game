"""
Pure board-logic functions — no Flask, no ORM, no side effects.
"""

WINNING_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # cols
    (0, 4, 8), (2, 4, 6),               # diagonals
]


def check_winner(board: list) -> str | None:
    """Return the winning symbol ('X' or 'O'), or None if no winner yet."""
    for a, b, c in WINNING_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: list) -> bool:
    """Return True if the board is full and there is no winner."""
    return all(cell is not None for cell in board) and check_winner(board) is None


def get_empty_cells(board: list) -> list[int]:
    """Return indices of empty cells."""
    return [i for i, cell in enumerate(board) if cell is None]


def apply_move(board: list, position: int, symbol: str) -> list:
    """Return a NEW board with the move applied (non-mutating)."""
    new_board = board[:]
    new_board[position] = symbol
    return new_board


def get_winning_line(board: list) -> tuple | None:
    """Return the winning (a, b, c) triple, or None."""
    for line in WINNING_LINES:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return line
    return None


def is_valid_move(board: list, position: int) -> bool:
    """Return True if position is in range and the cell is empty."""
    return 0 <= position <= 8 and board[position] is None
