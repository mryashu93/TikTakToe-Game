import csv
import io
import json
import random
import string
import time
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .achievements import BADGE_META, check_and_award
from .ai import get_ai_move
from .game_logic import apply_move, check_winner, is_draw, is_valid_move
from .models import Achievement, Game, Move, SurveyResponse, User

_SESSIONS = {}


def _build_guest_username():
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"Guest_{suffix}"


def index(request):
    return render(request, "game/index.html")


def play(request):
    return render(request, "game/play.html", {"board_cells": range(9)})


def pvp(request):
    return render(request, "game/pvp.html", {"board_cells": range(9)})


def leaderboard(request):
    users = User.objects.filter(is_guest=False).all()
    ranked = sorted(users, key=lambda u: u.wins, reverse=True)[:20]
    return render(request, "game/leaderboard.html", {"users": ranked})


@login_required
def profile(request):
    earned_qs = Achievement.objects.filter(user_id=request.user.id)
    earned_slugs = set(earned_qs.values_list("badge", flat=True))

    earned_badges = [
        {
            "slug": slug,
            "icon": BADGE_META[slug]["icon"],
            "name": BADGE_META[slug]["name"],
            "description": BADGE_META[slug]["description"],
        }
        for slug in earned_slugs
        if slug in BADGE_META
    ]

    locked_badges = [
        {
            "slug": slug,
            "name": meta["name"],
            "description": meta["description"],
        }
        for slug, meta in BADGE_META.items()
        if slug not in earned_slugs
    ]

    return render(request, "game/profile.html", {
        "earned_badges": earned_badges,
        "locked_badges": locked_badges,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect("game.index")

    errors = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm", "")

        if len(username) < 3:
            errors["username"] = "Username must be at least 3 characters."
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Username already taken."
        if not email:
            errors["email"] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Email already registered."
        if len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
        elif password != confirm:
            errors["confirm"] = "Passwords do not match."

        if not errors:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_guest=False,
            )
            messages.success(request, "Account created! Please log in.")
            return redirect("auth.login")

    return render(request, "auth/register.html", {"errors": errors})


def login(request):
    if request.user.is_authenticated:
        return redirect("game.index")

    errors = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = User.objects.filter(username=username).first()
        if user and user.check_password(password):
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(request.POST.get("next") or "game.index")
        errors["general"] = "Invalid username or password."

    return render(request, "auth/login.html", {"errors": errors})


@login_required
def logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("game.index")


def guest(request):
    username = _build_guest_username()
    user = User.objects.create(username=username, is_guest=True)
    auth_login(request, user)
    messages.info(request, f"Playing as guest: {username}")
    return redirect("game.index")


def _require_admin(request):
    if not request.user.is_authenticated or not request.user.is_admin:
        messages.error(request, "Admin access required.")
        return redirect("game.index")
    return None


@login_required
def admin_dashboard(request):
    guard = _require_admin(request)
    if guard:
        return guard
    return render(request, "admin/dashboard.html")


@login_required
def export_games(request):
    guard = _require_admin(request)
    if guard:
        return guard

    games = Game.objects.filter(result__isnull=False).order_by("id")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "game_id", "player_uuid", "game_type", "ai_level",
        "player_symbol", "result", "move_count", "duration_seconds",
        "started_at", "ended_at"
    ])
    for g in games:
        writer.writerow([
            g.id,
            g.player.uuid,
            g.game_type,
            g.ai_level or "",
            g.player_symbol,
            g.result,
            g.move_count,
            round(g.duration_seconds or 0, 2),
            g.started_at.isoformat() if g.started_at else "",
            g.ended_at.isoformat() if g.ended_at else "",
        ])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename=games_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return response


@login_required
def export_surveys(request):
    guard = _require_admin(request)
    if guard:
        return guard

    surveys = SurveyResponse.objects.order_by("id")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "survey_id", "game_id", "player_uuid", "ai_level",
        "ease_of_use", "challenge", "engagement", "replay_intent",
        "submitted_at"
    ])
    for s in surveys:
        writer.writerow([
            s.id,
            s.game_id,
            s.user.uuid,
            s.ai_level or "",
            s.ease_of_use,
            s.challenge,
            s.engagement,
            s.replay_intent,
            s.submitted_at.isoformat() if s.submitted_at else "",
        ])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename=surveys_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return response


