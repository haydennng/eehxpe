#!/usr/bin/env python3
"""
Add player_no_bet_status column to matches table

This migration adds a JSON column to store which players were in no-bet mode
for each match, enabling earnings calculations to account for no-bet players.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from sqlalchemy import text


def migrate():
    """Add player_no_bet_status column to matches table"""
    print("=" * 60)
    print("Migration: Add player_no_bet_status column")
    print("=" * 60)
    
    db = get_db()
    with db.engine.connect() as conn:
        print("\nChecking if column exists...")
        
        # Check if column already exists
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('matches')
            WHERE name = 'player_no_bet_status'
        """))
        
        exists = result.fetchone()[0] > 0
        
        if exists:
            print("✅ Column already exists, skipping migration")
            return
        
        print("Adding player_no_bet_status column...")
        
        # Add the column (SQLite-specific)
        conn.execute(text("""
            ALTER TABLE matches
            ADD COLUMN player_no_bet_status TEXT
        """))
        
        conn.commit()
        
        print("✅ Column added successfully")
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
