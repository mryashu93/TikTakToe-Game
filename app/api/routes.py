"""
JSON REST API Blueprint.

Endpoints:
  POST /api/game/new        — start a new AI game session
  POST /api/game/move       — submit a human move, receive AI response
  POST /api/survey          — submit post-game survey
  GET  /api/stats           — aggregate stats (used by admin dashboard JS)
"""

import time
from datetime import datetime

from flask import request, jsonify
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Game, Move, SurveyResponse
from ..game_logic import check_winner, is_draw, is_valid_move, apply_move
from ..ai import get_ai_move
from ..achievements import check_and_award, BADGE_META
from . import api_bp

# In-memory game state {game_id: {board, ai_symbol, human_symbol, move_count, start_time}}
_sessions: dict = {}


@api_bp.route("/game/new", methods=["POST"])
@login_required
def new_game():
    data = request.get_json(silent=True) or {}
    level = data.get("level", "easy").lower()
    if level not in ("easy", "medium", "hard"):
        return jsonify(error="Invalid level"), 400

    player_symbol = data.get("player_symbol", "X").upper()
    ai_symbol = "O" if player_symbol == "X" else "X"

    game = Game(
        player_id=current_user.id,
        game_type="ai",
        ai_level=level,
        player_symbol=player_symbol,
    )
    db.session.add(game)
    db.session.commit()

    board = [None] * 9
    _sessions[game.id] = {
        "board": board,
        "ai_symbol": ai_symbol,
        "human_symbol": player_symbol,
        "move_count": 0,
        "start_time": time.time(),
    }

    # If AI goes first (player chose O)
    first_ai_pos = None
    if ai_symbol == "X":
        first_ai_pos = get_ai_move(board, ai_symbol, level)
        board[first_ai_pos] = ai_symbol
        _sessions[game.id]["board"] = board
        _sessions[game.id]["move_count"] += 1
        move = Move(
            game_id=game.id,
            move_number=_sessions[game.id]["move_count"],
            player="ai",
            symbol=ai_symbol,
            position=first_ai_pos,
        )
        db.session.add(move)
        db.session.commit()

    return jsonify(
        game_id=game.id,
        board=board,
        player_symbol=player_symbol,
        ai_symbol=ai_symbol,
        level=level,
        ai_first_move=first_ai_pos,
    )


@api_bp.route("/game/move", methods=["POST"])
@login_required
def make_move():
    data = request.get_json(silent=True) or {}
    game_id = data.get("game_id")
    position = data.get("position")

    if game_id is None or position is None:
        return jsonify(error="Missing game_id or position"), 400

    game = Game.query.filter_by(id=game_id, player_id=current_user.id).first()
    if not game:
        return jsonify(error="Game not found"), 404

    if game.result is not None:
        return jsonify(error="Game already over"), 400

    session = _sessions.get(game_id)
    if not session:
        return jsonify(error="Session expired, please start a new game"), 410

    board = session["board"]
    human_symbol = session["human_symbol"]
    ai_symbol = session["ai_symbol"]

    if not is_valid_move(board, position):
        return jsonify(error="Invalid move"), 400

    # Apply human move
    board = apply_move(board, position, human_symbol)
    session["move_count"] += 1
    session["board"] = board

    move = Move(
        game_id=game_id,
        move_number=session["move_count"],
        player="human",
        symbol=human_symbol,
        position=position,
    )
    db.session.add(move)

    # Check game over after human move
    winner = check_winner(board)
    game_over = False
    result = None
    ai_position = None

    if winner == human_symbol:
        result = "win"
        game_over = True
    elif is_draw(board):
        result = "draw"
        game_over = True
    else:
        # AI move
        ai_position = get_ai_move(board, ai_symbol, game.ai_level)
        board = apply_move(board, ai_position, ai_symbol)
        session["move_count"] += 1
        session["board"] = board

        ai_move_rec = Move(
            game_id=game_id,
            move_number=session["move_count"],
            player="ai",
            symbol=ai_symbol,
            position=ai_position,
        )
        db.session.add(ai_move_rec)

        winner = check_winner(board)
        if winner == ai_symbol:
            result = "loss"
            game_over = True
        elif is_draw(board):
            result = "draw"
            game_over = True

    new_achievements = []
    if game_over:
        duration = time.time() - session["start_time"]
        game.result = result
        game.move_count = session["move_count"]
        game.duration_seconds = duration
        game.ended_at = datetime.utcnow()
        db.session.commit()
        _sessions.pop(game_id, None)

        earned = check_and_award(current_user, game)
        new_achievements = [
            {"badge": a.badge, **BADGE_META.get(a.badge, {})}
            for a in earned
        ]
    else:
        db.session.commit()

    return jsonify(
        board=board,
        ai_position=ai_position,
        game_over=game_over,
        result=result,
        new_achievements=new_achievements,
    )


