"""
MMR (Matchmaking Rating) Calculator using ELO System for Badminton

This module implements an ELO-based rating system for individual players
in team-based badminton matches (singles and doubles).

Key Features:
- Individual player ratings (starting at 1500)
- Team rating is the average of both players' ratings
- Higher rated players lose more when losing to lower rated players
- Lower rated players gain more when beating higher rated players
- Both teammates gain/lose the same amount of MMR
"""

import math
from typing import List, Dict, Tuple, Optional
from datetime import datetime


DEFAULT_STARTING_RATING = 1500
DEFAULT_K_FACTOR = 24  # Moderate rate of change


def calculate_expected_score(player_rating: float, opponent_rating: float) -> float:
    """
    Calculate the expected score for a player/team against an opponent.
    
    Args:
        player_rating: Current rating of the player/team
        opponent_rating: Current rating of the opponent/team
        
    Returns:
        Expected score between 0 and 1 (probability of winning)
    """
    return 1 / (1 + math.pow(10, (opponent_rating - player_rating) / 400))


def calculate_new_rating(
    old_rating: float,
    expected_score: float,
    actual_score: float,
    k_factor: float = DEFAULT_K_FACTOR
) -> float:
    """
    Calculate new rating after a match.
    
    Args:
        old_rating: Current rating before the match
        expected_score: Expected score (0-1) from calculate_expected_score
        actual_score: Actual outcome (1 for win, 0 for loss, 0.5 for tie)
        k_factor: Rate of change factor (default: 24)
        
    Returns:
        New rating after applying the update
    """
    return old_rating + k_factor * (actual_score - expected_score)


def calculate_team_mmr(*player_ratings: float) -> float:
    """
    Calculate team MMR as the average of all player ratings.
    
    Args:
        *player_ratings: Variable number of player ratings (1 for singles, 2 for doubles)
        
    Returns:
        Average team rating
    """
    if not player_ratings:
        return DEFAULT_STARTING_RATING
    return sum(player_ratings) / len(player_ratings)


def normalize_winner(winner: any) -> Optional[str]:
    """
    Normalize winner format to 'team1' or 'team2'.
    
    Args:
        winner: Winner value from match data (could be 'team1', 'team2', 1, 2, etc.)
        
    Returns:
        'team1' or 'team2', or None if invalid
    """
    if winner in ['team1', 'Team 1', '1', 1]:
        return 'team1'
    elif winner in ['team2', 'Team 2', '2', 2]:
        return 'team2'
    elif isinstance(winner, str):
        winner_lower = winner.lower().strip()
        if 'team1' in winner_lower or winner_lower == '1':
            return 'team1'
        elif 'team2' in winner_lower or winner_lower == '2':
            return 'team2'
    return None


def process_match(
    team1_players: List[str],
    team2_players: List[str],
    winner: str,
    player_ratings: Dict[str, float],
    k_factor: float = DEFAULT_K_FACTOR
) -> Dict[str, float]:
    """
    Process a single match and update player ratings.
    
    Args:
        team1_players: List of player names in team 1
        team2_players: List of player names in team 2
        winner: 'team1' or 'team2' (or variants that will be normalized)
        player_ratings: Dictionary mapping player name to current rating
        k_factor: Rate of change factor
        
    Returns:
        Dictionary of rating changes for each player involved
        
    Raises:
        ValueError: If match data is invalid
    """
    # Validate inputs
    if not team1_players or not team2_players:
        raise ValueError("Both teams must have at least one player")
    
    # Normalize winner
    normalized_winner = normalize_winner(winner)
    if normalized_winner is None:
        raise ValueError(f"Invalid winner value: {winner}")
    
    # Initialize missing players to starting rating
    all_players = team1_players + team2_players
    for player in all_players:
        if player not in player_ratings:
            player_ratings[player] = DEFAULT_STARTING_RATING
    
    # Calculate team ratings (average of players)
    team1_ratings = [player_ratings[p] for p in team1_players]
    team2_ratings = [player_ratings[p] for p in team2_players]
    
    team1_mmr = calculate_team_mmr(*team1_ratings)
    team2_mmr = calculate_team_mmr(*team2_ratings)
    
    # Calculate expected scores
    expected_team1 = calculate_expected_score(team1_mmr, team2_mmr)
    expected_team2 = 1 - expected_team1
    
    # Determine actual scores
    actual_team1 = 1.0 if normalized_winner == 'team1' else 0.0
    actual_team2 = 1.0 - actual_team1
    
    # Calculate rating changes
    delta_team1 = k_factor * (actual_team1 - expected_team1)
    delta_team2 = k_factor * (actual_team2 - expected_team2)
    
    # Apply changes to all players (same change for teammates)
    rating_changes = {}
    
    for player in team1_players:
        player_ratings[player] += delta_team1
        rating_changes[player] = delta_team1
    
    for player in team2_players:
        player_ratings[player] += delta_team2
        rating_changes[player] = delta_team2
    
    return rating_changes


