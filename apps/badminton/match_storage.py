"""
Database-Backed Match Storage System

Replacement for JSON-based MatchStorage that uses SQLAlchemy database.
Maintains API compatibility with the original match_storage.py.
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from database import session_scope
from models import User, Session, Match as MatchModel


class MatchStorage:
    """Database-backed match storage with compatible API"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the match storage system.
        data_dir parameter kept for API compatibility but not used.
        """
        # data_dir not used in database version but kept for compatibility
        pass
    
    def save_match(self, match_data: Dict) -> str:
        """
        Save a match to the database.
        
        Args:
            match_data: Dictionary containing match information with keys:
                - team1: List of 2 player usernames
                - team2: List of 2 player usernames
                - team1_score: integer
                - team2_score: integer
                - game_value: float
                - game_number: integer
                - winner: 'team1' or 'team2'
                - session_id: optional, defaults to today's session
                
        Returns:
            Match ID (string version of database ID)
        """
        with session_scope() as session:
            # Get or create session
            if 'session_id' in match_data and isinstance(match_data['session_id'], int):
                db_session_id = match_data['session_id']
            else:
                # Get today's session
                today = datetime.now().date()
                db_session_obj = self._get_or_create_session_for_date(today, session)
                db_session_id = db_session_obj.id
            
            # Get player IDs
            team1 = match_data.get('team1', [])
            team2 = match_data.get('team2', [])
            
            if len(team1) != 2 or len(team2) != 2:
                raise ValueError("Each team must have exactly 2 players")
            
            team1_p1 = session.query(User).filter_by(username=team1[0]).first()
            team1_p2 = session.query(User).filter_by(username=team1[1]).first()
            team2_p1 = session.query(User).filter_by(username=team2[0]).first()
            team2_p2 = session.query(User).filter_by(username=team2[1]).first()
            
            if not all([team1_p1, team1_p2, team2_p1, team2_p2]):
                missing = []
                if not team1_p1: missing.append(team1[0])
                if not team1_p2: missing.append(team1[1])
                if not team2_p1: missing.append(team2[0])
                if not team2_p2: missing.append(team2[1])
                raise ValueError(f"Unknown players: {', '.join(missing)}")
            
            # Determine winner team
            winner = match_data.get('winner', 'team1')
            winner_team = 1 if winner == 'team1' else 2
            
            # Create match
            match = MatchModel(
                session_id=db_session_id,
                game_number=match_data.get('game_number', 1),
                team1_player1_id=team1_p1.id,
                team1_player2_id=team1_p2.id,
                team2_player1_id=team2_p1.id,
                team2_player2_id=team2_p2.id,
                team1_score=match_data.get('team1_score', 0),
                team2_score=match_data.get('team2_score', 0),
                game_value=match_data.get('game_value', 0.0),
                winner_team=winner_team,
                mmr_change=match_data.get('mmr_change', 0.0)
            )
            
            session.add(match)
            session.flush()
            
            match_id = f"match_{match.id}"
            return match_id
    
    def get_all_matches(self) -> List[Dict]:
        """Get all matches from database"""
        with session_scope() as session:
            matches = session.query(MatchModel).all()
            return [self._match_to_dict(m) for m in matches]
    
    def get_matches_by_player(self, player_name: str) -> List[Dict]:
        """Get all matches involving a specific player"""
        with session_scope() as session:
            player = session.query(User).filter_by(username=player_name).first()
            if not player:
                return []
            
            from sqlalchemy import or_
            matches = session.query(MatchModel).filter(
                or_(
                    MatchModel.team1_player1_id == player.id,
                    MatchModel.team1_player2_id == player.id,
                    MatchModel.team2_player1_id == player.id,
                    MatchModel.team2_player2_id == player.id
                )
            ).all()
            
            return [self._match_to_dict(m) for m in matches]
    
    def get_recent_matches(self, limit: int = 10) -> List[Dict]:
        """Get the most recent matches"""
        with session_scope() as session:
            matches = session.query(MatchModel)\
                .order_by(MatchModel.created_at.desc())\
                .limit(limit)\
                .all()
            return [self._match_to_dict(m) for m in matches]
    
    def delete_match(self, match_id: str) -> bool:
        """Delete a match by ID"""
        with session_scope() as session:
            # Extract numeric ID from match_id string
            try:
                numeric_id = int(match_id.replace('match_', ''))
            except:
                return False
            
            match = session.query(MatchModel).filter_by(id=numeric_id).first()
            if match:
                session.delete(match)
                return True
            return False
    
    def get_or_create_session_for_date(self, session_date: date) -> Dict:
        """Get or create a session for a specific date"""
        with session_scope() as session:
            db_session = self._get_or_create_session_for_date(session_date, session)
            return self._session_to_dict(db_session)
    
    def _get_or_create_session_for_date(self, session_date: date, session) -> Session:
        """Internal helper to get or create session (within transaction)"""
        db_session = session.query(Session)\
            .filter(Session.session_date >= datetime.combine(session_date, datetime.min.time()))\
            .filter(Session.session_date < datetime.combine(session_date, datetime.max.time()))\
            .first()
        
        if not db_session:
            db_session = Session(
                session_date=datetime.combine(session_date, datetime.min.time()),
                notes=None
            )
            session.add(db_session)
            session.flush()
        
        return db_session
    
    def get_current_session(self) -> Dict:
        """Get or create today's session"""
        today = datetime.now().date()
        return self.get_or_create_session_for_date(today)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a specific session by ID"""
        with session_scope() as session:
            # Handle both string and int session IDs
            try:
                if isinstance(session_id, str) and session_id.startswith('session_'):
                    # Old format: session_YYYY-MM-DD
                    # We need to find by date
                    date_str = session_id.replace('session_', '')
                    session_date = datetime.fromisoformat(date_str).date()
                    db_session = session.query(Session)\
                        .filter(Session.session_date >= datetime.combine(session_date, datetime.min.time()))\
                        .filter(Session.session_date < datetime.combine(session_date, datetime.max.time()))\
                        .first()
                else:
                    numeric_id = int(session_id)
                    db_session = session.query(Session).filter_by(id=numeric_id).first()
                
                if db_session:
                    return self._session_to_dict(db_session)
            except:
                pass
            return None
    
    def get_all_sessions(self) -> List[Dict]:
        """Get all sessions"""
        with session_scope() as session:
            sessions = session.query(Session).all()
            return [self._session_to_dict(s) for s in sessions]
    
    def get_session_matches(self, session_id: str) -> List[Dict]:
        """Get all matches in a session"""
        with session_scope() as session:
            # Parse session ID
            try:
                if isinstance(session_id, str) and session_id.startswith('session_'):
                    date_str = session_id.replace('session_', '')
                    session_date = datetime.fromisoformat(date_str).date()
                    db_session = session.query(Session)\
                        .filter(Session.session_date >= datetime.combine(session_date, datetime.min.time()))\
                        .filter(Session.session_date < datetime.combine(session_date, datetime.max.time()))\
                        .first()
                else:
                    numeric_id = int(session_id)
                    db_session = session.query(Session).filter_by(id=numeric_id).first()
                
                if db_session:
                    return [self._match_to_dict(m) for m in db_session.matches]
            except:
                pass
            return []
    
    def get_sessions_summary(self) -> List[Dict]:
        """Get summary information for all sessions"""
        with session_scope() as session:
            sessions = session.query(Session).order_by(Session.session_date.desc()).all()
            
            summaries = []
            for sess in sessions:
                # Get unique players from matches
                players = set()
                for match in sess.matches:
                    players.add(match.team1_player1.username)
                    players.add(match.team1_player2.username)
                    players.add(match.team2_player1.username)
                    players.add(match.team2_player2.username)
                
                summaries.append({
                    'session_id': f'session_{sess.session_date.date()}',
                    'date': sess.session_date.isoformat(),
                    'match_count': len(sess.matches),
                    'players': sorted(list(players))
                })
            
            # Filter out sessions with no matches
            summaries = [s for s in summaries if s['match_count'] > 0]
            return summaries
    
    def get_player_stats(self, player_name: str) -> Dict:
        """Calculate statistics for a specific player"""
        matches = self.get_matches_by_player(player_name)
        
        stats = {
            'total_matches': len(matches),
            'wins': 0,
            'losses': 0,
            'total_earnings': 0.0,
            'total_winnings': 0.0,
            'total_losses': 0.0,
            'net_earnings': 0.0,
            'partners': set(),
            'opponents': set()
        }
        
        for match in matches:
            team1 = match.get('team1', [])
            team2 = match.get('team2', [])
            team1_score = match.get('team1_score', 0)
            team2_score = match.get('team2_score', 0)
            game_value = match.get('game_value', 0.0)
            
            on_team1 = player_name in team1
            
            # Track partners and opponents
            if on_team1:
                stats['partners'].update([p for p in team1 if p != player_name])
                stats['opponents'].update(team2)
                
                if team1_score > team2_score:
                    stats['wins'] += 1
                    stats['total_winnings'] += game_value
                elif team1_score < team2_score:
                    stats['losses'] += 1
                    stats['total_losses'] += game_value
            else:
                stats['partners'].update([p for p in team2 if p != player_name])
                stats['opponents'].update(team1)
                
                if team2_score > team1_score:
                    stats['wins'] += 1
                    stats['total_winnings'] += game_value
                elif team2_score < team1_score:
                    stats['losses'] += 1
                    stats['total_losses'] += game_value
        
        stats['net_earnings'] = stats['total_winnings'] - stats['total_losses']
        stats['total_earnings'] = stats['net_earnings']  # Alias for compatibility
        stats['partners'] = list(stats['partners'])
        stats['opponents'] = list(stats['opponents'])
        
        if stats['total_matches'] > 0:
            stats['win_rate'] = round(stats['wins'] / stats['total_matches'] * 100, 1)
        else:
            stats['win_rate'] = 0.0
        
        return stats
    
    def delete_session(self, session_id: str) -> Dict:
        """Delete a session and all its matches"""
        with session_scope() as session:
            try:
                if isinstance(session_id, str) and session_id.startswith('session_'):
                    date_str = session_id.replace('session_', '')
                    session_date = datetime.fromisoformat(date_str).date()
                    db_session = session.query(Session)\
                        .filter(Session.session_date >= datetime.combine(session_date, datetime.min.time()))\
                        .filter(Session.session_date < datetime.combine(session_date, datetime.max.time()))\
                        .first()
                else:
                    numeric_id = int(session_id)
                    db_session = session.query(Session).filter_by(id=numeric_id).first()
                
                if db_session:
                    match_count = len(db_session.matches)
                    session.delete(db_session)  # Cascade will delete matches
                    return {'deleted_matches': match_count}
            except:
                pass
            return {'deleted_matches': 0}
    
    def _match_to_dict(self, match: MatchModel) -> Dict:
        """Convert database Match to dict format compatible with old API"""
        return {
            'match_id': f'match_{match.id}',
            'timestamp': match.created_at.isoformat() if match.created_at else datetime.now().isoformat(),
            'session_id': f'session_{match.session.session_date.date()}' if match.session else 'unknown',
            'game_number': match.game_number,
            'team1': [match.team1_player1.username, match.team1_player2.username],
            'team2': [match.team2_player1.username, match.team2_player2.username],
            'team1_score': match.team1_score,
            'team2_score': match.team2_score,
            'game_value': match.game_value,
            'winner': 'team1' if match.winner_team == 1 else 'team2'
        }
    
    def _session_to_dict(self, sess: Session) -> Dict:
        """Convert database Session to dict format compatible with old API"""
        match_ids = [f'match_{m.id}' for m in sess.matches]
        return {
            'session_id': f'session_{sess.session_date.date()}',
            'date': sess.session_date.date().isoformat(),
            'match_ids': match_ids,
            'created_at': sess.created_at.isoformat() if sess.created_at else datetime.now().isoformat()
        }
    
    def migrate_matches_to_sessions(self):
        """Migrate matches to sessions (no-op for database version)."""
        # Already handled by database migration - this is a no-op for compatibility
        pass
    
    def cleanup_all_empty_sessions(self) -> int:
        """Remove all sessions that have no matches."""
        with session_scope() as session:
            # Find sessions with no matches
            empty_sessions = session.query(Session).filter(
                ~Session.matches.any()
            ).all()
            
            count = len(empty_sessions)
            for sess in empty_sessions:
                session.delete(sess)
            
            return count
    
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
