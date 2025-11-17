"""
Match Storage System for Badminton Matchups

This module handles persistence of match history using JSON files.
"""

import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional
from pathlib import Path
import threading


class MatchStorage:
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the match storage system.
        
        Args:
            data_dir: Directory to store match data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.matches_file = self.data_dir / "matches.json"
        self.sessions_file = self.data_dir / "sessions.json"
        self.lock = threading.Lock()
        
    def _load_json(self, file_path: Path):
        """Load data from a JSON file."""
        if not file_path.exists():
            return [] if file_path == self.matches_file else {}
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return [] if file_path == self.matches_file else {}
    
    def _save_json(self, file_path: Path, data):
        """Save data to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_local_today(self) -> date:
        """Get the current local date."""
        return datetime.now().date()
    
    def _date_from_timestamp(self, ts_str: str) -> date:
        """Parse a date from an ISO timestamp string."""
        try:
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            return dt.date()
        except (ValueError, AttributeError):
            return self._get_local_today()
    
    def _get_session_id_for_date(self, session_date: date) -> str:
        """Generate session ID from a date."""
        return f"session_{session_date.isoformat()}"
    
    def save_match(self, match_data: Dict) -> str:
        """
        Save a match to the history and associate with current session.
        
        Args:
            match_data: Dictionary containing match information
            
        Returns:
            Match ID
        """
        with self.lock:
            matches = self._load_json(self.matches_file)
            
            # Generate match ID
            match_id = f"match_{len(matches) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            timestamp = datetime.now().isoformat()
            
            # Determine session
            if 'session_id' in match_data:
                session_id = match_data['session_id']
            else:
                # Auto-associate with current session (unlocked version since we hold lock)
                today = self._get_local_today()
                session = self._get_or_create_session_for_date_unlocked(today)
                session_id = session['session_id']
            
            # Add metadata
            match_record = {
                'match_id': match_id,
                'timestamp': timestamp,
                'session_id': session_id,
                **{k: v for k, v in match_data.items() if k != 'session_id'}
            }
            
            matches.append(match_record)
            self._save_json(self.matches_file, matches)
            
            # Add match to session
            self._add_match_to_session(session_id, match_id)
            
            return match_id
    
    def get_all_matches(self) -> List[Dict]:
        """
        Retrieve all matches from history.
        
        Returns:
            List of match dictionaries
        """
        return self._load_json(self.matches_file)
    
    def get_matches_by_player(self, player_name: str) -> List[Dict]:
        """
        Get all matches involving a specific player.
        
        Args:
            player_name: Name of the player
            
        Returns:
            List of matches involving the player
        """
        all_matches = self.get_all_matches()
        player_matches = []
        
        for match in all_matches:
            team1 = match.get('team1', [])
            team2 = match.get('team2', [])
            if player_name in team1 or player_name in team2:
                player_matches.append(match)
        
        return player_matches
    
    def get_recent_matches(self, limit: int = 10) -> List[Dict]:
        """
        Get the most recent matches.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of recent matches
        """
        matches = self.get_all_matches()
        return matches[-limit:] if matches else []
    
    def delete_match(self, match_id: str) -> bool:
        """
        Delete a single match and remove from its session.
        
        Args:
            match_id: Match identifier
            
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            matches = self.get_all_matches()
            
            # Find the match
            match_to_delete = None
            for m in matches:
                if m.get('match_id') == match_id:
                    match_to_delete = m
                    break
            
            if not match_to_delete:
                return False
            
            # Remove from session
            session_id = match_to_delete.get('session_id')
            if session_id:
                self._remove_match_from_session(session_id, match_id)
            
            # Remove match
            matches = [m for m in matches if m.get('match_id') != match_id]
            self._save_json(self.matches_file, matches)
            
            return True
    
    def _get_or_create_session_for_date_unlocked(self, session_date: date) -> Dict:
        """
        Internal method: Get or create a session for a specific date.
        Does not acquire lock - caller must hold lock.
        
        Args:
            session_date: Date for the session
            
        Returns:
            Session dictionary
        """
        sessions = self._load_json(self.sessions_file)
        session_id = self._get_session_id_for_date(session_date)
        
        # Check if session exists
        if session_id in sessions:
            return sessions[session_id]
        
        # Create new session
        session = {
            'session_id': session_id,
            'date': session_date.isoformat(),
            'match_ids': [],
            'created_at': datetime.now().isoformat()
        }
        
        sessions[session_id] = session
        self._save_json(self.sessions_file, sessions)
        
        return session
    
    def get_or_create_session_for_date(self, session_date: date) -> Dict:
        """
        Get or create a session for a specific date.
        
        Args:
            session_date: Date for the session
            
        Returns:
            Session dictionary
        """
        with self.lock:
            return self._get_or_create_session_for_date_unlocked(session_date)
    
    def get_current_session(self) -> Dict:
        """
        Get or create today's session.
        
        Returns:
            Current session dictionary
        """
        today = self._get_local_today()
        return self.get_or_create_session_for_date(today)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get a specific session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session dictionary or None if not found
        """
        sessions = self._load_json(self.sessions_file)
        return sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Dict]:
        """
        Retrieve all sessions from history.
        
        Returns:
            List of session dictionaries
        """
        sessions = self._load_json(self.sessions_file)
        # Convert dict to list if needed, filtering out non-session entries
        if isinstance(sessions, dict):
            # Only return entries that have 'session_id' (are actual sessions)
            return [v for k, v in sessions.items() if isinstance(v, dict) and 'session_id' in v]
        return sessions
    
    def get_session_matches(self, session_id: str) -> List[Dict]:
        """
        Get all matches belonging to a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of match dictionaries
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        all_matches = self.get_all_matches()
        match_ids = set(session.get('match_ids', []))
        
        return [m for m in all_matches if m.get('match_id') in match_ids]
    
    def _add_match_to_session(self, session_id: str, match_id: str):
        """
        Add a match ID to a session's match list.
        Internal method - assumes lock is held.
        
        Args:
            session_id: Session identifier
            match_id: Match identifier
        """
        sessions = self._load_json(self.sessions_file)
        
        if session_id not in sessions:
            # Session doesn't exist, shouldn't happen but handle gracefully
            return
        
        if match_id not in sessions[session_id]['match_ids']:
            sessions[session_id]['match_ids'].append(match_id)
            self._save_json(self.sessions_file, sessions)
    
    def _remove_match_from_session(self, session_id: str, match_id: str):
        """
        Remove a match ID from a session's match list.
        Internal method - assumes lock is held.
        
        Args:
            session_id: Session identifier
            match_id: Match identifier
        """
        sessions = self._load_json(self.sessions_file)
        
        if session_id in sessions and match_id in sessions[session_id]['match_ids']:
            sessions[session_id]['match_ids'].remove(match_id)
            self._save_json(self.sessions_file, sessions)
    
    def delete_session(self, session_id: str) -> Dict:
        """
        Delete a session and all its matches.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with deletion info: {deleted_matches: count}
        """
        with self.lock:
            sessions = self._load_json(self.sessions_file)
            
            if session_id not in sessions:
                return {'deleted_matches': 0}
            
            # Get match IDs to delete
            match_ids_to_delete = set(sessions[session_id].get('match_ids', []))
            
            # Remove matches
            matches = self.get_all_matches()
            matches = [m for m in matches if m.get('match_id') not in match_ids_to_delete]
            self._save_json(self.matches_file, matches)
            
            # Remove session
            del sessions[session_id]
            self._save_json(self.sessions_file, sessions)
            
            return {'deleted_matches': len(match_ids_to_delete)}
    
    def get_sessions_summary(self) -> List[Dict]:
        """
        Get summary information for all sessions.
        
        Returns:
            List of session summaries with date, match_count, and players
        """
        sessions = self.get_all_sessions()
        all_matches = self.get_all_matches()
        
        # Create lookup for faster access
        match_lookup = {m['match_id']: m for m in all_matches}
        
        summaries = []
        for session in sessions:
            match_ids = session.get('match_ids', [])
            
            # Get unique players from matches
            players = set()
            for match_id in match_ids:
                match = match_lookup.get(match_id)
                if match:
                    players.update(match.get('team1', []))
                    players.update(match.get('team2', []))
            
            summaries.append({
                'session_id': session['session_id'],
                'date': session['date'],
                'match_count': len(match_ids),
                'players': sorted(list(players))
            })
        
        # Sort by date descending
        summaries.sort(key=lambda x: x['date'], reverse=True)
        
        return summaries
    
    def _compute_earnings(self, matches: List[Dict]) -> Dict[str, Dict]:
        """
        Compute earnings statistics for all players from a list of matches.
        Each player earns/loses the FULL game_value (no split).
        
        Args:
            matches: List of match dictionaries
            
        Returns:
            Dictionary keyed by player name with stats:
            - games_played: number of matches played
            - total_winnings: sum of game_value for wins (full amount)
            - total_losses: sum of game_value for losses (full amount)
            - net_earnings: total_winnings - total_losses (can be negative)
        """
        player_stats = {}
        
        for match in matches:
            team1 = match.get('team1', [])
            team2 = match.get('team2', [])
            team1_score = match.get('team1_score')
            team2_score = match.get('team2_score')
            game_value = match.get('game_value', 0)
            
            # Determine all participants
            all_players = set(team1 + team2)
            
            # Initialize player stats if not exists
            for player in all_players:
                if player not in player_stats:
                    player_stats[player] = {
                        'games_played': 0,
                        'total_winnings': 0.0,
                        'total_losses': 0.0,
                        'net_earnings': 0.0
                    }
                player_stats[player]['games_played'] += 1
            
            # Calculate earnings/losses if scores are available
            if team1_score is not None and team2_score is not None:
                if team1_score > team2_score:
                    # Team 1 wins - each player gets full game_value
                    for player in team1:
                        player_stats[player]['total_winnings'] += game_value
                    # Team 2 loses - each player loses full game_value
                    for player in team2:
                        player_stats[player]['total_losses'] += game_value
                elif team2_score > team1_score:
                    # Team 2 wins - each player gets full game_value
                    for player in team2:
                        player_stats[player]['total_winnings'] += game_value
                    # Team 1 loses - each player loses full game_value
                    for player in team1:
                        player_stats[player]['total_losses'] += game_value
                # If scores are equal, it's a tie - no earnings change
        
        # Calculate net earnings for each player
        for player in player_stats:
            player_stats[player]['net_earnings'] = round(
                player_stats[player]['total_winnings'] - player_stats[player]['total_losses'],
                2
            )
            player_stats[player]['total_winnings'] = round(player_stats[player]['total_winnings'], 2)
            player_stats[player]['total_losses'] = round(player_stats[player]['total_losses'], 2)
        
        return player_stats
    
    def get_player_stats(self, player_name: str) -> Dict:
        """
        Calculate statistics for a specific player.
        
        Args:
            player_name: Name of the player
            
        Returns:
            Dictionary with player statistics
        """
        matches = self.get_matches_by_player(player_name)
        
        # Use new earnings computation
        earnings_data = self._compute_earnings(matches)
        player_earnings = earnings_data.get(player_name, {
            'games_played': 0,
            'total_winnings': 0.0,
            'total_losses': 0.0,
            'net_earnings': 0.0
        })
        
        stats = {
            'total_matches': player_earnings['games_played'],
            'wins': 0,
            'losses': 0,
            'total_earnings': player_earnings['net_earnings'],  # Now net earnings
            'total_winnings': player_earnings['total_winnings'],
            'total_losses': player_earnings['total_losses'],
            'net_earnings': player_earnings['net_earnings'],
            'partners': set(),
            'opponents': set()
        }
        
        for match in matches:
            team1 = match.get('team1', [])
            team2 = match.get('team2', [])
            team1_score = match.get('team1_score')
            team2_score = match.get('team2_score')
            
            # Determine if player was on team1 or team2
            on_team1 = player_name in team1
            
            # Track partners and opponents
            if on_team1:
                stats['partners'].update([p for p in team1 if p != player_name])
                stats['opponents'].update(team2)
            else:
                stats['partners'].update([p for p in team2 if p != player_name])
                stats['opponents'].update(team1)
            
            # Track wins/losses if scores are available
            if team1_score is not None and team2_score is not None:
                if on_team1:
                    if team1_score > team2_score:
                        stats['wins'] += 1
                    elif team1_score < team2_score:
                        stats['losses'] += 1
                else:
                    if team2_score > team1_score:
                        stats['wins'] += 1
                    elif team2_score < team1_score:
                        stats['losses'] += 1
        
        # Convert sets to lists for JSON serialization
        stats['partners'] = list(stats['partners'])
        stats['opponents'] = list(stats['opponents'])
        
        if stats['total_matches'] > 0:
            stats['win_rate'] = round(stats['wins'] / stats['total_matches'] * 100, 1)
        else:
            stats['win_rate'] = 0.0
        
        return stats
    
    def get_session_player_stats(self, session_id: str) -> Dict[str, Dict]:
        """
        Calculate earnings statistics for all players in a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary keyed by player name with stats:
            - games_played: number of matches played in this session
            - total_winnings: sum of game_value for wins
            - total_losses: sum of game_value for losses
            - net_earnings: total_winnings - total_losses
        """
        # Get all matches for this session
        matches = self.get_session_matches(session_id)
        
        # Compute earnings using the common helper
        return self._compute_earnings(matches)
    
    def get_all_player_earnings(self) -> Dict[str, Dict]:
        """
        Calculate earnings statistics for all players across all matches.
        
        Returns:
            Dictionary keyed by player name with stats:
            - games_played: total number of matches played
            - total_winnings: sum of game_value for wins
            - total_losses: sum of game_value for losses
            - net_earnings: total_winnings - total_losses
        """
        # Get all matches
        matches = self.get_all_matches()
        
        # Compute earnings using the common helper
        return self._compute_earnings(matches)
    
    def get_monthly_player_earnings(self, year: int = None, month: int = None) -> List[Dict]:
        """
        Calculate earnings statistics for all players for a specific month.
        
        Args:
            year: Year (defaults to current year)
            month: Month (1-12, defaults to current month)
            
        Returns:
            List of player earnings dicts sorted by net_earnings descending:
            - player: player name
            - games_played: number of matches played in the month
            - total_winnings: sum of game_value for wins
            - total_losses: sum of game_value for losses
            - net_earnings: total_winnings - total_losses
        """
        # Default to current month if not specified
        now = datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        # Calculate month boundaries
        from calendar import monthrange
        month_start = datetime(year, month, 1, 0, 0, 0)
        
        # Calculate next month for upper boundary
        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1
        month_end = datetime(next_year, next_month, 1, 0, 0, 0)
        
        # Get all matches and filter by timestamp
        all_matches = self.get_all_matches()
        monthly_matches = []
        
        for match in all_matches:
            timestamp_str = match.get('timestamp')
            if not timestamp_str:
                continue
            
            try:
                # Parse timestamp
                match_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Remove timezone info for comparison
                match_dt = match_dt.replace(tzinfo=None)
                
                # Check if in month range
                if month_start <= match_dt < month_end:
                    monthly_matches.append(match)
            except (ValueError, AttributeError):
                continue
        
        # Compute earnings for filtered matches
        earnings_dict = self._compute_earnings(monthly_matches)
        
        # Convert to list format and sort
        earnings_list = [
            {
                'player': player,
                'games_played': stats['games_played'],
                'total_winnings': stats['total_winnings'],
                'total_losses': stats['total_losses'],
                'net_earnings': stats['net_earnings']
            }
            for player, stats in earnings_dict.items()
        ]
        
        # Sort by net earnings descending
        earnings_list.sort(key=lambda x: x['net_earnings'], reverse=True)
        
        return earnings_list
    
    def clear_history(self):
        """Clear all match and session history."""
        if self.matches_file.exists():
            self.matches_file.unlink()
        if self.sessions_file.exists():
            self.sessions_file.unlink()
    
    def export_to_csv(self, output_file: str):
        """
        Export match history to CSV format.
        
        Args:
            output_file: Path to output CSV file
        """
        import csv
        
        matches = self.get_all_matches()
        if not matches:
            return
        
        with open(output_file, 'w', newline='') as f:
            fieldnames = ['match_id', 'timestamp', 'team1', 'team2', 
                         'team1_score', 'team2_score', 'game_value']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for match in matches:
                row = {
                    'match_id': match.get('match_id', ''),
                    'timestamp': match.get('timestamp', ''),
                    'team1': ' & '.join(match.get('team1', [])),
                    'team2': ' & '.join(match.get('team2', [])),
                    'team1_score': match.get('team1_score', ''),
                    'team2_score': match.get('team2_score', ''),
                    'game_value': match.get('game_value', '')
                }
                writer.writerow(row)
    
    def update_session_date(self, session_id: str, new_date: date, merge: bool = False) -> Dict:
        """
        Update the date of a session.
        
        Args:
            session_id: Session identifier to update
            new_date: New date for the session (date object)
            merge: If True, merge with existing session on target date. If False, raise error on conflict.
            
        Returns:
            Updated session dictionary
            
        Raises:
            ValueError: If session not found or invalid date
            KeyError: If date conflict exists and merge is False
        """
        with self.lock:
            # Load sessions
            sessions = self._load_json(self.sessions_file)
            
            # Check if source session exists
            if session_id not in sessions:
                raise ValueError(f"Session {session_id} not found")
            
            source_session = sessions[session_id]
            current_date_str = source_session['date']
            new_date_str = new_date.isoformat()
            
            # If date hasn't changed, return unchanged
            if current_date_str == new_date_str:
                return source_session
            
            # Generate new session ID for the new date
            new_session_id = self._get_session_id_for_date(new_date)
            
            # Check if target session already exists
            target_session_exists = new_session_id in sessions and new_session_id != session_id
            
            if target_session_exists:
                if not merge:
                    raise KeyError(f"A session already exists for date {new_date_str}. Set merge=True to combine sessions.")
                
                # MERGE MODE: Move all matches from source to target session
                target_session = sessions[new_session_id]
                source_match_ids = source_session.get('match_ids', [])
                
                # Load all matches to update their session_id
                matches = self.get_all_matches()
                
                for match in matches:
                    if match.get('match_id') in source_match_ids:
                        # Update match to point to target session
                        match['session_id'] = new_session_id
                        
                        # Add to target session's match_ids if not already there
                        if match['match_id'] not in target_session['match_ids']:
                            target_session['match_ids'].append(match['match_id'])
                
                # Save updated matches
                self._save_json(self.matches_file, matches)
                
                # Delete source session
                del sessions[session_id]
                
                # Save updated sessions
                self._save_json(self.sessions_file, sessions)
                
                return target_session
            
            else:
                # NO CONFLICT: Update session in place
                # Load all matches to update their session_id
                matches = self.get_all_matches()
                source_match_ids = source_session.get('match_ids', [])
                
                for match in matches:
                    if match.get('match_id') in source_match_ids:
                        # Update match to point to new session_id
                        match['session_id'] = new_session_id
                
                # Save updated matches
                self._save_json(self.matches_file, matches)
                
                # Update session with new ID and date
                updated_session = {
                    'session_id': new_session_id,
                    'date': new_date_str,
                    'match_ids': source_session['match_ids'],
                    'created_at': source_session.get('created_at', datetime.now().isoformat())
                }
                
                # Remove old session and add updated one
                del sessions[session_id]
                sessions[new_session_id] = updated_session
                
                # Save updated sessions
                self._save_json(self.sessions_file, sessions)
                
                return updated_session
    
    def migrate_matches_to_sessions(self):
        """
        Migrate existing matches to session-based storage.
        Idempotent - can be run multiple times safely.
        """
        with self.lock:
            matches = self.get_all_matches()
            sessions = self._load_json(self.sessions_file)
            
            # Convert list to dict if needed (old format)
            if isinstance(sessions, list):
                sessions = {}
            
            migrated_count = 0
            
            for match in matches:
                # Skip if already has session_id
                if 'session_id' in match and match['session_id']:
                    continue
                
                # Determine date from timestamp
                timestamp = match.get('timestamp')
                if timestamp:
                    match_date = self._date_from_timestamp(timestamp)
                else:
                    # Fallback to today if no timestamp
                    match_date = self._get_local_today()
                
                # Get or create session for this date
                session_id = self._get_session_id_for_date(match_date)
                
                if session_id not in sessions:
                    sessions[session_id] = {
                        'session_id': session_id,
                        'date': match_date.isoformat(),
                        'match_ids': [],
                        'created_at': datetime.now().isoformat()
                    }
                
                # Add session_id to match
                match['session_id'] = session_id
                
                # Add match to session if not already there
                if match['match_id'] not in sessions[session_id]['match_ids']:
                    sessions[session_id]['match_ids'].append(match['match_id'])
                
                migrated_count += 1
            
            # Save updated data
            if migrated_count > 0:
                self._save_json(self.matches_file, matches)
                self._save_json(self.sessions_file, sessions)
                print(f"Migrated {migrated_count} matches to sessions")
            
            return migrated_count
