#!/usr/bin/env python3
"""
Badminton Matchup Manager - Flask Web Application

Main Flask application providing web UI and REST API for managing badminton matchups.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from match_storage import MatchStorage
import json
import threading
import os
import tempfile
import sys
from pathlib import Path

app = Flask(__name__)

# Load secret key from environment variable (required for production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
if not app.secret_key:
    print("ERROR: FLASK_SECRET_KEY environment variable not set!")
    print("Generate a secret key with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    print("Then set it with: setx FLASK_SECRET_KEY \"<generated_key>\"")
    sys.exit(1)

# Security headers and CORS
@app.after_request
def after_request(response):
    # CORS headers - restricted for production
    # Only enable if accessing from different domain, otherwise remove for security
    origin = request.headers.get('Origin')
    if origin:
        # Allow same-origin requests (PWA and direct access)
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Content Security Policy - allows inline scripts for PWA
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "manifest-src 'self'"
    )
    
    return response

# File paths
DATA_DIR = Path('data')
PLAYERS_FILE = DATA_DIR / 'players.json'
MATCHES_FILE = DATA_DIR / 'matches.json'

# Thread lock for file operations
file_lock = threading.Lock()

# In-memory session state
# Players is now list of dicts: [{'name': str, 'active': bool, 'order': int}, ...]
session_state = {
    'players': [],
    'next_game_number': 1
}

# Initialize storage
storage = MatchStorage(data_dir='data')


def ensure_data_files():
    """Ensure data directory and files exist."""
    DATA_DIR.mkdir(exist_ok=True)
    
    if not MATCHES_FILE.exists():
        with file_lock:
            with open(MATCHES_FILE, 'w') as f:
                json.dump([], f)
    
    if not PLAYERS_FILE.exists():
        with file_lock:
            with open(PLAYERS_FILE, 'w') as f:
                json.dump(session_state, f, indent=2)


def migrate_players_data():
    """
    Migrate players from old list-of-strings format to new object format.
    Old: ["Hayden", "Danny", ...]
    New: [{"name": "Hayden", "active": true, "order": 0}, ...]
    """
    with file_lock:
        if not PLAYERS_FILE.exists():
            return
        
        try:
            with open(PLAYERS_FILE, 'r') as f:
                data = json.load(f)
            
            players = data.get('players', [])
            
            # Check if migration is needed
            if not players:
                return
            
            # If first player is a string, migrate to object format
            if isinstance(players[0], str):
                print("Migrating players to new object format...")
                # Create backup
                backup_file = DATA_DIR / 'players.json.bak'
                with open(backup_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Backup saved to {backup_file}")
                
                # Convert to new format
                migrated_players = [
                    {'name': name, 'active': True, 'order': idx}
                    for idx, name in enumerate(players)
                ]
                data['players'] = migrated_players
                
                # Save migrated data atomically
                temp_fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, suffix='.json')
                try:
                    with os.fdopen(temp_fd, 'w') as f:
                        json.dump(data, f, indent=2)
                    os.replace(temp_path, PLAYERS_FILE)
                    print(f"Successfully migrated {len(migrated_players)} players")
                except Exception as e:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    raise e
            
            # If players are objects but missing 'active' or 'order', add defaults
            elif isinstance(players[0], dict):
                needs_update = False
                for idx, player in enumerate(players):
                    if 'active' not in player:
                        player['active'] = True
                        needs_update = True
                    if 'order' not in player:
                        player['order'] = idx
                        needs_update = True
                
                if needs_update:
                    print("Adding missing 'active' and 'order' fields to players...")
                    temp_fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, suffix='.json')
                    try:
                        with os.fdopen(temp_fd, 'w') as f:
                            json.dump(data, f, indent=2)
                        os.replace(temp_path, PLAYERS_FILE)
                        print("Successfully updated player data")
                    except Exception as e:
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                        raise e
        
        except json.JSONDecodeError as e:
            print(f"Error loading players.json: {e}")
        except Exception as e:
            print(f"Error during migration: {e}")


def load_session():
    """Load session state from file."""
    global session_state
    
    with file_lock:
        if PLAYERS_FILE.exists():
            try:
                with open(PLAYERS_FILE, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle missing keys
                    session_state['players'] = loaded.get('players', [])
                    session_state['next_game_number'] = loaded.get('next_game_number', 1)
            except json.JSONDecodeError:
                pass
    
    # Initialize next_game_number from existing matches if needed
    matches = storage.get_all_matches()
    if matches:
        max_game_number = max((m.get('game_number', 0) for m in matches), default=0)
        if max_game_number >= session_state['next_game_number']:
            session_state['next_game_number'] = max_game_number + 1


def get_active_players():
    """
    Get list of active player names.
    Returns: List of active player name strings
    """
    return [p['name'] for p in session_state['players'] if p.get('active', True)]


def get_player_by_name(name):
    """
    Get player object by name.
    Returns: Player dict or None
    """
    for player in session_state['players']:
        if player['name'] == name:
            return player
    return None


def save_session():
    """Save session state to file using atomic write."""
    # Note: Caller must hold file_lock
    # Use atomic write: write to temp file, then rename
    temp_fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, suffix='.json')
    try:
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(session_state, f, indent=2)
        # Atomic rename
        os.replace(temp_path, PLAYERS_FILE)
    except Exception as e:
        # Clean up temp file if it exists
        try:
            os.unlink(temp_path)
        except:
            pass
        raise e




# Initialize on startup
ensure_data_files()

# Migrate players from old sessions.json if needed
OLD_SESSIONS_FILE = DATA_DIR / 'sessions.json'
if OLD_SESSIONS_FILE.exists() and not PLAYERS_FILE.exists():
    print("Migrating players from old sessions.json...")
    try:
        with open(OLD_SESSIONS_FILE, 'r') as f:
            old_data = json.load(f)
            if isinstance(old_data, dict) and 'players' in old_data:
                # Old format - extract players
                session_state['players'] = old_data.get('players', [])
                session_state['next_game_number'] = old_data.get('next_game_number', 1)
                with file_lock:
                    with open(PLAYERS_FILE, 'w') as pf:
                        json.dump(session_state, pf, indent=2)
                print(f"Migrated {len(session_state['players'])} players")
    except Exception as e:
        print(f"Player migration error: {e}")

# Run player data migration first
print("Checking for player data migration...")
migrate_players_data()
print("Player migration check complete")

load_session()

# Run migration to add sessions to existing matches
print("Running match migration...")
storage.migrate_matches_to_sessions()
print("Migration complete")


# ==================== HTML Routes ====================

@app.route('/')
def index():
    """Dashboard page."""
    return render_template('index.html')


@app.route('/players')
def players_page():
    """Players management page."""
    return render_template('players.html')


@app.route('/matchups')
def matchups_page():
    """Generated matchups page."""
    return render_template('matchups.html')


@app.route('/history')
def history_page():
    """Match history page."""
    return render_template('history.html')


@app.route('/stats')
def stats_page():
    """Player statistics page."""
    import os
    template_path = os.path.join(app.root_path, 'templates', 'stats.html')
    print(f"[DEBUG] Loading stats template from: {template_path}")
    print(f"[DEBUG] Template exists: {os.path.exists(template_path)}")
    return render_template('stats.html')


@app.route('/record')
def record_page():
    """Redirect to matchups page."""
    return redirect(url_for('matchups_page'))


# ==================== API Routes ====================

# Session endpoints
@app.route('/api/session', methods=['GET'])
def get_session():
    """Get current session status."""
    return jsonify({
        'next_game_number': session_state['next_game_number'],
        'player_count': len(session_state['players'])
    })




# Player endpoints
@app.route('/api/players', methods=['GET'])
def get_players():
    """Get list of all players."""
    return jsonify(session_state['players'])


@app.route('/api/players', methods=['POST'])
def add_player():
    """Add a new player."""
    data = request.json
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Player name cannot be empty'}), 400
    
    if len(name) > 50:
        return jsonify({'error': 'Player name too long'}), 400
    
    # Check if player already exists (check by name)
    if any(p['name'] == name for p in session_state['players']):
        return jsonify({'error': 'Player already exists'}), 400
    
    # Add new player with default active state and order
    new_player = {
        'name': name,
        'active': True,
        'order': len(session_state['players'])  # Assign next order
    }
    session_state['players'].append(new_player)
    with file_lock:
        save_session()
    
    return jsonify({'player': new_player, 'message': 'Player added successfully'})


@app.route('/api/players/<name>', methods=['DELETE'])
def delete_player(name):
    """Delete a player."""
    player = get_player_by_name(name)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    session_state['players'].remove(player)
    with file_lock:
        save_session()
    
    return jsonify({'message': 'Player deleted successfully'})


@app.route('/api/players/<name>/active', methods=['PATCH'])
def toggle_player_active(name):
    """Toggle a player's active status."""
    player = get_player_by_name(name)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    data = request.json
    if 'active' not in data or not isinstance(data['active'], bool):
        return jsonify({'error': 'Invalid request: "active" field (boolean) is required'}), 400
    
    # Update player active status
    player['active'] = data['active']
    
    with file_lock:
        save_session()
    
    return jsonify({'player': player, 'message': 'Player status updated successfully'})




