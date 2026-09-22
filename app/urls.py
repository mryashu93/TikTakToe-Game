from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="game.index"),
    path("play/", views.play, name="game.play"),
    path("pvp/", views.pvp, name="game.pvp"),
    path("leaderboard/", views.leaderboard, name="game.leaderboard"),
    path("profile/", views.profile, name="game.profile"),
    path("auth/register/", views.register, name="auth.register"),
    path("auth/login/", views.login, name="auth.login"),
    path("auth/logout/", views.logout, name="auth.logout"),
    path("auth/guest/", views.guest, name="auth.guest"),
    path("admin/", views.admin_dashboard, name="admin.dashboard"),
    path("admin/export/games.csv", views.export_games, name="admin.export_games"),
    path("admin/export/surveys.csv", views.export_surveys, name="admin.export_surveys"),
    path("api/game/new", views.api_new_game, name="api.game.new"),
    path("api/game/move", views.api_make_move, name="api.game.move"),
    path("api/survey", views.submit_survey, name="api.survey"),
    path("api/stats", views.api_stats, name="api.stats"),
]
