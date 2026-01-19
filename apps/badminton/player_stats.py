"""
Player Statistics Module

Calculate player statistics from match history.
"""

from typing import Dict, List, Optional
from sqlalchemy import or_
from database import session_scope
from models import User, Match


def get_player_stats(user_id: int) -> Dict:
    """
    Calculate comprehensive statistics for a player.
    
    Args:
        user_id: User ID to calculate stats for
        
    Returns:
        Dictionary containing player statistics
    """
    with session_scope() as session:
        # Get player
        player = session.query(User).filter_by(id=user_id).first()
        if not player:
            return None
        
        # Get all matches involving this player
        matches = session.query(Match).filter(
            or_(
                Match.team1_player1_id == user_id,
                Match.team1_player2_id == user_id,
                Match.team2_player1_id == user_id,
                Match.team2_player2_id == user_id
            )
        ).all()
        
        # Calculate basic stats
        total_matches = len(matches)
        wins = sum(1 for m in matches if m.did_player_win(user_id))
        losses = total_matches - wins
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0
        
        # Calculate earnings (net earnings = winnings - losses)
        total_winnings = sum(m.game_value for m in matches if m.did_player_win(user_id))
        total_losses = sum(m.game_value for m in matches if not m.did_player_win(user_id))
        net_earnings = total_winnings - total_losses
        
        # Get unique partners
        partners = set()
        opponents = set()
        
        for match in matches:
            # Determine which team the player was on
            if user_id in [match.team1_player1_id, match.team1_player2_id]:
                # Player was on team 1
                if match.team1_player1_id == user_id:
                    partners.add(match.team1_player2.username)
                else:
                    partners.add(match.team1_player1.username)
                opponents.add(match.team2_player1.username)
                opponents.add(match.team2_player2.username)
            else:
                # Player was on team 2
                if match.team2_player1_id == user_id:
                    partners.add(match.team2_player2.username)
                else:
                    partners.add(match.team2_player1.username)
                opponents.add(match.team1_player1.username)
                opponents.add(match.team1_player2.username)
        
        return {
            'user_id': user_id,
            'username': player.username,
            'mmr': player.mmr,
            'role': player.role.value,
            'total_matches': total_matches,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'total_earnings': round(net_earnings, 2),
            'total_winnings': round(total_winnings, 2),
            'total_losses': round(total_losses, 2),
            'net_earnings': round(net_earnings, 2),
            'partners': sorted(list(partners)),
            'opponents': sorted(list(opponents)),
            'created_at': player.created_at.isoformat() if player.created_at else None
        }


def get_all_players_stats() -> List[Dict]:
    """
    Get statistics for all players.
    
    Returns:
        List of player statistics dictionaries
    """
    with session_scope() as session:
        players = session.query(User).all()
        player_ids = [p.id for p in players]
    
    # Call get_player_stats once per player to avoid race conditions
    stats_list = []
    for pid in player_ids:
        stats = get_player_stats(pid)
        if stats:
            stats_list.append(stats)
    return stats_list


def get_leaderboard(limit: int = 10) -> List[Dict]:
    """
    Get top players by MMR.
    
    Args:
        limit: Number of players to return
        
    Returns:
        List of player statistics sorted by MMR
    """
    with session_scope() as session:
        top_players = session.query(User)\
            .order_by(User.mmr.desc())\
            .limit(limit)\
            .all()
        
        player_ids = [p.id for p in top_players]
    
    # Call get_player_stats once per player to avoid race conditions
    stats_list = []
    for pid in player_ids:
        stats = get_player_stats(pid)
        if stats:
            stats_list.append(stats)
    return stats_list


def get_player_match_history(user_id: int, limit: Optional[int] = None) -> List[Dict]:
    """
    Get match history for a player.
    
    Args:
        user_id: User ID
        limit: Optional limit on number of matches to return (most recent)
        
    Returns:
        List of match dictionaries
    """
    with session_scope() as session:
        query = session.query(Match).filter(
            or_(
                Match.team1_player1_id == user_id,
                Match.team1_player2_id == user_id,
                Match.team2_player1_id == user_id,
                Match.team2_player2_id == user_id
            )
        ).order_by(Match.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        matches = query.all()
        return [m.to_dict() for m in matches]
