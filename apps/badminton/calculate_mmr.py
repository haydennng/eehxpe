"""
MMR Calculation Script

This script recalculates all player MMR ratings from historical match data
and updates the players.json file with the new ratings.

Usage:
    python calculate_mmr.py --write
    python calculate_mmr.py --dry-run
    python calculate_mmr.py --write --history data/mmr_history.json
    python calculate_mmr.py --write --k-factor 32
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from mmr_calculator import (
    process_matches_chronologically,
    get_rating_summary,
    DEFAULT_K_FACTOR,
    DEFAULT_STARTING_RATING
)


def load_json_file(file_path: Path) -> any:
    """Load data from a JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(file_path: Path, data: any, indent: int = 2):
    """Save data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def backup_file(file_path: Path):
    """Create a backup of a file with timestamp."""
    if not file_path.exists():
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.with_suffix(f'.backup.{timestamp}{file_path.suffix}')
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path


def calculate_mmr_ratings(
    matches_file: Path,
    players_file: Path,
    k_factor: float = DEFAULT_K_FACTOR,
    build_history: bool = False
) -> tuple:
    """
    Calculate MMR ratings from match history.
    
    Returns:
        Tuple of (player_ratings, history, players_data)
    """
    # Load match data
    print(f"Loading matches from {matches_file}...")
    matches = load_json_file(matches_file)
    print(f"Loaded {len(matches)} matches")
    
    # Load player data
    print(f"Loading players from {players_file}...")
    players_data = load_json_file(players_file)
    
    # Handle both list and dict formats for players
    if isinstance(players_data, dict) and 'players' in players_data:
        players_list = players_data['players']
    elif isinstance(players_data, list):
        players_list = players_data
        players_data = {'players': players_list}
    else:
        raise ValueError("Unexpected players.json format")
    
    print(f"Loaded {len(players_list)} players")
    
    # Process matches chronologically
    print(f"\nProcessing matches chronologically (K-factor: {k_factor})...")
    player_ratings, history = process_matches_chronologically(
        matches,
        initial_ratings=None,  # Start everyone at 1500
        k_factor=k_factor,
        skip_malformed=True,
        build_history=build_history
    )
    
    # Generate summary
    summary = get_rating_summary(player_ratings)
    print(f"\n{'='*60}")
    print("MMR Calculation Summary")
    print(f"{'='*60}")
    print(f"Players with ratings: {summary['player_count']}")
    print(f"Average rating:       {summary['avg_rating']:.2f}")
    print(f"Min rating:           {summary['min_rating']:.2f}")
    print(f"Max rating:           {summary['max_rating']:.2f}")
    print(f"Standard deviation:   {summary['std_dev']:.2f}")
    print(f"{'='*60}\n")
    
    # Show top and bottom players
    sorted_players = sorted(player_ratings.items(), key=lambda x: x[1], reverse=True)
    
    print("Top 5 Players:")
    for i, (player, rating) in enumerate(sorted_players[:5], 1):
        print(f"  {i}. {player}: {rating:.2f}")
    
    print("\nBottom 5 Players:")
    for i, (player, rating) in enumerate(sorted_players[-5:], 1):
        print(f"  {i}. {player}: {rating:.2f}")
    
    return player_ratings, history, players_data


def update_players_with_mmr(
    players_data: Dict,
    player_ratings: Dict[str, float],
    players_file: Path,
    write: bool = False
) -> Dict:
    """
    Update players data with MMR ratings.
    
    Returns:
        Updated players_data
    """
    # Get players list
    if isinstance(players_data, dict) and 'players' in players_data:
        players_list = players_data['players']
    else:
        players_list = players_data
    
    # Round ratings to integers and update
    updated_count = 0
    new_count = 0
    
    for player in players_list:
        player_name = player['name']
        
        if player_name in player_ratings:
            new_rating = round(player_ratings[player_name])
            old_rating = player.get('mmr')
            
            player['mmr'] = new_rating
            
            if old_rating is None:
                new_count += 1
            elif old_rating != new_rating:
                updated_count += 1
        else:
            # Player exists in players.json but has no matches
            if 'mmr' not in player:
                player['mmr'] = DEFAULT_STARTING_RATING
                new_count += 1
    
    print(f"\nPlayer MMR Updates:")
    print(f"  New MMR fields added:  {new_count}")
    print(f"  Existing MMRs updated: {updated_count}")
    
    if write:
        # Create backup before writing
        backup_file(players_file)
        
        # Write updated data
        save_json_file(players_file, players_data)
        print(f"\n✓ Updated {players_file}")
    else:
        print(f"\n⚠ Dry-run mode: {players_file} not modified")
    
    return players_data


def save_history(history: List[Dict], history_file: Path):
    """Save MMR history to a file."""
    print(f"\nSaving history to {history_file}...")
    
    # Round all ratings in history for readability
    for entry in history:
        for key in ['pre_ratings', 'post_ratings', 'rating_changes']:
            if key in entry:
                entry[key] = {
                    player: round(rating, 2)
                    for player, rating in entry[key].items()
                }
    
    save_json_file(history_file, history, indent=2)
    print(f"✓ Saved {len(history)} match records to {history_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Calculate MMR ratings from match history'
    )
    parser.add_argument(
        '--write',
        action='store_true',
        help='Write updated MMR values to players.json (default: dry-run)'
    )
    parser.add_argument(
        '--history',
        type=str,
        metavar='PATH',
        help='Save detailed match-by-match history to specified file'
    )
    parser.add_argument(
        '--k-factor',
        type=float,
        default=DEFAULT_K_FACTOR,
        metavar='K',
        help=f'K-factor for rating changes (default: {DEFAULT_K_FACTOR})'
    )
    parser.add_argument(
        '--matches-file',
        type=str,
        default='data/matches.json',
        help='Path to matches.json file (default: data/matches.json)'
    )
    parser.add_argument(
        '--players-file',
        type=str,
        default='data/players.json',
        help='Path to players.json file (default: data/players.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Alias for not using --write (compute without saving)'
    )
    
    args = parser.parse_args()
    
    # Handle dry-run flag
    if args.dry_run:
        args.write = False
    
    # Convert paths
    matches_file = Path(args.matches_file)
    players_file = Path(args.players_file)
    
    # Validate files exist
    if not matches_file.exists():
        print(f"Error: Matches file not found: {matches_file}")
        return 1
    
    if not players_file.exists():
        print(f"Error: Players file not found: {players_file}")
        return 1
    
    try:
        # Calculate MMR ratings
        player_ratings, history, players_data = calculate_mmr_ratings(
            matches_file,
            players_file,
            k_factor=args.k_factor,
            build_history=args.history is not None
        )
        
        # Update players data
        update_players_with_mmr(
            players_data,
            player_ratings,
            players_file,
            write=args.write
        )
        
        # Save history if requested
        if args.history:
            history_file = Path(args.history)
            save_history(history, history_file)
        
        print("\n✓ MMR calculation completed successfully!")
        
        if not args.write:
            print("\nNote: Run with --write to persist changes to players.json")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
