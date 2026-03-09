#!/usr/bin/env python3
"""
Test MMR Update on Match Recording

This script tests that MMR updates correctly when a match is recorded.
"""

import sys
from pathlib import Path

# Add apps/badminton to path
sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'badminton'))

from database import session_scope
from models import User, Match
from match_storage import MatchStorage
from mmr_database import update_mmr_for_match


def test_mmr_update():
    print("=" * 60)
    print("Testing MMR Update on Match Recording")
    print("=" * 60)
    print()
    
    # Get current MMR values
    print("Getting test players...")
    with session_scope() as session:
        test_players = session.query(User).filter(
            User.username.in_(['Hayden', 'Maric', 'Phi', 'John'])
        ).all()
        
        print("Current MMR values:")
        for player in test_players:
            print(f"  {player.username}: {player.mmr:.2f}")
    
    print()
    print("Simulating match recording...")
    print("  Team 1: Hayden & Maric (Score: 21)")
    print("  Team 2: Phi & John (Score: 15)")
    print("  Winner: Team 1 (Hayden & Maric)")
    print()
    
    # Create test match data
    match_data = {
        'game_number': 999,  # Test game number
        'team1': ['Hayden', 'Maric'],
        'team2': ['Phi', 'John'],
        'team1_score': 21,
        'team2_score': 15,
        'game_value': 5,
        'winner': 'team1',
        'player_no_bet_status': {}
    }
    
    # Save match
    storage = MatchStorage()
    try:
        match_id = storage.save_match(match_data)
        print(f"✓ Match saved with ID: {match_id}")
        
        # Extract numeric ID
        numeric_id = int(match_id.replace('match_', ''))
        
        # Update MMR
        print(f"Updating MMR for match {numeric_id}...")
        rating_changes, mmr_change = update_mmr_for_match(numeric_id)
        
        print()
        print("MMR Changes:")
        for player, change in rating_changes.items():
            print(f"  {player}: {change:+.2f}")
        print(f"\nMMR Change Value: {mmr_change:.2f}")
        
        # Get updated values
        print()
        print("Updated MMR values:")
        with session_scope() as session:
            updated_players = session.query(User).filter(
                User.username.in_(['Hayden', 'Maric', 'Phi', 'John'])
            ).all()
            for player in updated_players:
                print(f"  {player.username}: {player.mmr:.2f}")
        
        print()
        print("✓ Test completed successfully!")
        print()
        print("NOTE: Delete the test match (Game #999) from your match history")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(test_mmr_update())
