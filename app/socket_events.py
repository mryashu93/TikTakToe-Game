"""
Socket.IO event handlers for real-time PvP.

Room state is kept in-memory (dict). For production, swap to a Redis
store with flask_socketio's message_queue option.
"""

import random
import string
from datetime import datetime

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from .extensions import socketio, db
from .game_logic import check_winner, is_draw, apply_move, is_valid_move
from .models import Game, Move

# {room_code: {board, players: {sid: symbol}, turn: symbol, game_id: int|None}}
_rooms: dict = {}


def _gen_code(length=5) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


@socketio.on("connect")
def on_connect():
    pass  # no-op; auth handled per event


@socketio.on("create_room")
def on_create_room(data):
    if not current_user.is_authenticated:
        emit("error", {"message": "Login required"})
        return

    code = _gen_code()
    while code in _rooms:
        code = _gen_code()

    _rooms[code] = {
        "board": [None] * 9,
        "players": {request.sid: "X"},
        "usernames": {request.sid: current_user.username},
        "turn": "X",
        "game_id": None,
        "result": None,
    }
    join_room(code)
    emit("room_created", {"room_code": code, "symbol": "X"})


@socketio.on("join_room_pvp")
def on_join_room(data):
    if not current_user.is_authenticated:
        emit("error", {"message": "Login required"})
        return

    code = data.get("room_code", "").strip().upper()
    room = _rooms.get(code)

    if not room:
        emit("error", {"message": "Room not found"})
        return

    if len(room["players"]) >= 2:
        emit("error", {"message": "Room is full"})
        return

    if request.sid in room["players"]:
        emit("error", {"message": "Already in room"})
        return

    room["players"][request.sid] = "O"
    room["usernames"][request.sid] = current_user.username
    join_room(code)

    # Create a game record for player X (first joiner)
    x_sid = next(sid for sid, sym in room["players"].items() if sym == "X")
    # We'll attribute the game to the X player
    # (For simplicity, both players share one game record)
    emit("room_joined", {"room_code": code, "symbol": "O"}, to=request.sid)

    usernames = list(room["usernames"].values())
    emit("game_start", {
        "board": room["board"],
        "turn": room["turn"],
        "players": {sym: name for sid, sym in room["players"].items()
                    for name in [room["usernames"][sid]]},
    }, to=code)


@socketio.on("pvp_move")
def on_pvp_move(data):
    code = data.get("room_code", "").strip().upper()
    position = data.get("position")
    room = _rooms.get(code)

    if not room or request.sid not in room["players"]:
        emit("error", {"message": "Invalid room"})
        return

    if room["result"]:
        emit("error", {"message": "Game already over"})
        return

    player_symbol = room["players"][request.sid]
    if room["turn"] != player_symbol:
        emit("error", {"message": "Not your turn"})
        return

    board = room["board"]
    if not is_valid_move(board, position):
        emit("error", {"message": "Invalid move"})
        return

    board = apply_move(board, position, player_symbol)
    room["board"] = board
    room["turn"] = "O" if player_symbol == "X" else "X"

    winner = check_winner(board)
    game_over = False
    result = None

    if winner:
        result = winner  # 'X' or 'O'
        game_over = True
        room["result"] = result
    elif is_draw(board):
        result = "draw"
        game_over = True
        room["result"] = result

    emit("board_update", {
        "board": board,
        "last_move": position,
        "turn": room["turn"],
        "game_over": game_over,
        "result": result,
        "winner_symbol": winner if winner else None,
    }, to=code)

    if game_over:
        _rooms.pop(code, None)


@socketio.on("disconnect")
def on_disconnect():
    # Notify opponent if still in a room
    for code, room in list(_rooms.items()):
        if request.sid in room["players"]:
            leave_room(code)
            emit("opponent_disconnected", {}, to=code)
            _rooms.pop(code, None)
            break
