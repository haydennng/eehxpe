#!/usr/bin/env python3
"""
Add preset_state table

Stores the shared preset schedule so all devices see the same state.
Single-row table (id=1) containing a JSON blob of the full schedule.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from sqlalchemy import text


def migrate():
    print("=" * 60)
    print("Migration: Add preset_state table")
    print("=" * 60)

    db = get_db()
    with db.engine.connect() as conn:
        print("\nChecking if table exists...")

        result = conn.execute(text("""
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='preset_state'
        """))

        if result.fetchone()[0] > 0:
            print("Table already exists, skipping migration")
            return

        print("Creating preset_state table...")

        conn.execute(text("""
            CREATE TABLE preset_state (
                id INTEGER PRIMARY KEY,
                state_json JSON,
                updated_at DATETIME NOT NULL
            )
        """))

        conn.commit()

        print("Table created successfully")

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
