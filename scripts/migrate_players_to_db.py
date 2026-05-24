#!/usr/bin/env python3
"""
Migration: Add player status columns to users table and migrate players.json data.

Run once from the project root:
    python scripts/migrate_players_to_db.py

What it does:
  1. Adds active, display_order, no_bet, deactivated columns to the users table
     (safe to re-run — skips columns that already exist)
  2. Reads data/players.json and copies active/order/no_bet/deactivated values
     into each matching User record in the database
  3. Warns about any players in the JSON that have no DB account

After running this, players.json is no longer needed and can be deleted.
"""
import sys
import json
from pathlib import Path
from sqlalchemy import text, inspect

# ── Path setup ────────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'apps' / 'badminton'))

from database import init_db, session_scope
from models import User


def add_columns(engine):
    """Add new columns to users table if they don't already exist."""
    inspector = inspect(engine)
    existing = {col['name'] for col in inspector.get_columns('users')}

    new_cols = [
        ('active',        'BOOLEAN NOT NULL DEFAULT 1'),
        ('display_order', 'INTEGER NOT NULL DEFAULT 0'),
        ('no_bet',        'BOOLEAN NOT NULL DEFAULT 0'),
        ('deactivated',   'BOOLEAN NOT NULL DEFAULT 0'),
    ]

    with engine.connect() as conn:
        for col_name, col_def in new_cols:
            if col_name not in existing:
                conn.execute(text(f'ALTER TABLE users ADD COLUMN {col_name} {col_def}'))
                print(f'  ✓ Added column: {col_name}')
            else:
                print(f'  · Already exists: {col_name}')
        conn.commit()


def migrate_players(players_file: Path):
    """Copy status fields from players.json into User records."""
    with open(players_file) as f:
        data = json.load(f)

    players = data.get('players', [])
    print(f'\nFound {len(players)} players in players.json')

    updated = 0
    skipped = 0

    with session_scope() as session:
        for i, player in enumerate(players):
            name        = player.get('name')
            active      = bool(player.get('active', True))
            order       = int(player.get('order', i))
            no_bet      = bool(player.get('no_bet', False))
            deactivated = bool(player.get('deactivated', False))

            user = session.query(User).filter_by(username=name).first()
            if user:
                user.active        = active
                user.display_order = order
                user.no_bet        = no_bet
                user.deactivated   = deactivated
                status = 'deactivated' if deactivated else ('active' if active else 'inactive')
                print(f'  ✓ {name:15s}  order={order:2d}  {status}')
                updated += 1
            else:
                print(f'  ⚠ No DB account for "{name}" — skipping (player has no login)')
                skipped += 1

    print(f'\n  Updated: {updated}  |  Skipped (no DB account): {skipped}')


def main():
    print('=' * 55)
    print(' Migration: players.json → users table')
    print('=' * 55)

    db = init_db()

    print('\nStep 1: Adding columns to users table...')
    add_columns(db.engine)

    players_file = project_root / 'data' / 'players.json'
    if not players_file.exists():
        print(f'\nERROR: {players_file} not found — cannot migrate player data.')
        sys.exit(1)

    print('\nStep 2: Migrating player status data...')
    migrate_players(players_file)

    print('\n✓ Migration complete. You can now delete:')
    print('    data/players.json')
    print('    data/matches.json')
    print('    data/sessions.json')
    print('    apps/badminton/data/ (legacy files)')


if __name__ == '__main__':
    main()