@api_bp.route("/survey", methods=["POST"])
@login_required
def submit_survey():
    data = request.get_json(silent=True) or {}
    game_id = data.get("game_id")

    game = Game.query.filter_by(id=game_id, player_id=current_user.id, game_type="ai").first()
    if not game:
        return jsonify(error="Game not found"), 404

    if game.survey:
        return jsonify(error="Survey already submitted"), 400

    def likert(key):
        val = int(data.get(key, 0))
        if val < 1 or val > 5:
            raise ValueError(f"Invalid Likert value for {key}: {val}")
        return val

    try:
        resp = SurveyResponse(
            game_id=game_id,
            user_id=current_user.id,
            ai_level=game.ai_level,
            ease_of_use=likert("ease_of_use"),
            challenge=likert("challenge"),
            engagement=likert("engagement"),
            replay_intent=likert("replay_intent"),
        )
    except (ValueError, TypeError) as e:
        return jsonify(error=str(e)), 400

    db.session.add(resp)
    db.session.commit()
    return jsonify(ok=True)


@api_bp.route("/stats")
def stats():
    from sqlalchemy import func
    from ..models import SurveyResponse

    rows = db.session.query(
        Game.ai_level,
        func.count(Game.id).label("total"),
        func.sum((Game.result == "win").cast(db.Integer)).label("wins"),
        func.sum((Game.result == "loss").cast(db.Integer)).label("losses"),
        func.sum((Game.result == "draw").cast(db.Integer)).label("draws"),
        func.avg(Game.duration_seconds).label("avg_duration"),
        func.avg(Game.move_count).label("avg_moves"),
    ).filter(Game.game_type == "ai", Game.result.isnot(None)).group_by(Game.ai_level).all()

    survey_rows = db.session.query(
        SurveyResponse.ai_level,
        func.avg(SurveyResponse.ease_of_use).label("ease"),
        func.avg(SurveyResponse.challenge).label("challenge"),
        func.avg(SurveyResponse.engagement).label("engagement"),
        func.avg(SurveyResponse.replay_intent).label("replay"),
        func.count(SurveyResponse.id).label("count"),
    ).group_by(SurveyResponse.ai_level).all()

    survey_map = {r.ai_level: r for r in survey_rows}

    result = []
    for r in rows:
        s = survey_map.get(r.ai_level)
        result.append({
            "level": r.ai_level,
            "total": r.total,
            "wins": r.wins or 0,
            "losses": r.losses or 0,
            "draws": r.draws or 0,
            "win_rate": round((r.wins or 0) / r.total * 100, 1) if r.total else 0,
            "avg_duration": round(r.avg_duration or 0, 1),
            "avg_moves": round(r.avg_moves or 0, 1),
            "survey": {
                "ease_of_use": round(s.ease, 2) if s else None,
                "challenge": round(s.challenge, 2) if s else None,
                "engagement": round(s.engagement, 2) if s else None,
                "replay_intent": round(s.replay, 2) if s else None,
                "count": s.count if s else 0,
            } if s else None,
        })

    return jsonify(result)
