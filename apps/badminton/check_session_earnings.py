#!/usr/bin/env python3
"""Check session earnings"""

from match_storage import MatchStorage
from datetime import datetime

storage = MatchStorage()

# Get today's session
today = datetime.now().date()
session = storage.get_or_create_session_for_date(today)
session_id = session['session_id']

print(f"Session ID: {session_id}")
print(f"Date: {session['date']}")

# Get matches for this session
matches = storage.get_session_matches(session_id)
print(f"\nMatches in this session: {len(matches)}")

# Show last 3 matches
print("\nLast 3 matches:")
for match in matches[-3:]:
    print(f"\n  Match {match['match_id']}:")
    print(f"    {match['team1']} vs {match['team2']}")
    print(f"    Score: {match['team1_score']}-{match['team2_score']}")
    print(f"    Winner: {match['winner']}")
    print(f"    Game value: ${match['game_value']}")
    print(f"    No-bet status: {match.get('player_no_bet_status', {})}")

# Get session earnings
print("\n" + "=" * 60)
print("SESSION EARNINGS:")
print("=" * 60)
session_earnings = storage.get_session_player_stats(session_id)

for player, stats in sorted(session_earnings.items()):
    print(f"{player:15} | Games: {stats['games_played']:2} | Wins: ${stats['total_winnings']:6.2f} | Losses: ${stats['total_losses']:6.2f} | Net: ${stats['net_earnings']:+7.2f}")
