import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, '..', 'tiktaktoe.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -------------------------------------------------------------------
    # Medium AI tuning knob
    # Probability (0.0–1.0) that the Medium AI plays the "smart" move
    # (win-or-block heuristic) vs a random move.
    # 1.0  → always smart  (equivalent to Hard but without full Minimax)
    # 0.5  → smart half the time  (default research setting)
    # 0.0  → fully random  (same as Easy)
    # -------------------------------------------------------------------
    MEDIUM_AI_SKILL = float(os.environ.get("MEDIUM_AI_SKILL", "0.7"))
