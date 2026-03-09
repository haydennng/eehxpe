#!/usr/bin/env python3
"""
Recalculate MMR for all players based on database matches

This script recalculates MMR from scratch for all players based on
all matches stored in the database. Run this after migrating to the
new database-based MMR system.

Usage:
    python recalculate_mmr_db.py
    python recalculate_mmr_db.py --yes  # Auto-confirm
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from mmr_database import recalculate_all_mmr
from database import session_scope
from models import User


def main():
    print("=" * 60)
    print("MMR Recalculation Script (Database)")
    print("=" * 60)
    print()
    
    # Show current MMR values
    print("Current MMR values:")
    with session_scope() as session:
        users = session.query(User).order_by(User.mmr.desc()).all()
        for user in users:
            print(f"  {user.username}: {user.mmr:.2f}")
    print()
    
    # Confirm action
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    if not auto_confirm:
        response = input("Recalculate MMR from all matches? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    else:
        print("Auto-confirming recalculation...")
    
    print()
    print("Recalculating MMR...")
    
    try:
        # Recalculate MMR
        player_ratings = recalculate_all_mmr(k_factor=24)
        
        print()
        print("=" * 60)
        print("MMR Recalculation Complete!")
        print("=" * 60)
        print()
        
        # Show new MMR values
        print("New MMR values:")
        sorted_ratings = sorted(player_ratings.items(), key=lambda x: x[1], reverse=True)
        for username, rating in sorted_ratings:
            print(f"  {username}: {rating:.2f}")
        
        print()
        print(f"Total players updated: {len(player_ratings)}")
        print()
        print("✓ MMR recalculation successful!")
        
    except Exception as e:
        print()
        print("✗ Error during recalculation:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
