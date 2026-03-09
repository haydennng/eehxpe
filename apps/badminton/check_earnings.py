#!/usr/bin/env python3
"""Check earnings calculation for recent matches"""

from match_storage import MatchStorage

storage = MatchStorage()

# Get all matches and compute earnings
matches = storage.get_all_matches()
print(f"Total matches: {len(matches)}")

# Get the most recent match
if matches:
    recent_match = matches[-1]  # Should be most recent based on ID
    print(f"\nMost recent match:")
    print(f"  Match ID: {recent_match['match_id']}")
    print(f"  Team 1: {recent_match['team1']}")
    print(f"  Team 2: {recent_match['team2']}")
    print(f"  Scores: {recent_match['team1_score']}-{recent_match['team2_score']}")
    print(f"  Game Value: ${recent_match['game_value']}")
    print(f"  Winner: {recent_match['winner']}")
    print(f"  No-bet status: {recent_match.get('player_no_bet_status', {})}")

# Compute earnings for all players
earnings = storage.get_all_player_earnings()

print("\n\nPlayer Earnings:")
print("-" * 60)
for player, stats in sorted(earnings.items()):
    print(f"{player:15} | Wins: ${stats['total_winnings']:6.2f} | Losses: ${stats['total_losses']:6.2f} | Net: ${stats['net_earnings']:6.2f}")
