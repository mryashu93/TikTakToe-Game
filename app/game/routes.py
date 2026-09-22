from flask import render_template, redirect, url_for
from flask_login import login_required, current_user

from ..models import User
from . import game_bp


@game_bp.route("/")
def index():
    return render_template("game/index.html")


@game_bp.route("/play")
@login_required
def play():
    """Single-player vs AI page."""
    return render_template("game/play.html")


@game_bp.route("/pvp")
@login_required
def pvp():
    """PvP lobby / room page."""
    return render_template("game/pvp.html")


@game_bp.route("/leaderboard")
def leaderboard():
    # Top 20 users by wins, registered (non-guest) users only
    users = (
        User.query
        .filter_by(is_guest=False)
        .all()
    )
    ranked = sorted(users, key=lambda u: u.wins, reverse=True)[:20]
    return render_template("game/leaderboard.html", users=ranked)


@game_bp.route("/profile")
@login_required
def profile():
    from ..achievements import BADGE_META
    from ..models import Achievement
    badges = Achievement.query.filter_by(user_id=current_user.id).all()
    return render_template("game/profile.html", badges=badges, badge_meta=BADGE_META)
