# eehxpe

A personal web platform for managing recreational sports sessions, starting with a badminton matchup manager. The goal is to build a multi-sport hub where each sport gets its own app mounted under a shared domain, making it easy to track games, stats, and player progression over time.

## What I'm Building

**eehxpe** is a full-stack web platform hosted at [eehxpe.com](https://eehxpe.com). The core idea is a lightweight, self-hosted sports management tool for friend groups — no third-party apps, no subscriptions, just a clean interface for tracking who played who, how much was won or lost, and how player skill evolves over time.

The platform is designed as a multi-app aggregator: each sport runs as its own Flask app mounted at a subpath (e.g. `/badminton`), all served behind a shared Cloudflare tunnel from a home server.

---

## Badminton App (`/badminton`)

The first and currently active app. Built for managing weekly badminton sessions with a group of friends.

### Features

- **Session management** — create and track individual play sessions by date
- **Live matchup generator** — recommends balanced 2v2 matchups based on MMR and partnership history to keep games fair and rotate partners
- **Match recording** — log scores, game value (stakes), and per-player no-bet flags
- **MMR rating system** — ELO-based skill rating that updates after every match, with monthly breakdowns
- **Earnings tracking** — tracks net winnings and losses per player across sessions
- **Player stats** — win rates, partnership records, opponent history, and leaderboards
- **User accounts** — each player has a login, profile page, and personal stats view
- **PWA support** — installable as a mobile app with offline fallback

### Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python / Flask |
| Auth | Flask-Login + Argon2 password hashing |
| Database | SQLite via SQLAlchemy ORM |
| Frontend | Vanilla JS, HTML/CSS |
| Charts | Chart.js |
| Server | Waitress (WSGI) |
| Hosting | Self-hosted Windows PC via Cloudflare Named Tunnel |
| HTTPS | Cloudflare (terminates TLS) |

---

## Project Structure

```
eehxpe/
├── apps/
│   └── badminton/          # Badminton Flask app
│       ├── app.py          # Routes and API endpoints
│       ├── auth.py         # Authentication helpers
│       ├── models.py       # SQLAlchemy models
│       ├── database.py     # DB session management
│       ├── match_storage.py
│       ├── mmr_calculator.py
│       ├── player_stats.py
│       ├── static/         # CSS, JS, icons
│       └── templates/      # Jinja2 HTML templates
├── eehxpe/
│   └── wsgi.py             # Multi-app WSGI dispatcher
├── scripts/                # PowerShell deployment scripts
├── start_production.py     # Production server entry point
└── requirements.txt
```

---

## Roadmap

- [ ] Add more sports apps (tennis, ping pong, etc.) under the same platform
- [ ] Improve matchup algorithm with court-aware multi-court support
- [ ] Session history with detailed per-session stat breakdowns
- [ ] Admin dashboard for managing users and recalculating ratings
- [ ] Notifications / reminders for scheduled sessions

---

## Deployment

The app runs on a Windows home server exposed via a Cloudflare Named Tunnel. Production is managed with PowerShell scripts in `scripts/` and served by Waitress on port 8001.

Environment configuration is loaded from `.env.production` (not committed — see `.env.production.example` for the required variables).
