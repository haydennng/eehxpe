# CLAUDE.md — eehxpe Project Context

This file gives you everything you need to work on the eehxpe platform without re-explaining the project each session.

---

## What This Project Is

**eehxpe** is a self-hosted, personal web platform for tracking recreational sports sessions with a friend group. It lives at [eehxpe.com](https://eehxpe.com). The first and only active app is a **badminton matchup manager** mounted at `/badminton`.

The platform is designed as a **multi-app aggregator**: each sport is its own Flask app, mounted at a subpath via Werkzeug's `DispatcherMiddleware`. Adding a new sport = creating a new app and registering it in `eehxpe/wsgi.py`.

---

## Architecture

```
eehxpe/
├── apps/
│   └── badminton/          # The only active sport app
│       ├── app.py          # All routes and API endpoints
│       ├── auth.py         # Login, password hashing, role decorators
│       ├── models.py       # SQLAlchemy ORM models
│       ├── database.py     # DB init, session management
│       ├── match_storage.py
│       ├── mmr_calculator.py
│       ├── matchup_generator.py
│       ├── game_valuation.py
│       ├── player_stats.py
│       ├── static/         # CSS, JS, icons, service worker
│       └── templates/      # Jinja2 HTML templates
├── eehxpe/
│   └── wsgi.py             # DispatcherMiddleware — mounts each sport app
├── data/
│   └── badminton/
│       └── badminton.db    # SQLite database (do not commit)
├── scripts/                # PowerShell deployment scripts
├── start_production.py     # Production entry point
└── requirements.txt
```

**Request flow:** Cloudflare Tunnel → Windows home server → Waitress (port 8001) → `wsgi.py` dispatcher → Flask badminton app

---

## Deployment

- **Server:** Windows home PC, always-on
- **WSGI server:** Waitress, port `8001`, 4 threads
- **Entry point:** `python start_production.py`
  - Kills any existing process on port 8001
  - Loads env vars from `.env.production` (not committed)
  - Sets `WSGI_DISPATCHER=true`
  - Starts Waitress
- **Env file:** `.env.production` — see `.env.production.example` for required keys
- **Required env vars:**
  - `FLASK_SECRET_KEY` — 32+ hex chars, required for session signing
  - `DATABASE_URL` — optional, defaults to `sqlite:///data/badminton/badminton.db`

To restart in production: run `start_production.py` from PowerShell. It self-cleans the old process.

---

## Database

- **Engine:** SQLite via SQLAlchemy ORM
- **Location:** `data/badminton/badminton.db`
- **Pool:** `NullPool` (no connection caching — required for SQLite stability with Waitress threads)
- **Always use `session_scope()`** for any DB operation:

```python
from database import session_scope

with session_scope() as session:
    user = session.query(User).filter_by(username='hayden').first()
    user.mmr = 1600
# auto-commits on exit, auto-rollbacks on exception
```

Never call `session.commit()` manually inside a `session_scope()` block — it handles that for you.

### Schema

**`users`**
- `id`, `username` (unique), `password_hash` (Argon2), `role` (enum: `player`/`admin`)
- `mmr` (Float, default 1500.0)
- `created_at`, `updated_at` (Pacific timezone)

**`sessions`** — a single day of play
- `id`, `session_date`, `notes`
- has-many `matches` (cascade delete)

**`matches`** — individual 2v2 games
- `id`, `session_id` (FK)
- `team1_player1_id`, `team1_player2_id`, `team2_player1_id`, `team2_player2_id` (all FK to users)
- `team1_score`, `team2_score`, `winner_team` (1 or 2)
- `game_value` (Float — dollar stake per match)
- `mmr_change` (Float — total shift from this match)
- `player_no_bet_status` (JSON — `{"PlayerName": bool}`, true = sitting out the bet)
- `birds_used` (Integer, optional — shuttlecocks consumed)
- `created_at` (Pacific timezone)

---

## MMR System

- **Algorithm:** ELO rating
- **Starting rating:** 1500
- **K-factor:** 24 (moderate rate of change)
- **Team rating:** average of both players' individual ratings
- **Both teammates gain/lose the same MMR delta per match**
- Formula: `new_rating = old_rating + K * (actual_score - expected_score)`
- `expected_score = 1 / (1 + 10^((opponent_rating - player_rating) / 400))`
- Winner `actual_score = 1.0`, loser `actual_score = 0.0`

Key functions in `mmr_calculator.py`:
- `process_match(team1, team2, winner, player_ratings)` — single match
- `process_matches_chronologically(matches, ...)` — bulk recalculation with optional history

---

## Matchup Generator

Located in `matchup_generator.py`. Uses a **weighted scoring algorithm** to find the fairest 2v2 matchup from available players.

Priority order (weights):
1. **Sit-out balance** — weight 100 (dominant priority: rotate who sits out)
2. **Partner variety** — weight 5 (vary who plays together)
3. **Opponent variety** — weight 4 (face different opponents)

The algorithm brute-forces all possible combinations and picks the lowest-cost one. Fine for groups up to ~8 players.

---

## Authentication

- **Passwords:** Argon2 hashed via `argon2-cffi`
- **Sessions:** Flask-Login
- **Roles:** `player` (default) and `admin`
- **Decorators in `auth.py`:**
  - `@admin_required` — admin only
  - `@admin_or_self_required` — admin or the player themselves

---

## Frontend Conventions

- **No build step.** Vanilla JS only — no React, no Webpack, no npm.
- **Templates:** Jinja2 in `apps/badminton/templates/`
- **Charts:** Chart.js (loaded via CDN in templates)
- **PWA:** Service worker at `static/sw.js` — app is installable on mobile
- **CSS/JS:** All embedded or in `static/` — do not introduce external build tools

When editing templates, keep JS inline or in `static/`. Do not create separate JS modules.

---

## Timezones

All datetimes are stored and displayed in **US/Pacific timezone**. Use `zoneinfo` (not `pytz`):

```python
from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo('America/Los_Angeles')
now = datetime.now(PACIFIC)
```

---

## Key Design Decisions (don't change without reason)

- **NullPool for SQLite** — prevents connection caching issues with Waitress threading. Do not switch to a connection pool.
- **4 Waitress threads** — conservative limit chosen because SQLite can handle multiple readers but not concurrent writers. Don't increase without switching to Postgres.
- **No build step** — intentional. Keep the frontend simple and deployable without Node.
- **DispatcherMiddleware** — the multi-sport architecture. New sports go in `apps/` and get mounted in `eehxpe/wsgi.py`.
- **`WSGI_DISPATCHER=true` env flag** — used by Flask apps to know they're running under the dispatcher (affects URL prefixes).

---

## Common Tasks

**Add a new API endpoint:** Edit `apps/badminton/app.py`. Follow existing patterns for auth decorators and `session_scope()` usage.

**Add a new DB column:** Add to the model in `models.py`, then run a migration or recreate tables in dev. There's no Alembic — migrations have been done manually via scripts in `scripts/`.

**Recalculate all MMR from scratch:** Use `process_matches_chronologically()` in `mmr_calculator.py` with `build_history=True`.

**Restart production server:** Run `python start_production.py` in PowerShell from the project root.

**Run tests/utilities:** Root-level scripts like `test_mmr_update.py`, `test_delete_match.py`, `fix_hayden_mmr.py` are standalone and can be run directly.

---

## Roadmap (from README)

- [ ] Add more sports (tennis, ping pong) as new apps under `apps/`
- [ ] Multi-court support in matchup generator
- [ ] Session history with per-session stat breakdowns
- [ ] Admin dashboard for user management and MMR recalculation
- [ ] Notifications/reminders for scheduled sessions
