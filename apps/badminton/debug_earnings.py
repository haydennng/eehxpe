#!/usr/bin/env python3
"""Debug earnings calculation for a specific match"""

from match_storage import MatchStorage

storage = MatchStorage()

# Get matches
matches = storage.get_all_matches()

# Find match 300
match_300 = None
for m in matches:
    if m['match_id'] == 'match_300':
        match_300 = m
        break

if not match_300:
    print("Match 300 not found!")
    exit(1)

print("Match 300 Details:")
print(f"  Team 1: {match_300['team1']}")
print(f"  Team 2: {match_300['team2']}")
print(f"  Scores: {match_300['team1_score']}-{match_300['team2_score']}")
print(f"  Game Value: ${match_300['game_value']}")
print(f"  Winner: {match_300['winner']}")
print(f"  No-bet status: {match_300.get('player_no_bet_status', {})}")

# Manually calculate earnings for this one match
team1 = match_300['team1']
team2 = match_300['team2']
team1_score = match_300['team1_score']
team2_score = match_300['team2_score']
game_value = match_300['game_value']
no_bet_status = match_300.get('player_no_bet_status', {})

print("\n\nManual Earnings Calculation:")
print("=" * 60)

player_stats = {p: {'winnings': 0, 'losses': 0} for p in team1 + team2}

if team1_score > team2_score:
    print("Team 1 WINS")
    no_bet_losers = [p for p in team2 if no_bet_status.get(p, False)]
    print(f"No-bet losers on Team 2: {no_bet_losers}")
    
    print("\nProcessing Team 1 (winners):")
    for player in team1:
        is_no_bet = no_bet_status.get(player, False)
        print(f"  {player}: no_bet={is_no_bet}")
        if is_no_bet:
            print(f"    -> Gets $0 (no-bet player)")
        else:
            if len(no_bet_losers) > 0:
                winnings = game_value / 2
                print(f"    -> Gets ${winnings} (split because opponent is no-bet)")
                player_stats[player]['winnings'] = winnings
            else:
                print(f"    -> Gets ${game_value} (full amount)")
                player_stats[player]['winnings'] = game_value
    
    print("\nProcessing Team 2 (losers):")
    for player in team2:
        is_no_bet = no_bet_status.get(player, False)
        print(f"  {player}: no_bet={is_no_bet}")
        if is_no_bet:
            print(f"    -> Loses $0 (no-bet player)")
        else:
            print(f"    -> Loses ${game_value} (full amount)")
            player_stats[player]['losses'] = game_value

print("\n\nFinal Earnings for this match:")
for player, stats in player_stats.items():
    net = stats['winnings'] - stats['losses']
    print(f"  {player}: +${stats['winnings']:.2f} / -${stats['losses']:.2f} = ${net:+.2f}")
