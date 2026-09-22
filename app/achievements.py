"""
Achievement badge definitions and award logic.

Badges (slugs):
  first_victory    — win any game
  stalemate_master — draw against the Hard AI (best possible result)
  medium_slayer    — beat the Medium AI
  hat_trick        — win 3 games in a row
  veteran          — play 10+ games total
"""

from .models import Achievement, Game

BADGE_META = {
    "first_victory": {
        "name": "First Victory",
        "description": "Won your first game!",
        "icon": "🏆",
    },
    "stalemate_master": {
        "name": "Stalemate Master",
        "description": "Drew against the unbeatable Hard AI — the best possible outcome!",
        "icon": "🤝",
    },
    "medium_slayer": {
        "name": "Medium Slayer",
        "description": "Defeated the Medium AI!",
        "icon": "⚔️",
    },
    "hat_trick": {
        "name": "Hat Trick",
        "description": "Won 3 games in a row!",
        "icon": "🎩",
    },
    "veteran": {
        "name": "Veteran",
        "description": "Played 10 or more games!",
        "icon": "🎖️",
    },
}


def _award(user, badge: str):
    """Grant a badge if the user doesn't already have it. Returns the new Achievement or None."""
    obj, created = Achievement.objects.get_or_create(user=user, badge=badge)
    return obj if created else None


def check_and_award(user, game: Game) -> list:
    """
    Evaluate all achievement conditions after a completed game.
    Returns a list of newly awarded Achievement objects (may be empty).
    """
    new_achievements = []

    # --- first_victory ---
    if game.result == "win":
        ach = _award(user, "first_victory")
        if ach:
            new_achievements.append(ach)

    # --- stalemate_master ---
    if game.result == "draw" and game.ai_level == "hard":
        ach = _award(user, "stalemate_master")
        if ach:
            new_achievements.append(ach)

    # --- medium_slayer ---
    if game.result == "win" and game.ai_level == "medium":
        ach = _award(user, "medium_slayer")
        if ach:
            new_achievements.append(ach)

    # --- hat_trick — last 3 AI games all won ---
    recent = (
        Game.objects
        .filter(player=user, game_type="ai")
        .order_by("-id")[:3]
    )
    recent_list = list(recent)
    if len(recent_list) == 3 and all(g.result == "win" for g in recent_list):
        ach = _award(user, "hat_trick")
        if ach:
            new_achievements.append(ach)

    # --- veteran — 10+ games ---
    if user.total_games >= 10:
        ach = _award(user, "veteran")
        if ach:
            new_achievements.append(ach)

    return new_achievements