# Match history endpoints
@app.route('/api/matches', methods=['GET'])
def get_matches():
    """Get all recorded matches."""
    matches = storage.get_all_matches()
    return jsonify(matches)


@app.route('/api/matches', methods=['POST'])
def record_match():
    """Record a new match result."""
    print("\n=== POST /api/matches called ===")
    print(f"Request data: {request.get_data()}")
    data = request.json
    print(f"Parsed JSON: {data}")
    
    # Extract and validate required fields
    print("Extracting fields...")
    team1 = data.get('team1')
    team2 = data.get('team2')
    team1_score = data.get('team1_score')
    team2_score = data.get('team2_score')
    game_value = data.get('game_value')
    print(f"Fields: team1={team1}, team2={team2}, scores={team1_score}/{team2_score}, value={game_value}")
    
    # Validate teams
    print("Validating teams...")
    if not team1 or not team2:
        print("ERROR: Teams missing")
        return jsonify({'error': 'Both teams are required'}), 400
    
    if not isinstance(team1, list) or not isinstance(team2, list):
        return jsonify({'error': 'Teams must be arrays'}), 400
    
    if len(team1) != 2 or len(team2) != 2:
        return jsonify({'error': 'Each team must have exactly 2 players'}), 400
    
    # Validate all players are distinct
    all_players = team1 + team2
    if len(set(all_players)) != 4:
        return jsonify({'error': 'All 4 players must be distinct'}), 400
    
    # Validate scores
    print("Validating scores...")
    try:
        team1_score = int(team1_score)
        team2_score = int(team2_score)
        if team1_score < 0 or team2_score < 0:
            print("ERROR: Negative scores")
            return jsonify({'error': 'Scores must be non-negative'}), 400
        print(f"Scores OK: {team1_score} - {team2_score}")
    except (ValueError, TypeError) as e:
        print(f"ERROR: Invalid scores - {e}")
        return jsonify({'error': 'Invalid scores'}), 400
    
    # Validate game value
    print("Validating game value...")
    try:
        game_value = int(game_value)
        if game_value < 0 or game_value > 5:
            print("ERROR: Game value out of range")
            return jsonify({'error': 'Game value must be between 0 and 5'}), 400
        print(f"Game value OK: ${game_value}")
    except (ValueError, TypeError) as e:
        print(f"ERROR: Invalid game value - {e}")
        return jsonify({'error': 'Invalid game value'}), 400
    
    # Assign game number and increment
    print("Assigning game number...")
    with file_lock:
        game_number = session_state['next_game_number']
        print(f"Assigned game number: {game_number}")
        session_state['next_game_number'] += 1
        print("Saving session...")
        save_session()
        print("Session saved")
    
    # Create match record
    print("Creating match record...")
    match_data = {
        'game_number': game_number,
        'team1': team1,
        'team2': team2,
        'team1_score': team1_score,
        'team2_score': team2_score,
        'game_value': game_value,
        'winner': 'team1' if team1_score > team2_score else 'team2'
    }
    print(f"Match data: {match_data}")
    
    print("Saving match to storage...")
    match_id = storage.save_match(match_data)
    print(f"Match saved with ID: {match_id}")
    
    # Get the saved match to return
    print("Loading all matches...")
    all_matches = storage.get_all_matches()
    print(f"Total matches: {len(all_matches)}")
    saved_match = next((m for m in all_matches if m.get('match_id') == match_id), None)
    print(f"Returning match: {saved_match}")
    
    print("=== Returning response ===\n")
    return jsonify(saved_match)


