#!/usr/bin/env python3
"""
JSON to Database Migration Script

Migrates existing JSON data (players, matches, sessions) to the SQLite database.
Creates user accounts for existing players and preserves all match history.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, session_scope
from auth import create_user, hash_password
from models import User, UserRole, Session, Match


# Default password for migrated players
DEFAULT_PLAYER_PASSWORD = "badminton2025"


def load_json_file(file_path):
    """Load and parse JSON file"""
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing {file_path}: {e}")
        return None


def migrate_players(players_data, session):
    """
    Migrate players from JSON to database as users.
    
    Returns:
        dict: Mapping of player names to user IDs
    """
    print("\n" + "=" * 60)
    print("Migrating Players")
    print("=" * 60)
    
    if not players_data or 'players' not in players_data:
        print("⚠️  No player data found")
        return {}
    
    players = players_data.get('players', [])
    name_to_id = {}
    
    for player_data in players:
        name = player_data.get('name')
        if not name:
            continue
        
        mmr = player_data.get('mmr', 1500.0)
        
        # Check if user already exists
        existing_user = session.query(User).filter_by(username=name).first()
        if existing_user:
            print(f"  • {name} - Already exists (ID: {existing_user.id}, MMR: {existing_user.mmr})")
            name_to_id[name] = existing_user.id
            continue
        
        # Create new user
        try:
            user = User(
                username=name,
                password_hash=hash_password(DEFAULT_PLAYER_PASSWORD),
                role=UserRole.PLAYER,
                mmr=float(mmr)
            )
            session.add(user)
            session.flush()  # Get ID assigned
            
            name_to_id[name] = user.id
            print(f"  ✅ {name} - Created (ID: {user.id}, MMR: {mmr})")
        except Exception as e:
            print(f"  ❌ {name} - Error: {e}")
    
    print(f"\n✅ Migrated {len(name_to_id)} players")
    return name_to_id


def migrate_sessions_and_matches(matches_data, name_to_id, db_session):
    """
    Migrate sessions and matches from JSON to database.
    Groups matches by session_id.
    """
    print("\n" + "=" * 60)
    print("Migrating Sessions and Matches")
    print("=" * 60)
    
    if not matches_data:
        print("⚠️  No match data found")
        return
    
    # Group matches by session
    sessions_map = defaultdict(list)
    for match_data in matches_data:
        session_id = match_data.get('session_id', 'unknown')
        sessions_map[session_id].append(match_data)
    
    print(f"\nFound {len(sessions_map)} unique sessions")
    print(f"Total matches to migrate: {len(matches_data)}")
    
    session_id_map = {}  # Map old session_id to new database ID
    total_matches_migrated = 0
    skipped_matches = 0
    
    for old_session_id, session_matches in sessions_map.items():
        # Parse session date from session_id (format: session_YYYY-MM-DD)
        try:
            date_str = old_session_id.replace('session_', '')
            session_date = datetime.fromisoformat(date_str)
        except:
            # Fallback: use timestamp from first match
            first_match = session_matches[0]
            timestamp_str = first_match.get('timestamp', datetime.now().isoformat())
            session_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Create or get session
        db_session_obj = db_session.query(Session).filter_by(session_date=session_date).first()
        if not db_session_obj:
            db_session_obj = Session(
                session_date=session_date,
                notes=f"Migrated from {old_session_id}"
            )
            db_session.add(db_session_obj)
            db_session.flush()
        
        session_id_map[old_session_id] = db_session_obj.id
        print(f"\n  Session: {old_session_id}")
        print(f"    Date: {session_date.date()}")
        print(f"    Matches: {len(session_matches)}")
        
        # Migrate matches for this session
        for match_data in session_matches:
            try:
                # Get player names
                team1 = match_data.get('team1', [])
                team2 = match_data.get('team2', [])
                
                if len(team1) != 2 or len(team2) != 2:
                    print(f"    ⚠️  Game {match_data.get('game_number')}: Invalid team size")
                    skipped_matches += 1
                    continue
                
                # Map player names to IDs
                team1_p1_id = name_to_id.get(team1[0])
                team1_p2_id = name_to_id.get(team1[1])
                team2_p1_id = name_to_id.get(team2[0])
                team2_p2_id = name_to_id.get(team2[1])
                
                if None in [team1_p1_id, team1_p2_id, team2_p1_id, team2_p2_id]:
                    print(f"    ⚠️  Game {match_data.get('game_number')}: Unknown player(s)")
                    skipped_matches += 1
                    continue
                
                # Determine winner team (1 or 2)
                winner = match_data.get('winner', 'team1')
                winner_team = 1 if winner == 'team1' else 2
                
                # Create match
                match = Match(
                    session_id=db_session_obj.id,
                    game_number=match_data.get('game_number', 0),
                    team1_player1_id=team1_p1_id,
                    team1_player2_id=team1_p2_id,
                    team2_player1_id=team2_p1_id,
                    team2_player2_id=team2_p2_id,
                    team1_score=match_data.get('team1_score', 0),
                    team2_score=match_data.get('team2_score', 0),
                    game_value=match_data.get('game_value', 0.0),
                    winner_team=winner_team,
                    mmr_change=0.0,  # We'll recalculate MMR separately if needed
                    created_at=datetime.fromisoformat(
                        match_data.get('timestamp', datetime.now().isoformat()).replace('Z', '+00:00')
                    )
                )
                
                db_session.add(match)
                total_matches_migrated += 1
                
            except Exception as e:
                print(f"    ❌ Game {match_data.get('game_number')}: Error - {e}")
                skipped_matches += 1
    
    print(f"\n✅ Migrated {total_matches_migrated} matches")
    if skipped_matches > 0:
        print(f"⚠️  Skipped {skipped_matches} matches due to errors")


def main():
    """Main migration function"""
    print("=" * 60)
    print("JSON to Database Migration")
    print("=" * 60)
    print()
    
    # Paths to JSON files
    data_dir = Path(__file__).parent.parent.parent.parent / 'data'
    players_file = data_dir / 'players.json'
    matches_file = data_dir / 'matches.json'
    
    print("Data directory:", data_dir)
    print("Players file:", players_file)
    print("Matches file:", matches_file)
    
    # Load JSON data
    print("\n" + "=" * 60)
    print("Loading JSON Files")
    print("=" * 60)
    
    players_data = load_json_file(players_file)
    matches_data = load_json_file(matches_file)
    
    if players_data is None and matches_data is None:
        print("\n❌ No data to migrate!")
        return
    
    # Initialize database
    print("\n" + "=" * 60)
    print("Initializing Database")
    print("=" * 60)
    
    try:
        db = init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return
    
    # Perform migration in a transaction
    print("\n" + "=" * 60)
    print("Starting Migration")
    print("=" * 60)
    
    try:
        with session_scope() as session:
            # Migrate players
            name_to_id = migrate_players(players_data, session)
            
            # Migrate sessions and matches
            if matches_data:
                migrate_sessions_and_matches(matches_data, name_to_id, session)
            
            # Transaction will auto-commit on context exit
            
        print("\n" + "=" * 60)
        print("Migration Complete!")
        print("=" * 60)
        print()
        print("✅ All data successfully migrated to database")
        print()
        print("Next steps:")
        print(f"1. All migrated players have the default password: '{DEFAULT_PLAYER_PASSWORD}'")
        print("2. Players should change their passwords after first login")
        print("3. Admin user credentials: username='admin', password='watermelon'")
        print("4. Start the development server: .\\dev.ps1")
        print()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