def api_new_game(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    data = json.loads(request.body or b"{}") if request.body else {}
    level = str(data.get("level", "easy")).lower()
    if level not in ("easy", "medium", "hard"):
        return JsonResponse({"error": "Invalid level"}, status=400)

    player_symbol = str(data.get("player_symbol", "X")).upper()
    ai_symbol = "O" if player_symbol == "X" else "X"

    game = Game.objects.create(
        player=request.user,
        game_type="ai",
        ai_level=level,
        player_symbol=player_symbol,
    )

    board = [None] * 9
    _SESSIONS[game.id] = {
        "board": board,
        "ai_symbol": ai_symbol,
        "human_symbol": player_symbol,
        "move_count": 0,
        "start_time": time.time(),
    }

    first_ai_pos = None
    if ai_symbol == "X":
        first_ai_pos = get_ai_move(board, ai_symbol, level)
        board[first_ai_pos] = ai_symbol
        _SESSIONS[game.id]["board"] = board
        _SESSIONS[game.id]["move_count"] += 1
        Move.objects.create(
            game_id=game.id,
            move_number=_SESSIONS[game.id]["move_count"],
            player="ai",
            symbol=ai_symbol,
            position=first_ai_pos,
        )

    return JsonResponse({
        "game_id": game.id,
        "board": board,
        "player_symbol": player_symbol,
        "ai_symbol": ai_symbol,
        "level": level,
        "ai_first_move": first_ai_pos,
    })


def api_make_move(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    data = json.loads(request.body or b"{}") if request.body else {}
    game_id = data.get("game_id")
    position = data.get("position")

    if game_id is None or position is None:
        return JsonResponse({"error": "Missing game_id or position"}, status=400)

    try:
        game = Game.objects.get(id=game_id, player_id=request.user.id)
    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status=404)

    if game.result is not None:
        return JsonResponse({"error": "Game already over"}, status=400)

    session = _SESSIONS.get(game_id)
    if not session:
        return JsonResponse({"error": "Session expired, please start a new game"}, status=410)

    board = session["board"]
    human_symbol = session["human_symbol"]
    ai_symbol = session["ai_symbol"]

    if not is_valid_move(board, position):
        return JsonResponse({"error": "Invalid move"}, status=400)

    board = apply_move(board, position, human_symbol)
    session["move_count"] += 1
    session["board"] = board

    Move.objects.create(
        game_id=game_id,
        move_number=session["move_count"],
        player="human",
        symbol=human_symbol,
        position=position,
    )

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
        ai_position = get_ai_move(board, ai_symbol, game.ai_level)
        board = apply_move(board, ai_position, ai_symbol)
        session["move_count"] += 1
        session["board"] = board

        Move.objects.create(
            game_id=game_id,
            move_number=session["move_count"],
            player="ai",
            symbol=ai_symbol,
            position=ai_position,
        )

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
        game.save()
        _SESSIONS.pop(game_id, None)
        earned = check_and_award(request.user, game)
        new_achievements = [
            {"badge": a.badge, **BADGE_META.get(a.badge, {})}
            for a in earned
        ]
    else:
        game.save(update_fields=[])

    return JsonResponse({
        "board": board,
        "ai_position": ai_position,
        "game_over": game_over,
        "result": result,
        "new_achievements": new_achievements,
    })


@login_required
def submit_survey(request):
    data = json.loads(request.body or b"{}") if request.body else {}
    game_id = data.get("game_id")

    try:
        game = Game.objects.get(id=game_id, player_id=request.user.id, game_type="ai")
    except Game.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status=404)

    if hasattr(game, "survey") and game.survey is not None:
        return JsonResponse({"error": "Survey already submitted"}, status=400)

    def likert(key):
        try:
            val = int(data.get(key, 0))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid Likert value for {key}: {data.get(key)}")
        if val < 1 or val > 5:
            raise ValueError(f"Invalid Likert value for {key}: {val}")
        return val

    try:
        SurveyResponse.objects.create(
            game_id=game.id,
            user=request.user,
            ai_level=game.ai_level,
            ease_of_use=likert("ease_of_use"),
            challenge=likert("challenge"),
            engagement=likert("engagement"),
            replay_intent=likert("replay_intent"),
        )
    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"ok": True})


def api_stats(request):
    rows = list(
        Game.objects.filter(game_type="ai", result__isnull=False)
        .values("ai_level")
        .annotate(
            total=Count("id"),
            wins=Count("id", filter=Q(result="win")),
            losses=Count("id", filter=Q(result="loss")),
            draws=Count("id", filter=Q(result="draw")),
            avg_duration=Avg("duration_seconds"),
            avg_moves=Avg("move_count"),
        )
    )

    survey_rows = list(
        SurveyResponse.objects.values("ai_level")
        .annotate(
            ease=Avg("ease_of_use"),
            challenge=Avg("challenge"),
            engagement=Avg("engagement"),
            replay=Avg("replay_intent"),
            count=Count("id"),
        )
    )

    survey_map = {r["ai_level"]: r for r in survey_rows}
    result = []
    for r in rows:
        s = survey_map.get(r["ai_level"])
        result.append({
            "level": r["ai_level"],
            "total": r["total"],
            "wins": r["wins"] or 0,
            "losses": r["losses"] or 0,
            "draws": r["draws"] or 0,
            "win_rate": round((r["wins"] or 0) / r["total"] * 100, 1) if r["total"] else 0,
            "avg_duration": round(r["avg_duration"] or 0, 1),
            "avg_moves": round(r["avg_moves"] or 0, 1),
            "survey": {
                "ease_of_use": round(s["ease"], 2) if s else None,
                "challenge": round(s["challenge"], 2) if s else None,
                "engagement": round(s["engagement"], 2) if s else None,
                "replay_intent": round(s["replay"], 2) if s else None,
                "count": s["count"] if s else 0,
            } if s else None,
        })
    return JsonResponse(result, safe=False)
