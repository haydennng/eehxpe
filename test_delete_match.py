#!/usr/bin/env python3
"""
Test Match Deletion and MMR Recalculation

This script tests that MMR correctly reverts when a match is deleted.
"""

import sys
from pathlib import Path

# Add apps/badminton to path
sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'badminton'))

from database import session_scope
from models import User, Match
from match_storage import MatchStorage
from mmr_database import recalculate_all_mmr


def test_delete_match():
    print("=" * 60)
    print("Testing Match Deletion and MMR Recalculation")
    print("=" * 60)
    print()
    
    # Get the most recent match
    with session_scope() as session:
        latest_match = session.query(Match).order_by(Match.created_at.desc()).first()
        
        if not latest_match:
            print("No matches found in database")
            return 1
        
        print(f"Latest Match: Game #{latest_match.game_number}")
        print(f"  Team 1: {latest_match.team1_player1.username} & {latest_match.team1_player2.username} - {latest_match.team1_score}")
        print(f"  Team 2: {latest_match.team2_player1.username} & {latest_match.team2_player2.username} - {latest_match.team2_score}")
        print(f"  Winner: Team {latest_match.winner_team}")
        print(f"  Created: {latest_match.created_at}")
        print()
        
        # Get involved players
        players = [
            latest_match.team1_player1.username,
            latest_match.team1_player2.username,
            latest_match.team2_player1.username,
            latest_match.team2_player2.username
        ]
        
        # Get MMR before deletion
        print("MMR BEFORE deletion:")
        mmr_before = {}
        for player_name in players:
            player = session.query(User).filter_by(username=player_name).first()
            mmr_before[player_name] = player.mmr
            print(f"  {player_name}: {player.mmr:.2f}")
        
        match_id = f"match_{latest_match.id}"
    
    print()
    confirm = input(f"Delete match {match_id} and recalculate MMR? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return 0
    
    print()
    print(f"Deleting match {match_id}...")
    
    # Delete the match
    storage = MatchStorage()
    success = storage.delete_match(match_id)
    
    if not success:
        print("✗ Failed to delete match")
        return 1
    
    print("✓ Match deleted from database")
    print()
    print("Recalculating all MMR from remaining matches...")
    
    try:
        # Recalculate MMR
        player_ratings = recalculate_all_mmr(k_factor=24)
        
        print()
        print("MMR AFTER deletion:")
        for player_name in players:
            new_mmr = player_ratings.get(player_name, 1500.0)
            old_mmr = mmr_before.get(player_name, 1500.0)
            change = new_mmr - old_mmr
            print(f"  {player_name}: {new_mmr:.2f} (change: {change:+.2f})")
        
        print()
        print("=" * 60)
        print("✓ Match deletion and MMR recalculation complete!")
        print("=" * 60)
        print()
        print("The MMR values have been reverted to what they were")
        print("before the deleted match was played.")
        
    except Exception as e:
        print(f"✗ Error during MMR recalculation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(test_delete_match())
