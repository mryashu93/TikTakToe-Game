"""
Admin / Researcher dashboard routes.

All routes require is_admin=True.
"""

import csv
import io
from datetime import datetime

from flask import render_template, redirect, url_for, flash, Response
from flask_login import login_required, current_user

from ..models import Game, SurveyResponse, User
from . import admin_bp


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Admin access required.", "danger")
        return redirect(url_for("game.index"))
    return None


@admin_bp.route("/")
@login_required
def dashboard():
    guard = _require_admin()
    if guard:
        return guard
    return render_template("admin/dashboard.html")


# ---------------------------------------------------------------------------
# CSV exports
# ---------------------------------------------------------------------------

@admin_bp.route("/export/games.csv")
@login_required
def export_games():
    guard = _require_admin()
    if guard:
        return guard

    games = Game.query.filter(Game.result.isnot(None)).order_by(Game.id).all()

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

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=games_{datetime.utcnow().strftime('%Y%m%d')}.csv"},
    )


@admin_bp.route("/export/surveys.csv")
@login_required
def export_surveys():
    guard = _require_admin()
    if guard:
        return guard

    surveys = SurveyResponse.query.order_by(SurveyResponse.id).all()

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

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=surveys_{datetime.utcnow().strftime('%Y%m%d')}.csv"},
    )
