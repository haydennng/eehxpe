"""
Database-Based MMR Calculator

This module provides MMR calculation functions that work directly with the database
instead of JSON files. It updates User.mmr fields and Match.mmr_change fields.
"""

from typing import Dict, Tuple
from database import session_scope
from models import User, Match
from mmr_calculator import (
    process_match,
    DEFAULT_STARTING_RATING,
    DEFAULT_K_FACTOR
)


def recalculate_all_mmr(k_factor: float = DEFAULT_K_FACTOR) -> Dict[str, float]:
    """
    Recalculate MMR for all players based on all matches in the database.
    
    This function:
    1. Resets all players to starting MMR (1500)
    2. Processes all matches chronologically
    3. Updates User.mmr for each player
    4. Updates Match.mmr_change for each match
    
    Args:
        k_factor: ELO k-factor for rating changes (default: 24)
        
    Returns:
        Dictionary mapping username to final MMR rating
    """
    with session_scope() as session:
        # Get all users and reset MMR to starting rating
        users = session.query(User).all()
        player_ratings = {}
        
        for user in users:
            user.mmr = DEFAULT_STARTING_RATING
            player_ratings[user.username] = DEFAULT_STARTING_RATING
        
        # Get all matches ordered chronologically
        matches = session.query(Match).order_by(Match.created_at).all()
        
        # Process each match
        for match in matches:
            # Get player usernames
            team1_players = [match.team1_player1.username, match.team1_player2.username]
            team2_players = [match.team2_player1.username, match.team2_player2.username]
            winner = 'team1' if match.winner_team == 1 else 'team2'
            
            # Calculate rating changes
            rating_changes = process_match(
                team1_players,
                team2_players,
                winner,
                player_ratings,
                k_factor
            )
            
            # Update user MMR in database
            for username, new_rating in player_ratings.items():
                user = session.query(User).filter_by(username=username).first()
                if user:
                    user.mmr = new_rating
            
            # Store the MMR change for the match (use average change across all players)
            if rating_changes:
                # Take absolute value of any player's change (they're all the same magnitude)
                mmr_change = abs(list(rating_changes.values())[0])
                match.mmr_change = mmr_change
        
        session.commit()
        
        return player_ratings


def update_mmr_for_match(match_id: int, k_factor: float = DEFAULT_K_FACTOR) -> Tuple[Dict[str, float], float]:
    """
    Update MMR for all players involved in a specific match.
    
    This function calculates the MMR change for a single match and updates
    the User.mmr fields for all involved players, as well as the Match.mmr_change field.
    
    Args:
        match_id: Database ID of the match
        k_factor: ELO k-factor for rating changes (default: 24)
        
    Returns:
        Tuple of (rating_changes dict, mmr_change value)
        - rating_changes: Dictionary mapping username to MMR change
        - mmr_change: The absolute MMR change value
    """
    with session_scope() as session:
        # Get the match
        match = session.query(Match).filter_by(id=match_id).first()
        if not match:
            raise ValueError(f"Match with ID {match_id} not found")
        
        # Get current player ratings
        player_ratings = {
            match.team1_player1.username: match.team1_player1.mmr,
            match.team1_player2.username: match.team1_player2.mmr,
            match.team2_player1.username: match.team2_player1.mmr,
            match.team2_player2.username: match.team2_player2.mmr
        }
        
        # Get player usernames
        team1_players = [match.team1_player1.username, match.team1_player2.username]
        team2_players = [match.team2_player1.username, match.team2_player2.username]
        winner = 'team1' if match.winner_team == 1 else 'team2'
        
        # Calculate rating changes
        rating_changes = process_match(
            team1_players,
            team2_players,
            winner,
            player_ratings,
            k_factor
        )
        
        # Update user MMR in database
        for username, new_rating in player_ratings.items():
            user = session.query(User).filter_by(username=username).first()
            if user:
                user.mmr = new_rating
        
        # Calculate and store MMR change
        mmr_change = abs(list(rating_changes.values())[0]) if rating_changes else 0.0
        match.mmr_change = mmr_change
        
        session.commit()
        
        return rating_changes, mmr_change


def get_player_mmr_history(username: str) -> list:
    """
    Get the MMR history for a specific player across all their matches.
    
    Args:
        username: Player's username
        
    Returns:
        List of tuples: (match_id, timestamp, mmr_after_match, mmr_change)
    """
    with session_scope() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return []
        
        # Get all matches involving this player, ordered chronologically
        from sqlalchemy import or_
        matches = session.query(Match).filter(
            or_(
                Match.team1_player1_id == user.id,
                Match.team1_player2_id == user.id,
                Match.team2_player1_id == user.id,
                Match.team2_player2_id == user.id
            )
        ).order_by(Match.created_at).all()
        
        # Reconstruct MMR history by replaying matches
        player_ratings = {username: DEFAULT_STARTING_RATING}
        history = []
        
        for match in matches:
            # Get player usernames
            team1_players = [match.team1_player1.username, match.team1_player2.username]
            team2_players = [match.team2_player1.username, match.team2_player2.username]
            
            # Initialize ratings for all players in this match
            for player in team1_players + team2_players:
                if player not in player_ratings:
                    player_ratings[player] = DEFAULT_STARTING_RATING
            
            winner = 'team1' if match.winner_team == 1 else 'team2'
            
            # Calculate rating changes
            rating_changes = process_match(
                team1_players,
                team2_players,
                winner,
                player_ratings,
                DEFAULT_K_FACTOR
            )
            
            # Record this player's MMR after this match
            mmr_after = player_ratings[username]
            mmr_change = rating_changes.get(username, 0.0)
            
            history.append((
                match.id,
                match.created_at,
                mmr_after,
                mmr_change
            ))
        
        return history
