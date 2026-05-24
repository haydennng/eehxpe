#!/usr/bin/env python3
"""
Add birds_used column to matches table

This migration adds an integer column to store how many shuttlecocks
were used per match, enabling bird usage stats over time.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from sqlalchemy import text


def migrate():
    print("=" * 60)
    print("Migration: Add birds_used column")
    print("=" * 60)

    db = get_db()
    with db.engine.connect() as conn:
        print("\nChecking if column exists...")

        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('matches')
            WHERE name = 'birds_used'
        """))

        if result.fetchone()[0] > 0:
            print("Column already exists, skipping migration")
            return

        print("Adding birds_used column...")

        conn.execute(text("""
            ALTER TABLE matches
            ADD COLUMN birds_used INTEGER
        """))

        conn.commit()

        print("Column added successfully")

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
