#!/usr/bin/env python3
"""Check the most recent match's no-bet status"""

from database import get_db, session_scope
from models import Match

db = get_db()

with session_scope() as s:
    matches = s.query(Match).order_by(Match.created_at.desc()).limit(1).all()
    for m in matches:
        print(f"Match ID: {m.id}")
        print(f"Team 1: {m.team1_player1.username}, {m.team1_player2.username}")
        print(f"Team 2: {m.team2_player1.username}, {m.team2_player2.username}")
        print(f"Scores: {m.team1_score}-{m.team2_score}")
        print(f"Game Value: ${m.game_value}")
        print(f"Winner: Team {m.winner_team}")
        print(f"No-bet status (raw): {repr(m.player_no_bet_status)}")
        print(f"No-bet status (type): {type(m.player_no_bet_status)}")
        
        if m.player_no_bet_status:
            print("\nNo-bet players:")
            for player, is_no_bet in m.player_no_bet_status.items():
                print(f"  {player}: {is_no_bet}")
