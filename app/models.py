import uuid
from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True, blank=True, null=True)
    is_guest = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.utcnow)

    @property
    def wins(self):
        return self.games.filter(result="win").count()

    @property
    def losses(self):
        return self.games.filter(result="loss").count()

    @property
    def draws(self):
        return self.games.filter(result="draw").count()

    @property
    def total_games(self):
        return self.games.count()

    class Meta:
        app_label = "app"


class Game(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name="games")
    game_type = models.CharField(max_length=10, default="ai")
    ai_level = models.CharField(max_length=10, null=True, blank=True)
    player_symbol = models.CharField(max_length=1, default="X")
    result = models.CharField(max_length=10, null=True, blank=True)
    move_count = models.IntegerField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    started_at = models.DateTimeField(default=datetime.utcnow)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "app"


class Move(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moves")
    move_number = models.IntegerField()
    player = models.CharField(max_length=10)
    symbol = models.CharField(max_length=1)
    position = models.IntegerField()
    timestamp = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        app_label = "app"


class SurveyResponse(models.Model):
    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name="survey")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="survey_responses")
    ai_level = models.CharField(max_length=10, null=True, blank=True)
    ease_of_use = models.IntegerField()
    challenge = models.IntegerField()
    engagement = models.IntegerField()
    replay_intent = models.IntegerField()
    submitted_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        app_label = "app"


class Achievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    badge = models.CharField(max_length=50)
    earned_at = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        app_label = "app"
        constraints = [
            models.UniqueConstraint(fields=["user", "badge"], name="uq_user_badge"),
        ]
