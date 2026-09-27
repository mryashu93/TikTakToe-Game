"""
Django Channels WebSocket consumer for real-time PvP.
Replaces the old Flask-SocketIO socket_events.py.
"""

import json
import random
import string

from channels.generic.websocket import AsyncWebsocketConsumer

from .game_logic import check_winner, is_draw, apply_move, is_valid_move

# In-memory room store: {room_code: {board, players, usernames, turn, result}}
_rooms: dict = {}


def _gen_code(length=5) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class PvPConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_code = None
        if self.scope["user"].is_authenticated:
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.room_code and self.room_code in _rooms:
            room = _rooms[self.room_code]
            if self.channel_name in room["players"]:
                # Notify opponent
                await self.channel_layer.group_send(
                    self.room_code,
                    {"type": "pvp_event", "data": {"type": "opponent_disconnected"}},
                )
                del room["players"][self.channel_name]
                if not room["players"]:
                    _rooms.pop(self.room_code, None)
            await self.channel_layer.group_discard(self.room_code, self.channel_name)

    async def receive(self, text_data):
        try:
            msg = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = msg.get("type")

        if action == "create_room":
            await self.handle_create_room()

        elif action == "join_room":
            await self.handle_join_room(msg.get("room_code", ""))

        elif action == "pvp_move":
            await self.handle_move(msg.get("position"))

    # ------------------------------------------------------------------ #
    #  Handlers
    # ------------------------------------------------------------------ #

    async def handle_create_room(self):
        # Generate unique code
        code = _gen_code()
        while code in _rooms:
            code = _gen_code()

        user = self.scope["user"]
        _rooms[code] = {
            "board": [None] * 9,
            "players": {self.channel_name: "X"},
            "usernames": {self.channel_name: user.username},
            "turn": "X",
            "result": None,
        }
        self.room_code = code
        await self.channel_layer.group_add(code, self.channel_name)
        await self.send_json({"type": "room_created", "room_code": code, "symbol": "X"})

    async def handle_join_room(self, code):
        code = code.strip().upper()
        room = _rooms.get(code)

        if not room:
            await self.send_json({"type": "error", "message": "Room not found"})
            return

        if len(room["players"]) >= 2:
            await self.send_json({"type": "error", "message": "Room is full"})
            return

        if self.channel_name in room["players"]:
            await self.send_json({"type": "error", "message": "Already in room"})
            return

        user = self.scope["user"]
        room["players"][self.channel_name] = "O"
        room["usernames"][self.channel_name] = user.username
        self.room_code = code
        await self.channel_layer.group_add(code, self.channel_name)

        # Tell the joiner their symbol
        await self.send_json({"type": "room_joined", "room_code": code, "symbol": "O"})

        # Build players map {symbol: username}
        players_map = {sym: room["usernames"][sid]
                       for sid, sym in room["players"].items()}

        # Broadcast game_start to everyone in the room
        await self.channel_layer.group_send(code, {
            "type": "pvp_event",
            "data": {
                "type": "game_start",
                "board": room["board"],
                "turn": room["turn"],
                "players": players_map,
            }
        })

    async def handle_move(self, position):
        if self.room_code is None or self.room_code not in _rooms:
            await self.send_json({"type": "error", "message": "Not in a room"})
            return

        room = _rooms[self.room_code]

        if room["result"]:
            await self.send_json({"type": "error", "message": "Game already over"})
            return

        if self.channel_name not in room["players"]:
            await self.send_json({"type": "error", "message": "Not in this room"})
            return

        player_symbol = room["players"][self.channel_name]

        if room["turn"] != player_symbol:
            await self.send_json({"type": "error", "message": "Not your turn"})
            return

        if position is None or not is_valid_move(room["board"], int(position)):
            await self.send_json({"type": "error", "message": "Invalid move"})
            return

        board = apply_move(room["board"], int(position), player_symbol)
        room["board"] = board
        room["turn"] = "O" if player_symbol == "X" else "X"

        winner = check_winner(board)
        game_over = False
        result = None

        if winner:
            result = winner
            game_over = True
            room["result"] = result
        elif is_draw(board):
            result = "draw"
            game_over = True
            room["result"] = result

        await self.channel_layer.group_send(self.room_code, {
            "type": "pvp_event",
            "data": {
                "type": "board_update",
                "board": board,
                "turn": room["turn"],
                "game_over": game_over,
                "result": result,
                "winner_symbol": winner if winner else None,
            }
        })

        if game_over:
            _rooms.pop(self.room_code, None)

    # ------------------------------------------------------------------ #
    #  Channel layer message handler
    # ------------------------------------------------------------------ #

    async def pvp_event(self, event):
        """Forward group messages to this WebSocket client."""
        await self.send_json(event["data"])

    # ------------------------------------------------------------------ #
    #  Helper
    # ------------------------------------------------------------------ #

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))
