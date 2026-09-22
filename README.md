# Tik Tak Toe — Research Project

A full-stack Tic-Tac-Toe web app (Flask + SQLAlchemy + Socket.IO) built to
support the research proposal **"Tik Tak Toe: Evaluating AI Difficulty and
Player Engagement"** (Harshal Sandip Shelke, Akshay Vijay Patil —
GH Raisoni College of Engineering & Management, Jalgaon).

---

## Quick Start

```bash
# 1. Enter the project directory
cd tiktaktoe

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed the database (creates admin / admin123)
python seed.py

# 5. Run the server
python run.py
```

Open **http://localhost:5000** in your browser.

---

## Accounts

| Role  | Username | Password  | URL      |
|-------|----------|-----------|----------|
| Admin | admin    | admin123  | /admin   |
| Guest | —        | —         | click "Play as Guest" on home page |

> ⚠️ **Change the admin password before any public deployment.**

---

## Features

| Feature | Details |
|---------|---------|
| **3 AI Levels** | Easy (random), Medium (heuristic + tunable `MEDIUM_AI_SKILL`), Hard (Minimax + alpha-beta — unbeatable) |
| **Real-time PvP** | Create a room → share 5-char code → play live over Socket.IO |
| **Accounts** | Register, login, or auto-guest |
| **Game logging** | Every move, result, duration & move count stored automatically |
| **Post-game survey** | 4-question Likert-5 modal after each AI game |
| **Achievements** | 5 badges: First Victory, Stalemate Master, Medium Slayer, Hat Trick, Veteran |
| **Leaderboard** | Global ranking by wins (registered users) |
| **Admin dashboard** | Charts + table: win rate, avg duration/moves, survey averages — all by difficulty |
| **CSV export** | `/admin/export/games.csv` & `/admin/export/surveys.csv` for SPSS/Excel |

---

## Project Structure

```
tiktaktoe/
├── run.py                # Entry point
├── seed.py               # Create admin user
├── requirements.txt
├── .env                  # Config (copy from .env.example)
└── app/
    ├── __init__.py       # Application factory
    ├── config.py         # Settings (MEDIUM_AI_SKILL tuning knob)
    ├── extensions.py     # db, login_manager, bcrypt, socketio
    ├── models.py         # User, Game, Move, SurveyResponse, Achievement
    ├── game_logic.py     # Pure board functions (win detection, etc.)
    ├── ai.py             # Easy / Medium / Hard AI engines
    ├── achievements.py   # Badge award logic
    ├── socket_events.py  # Socket.IO PvP handlers
    ├── auth/             # register / login / logout / guest routes
    ├── game/             # Page routes (home, play, pvp, leaderboard, profile)
    ├── api/              # JSON REST API
    ├── admin/            # Research dashboard + CSV export
    ├── templates/        # Jinja2 HTML templates
    └── static/
        ├── css/style.css
        └── js/ (play.js, pvp.js, admin.js)
```

---

## AI Difficulty Tuning

Open `app/config.py` (or set `MEDIUM_AI_SKILL` in `.env`):

```python
MEDIUM_AI_SKILL = 0.7   # 0.0 = fully random, 1.0 = always smart
```

The Medium AI uses a win/block heuristic with probability `MEDIUM_AI_SKILL`,
falling back to a random move otherwise. This lets you continuously dial
difficulty without switching between discrete on/off modes.

---

## Research Mapping

| Research Proposal Section | Where it lives |
|---|---|
| 3 AI difficulty levels | `app/ai.py` |
| Data collection | `Game` + `Move` tables (automatic) |
| Post-test questionnaire (Likert) | In-app survey → `SurveyResponse` table |
| Anonymity | Users identified by UUID; guests have no PII |
| Pilot testing | Register 3-5 test users, play all levels, check `/admin` |
| Data export for SPSS/Excel | `/admin/export/games.csv`, `/admin/export/surveys.csv` |