def process_matches_chronologically(
    matches: List[Dict],
    initial_ratings: Optional[Dict[str, float]] = None,
    k_factor: float = DEFAULT_K_FACTOR,
    skip_malformed: bool = True,
    build_history: bool = False
) -> Tuple[Dict[str, float], Optional[List[Dict]]]:
    """
    Process multiple matches in chronological order to calculate final ratings.
    
    Args:
        matches: List of match dictionaries with keys:
                 - timestamp: ISO format timestamp
                 - team1: List of player names
                 - team2: List of player names
                 - winner: 'team1' or 'team2' (or variants)
        initial_ratings: Optional starting ratings (defaults to 1500 for all)
        k_factor: Rate of change factor
        skip_malformed: If True, skip invalid matches instead of raising errors
        build_history: If True, build and return detailed match-by-match history
        
    Returns:
        Tuple of (final_ratings, history)
        - final_ratings: Dict mapping player name to final rating
        - history: List of match processing records (if build_history=True), else None
    """
    # Initialize ratings
    player_ratings = dict(initial_ratings) if initial_ratings else {}
    history = [] if build_history else None
    
    # Sort matches by timestamp
    sorted_matches = sorted(
        matches,
        key=lambda m: m.get('timestamp', ''),
    )
    
    skipped_count = 0
    processed_count = 0
    
    for match in sorted_matches:
        # Extract match data
        match_id = match.get('match_id', 'unknown')
        timestamp = match.get('timestamp')
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        winner = match.get('winner')
        
        # Validate match data
        if not team1 or not team2 or not winner or not timestamp:
            if skip_malformed:
                skipped_count += 1
                continue
            else:
                raise ValueError(f"Malformed match {match_id}: missing required fields")
        
        # Store pre-match ratings for history
        if build_history:
            pre_ratings = {p: player_ratings.get(p, DEFAULT_STARTING_RATING) 
                          for p in team1 + team2}
        
        try:
            # Process the match
            rating_changes = process_match(
                team1, team2, winner, player_ratings, k_factor
            )
            processed_count += 1
            
            # Build history entry
            if build_history:
                post_ratings = {p: player_ratings[p] for p in team1 + team2}
                history.append({
                    'match_id': match_id,
                    'timestamp': timestamp,
                    'team1': team1,
                    'team2': team2,
                    'winner': winner,
                    'pre_ratings': pre_ratings,
                    'post_ratings': post_ratings,
                    'rating_changes': rating_changes
                })
        
        except (ValueError, KeyError) as e:
            if skip_malformed:
                skipped_count += 1
                continue
            else:
                raise
    
    if skipped_count > 0:
        print(f"Processed {processed_count} matches, skipped {skipped_count} malformed matches")
    
    return player_ratings, history


def get_rating_summary(player_ratings: Dict[str, float]) -> Dict:
    """
    Generate a summary of the rating distribution.
    
    Args:
        player_ratings: Dictionary mapping player name to rating
        
    Returns:
        Dictionary with summary statistics
    """
    if not player_ratings:
        return {
            'player_count': 0,
            'avg_rating': 0,
            'min_rating': 0,
            'max_rating': 0,
            'std_dev': 0
        }
    
    ratings = list(player_ratings.values())
    avg_rating = sum(ratings) / len(ratings)
    
    # Calculate standard deviation
    variance = sum((r - avg_rating) ** 2 for r in ratings) / len(ratings)
    std_dev = math.sqrt(variance)
    
    return {
        'player_count': len(player_ratings),
        'avg_rating': round(avg_rating, 2),
        'min_rating': round(min(ratings), 2),
        'max_rating': round(max(ratings), 2),
        'std_dev': round(std_dev, 2)
    }