@app.route('/api/matches/<match_id>', methods=['PATCH'])
def update_match(match_id):
    """Update an existing match."""
    data = request.json
    
    # Load all matches
    matches = storage.get_all_matches()
    
    # Find the match to update
    match_to_update = None
    match_index = None
    for i, match in enumerate(matches):
        if match.get('match_id') == match_id:
            match_to_update = match
            match_index = i
            break
    
    if not match_to_update:
        return jsonify({'error': 'Match not found'}), 404
    
    # Update fields
    if 'team1_score' in data:
        try:
            score = int(data['team1_score'])
            if score < 0:
                return jsonify({'error': 'Score must be non-negative'}), 400
            match_to_update['team1_score'] = score
        except ValueError:
            return jsonify({'error': 'Invalid team1_score'}), 400
    
    if 'team2_score' in data:
        try:
            score = int(data['team2_score'])
            if score < 0:
                return jsonify({'error': 'Score must be non-negative'}), 400
            match_to_update['team2_score'] = score
        except ValueError:
            return jsonify({'error': 'Invalid team2_score'}), 400
    
    # Recalculate winner
    if 'team1_score' in match_to_update and 'team2_score' in match_to_update:
        match_to_update['winner'] = 'team1' if match_to_update['team1_score'] > match_to_update['team2_score'] else 'team2'
    
    if 'game_value' in data:
        try:
            value = float(data['game_value'])
            if value < 0:
                return jsonify({'error': 'Value must be non-negative'}), 400
            match_to_update['game_value'] = round(value, 2)
        except ValueError:
            return jsonify({'error': 'Invalid game_value'}), 400
    
    # Save updated matches
    matches[match_index] = match_to_update
    with file_lock:
        with open(MATCHES_FILE, 'w') as f:
            json.dump(matches, f, indent=2)
    
    return jsonify(match_to_update)


@app.route('/api/matches/<match_id>', methods=['DELETE'])
def delete_match(match_id):
    """Delete a match."""
    success = storage.delete_match(match_id)
    
    if not success:
        return jsonify({'error': 'Match not found'}), 404
    
    return jsonify({'message': 'Match deleted successfully', 'match_id': match_id})


