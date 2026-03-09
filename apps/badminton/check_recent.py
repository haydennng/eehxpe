#!/usr/bin/env python3
from match_storage import MatchStorage

s = MatchStorage()
matches = s.get_all_matches()
print(f'Total matches: {len(matches)}')
print('\nLast 5 matches:')
for m in matches[-5:]:
    print(f"\n{m['match_id']}: {m['team1']} vs {m['team2']}")
    print(f"  Score: {m['team1_score']}-{m['team2_score']}")
    print(f"  Winner: {m['winner']}")
    print(f"  No-bet: {m.get('player_no_bet_status', {})}")