# Session endpoints
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions with summary information."""
    summaries = storage.get_sessions_summary()
    return jsonify(summaries)


@app.route('/api/sessions/current', methods=['GET'])
def api_get_current_session():
    """Get or create the current (today's) session."""
    session = storage.get_current_session()
    
    # Get matches for this session
    matches = storage.get_session_matches(session['session_id'])
    
    # Get unique players
    players = set()
    for match in matches:
        players.update(match.get('team1', []))
        players.update(match.get('team2', []))
    
    return jsonify({
        'session_id': session['session_id'],
        'date': session['date'],
        'match_count': len(matches),
        'players': sorted(list(players))
    })


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_detail(session_id):
    """Get detailed information about a specific session."""
    session = storage.get_session(session_id)
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Get matches for this session
    matches = storage.get_session_matches(session_id)
    
    # Get unique players
    players = set()
    for match in matches:
        players.update(match.get('team1', []))
        players.update(match.get('team2', []))
    
    return jsonify({
        'session_id': session['session_id'],
        'date': session['date'],
        'match_count': len(matches),
        'players': sorted(list(players)),
        'matches': matches
    })


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create or get a session for a specific date."""
    data = request.json or {}
    
    # Use provided date or default to today
    if 'date' in data:
        from datetime import date as date_cls
        try:
            session_date = date_cls.fromisoformat(data['date'])
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        session_date = storage._get_local_today()
    
    session = storage.get_or_create_session_for_date(session_date)
    
    # Get summary info
    matches = storage.get_session_matches(session['session_id'])
    players = set()
    for match in matches:
        players.update(match.get('team1', []))
        players.update(match.get('team2', []))
    
    return jsonify({
        'session_id': session['session_id'],
        'date': session['date'],
        'match_count': len(matches),
        'players': sorted(list(players))
    })


@app.route('/api/sessions/<session_id>', methods=['PATCH'])
def update_session(session_id):
    """Update a session's date."""
    data = request.json or {}
    
    # Validate date field
    if 'date' not in data:
        return jsonify({'error': 'Date field is required'}), 400
    
    # Parse and validate date
    try:
        from datetime import date as date_cls
        new_date = date_cls.fromisoformat(data['date'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Get merge parameter (default False)
    merge = data.get('merge', False)
    if not isinstance(merge, bool):
        return jsonify({'error': 'Merge must be a boolean'}), 400
    
    # Update session date
    try:
        updated_session = storage.update_session_date(session_id, new_date, merge)
        
        # Get match count for response
        matches = storage.get_session_matches(updated_session['session_id'])
        
        return jsonify({
            'session_id': updated_session['session_id'],
            'date': updated_session['date'],
            'match_count': len(matches),
            'merged': merge and updated_session['session_id'] != session_id
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except KeyError as e:
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        return jsonify({'error': f'Failed to update session: {str(e)}'}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session and all its matches."""
    result = storage.delete_session(session_id)
    
    if result['deleted_matches'] == 0:
        # Check if session exists
        session = storage.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'message': 'Session deleted successfully',
        'session_id': session_id,
        'deleted_matches': result['deleted_matches']
    })


# Stats endpoint
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get player statistics."""
    # Extract player names from session_state (which contains player objects)
    all_players = set()
    for p in session_state['players']:
        player_name = p['name'] if isinstance(p, dict) else p
        all_players.add(player_name)
    
    # Also include players from match history
    matches = storage.get_all_matches()
    for match in matches:
        all_players.update(match.get('team1', []))
        all_players.update(match.get('team2', []))
    
    stats_list = []
    for player in all_players:
        stats = storage.get_player_stats(player)
        # Get MMR from player data
        player_obj = get_player_by_name(player)
        mmr = player_obj.get('mmr', 1500) if player_obj else 1500
        
        stats_list.append({
            'player': player,
            'total_matches': stats['total_matches'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': stats['win_rate'],
            'earnings': stats['total_earnings'],  # Now net earnings
            'net_earnings': stats['net_earnings'],
            'total_winnings': stats['total_winnings'],
            'total_losses': stats['total_losses'],
            'partners': ', '.join(stats['partners']),
            'opponents': ', '.join(stats['opponents']),
            'mmr': mmr
        })
    
    # Sort by total matches (most active first)
    stats_list.sort(key=lambda x: x['total_matches'], reverse=True)
    
    return jsonify(stats_list)


@app.route('/api/earnings', methods=['GET'])
def get_earnings():
    """Get player earnings/losses for all players."""
    earnings_data = storage.get_all_player_earnings()
    
    # Convert dict to list and sort by net earnings descending
    earnings_list = []
    for player, stats in earnings_data.items():
        earnings_list.append({
            'player': player,
            'games_played': stats['games_played'],
            'total_winnings': stats['total_winnings'],
            'total_losses': stats['total_losses'],
            'net_earnings': stats['net_earnings']
        })
    
    # Sort by net earnings descending (winners first)
    earnings_list.sort(key=lambda x: x['net_earnings'], reverse=True)
    
    return jsonify(earnings_list)


@app.route('/api/earnings/monthly', methods=['GET'])
def get_monthly_earnings():
    """Get player earnings/losses for a specific month.
    
    Query params:
        year (int, optional): Year (defaults to current year)
        month (int, optional): Month 1-12 (defaults to current month)
    """
    # Get optional query params
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # Get monthly earnings from storage
    earnings_list = storage.get_monthly_player_earnings(year, month)
    
    return jsonify(earnings_list)


@app.route('/api/partnerships', methods=['GET'])
def get_partnerships():
    """
    Get partnership statistics across all matches.
    
    Returns aggregated stats for all player partnerships including:
    - Win/loss record as partners
    - Win rate
    - Combined earnings when playing together
    
    Query params:
        min_games (int): Minimum games required to include partnership (default: 0)
    """
    min_games = int(request.args.get('min_games', 0))
    
    # Get all matches
    matches = storage.get_all_matches()
    
    # Aggregate partnership statistics
    partnerships = {}  # key: frozenset of player names
    
    for match in matches:
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        team1_score = match.get('team1_score')
        team2_score = match.get('team2_score')
        game_value = match.get('game_value', 0)
        
        # Skip if not a doubles match or missing scores
        if len(team1) != 2 or len(team2) != 2:
            continue
        if team1_score is None or team2_score is None:
            continue
        
        # Determine winner
        team1_won = team1_score > team2_score
        team2_won = team2_score > team1_score
        
        # Process team1 partnership
        team1_key = frozenset(team1)
        if team1_key not in partnerships:
            partnerships[team1_key] = {
                'players': sorted(team1),
                'wins': 0,
                'losses': 0,
                'games': 0,
                'earnings': 0.0
            }
        
        partnerships[team1_key]['games'] += 1
        if team1_won:
            partnerships[team1_key]['wins'] += 1
            # Both partners earn the full game_value when they win
            partnerships[team1_key]['earnings'] += game_value * 2
        elif team2_won:
            partnerships[team1_key]['losses'] += 1
            # Both partners lose the full game_value when they lose
            partnerships[team1_key]['earnings'] -= game_value * 2
        
        # Process team2 partnership
        team2_key = frozenset(team2)
        if team2_key not in partnerships:
            partnerships[team2_key] = {
                'players': sorted(team2),
                'wins': 0,
                'losses': 0,
                'games': 0,
                'earnings': 0.0
            }
        
        partnerships[team2_key]['games'] += 1
        if team2_won:
            partnerships[team2_key]['wins'] += 1
            partnerships[team2_key]['earnings'] += game_value * 2
        elif team1_won:
            partnerships[team2_key]['losses'] += 1
            partnerships[team2_key]['earnings'] -= game_value * 2
    
    # Convert to list and compute win rates
    result = []
    for partner_set, stats in partnerships.items():
        if stats['games'] < min_games:
            continue
        
        win_rate = stats['wins'] / stats['games'] if stats['games'] > 0 else 0.0
        key = ' & '.join(stats['players'])
        
        result.append({
            'players': stats['players'],
            'key': key,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'games': stats['games'],
            'win_rate': round(win_rate, 4),
            'earnings': round(stats['earnings'], 2)
        })
    
    return jsonify({'partnerships': result})


@app.route('/api/current-session/player/<player_name>/matches', methods=['GET'])
def get_player_session_matches(player_name):
    """Get all matches for a specific player in the current session."""
    from urllib.parse import unquote
    
    # URL-decode and normalize player name
    player_name = unquote(player_name).strip()
    
    # Get current session
    session = storage.get_current_session()
    session_id = session['session_id']
    
    # Get all matches for this session
    matches = storage.get_session_matches(session_id)
    
    # Filter and process matches for this player
    player_matches = []
    game_number = 0
    
    for match in matches:
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        team1_score = match.get('team1_score')
        team2_score = match.get('team2_score')
        game_value = match.get('game_value', 0)
        
        # Check if player is in this match
        player_team = None
        if player_name in team1:
            player_team = 1
        elif player_name in team2:
            player_team = 2
        else:
            continue  # Player not in this match
        
        game_number += 1
        
        # Determine result and amount delta
        result = 'Push'
        amount_delta = 0
        
        if team1_score is not None and team2_score is not None:
            if team1_score > team2_score:
                if player_team == 1:
                    result = 'Win'
                    amount_delta = game_value
                else:
                    result = 'Loss'
                    amount_delta = -game_value
            elif team2_score > team1_score:
                if player_team == 2:
                    result = 'Win'
                    amount_delta = game_value
                else:
                    result = 'Loss'
                    amount_delta = -game_value
        
        # Get opponents (players on the other team)
        opponents = team2 if player_team == 1 else team1
        
        player_matches.append({
            'game_number': game_number,
            'team1': team1,
            'team2': team2,
            'team1_score': team1_score,
            'team2_score': team2_score,
            'game_value': game_value,
            'timestamp': match.get('timestamp'),
            'player_team': player_team,
            'result': result,
            'amount_delta': round(amount_delta, 2),
            'opponents': opponents
        })
    
    return jsonify({
        'player': player_name,
        'session_id': session_id,
        'matches': player_matches
    })


@app.route('/api/sessions/<session_id>/earnings', methods=['GET'])
def get_session_earnings(session_id):
    """Get player earnings/losses for a specific session."""
    # Verify session exists
    session = storage.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    earnings_data = storage.get_session_player_stats(session_id)
    
    # Convert dict to list and sort by net earnings descending
    earnings_list = []
    for player, stats in earnings_data.items():
        earnings_list.append({
            'player': player,
            'games_played': stats['games_played'],
            'total_winnings': stats['total_winnings'],
            'total_losses': stats['total_losses'],
            'net_earnings': stats['net_earnings']
        })
    
    # Sort by net earnings descending (winners first)
    earnings_list.sort(key=lambda x: x['net_earnings'], reverse=True)
    
    return jsonify({
        'session_id': session_id,
        'players': earnings_list
    })


@app.route('/api/sessions/<session_id>/stats', methods=['GET'])
def get_session_stats(session_id):
    """Get player and partnership win rates for a specific session."""
    # Verify session exists
    session = storage.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Get matches for this session
    matches = storage.get_session_matches(session_id)
    
    # Initialize stats tracking
    player_stats = {}
    partnership_stats = {}
    
    # Process each match
    for match in matches:
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        team1_score = match.get('team1_score')
        team2_score = match.get('team2_score')
        
        # Skip malformed matches
        if not team1 or not team2 or team1_score is None or team2_score is None:
            continue
        
        # Determine winner
        team1_won = team1_score > team2_score
        team2_won = team2_score > team1_score
        is_tie = team1_score == team2_score
        
        # Process players in team1
        for player in team1:
            if player not in player_stats:
                player_stats[player] = {'games': 0, 'wins': 0, 'losses': 0}
            player_stats[player]['games'] += 1
            if team1_won:
                player_stats[player]['wins'] += 1
            elif team2_won:
                player_stats[player]['losses'] += 1
        
        # Process players in team2
        for player in team2:
            if player not in player_stats:
                player_stats[player] = {'games': 0, 'wins': 0, 'losses': 0}
            player_stats[player]['games'] += 1
            if team2_won:
                player_stats[player]['wins'] += 1
            elif team1_won:
                player_stats[player]['losses'] += 1
        
        # Process partnerships (doubles only)
        if len(team1) == 2:
            partnership_key = ' and '.join(sorted(team1))
            if partnership_key not in partnership_stats:
                partnership_stats[partnership_key] = {'games': 0, 'wins': 0, 'losses': 0}
            partnership_stats[partnership_key]['games'] += 1
            if team1_won:
                partnership_stats[partnership_key]['wins'] += 1
            elif team2_won:
                partnership_stats[partnership_key]['losses'] += 1
        
        if len(team2) == 2:
            partnership_key = ' and '.join(sorted(team2))
            if partnership_key not in partnership_stats:
                partnership_stats[partnership_key] = {'games': 0, 'wins': 0, 'losses': 0}
            partnership_stats[partnership_key]['games'] += 1
            if team2_won:
                partnership_stats[partnership_key]['wins'] += 1
            elif team1_won:
                partnership_stats[partnership_key]['losses'] += 1
    
    # Build player list with win rates
    players = []
    for name, stats in player_stats.items():
        if stats['games'] > 0:
            win_rate = round((stats['wins'] / stats['games']) * 100, 1) if stats['games'] > 0 else 0.0
            players.append({
                'name': name,
                'games': stats['games'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'winRate': win_rate
            })
    
    # Build partnership list with win rates
    partnerships = []
    for partnership, stats in partnership_stats.items():
        if stats['games'] > 0:
            win_rate = round((stats['wins'] / stats['games']) * 100, 1) if stats['games'] > 0 else 0.0
            partnerships.append({
                'partnership': partnership,
                'games': stats['games'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'winRate': win_rate
            })
    
    # Sort: winRate desc, then games desc, then name asc
    players.sort(key=lambda x: (-x['winRate'], -x['games'], x['name']))
    partnerships.sort(key=lambda x: (-x['winRate'], -x['games'], x['partnership']))
    
    return jsonify({
        'session_id': session_id,
        'players': players,
        'partnerships': partnerships
    })


@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Get recommended matchups based on current session partnership history.
    
    Supports dual-court mode when 8+ active players are available.
    Returns single matchup for <8 players, dual matchup for 8+ players.
    
    Query params:
        exclude_ids: Comma-separated player names to exclude (for cycling)
    """
    from collections import Counter
    import itertools
    import random
    from flask import request
    
    # Get only active players
    all_active_players = get_active_players()
    
    # Get current session and its matches FIRST (to count games before filtering)
    current_session = storage.get_current_session()
    session_matches = storage.get_session_matches(current_session['session_id'])
    
    # Build partnership counter and total games (only teammates, not opponents)
    partnership_counts = Counter()
    total_games = Counter()
    
    for match in session_matches:
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        
        # Count partnerships (teammates)
        if len(team1) == 2:
            partnership_counts[frozenset(team1)] += 1
            for player in team1:
                total_games[player] += 1
        
        if len(team2) == 2:
            partnership_counts[frozenset(team2)] += 1
            for player in team2:
                total_games[player] += 1
    
    # Determine if dual-court mode (8+ active players available)
    is_dual_court = len(all_active_players) >= 8
    
    # For dual-court mode, ALWAYS use all active players (ignore exclude_ids)
    # For single-court mode, handle exclude_ids for cycling
    if is_dual_court:
        players = all_active_players
    else:
        # Single-court mode: handle exclude_ids parameter for cycling
        exclude_ids = request.args.get('exclude_ids', '')
        excluded_players = set(exclude_ids.split(',')) if exclude_ids else set()
        
        # Filter out excluded players
        players = [p for p in all_active_players if p not in excluded_players]
        
        # Check if we need to handle insufficient players after exclusion
        if len(players) < 4 and len(excluded_players) > 0:
            # For single-court mode cycling: if we don't have 4 players left after exclusion,
            # prioritize players who have played fewer games
            players_with_games = [(p, total_games.get(p, 0)) for p in all_active_players]
            players_with_games.sort(key=lambda x: x[1])  # Sort by game count ascending
            
            # Take top 4+ players with fewest games, prioritizing non-excluded
            non_excluded = [(p, g) for p, g in players_with_games if p not in excluded_players]
            excluded_sorted = [(p, g) for p, g in players_with_games if p in excluded_players]
            
            # Combine: non-excluded first (sorted by games), then excluded (sorted by games)
            combined = non_excluded + excluded_sorted
            players = [p for p, g in combined]
        
        # Need at least 4 players total
        if len(players) < 4:
            if len(all_active_players) >= 4:
                players = all_active_players
            else:
                return jsonify({'error': 'Not enough players'}), 400
    
    def format_count(count):
        if count == 0:
            return "🆕"
        elif count == 1:
            return "①"
        else:
            return f"×{count}"
    
    def generate_matchup_for_players(candidate_players, partnership_counts, total_games):
        """Generate best single matchup for given players."""
        all_matchups = []
        
        # Try all 4-player combinations
        for four_players in itertools.combinations(candidate_players, 4):
            p1, p2, p3, p4 = four_players
            
            # Try all possible 2v2 partitions
            partitions = [
                ((p1, p2), (p3, p4)),
                ((p1, p3), (p2, p4)),
                ((p1, p4), (p2, p3))
            ]
            
            for team_a, team_b in partitions:
                # Get partnership counts for each team
                count_a = partnership_counts.get(frozenset(team_a), 0)
                count_b = partnership_counts.get(frozenset(team_b), 0)
                
                # Calculate games balance
                games_a = total_games.get(team_a[0], 0) + total_games.get(team_a[1], 0)
                games_b = total_games.get(team_b[0], 0) + total_games.get(team_b[1], 0)
                games_balance = abs(games_a - games_b)
                
                # Score tuple: prioritize new partnerships, then minimize total repetition
                score = (
                    max(count_a, count_b),  # Worst partnership count
                    count_a + count_b,       # Total partnership count
                    games_balance,           # Balance of total games played
                    sorted([p1, p2, p3, p4]) # Deterministic tiebreaker
                )
                
                all_matchups.append({
                    'score': score,
                    'team_a': list(team_a),
                    'team_b': list(team_b),
                    'count_a': count_a,
                    'count_b': count_b,
                    'players': set([p1, p2, p3, p4])
                })
        
        if not all_matchups:
            return None
        
        # Sort by score and return best
        all_matchups.sort(key=lambda x: x['score'])
        return all_matchups[0]
    
    if is_dual_court:
        # DUAL-COURT MODE: Generate 2 separate matchups
        # For cycling: shuffle ALL players and take first 8 to ensure rotation
        shuffled_players = players[:]
        random.shuffle(shuffled_players)
        
        # Take only first 8 players from shuffled list to force rotation
        selected_8 = shuffled_players[:8]
        
        # First matchup: best from first 4 of selected 8
        first_matchup = generate_matchup_for_players(selected_8[:4], partnership_counts, total_games)
        
        if not first_matchup:
            return '', 204  # No Content
        
        # Second matchup: use the remaining 4 from selected 8
        second_matchup = generate_matchup_for_players(selected_8[4:8], partnership_counts, total_games)
        
        if second_matchup:
                # Build dual-court response
                court1_explanation = f"{first_matchup['team_a'][0]}/{first_matchup['team_a'][1]} {format_count(first_matchup['count_a'])} vs {first_matchup['team_b'][0]}/{first_matchup['team_b'][1]} {format_count(first_matchup['count_b'])}"
                court2_explanation = f"{second_matchup['team_a'][0]}/{second_matchup['team_a'][1]} {format_count(second_matchup['count_a'])} vs {second_matchup['team_b'][0]}/{second_matchup['team_b'][1]} {format_count(second_matchup['count_b'])}"
                
                # Player IDs in court order: Court 1 (Team A, Team B), Court 2 (Team A, Team B)
                player_ids = (
                    first_matchup['team_a'] + 
                    first_matchup['team_b'] + 
                    second_matchup['team_a'] + 
                    second_matchup['team_b']
                )
                
                return jsonify({
                    'dual_court': True,
                    'matchups': [
                        {
                            'court': 1,
                            'team_a': first_matchup['team_a'],
                            'team_b': first_matchup['team_b'],
                            'explanation': court1_explanation
                        },
                        {
                            'court': 2,
                            'team_a': second_matchup['team_a'],
                            'team_b': second_matchup['team_b'],
                            'explanation': court2_explanation
                        }
                    ],
                    'player_ids': player_ids,
                    'current_index': 0
                })
        
        # Fallback to single-court if we can't make 2 matchups
        # (This shouldn't happen if is_dual_court is true, but handle gracefully)
    
    # SINGLE-COURT MODE: Generate 1 matchup (original behavior)
    best_matchup = generate_matchup_for_players(players, partnership_counts, total_games)
    
    if not best_matchup:
        return '', 204  # No Content
    
    # Generate alternatives for cycling
    all_matchups_for_alternatives = []
    for four_players in itertools.combinations(players, 4):
        p1, p2, p3, p4 = four_players
        partitions = [
            ((p1, p2), (p3, p4)),
            ((p1, p3), (p2, p4)),
            ((p1, p4), (p2, p3))
        ]
        for team_a, team_b in partitions:
            count_a = partnership_counts.get(frozenset(team_a), 0)
            count_b = partnership_counts.get(frozenset(team_b), 0)
            games_a = total_games.get(team_a[0], 0) + total_games.get(team_a[1], 0)
            games_b = total_games.get(team_b[0], 0) + total_games.get(team_b[1], 0)
            games_balance = abs(games_a - games_b)
            score = (
                max(count_a, count_b),
                count_a + count_b,
                games_balance,
                sorted([p1, p2, p3, p4])
            )
            all_matchups_for_alternatives.append({
                'score': score,
                'team_a': list(team_a),
                'team_b': list(team_b),
                'count_a': count_a,
                'count_b': count_b
            })
    
    all_matchups_for_alternatives.sort(key=lambda x: x['score'])
    
    # Return top 10 alternatives for single-court
    recommendations = []
    for matchup in all_matchups_for_alternatives[:10]:
        team_a = matchup['team_a']
        team_b = matchup['team_b']
        count_a = matchup['count_a']
        count_b = matchup['count_b']
        explanation = f"{team_a[0]}/{team_a[1]} {format_count(count_a)} vs {team_b[0]}/{team_b[1]} {format_count(count_b)}"
        recommendations.append({
            'team_a': team_a,
            'team_b': team_b,
            'explanation': explanation
        })
    
    # Player IDs in order: Team A, Team B
    player_ids = best_matchup['team_a'] + best_matchup['team_b']
    
    return jsonify({
        'dual_court': False,
        'team_a': best_matchup['team_a'],
        'team_b': best_matchup['team_b'],
        'explanation': f"{best_matchup['team_a'][0]}/{best_matchup['team_a'][1]} {format_count(best_matchup['count_a'])} vs {best_matchup['team_b'][0]}/{best_matchup['team_b'][1]} {format_count(best_matchup['count_b'])}",
        'player_ids': player_ids,
        'recommendations': recommendations,
        'current_index': 0
    })


# ==================== Admin Endpoints ====================

@app.route('/api/admin/recalculate-mmr', methods=['POST'])
def recalculate_mmr():
    """
    Admin endpoint to recalculate MMR ratings for all players.
    Requires ADMIN_TOKEN environment variable for authorization.
    """
    # Check authorization
    admin_token = os.environ.get('ADMIN_TOKEN')
    if admin_token:
        provided_token = request.headers.get('X-Admin-Token')
        if provided_token != admin_token:
            return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from pathlib import Path
        from calculate_mmr import calculate_mmr_ratings, update_players_with_mmr
        
        # Calculate new MMR ratings
        player_ratings, history, players_data = calculate_mmr_ratings(
            matches_file=Path('data/matches.json'),
            players_file=Path('data/players.json'),
            k_factor=24,
            build_history=False
        )
        
        # Update players with new ratings
        update_players_with_mmr(
            players_data,
            player_ratings,
            Path('data/players.json'),
            write=True
        )
        
        # Reload session to pick up new MMR values
        load_session()
        
        return jsonify({
            'message': 'MMR ratings recalculated successfully',
            'timestamp': datetime.now().isoformat(),
            'player_count': len(player_ratings),
            'ratings': {player: round(rating) for player, rating in player_ratings.items()}
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to recalculate MMR: {str(e)}'
        }), 500


if __name__ == '__main__':
    # Determine if running in production or development
    is_dev = os.environ.get('FLASK_ENV') == 'development'
    
    if is_dev:
        print("\n=== DEVELOPMENT MODE ===")
        print("Running with Flask development server")
        print("Access at: http://localhost:5000")
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=True)
    else:
        print("\n=== PRODUCTION MODE ===")
        print("For production, use Waitress:")
        print("  python -m waitress --listen=127.0.0.1:5000 app:app")
        print("\nOr run directly (not recommended for production):")
        print("  Setting host to 127.0.0.1 (localhost only)")
        print("  Access via Cloudflare Tunnel")
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
