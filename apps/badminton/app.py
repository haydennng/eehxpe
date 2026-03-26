#!/usr/bin/env python3
"""
Badminton Matchup Manager - Flask Web Application

Main Flask application providing web UI and REST API for managing badminton matchups.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session as flask_session
from datetime import datetime
from zoneinfo import ZoneInfo
from match_storage import MatchStorage

_PACIFIC = ZoneInfo('America/Los_Angeles')

def _now_pacific():
    """Return current time in Pacific timezone as a naive datetime."""
    return datetime.now(_PACIFIC).replace(tzinfo=None)
from flask_httpauth import HTTPBasicAuth
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import json
import threading
import os
import tempfile
import sys
from pathlib import Path

# Import database and auth modules
from database import init_db, session_scope
from models import User, UserRole, Match
from auth import authenticate_user, create_user, get_user_by_id, get_user_by_username, change_password, admin_required
from player_stats import get_player_stats, get_leaderboard

app = Flask(__name__)
auth = HTTPBasicAuth()  # Keep for backwards compatibility

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Configure for subpath mounting when running under WSGI dispatcher
if os.environ.get('WSGI_DISPATCHER') == 'true':
    app.config['APPLICATION_ROOT'] = '/badminton'
    print("Configured APPLICATION_ROOT=/badminton for WSGI dispatcher")

# Load secret key from environment variable (required for production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
if not app.secret_key:
    print("ERROR: FLASK_SECRET_KEY environment variable not set!")
    print("Generate a secret key with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    print("Then set it with: setx FLASK_SECRET_KEY \"<generated_key>\"")
    sys.exit(1)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return get_user_by_id(int(user_id))


# Password verification for HTTP Basic Authentication (backwards compatibility)
@auth.verify_password
def verify_password(username, password):
    """Verify username and password for Basic Auth."""
    user = authenticate_user(username, password)
    if user:
        return username
    return None


# Security headers and CORS
@app.after_request
def after_request(response):
    # No CORS headers needed - app is served same-origin via Cloudflare
    
    # Cache control headers - prevent aggressive browser caching during development
    # For HTML pages and API responses, disable caching
    if response.content_type and ('text/html' in response.content_type or 'application/json' in response.content_type):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # For static assets (CSS, JS, images), use short cache with validation
    elif request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=300, must-revalidate'  # 5 minutes
    
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

# File paths - use parent data directory to match production
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
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
storage = MatchStorage(data_dir=str(DATA_DIR))


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
    Get list of active player names (excluding deactivated players).
    Returns: List of active player name strings
    """
    return [
        p['name'] for p in session_state['players'] 
        if p.get('active', True) and not p.get('deactivated', False)
    ]


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




# Initialize database FIRST (before any database queries)
print("Initializing database...")
init_db()
print("Database initialization complete")

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

# Clean up any empty sessions (sessions with no games/players)
print("Cleaning up empty sessions...")
deleted_count = storage.cleanup_all_empty_sessions()
if deleted_count > 0:
    print(f"Removed {deleted_count} empty session(s)")
else:
    print("No empty sessions to clean up")


# ==================== HTML Routes ====================

@app.route('/')
@login_required
def index():
    """Root page - redirect to dashboard."""
    return redirect(url_for('dashboard_page'))


@app.route('/dashboard')
@login_required
def dashboard_page():
    """Dashboard page with lobby stats."""
    return render_template('dashboard.html')


@app.route('/players')
@login_required
def players_page():
    """Players management page."""
    return render_template('players.html')


@app.route('/matchups')
@login_required
def matchups_page():
    """Generated matchups page."""
    return render_template('matchups.html')


@app.route('/history')
@login_required
def history_page():
    """Match history page."""
    return render_template('history.html')


@app.route('/stats')
@login_required
def stats_page():
    """Player statistics page."""
    import os
    template_path = os.path.join(app.root_path, 'templates', 'stats.html')
    print(f"[DEBUG] Loading stats template from: {template_path}")
    print(f"[DEBUG] Template exists: {os.path.exists(template_path)}")
    return render_template('stats.html')


@app.route('/sw.js')
def service_worker():
    """Serve the service worker with proper MIME type."""
    from flask import send_from_directory
    response = send_from_directory('templates', 'sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/badminton/'
    return response


@app.route('/record')
def record_page():
    """Redirect to matchups page."""
    return redirect(url_for('matchups_page'))


# ==================== API Routes ====================

# ==================== Authentication Routes ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'GET':
        # If already logged in, redirect to index
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # POST - handle login
    data = request.json if request.is_json else request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        if request.is_json:
            return jsonify({'error': 'Username and password required'}), 400
        flash('Username and password required', 'danger')
        return redirect(url_for('login'))
    
    user = authenticate_user(username, password)
    if user:
        login_user(user, remember=True)
        if request.is_json:
            return jsonify({
                'message': 'Login successful',
                'user': user.to_dict()
            })
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('index'))
    
    if request.is_json:
        return jsonify({'error': 'Invalid username or password'}), 401
    flash('Invalid username or password', 'danger')
    return redirect(url_for('login'))


@app.route('/api/register', methods=['POST'])
@admin_required
def register():
    """Register a new user account."""
    data = request.json if request.is_json else request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if len(username) < 3 or len(username) > 50:
        return jsonify({'error': 'Username must be 3-50 characters'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    try:
        user = create_user(username, password, UserRole.PLAYER)
        return jsonify({
            'message': 'Account created successfully',
            'user': user.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """Logout current user."""
    logout_user()
    if request.is_json or request.method == 'POST':
        return jsonify({'message': 'Logged out successfully'})
    return redirect(url_for('login'))


@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Get current authentication status."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        })
    return jsonify({'authenticated': False})






# ==================== Profile and Stats Routes ====================

@app.route('/profile')
@login_required
def profile_page():
    """User profile page."""
    return render_template('profile.html', user=current_user)


@app.route('/player/<username>')
@login_required
def public_player_profile(username):
    """Public player profile page - view any player's stats."""
    # Check if player exists
    user = get_user_by_username(username)
    if not user:
        flash(f'Player {username} not found', 'danger')
        return redirect(url_for('stats_page'))
    
    return render_template('player_public.html', player_username=username)


@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile with stats."""
    stats = get_player_stats(current_user.id)
    return jsonify(stats)


@app.route('/api/players/<username>/public-stats', methods=['GET'])
@login_required
def get_public_player_stats(username):
    """Get any player's public stats by username."""
    # Get user by username
    user = get_user_by_username(username)
    if not user:
        return jsonify({'error': 'Player not found'}), 404
    
    # Get stats for this player
    stats = get_player_stats(user.id)
    if not stats:
        return jsonify({'error': 'Stats not found'}), 404
    
    return jsonify(stats)


@app.route('/api/players/<int:user_id>/partners', methods=['GET'])
@login_required
def get_player_partners(user_id):
    """Get any player's partner statistics by user ID."""
    from sqlalchemy import or_, func
    from collections import defaultdict
    
    with session_scope() as session:
        # Verify user exists
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'Player not found'}), 404
        
        # Get all matches for this user
        matches = session.query(Match).filter(
            or_(
                Match.team1_player1_id == user_id,
                Match.team1_player2_id == user_id,
                Match.team2_player1_id == user_id,
                Match.team2_player2_id == user_id
            )
        ).all()
        
        # Calculate partner stats
        partner_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_games': 0})
        
        for match in matches:
            # Find partner
            partner_id = None
            won = False
            
            if match.team1_player1_id == user_id:
                partner_id = match.team1_player2_id
                won = match.winner_team == 1
            elif match.team1_player2_id == user_id:
                partner_id = match.team1_player1_id
                won = match.winner_team == 1
            elif match.team2_player1_id == user_id:
                partner_id = match.team2_player2_id
                won = match.winner_team == 2
            elif match.team2_player2_id == user_id:
                partner_id = match.team2_player1_id
                won = match.winner_team == 2
            
            if partner_id:
                partner = session.query(User).filter_by(id=partner_id).first()
                if partner:
                    partner_stats[partner.username]['total_games'] += 1
                    if won:
                        partner_stats[partner.username]['wins'] += 1
                    else:
                        partner_stats[partner.username]['losses'] += 1
        
        # Convert to list, filter by min 5 games, and calculate win rates
        result = []
        for partner, stats in partner_stats.items():
            if stats['total_games'] >= 5:  # Only include partners with 5+ games
                win_rate = (stats['wins'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                result.append({
                    'partner': partner,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'total_games': stats['total_games'],
                    'win_rate': win_rate
                })
        
        # Sort by win rate (descending) and limit to top 5
        result.sort(key=lambda x: x['win_rate'], reverse=True)
        result = result[:5]
        
        return jsonify(result)


@app.route('/api/profile/partners', methods=['GET'])
@login_required
def get_profile_partners():
    """Get current user's partner statistics."""
    from sqlalchemy import or_, func
    from collections import defaultdict
    
    with session_scope() as session:
        # Get all matches for current user
        matches = session.query(Match).filter(
            or_(
                Match.team1_player1_id == current_user.id,
                Match.team1_player2_id == current_user.id,
                Match.team2_player1_id == current_user.id,
                Match.team2_player2_id == current_user.id
            )
        ).all()
        
        # Calculate partner stats
        partner_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_games': 0})
        
        for match in matches:
            # Find partner
            partner_id = None
            won = False
            
            if match.team1_player1_id == current_user.id:
                partner_id = match.team1_player2_id
                won = match.winner_team == 1
            elif match.team1_player2_id == current_user.id:
                partner_id = match.team1_player1_id
                won = match.winner_team == 1
            elif match.team2_player1_id == current_user.id:
                partner_id = match.team2_player2_id
                won = match.winner_team == 2
            elif match.team2_player2_id == current_user.id:
                partner_id = match.team2_player1_id
                won = match.winner_team == 2
            
            if partner_id:
                partner = session.query(User).filter_by(id=partner_id).first()
                if partner:
                    partner_stats[partner.username]['total_games'] += 1
                    if won:
                        partner_stats[partner.username]['wins'] += 1
                    else:
                        partner_stats[partner.username]['losses'] += 1
        
        # Convert to list, filter by min 5 games, and calculate win rates
        result = []
        for partner, stats in partner_stats.items():
            if stats['total_games'] >= 5:  # Only include partners with 5+ games
                win_rate = (stats['wins'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                result.append({
                    'partner': partner,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'total_games': stats['total_games'],
                    'win_rate': win_rate
                })
        
        # Sort by win rate (descending) and limit to top 5
        result.sort(key=lambda x: x['win_rate'], reverse=True)
        result = result[:5]
        
        return jsonify(result)


@app.route('/api/players/<int:user_id>/opponents', methods=['GET'])
@login_required
def get_player_opponents(user_id):
    """Get any player's opponent statistics by user ID."""
    from sqlalchemy import or_
    from collections import defaultdict
    
    with session_scope() as session:
        # Verify user exists
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'Player not found'}), 404
        
        # Get all matches for this user
        matches = session.query(Match).filter(
            or_(
                Match.team1_player1_id == user_id,
                Match.team1_player2_id == user_id,
                Match.team2_player1_id == user_id,
                Match.team2_player2_id == user_id
            )
        ).all()
        
        # Calculate opponent stats
        opponent_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_games': 0})
        
        for match in matches:
            # Find opponents
            opponent_ids = []
            won = False
            
            if match.team1_player1_id == user_id or match.team1_player2_id == user_id:
                # User on team 1 - opponents are team 2
                opponent_ids = [match.team2_player1_id, match.team2_player2_id]
                won = match.winner_team == 1
            else:
                # User on team 2 - opponents are team 1
                opponent_ids = [match.team1_player1_id, match.team1_player2_id]
                won = match.winner_team == 2
            
            for opp_id in opponent_ids:
                opponent = session.query(User).filter_by(id=opp_id).first()
                if opponent:
                    opponent_stats[opponent.username]['total_games'] += 1
                    if won:
                        opponent_stats[opponent.username]['wins'] += 1
                    else:
                        opponent_stats[opponent.username]['losses'] += 1
        
        # Convert to lists and filter by minimum 5 games
        all_opponents = []
        for opponent, stats in opponent_stats.items():
            if stats['total_games'] >= 5:  # Only include opponents with 5+ games
                win_rate = (stats['wins'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                loss_rate = (stats['losses'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                all_opponents.append({
                    'opponent': opponent,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'total_games': stats['total_games'],
                    'win_rate': win_rate,
                    'loss_rate': loss_rate
                })
        
        # Top 3 with highest loss rate (opponents you lose most against)
        lost_against = sorted(all_opponents, key=lambda x: x['loss_rate'], reverse=True)[:3]
        
        # Top 3 with highest win rate (opponents you win most against)
        won_against = sorted(all_opponents, key=lambda x: x['win_rate'], reverse=True)[:3]
        
        return jsonify({
            'lost_against': lost_against,
            'won_against': won_against
        })


@app.route('/api/profile/opponents', methods=['GET'])
@login_required
def get_profile_opponents():
    """Get current user's opponent statistics."""
    from sqlalchemy import or_
    from collections import defaultdict
    
    with session_scope() as session:
        # Get all matches for current user
        matches = session.query(Match).filter(
            or_(
                Match.team1_player1_id == current_user.id,
                Match.team1_player2_id == current_user.id,
                Match.team2_player1_id == current_user.id,
                Match.team2_player2_id == current_user.id
            )
        ).all()
        
        # Calculate opponent stats
        opponent_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_games': 0})
        
        for match in matches:
            # Find opponents
            opponent_ids = []
            won = False
            
            if match.team1_player1_id == current_user.id or match.team1_player2_id == current_user.id:
                # User on team 1 - opponents are team 2
                opponent_ids = [match.team2_player1_id, match.team2_player2_id]
                won = match.winner_team == 1
            else:
                # User on team 2 - opponents are team 1
                opponent_ids = [match.team1_player1_id, match.team1_player2_id]
                won = match.winner_team == 2
            
            for opp_id in opponent_ids:
                opponent = session.query(User).filter_by(id=opp_id).first()
                if opponent:
                    opponent_stats[opponent.username]['total_games'] += 1
                    if won:
                        opponent_stats[opponent.username]['wins'] += 1
                    else:
                        opponent_stats[opponent.username]['losses'] += 1
        
        # Convert to lists and filter by minimum 5 games
        all_opponents = []
        for opponent, stats in opponent_stats.items():
            if stats['total_games'] >= 5:  # Only include opponents with 5+ games
                win_rate = (stats['wins'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                loss_rate = (stats['losses'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                all_opponents.append({
                    'opponent': opponent,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'total_games': stats['total_games'],
                    'win_rate': win_rate,
                    'loss_rate': loss_rate
                })
        
        # Top 3 with highest loss rate (opponents you lose most against)
        lost_against = sorted(all_opponents, key=lambda x: x['loss_rate'], reverse=True)[:3]
        
        # Top 3 with highest win rate (opponents you win most against)
        won_against = sorted(all_opponents, key=lambda x: x['win_rate'], reverse=True)[:3]
        
        return jsonify({
            'lost_against': lost_against,
            'won_against': won_against
        })


@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_user_password():
    """Change current user's password."""
    data = request.json if request.is_json else request.form
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current password and new password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    try:
        success = change_password(current_user.id, current_password, new_password)
        
        if success:
            return jsonify({'message': 'Password changed successfully'})
        else:
            return jsonify({'error': 'Current password is incorrect'}), 401
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An error occurred while changing password'}), 500


@app.route('/api/players/stats', methods=['GET'])
@login_required
def get_all_player_stats():
    """Get stats for all players (leaderboard)."""
    limit = request.args.get('limit', type=int)
    if limit:
        leaderboard = get_leaderboard(limit)
    else:
        # No limit - return all players
        from player_stats import get_all_players_stats
        leaderboard = get_all_players_stats()
    return jsonify(leaderboard)


@app.route('/api/players/<int:user_id>/stats', methods=['GET'])
@login_required
def get_user_stats(user_id):
    """Get stats for a specific player."""
    stats = get_player_stats(user_id)
    if stats:
        return jsonify(stats)
    return jsonify({'error': 'Player not found'}), 404


# Session endpoints
@app.route('/api/session', methods=['GET'])
@login_required
def get_session():
    """Get current session status."""
    return jsonify({
        'next_game_number': session_state['next_game_number'],
        'player_count': len(session_state['players'])
    })




# Player endpoints
@app.route('/api/players', methods=['GET'])
@login_required
def get_players():
    """
    Get list of all players with MMR from database.
    
    Returns player objects with name, active status, and MMR from database.
    """
    # Get session players (contains name, active, order, etc.)
    players_list = session_state['players']
    
    # Enrich with MMR from database
    enriched_players = []
    with session_scope() as session:
        for player in players_list:
            player_name = player['name'] if isinstance(player, dict) else player
            
            # Get MMR from database
            user = session.query(User).filter_by(username=player_name).first()
            mmr = user.mmr if user else 1500.0
            
            # Create enriched player object
            if isinstance(player, dict):
                enriched_player = dict(player)  # Copy existing fields
                enriched_player['mmr'] = mmr
            else:
                # Old string format - convert to object
                enriched_player = {
                    'name': player_name,
                    'active': True,
                    'mmr': mmr
                }
            
            enriched_players.append(enriched_player)
    
    return jsonify(enriched_players)


@app.route('/api/players', methods=['POST'])
@login_required
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
    
    # Create user account in database for this player
    try:
        # Check if user already exists in database
        existing_user = get_user_by_username(name)
        if not existing_user:
            # Create new user with default password (same as username)
            create_user(name, name, role=UserRole.PLAYER, mmr=1500.0)
            print(f"Created database user for player: {name}")
    except Exception as e:
        print(f"Warning: Failed to create database user for {name}: {e}")
        # Continue anyway - player can still be added to session
    
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
@admin_required
def delete_player(name):
    """Delete a player (admin only)."""
    player = get_player_by_name(name)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    session_state['players'].remove(player)
    with file_lock:
        save_session()
    
    return jsonify({'message': 'Player deleted successfully'})


@app.route('/api/players/<name>/active', methods=['PATCH'])
@login_required
def toggle_player_active(name):
    """Toggle a player's active status and no-bet mode."""
    player = get_player_by_name(name)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    data = request.json
    if 'active' not in data or not isinstance(data['active'], bool):
        return jsonify({'error': 'Invalid request: "active" field (boolean) is required'}), 400
    
    # Update player active status
    player['active'] = data['active']
    
    # Update no_bet status if provided
    if 'no_bet' in data and isinstance(data['no_bet'], bool):
        player['no_bet'] = data['no_bet']
    
    with file_lock:
        save_session()
    
    return jsonify({'player': player, 'message': 'Player status updated successfully'})


@app.route('/api/players/<name>/deactivated', methods=['PATCH'])
@login_required
def toggle_player_deactivated(name):
    """Toggle a player's deactivated status (hidden from main view)."""
    player = get_player_by_name(name)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    data = request.json
    if 'deactivated' not in data or not isinstance(data['deactivated'], bool):
        return jsonify({'error': 'Invalid request: "deactivated" field (boolean) is required'}), 400
    
    # Update player deactivated status
    player['deactivated'] = data['deactivated']
    
    # When deactivating a player, also mark them as inactive (so they're excluded from recommendations)
    # When reactivating a player, also make them active by default
    if data['deactivated']:
        player['active'] = False  # Deactivated players should not be in recommendations
    else:
        player['active'] = True   # Reactivated players become active
    
    with file_lock:
        save_session()
    
    return jsonify({'player': player, 'message': 'Player visibility updated successfully'})




# Match history endpoints
@app.route('/api/matches', methods=['GET'])
@login_required
def get_matches():
    """Get all recorded matches from database."""
    try:
        with session_scope() as db_session:
            from sqlalchemy.orm import joinedload
            matches = db_session.query(Match).options(
                joinedload(Match.team1_player1),
                joinedload(Match.team1_player2),
                joinedload(Match.team2_player1),
                joinedload(Match.team2_player2),
                joinedload(Match.session)
            ).order_by(Match.created_at.desc()).all()
            
            # Convert to dict format WITHIN session context
            match_list = []
            for m in matches:
                match_list.append({
                    'match_id': str(m.id),
                    'game_number': m.game_number,
                    'session_id': f'session_{m.session.session_date.strftime("%Y-%m-%d")}' if m.session else None,
                    'team1': [m.team1_player1.username, m.team1_player2.username],
                    'team2': [m.team2_player1.username, m.team2_player2.username],
                    'team1_score': m.team1_score,
                    'team2_score': m.team2_score,
                    'game_value': m.game_value,
                    'winner': 'team1' if m.winner_team == 1 else 'team2',
                    'timestamp': m.created_at.isoformat() if m.created_at else None
                })
            
            return jsonify(match_list)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/matches', methods=['POST'])
@login_required
def record_match():
    """Record a new match result."""
    data = request.json

    # Extract and validate required fields
    team1 = data.get('team1')
    team2 = data.get('team2')
    team1_score = data.get('team1_score')
    team2_score = data.get('team2_score')
    game_value = data.get('game_value')
    player_no_bet_status = data.get('player_no_bet_status', {})

    # Validate teams
    if not team1 or not team2:
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
    try:
        team1_score = int(team1_score)
        team2_score = int(team2_score)
        if team1_score < 0 or team2_score < 0:
            return jsonify({'error': 'Scores must be non-negative'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid scores'}), 400

    # Validate game value
    try:
        game_value = int(game_value)
        if game_value < 0 or game_value > 5:
            return jsonify({'error': 'Game value must be between 0 and 5'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid game value'}), 400

    # Assign game number and increment
    with file_lock:
        game_number = session_state['next_game_number']
        session_state['next_game_number'] += 1
        save_session()

    # Create match record
    match_data = {
        'game_number': game_number,
        'team1': team1,
        'team2': team2,
        'team1_score': team1_score,
        'team2_score': team2_score,
        'game_value': game_value,
        'winner': 'team1' if team1_score > team2_score else 'team2',
        'player_no_bet_status': player_no_bet_status
    }

    # Include session_id if provided (for adding to specific session)
    if 'session_id' in data:
        match_data['session_id'] = data['session_id']

    match_id = storage.save_match(match_data)

    # Update MMR after match is saved
    try:
        from mmr_database import update_mmr_for_match
        numeric_match_id = int(match_id.replace('match_', ''))
        update_mmr_for_match(numeric_match_id, k_factor=24)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Don't fail the match save if MMR update fails

    all_matches = storage.get_all_matches()
    saved_match = next((m for m in all_matches if m.get('match_id') == match_id), None)
    return jsonify(saved_match)


@app.route('/api/matches/<match_id>', methods=['PATCH'])
@login_required
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
    
    # Update teams if provided
    if 'team1' in data:
        if not isinstance(data['team1'], list) or len(data['team1']) != 2:
            return jsonify({'error': 'team1 must be an array of 2 players'}), 400
        match_to_update['team1'] = data['team1']
    
    if 'team2' in data:
        if not isinstance(data['team2'], list) or len(data['team2']) != 2:
            return jsonify({'error': 'team2 must be an array of 2 players'}), 400
        match_to_update['team2'] = data['team2']
    
    # Validate all players are distinct if both teams are provided
    if 'team1' in data or 'team2' in data:
        all_players = match_to_update.get('team1', []) + match_to_update.get('team2', [])
        if len(set(all_players)) != 4:
            return jsonify({'error': 'All 4 players must be distinct'}), 400
    
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
    
    # Recalculate MMR after match update
    # Since match details changed, we need to recalculate all MMR from scratch
    print(f"Match {match_id} updated, recalculating all MMR...")
    try:
        from mmr_database import recalculate_all_mmr
        
        # Recalculate MMR for all players from all matches
        player_ratings = recalculate_all_mmr(k_factor=24)
        
        print(f"MMR recalculated successfully for {len(player_ratings)} players")
    except Exception as e:
        import traceback
        print(f"Warning: Failed to recalculate MMR after edit: {e}")
        traceback.print_exc()
    
    return jsonify(match_to_update)


@app.route('/api/matches/<match_id>', methods=['DELETE'])
@admin_required
def delete_match(match_id):
    """
    Delete a match (admin only).
    
    After deletion, recalculates all MMR from scratch to ensure accuracy.
    This is necessary because ELO ratings depend on the chronological order
    of matches, so removing a match requires replaying all remaining matches.
    """
    print(f"\n=== DELETE /api/matches/{match_id} called ===")
    
    success = storage.delete_match(match_id)
    
    if not success:
        print(f"Match {match_id} not found")
        return jsonify({'error': 'Match not found'}), 404
    
    print(f"Match {match_id} deleted from database")
    
    # Recalculate ALL MMR from scratch after match deletion
    # This ensures MMR accurately reflects the remaining match history
    print("Recalculating all MMR from remaining matches...")
    try:
        from mmr_database import recalculate_all_mmr
        
        # Recalculate MMR for all players from all remaining matches
        player_ratings = recalculate_all_mmr(k_factor=24)
        
        print(f"MMR recalculated successfully for {len(player_ratings)} players")
        print("Sample new ratings:")
        for player, rating in list(player_ratings.items())[:5]:
            print(f"  {player}: {rating:.2f}")
    
    except Exception as e:
        import traceback
        print(f"Warning: Failed to recalculate MMR after delete: {e}")
        traceback.print_exc()
        # Don't fail the delete if MMR recalculation fails
    
    print(f"=== Match {match_id} deletion complete ===\n")
    return jsonify({'message': 'Match deleted successfully', 'match_id': match_id})


# Session endpoints
@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all sessions with summary information from database."""
    from models import Session as SessionModel
    with session_scope() as db_session:
        sessions = db_session.query(SessionModel).order_by(SessionModel.session_date.desc()).all()
        
        session_list = []
        for s in sessions:
            session_list.append({
                'session_id': f'session_{s.session_date.strftime("%Y-%m-%d")}',
                'date': s.session_date.strftime("%Y-%m-%d"),
                'match_count': len(s.matches) if s.matches else 0
            })
        
        return jsonify(session_list)


@app.route('/api/sessions/current', methods=['GET'])
@login_required
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
@login_required
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
@login_required
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
@admin_required
def update_session(session_id):
    """Update a session's date (admin only)."""
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
@admin_required
def delete_session(session_id):
    """Delete a session and all its matches (admin only)."""
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


@app.route('/api/sessions/cleanup', methods=['POST'])
@admin_required
def cleanup_empty_sessions():
    """Delete all sessions with no games (admin only)."""
    deleted_count = storage.cleanup_all_empty_sessions()
    return jsonify({
        'message': 'Empty sessions cleaned up',
        'deleted_count': deleted_count
    })


# Stats endpoint
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """
    Get player statistics from database.
    
    IMPORTANT: This endpoint now reads from the database, not JSON files.
    It returns comprehensive stats including MMR from the User table.
    """
    from player_stats import get_all_players_stats
    
    try:
        # Get all player stats from database
        stats_list = get_all_players_stats()
        
        # Transform to match expected format for frontend
        # (get_all_players_stats returns different field names)
        transformed = []
        for player_stat in stats_list:
            transformed.append({
                'player': player_stat['username'],
                'total_matches': player_stat['total_matches'],
                'wins': player_stat['wins'],
                'losses': player_stat['losses'],
                'win_rate': player_stat['win_rate'],
                'earnings': player_stat['net_earnings'],
                'net_earnings': player_stat['net_earnings'],
                'total_winnings': player_stat['total_winnings'],
                'total_losses': player_stat['total_losses'],
                'partners': ', '.join(player_stat.get('partners', [])),
                'opponents': ', '.join(player_stat.get('opponents', [])),
                'mmr': player_stat['mmr']  # MMR from database
            })
        
        # Sort by total matches (most active first)
        transformed.sort(key=lambda x: x['total_matches'], reverse=True)
        
        return jsonify(transformed)
    
    except Exception as e:
        import traceback
        print(f"Error in /api/stats: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to load stats'}), 500


@app.route('/api/earnings', methods=['GET'])
@login_required
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
@login_required
def get_monthly_earnings():
    """Get player earnings/losses for a specific month.
    
    Query params:
        year (int, optional): Year (defaults to current year)
        month (int, optional): Month 1-12 (defaults to current month)
    """
    # Get optional query params
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # Use match_storage's no-bet aware monthly earnings calculation
    earnings_list = storage.get_monthly_player_earnings(year, month)

    return jsonify(earnings_list)


@app.route('/api/earnings/range', methods=['GET'])
@login_required
def get_earnings_range():
    """Get player earnings for a date range (both months inclusive).

    Query params:
        from_year (int): Start year
        from_month (int): Start month 1-12
        to_year (int): End year
        to_month (int): End month 1-12
    """
    now = _now_pacific()
    from_year = request.args.get('from_year', type=int) or now.year
    from_month = request.args.get('from_month', type=int) or 1
    to_year = request.args.get('to_year', type=int) or now.year
    to_month = request.args.get('to_month', type=int) or now.month

    earnings_list = storage.get_player_earnings_range(from_year, from_month, to_year, to_month)
    return jsonify(earnings_list)


@app.route('/api/mmr/snapshot', methods=['GET'])
@login_required
def get_mmr_snapshot():
    """Get absolute MMR for all players as of the end of a given month.

    Replays all matches chronologically up to end of target month.

    Query params:
        year (int): Target year
        month (int): Target month 1-12
    """
    try:
        from datetime import date as date_cls
        from mmr_calculator import process_match

        now = _now_pacific()
        year = request.args.get('year', type=int) or now.year
        month = request.args.get('month', type=int) or now.month

        # Cutoff: first day of the month after the target
        if month == 12:
            cutoff = date_cls(year + 1, 1, 1)
        else:
            cutoff = date_cls(year, month + 1, 1)

        all_matches = storage.get_all_matches()
        all_matches.sort(key=lambda m: m.get('session_id', ''))

        mmr_state = {}

        for match in all_matches:
            session_id = match.get('session_id', '')
            date_str = session_id.replace('session_', '') if session_id.startswith('session_') else None
            if not date_str:
                continue
            try:
                match_date = date_cls.fromisoformat(date_str)
            except ValueError:
                continue

            if match_date >= cutoff:
                break

            team1 = match.get('team1', [])
            team2 = match.get('team2', [])
            winner = match.get('winner')

            for player in team1 + team2:
                if player not in mmr_state:
                    mmr_state[player] = 1500

            if len(team1) == 2 and len(team2) == 2 and winner:
                process_match(team1, team2, winner, mmr_state, k_factor=24)

        return jsonify({p: round(v) for p, v in mmr_state.items()})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/mmr/monthly', methods=['GET'])
@login_required
def get_monthly_mmr_changes():
    """Calculate MMR changes for a specific month by processing matches chronologically.
    
    Query params:
        year (int, optional): Year (defaults to current year)
        month (int, optional): Month 1-12 (defaults to current month)
    """
    try:
        from datetime import date as date_cls
        from mmr_calculator import process_match
        
        # Get optional query params
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        # Default to current year/month if not provided
        if not year or not month:
            now = _now_pacific()
            year = year or now.year
            month = month or now.month
        
        # Calculate first and last day of the month
        first_day = date_cls(year, month, 1)
        if month == 12:
            last_day = date_cls(year + 1, 1, 1)
        else:
            last_day = date_cls(year, month + 1, 1)
        
        # Get all matches sorted by date
        all_matches = storage.get_all_matches()
        all_matches.sort(key=lambda m: m.get('session_id', ''))
        
        # Initialize MMR ratings at 1500 for all players
        mmr_before_month = {}  # MMR just before month starts
        mmr_after_month = {}   # MMR just after month ends
        mmr_current = {}       # Running MMR (player_name: current_rating)
        in_target_month = False
        
        # Process all matches chronologically
        for match in all_matches:
            session_id = match.get('session_id', '')
            # Session ID format: "session_2025-10-27" -> extract "2025-10-27"
            match_date_str = session_id.replace('session_', '') if session_id.startswith('session_') else None
            
            if not match_date_str:
                continue
            
            try:
                match_date = date_cls.fromisoformat(match_date_str)
            except ValueError:
                continue
            
            team1 = match.get('team1', [])
            team2 = match.get('team2', [])
            winner = match.get('winner')
            
            # Initialize players if not seen before
            for player in team1 + team2:
                if player not in mmr_current:
                    mmr_current[player] = 1500
            
            # Track when we enter the target month
            if match_date >= first_day and not in_target_month:
                in_target_month = True
                # Save MMR at start of month
                mmr_before_month = dict(mmr_current)
            
            # Track when we exit the target month
            if in_target_month and match_date >= last_day:
                # Save MMR at end of month (only once)
                if not mmr_after_month:
                    mmr_after_month = dict(mmr_current)
            
            # Calculate MMR changes for this match (for all matches, to track running totals)
            if len(team1) == 2 and len(team2) == 2 and winner:
                # process_match modifies mmr_current in place and returns changes
                rating_changes = process_match(
                    team1, team2, 
                    winner, 
                    mmr_current,
                    k_factor=24
                )
        
        # If we never exited the month (month is current or last), use current MMR
        if in_target_month and not mmr_after_month:
            mmr_after_month = dict(mmr_current)
        
        # Calculate monthly changes only for players who played in the month
        monthly_changes = {}
        for player in mmr_before_month:
            start = mmr_before_month.get(player, 1500)
            end = mmr_after_month.get(player, start)
            monthly_changes[player] = round(end - start)
        
        return jsonify(monthly_changes)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/partnerships', methods=['GET'])
@login_required
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
@login_required
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
@login_required
def get_session_earnings(session_id):
    """Get player earnings/losses for a specific session."""
    # Use match_storage's no-bet aware earnings calculation
    earnings_dict = storage.get_session_player_stats(session_id)
    
    if not earnings_dict:
        # Check if session exists
        session = storage.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
    
    # Convert to list
    earnings_list = []
    for player, stats in earnings_dict.items():
        earnings_list.append({
            'player': player,
            'games_played': stats['games_played'],
            'total_winnings': stats['total_winnings'],
            'total_losses': stats['total_losses'],
            'net_earnings': stats['net_earnings']
        })
    
    # Sort by net earnings descending
    earnings_list.sort(key=lambda x: x['net_earnings'], reverse=True)
    
    return jsonify({
        'session_id': session_id,
        'players': earnings_list
    })


@app.route('/api/sessions/<session_id>/stats', methods=['GET'])
@login_required
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
@login_required
def get_recommendations():
    """Get recommended matchups based on current session partnership history.
    
    Supports multi-court mode based on active player count.
    
    Query params:
        exclude_ids: Comma-separated player names to exclude (for cycling)
        current_courts: JSON array of current court assignments [{"court": 1, "players": ["A", "B", "C", "D"]}, ...]
    """
    from collections import Counter, defaultdict
    import itertools
    import random
    import json
    from flask import request
    
    # Get only active players
    all_active_players = get_active_players()
    
    # Parse current_courts parameter to track who's currently playing
    current_courts_param = request.args.get('current_courts', '[]')
    try:
        current_courts_data = json.loads(current_courts_param)
        currently_playing_players = set()
        for court_data in current_courts_data:
            players_on_court = court_data.get('players', [])
            currently_playing_players.update(players_on_court)
    except (json.JSONDecodeError, TypeError):
        currently_playing_players = set()
    
    # Get current session and its matches FIRST (to count games before filtering)
    current_session = storage.get_current_session()
    session_matches = storage.get_session_matches(current_session['session_id'])
    
    # Build partnership counter, total games, and same-court counts
    partnership_counts = Counter()
    total_games = Counter()
    same_court_counts = Counter()  # Track how often players are on same court (teammate or opponent)
    teammate_counts = defaultdict(Counter)  # Track who each player has been teammates with
    opponent_counts = defaultdict(Counter)  # Track who each player has played against
    
    # Track who played in the last round (to prioritize those who sat out)
    # For multi-court, collect from the last num_courts matches (one per court per round)
    _num_courts_for_last_round = max(1, len(all_active_players) // 4)
    last_game_players = set()
    if session_matches:
        last_round_matches = session_matches[-_num_courts_for_last_round:]
        for _m in last_round_matches:
            last_game_players.update(_m.get('team1', []) + _m.get('team2', []))
    
    for match in session_matches:
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        
        # Count partnerships (teammates)
        if len(team1) == 2:
            partnership_counts[frozenset(team1)] += 1
            for player in team1:
                total_games[player] += 1
            # Track teammate relationships
            teammate_counts[team1[0]][team1[1]] += 1
            teammate_counts[team1[1]][team1[0]] += 1
        
        if len(team2) == 2:
            partnership_counts[frozenset(team2)] += 1
            for player in team2:
                total_games[player] += 1
            # Track teammate relationships
            teammate_counts[team2[0]][team2[1]] += 1
            teammate_counts[team2[1]][team2[0]] += 1
        
        # Track opponent relationships
        if len(team1) == 2 and len(team2) == 2:
            for p1 in team1:
                for p2 in team2:
                    opponent_counts[p1][p2] += 1
                    opponent_counts[p2][p1] += 1
        
        # Count same-court occurrences (all 4 players on court together)
        all_players_in_match = team1 + team2
        if len(all_players_in_match) == 4:
            # For each pair of players in this match, increment their same-court count
            for i in range(len(all_players_in_match)):
                for j in range(i + 1, len(all_players_in_match)):
                    pair_key = frozenset([all_players_in_match[i], all_players_in_match[j]])
                    same_court_counts[pair_key] += 1
    
    # Calculate win rates for all active players from historical data
    player_win_rates = {}
    for player in all_active_players:
        stats = storage.get_player_stats(player)
        total_matches = stats.get('total_matches', 0)
        wins = stats.get('wins', 0)
        # Calculate win rate as percentage (0-100)
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 50.0
        player_win_rates[player] = win_rate
    
    # Determine number of courts needed based on active players
    # 1 court per 4 players: 4-7=1 court, 8-11=2 courts, 12-15=3 courts, etc.
    num_courts = max(1, len(all_active_players) // 4)
    is_multi_court = num_courts > 1
    
    # For multi-court mode, ALWAYS use all active players (ignore exclude_ids)
    # For single-court mode, handle exclude_ids for cycling
    if is_multi_court:
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
    
    def calculate_sitout_penalty(players_in_matchup):
        """Calculate penalty for players sitting out.

        When a game is in progress (currently_playing_players is set):
          - Any player NOT on court right now MUST be in the next suggestion.
          - This ensures everyone currently sitting out gets included.

        Between games (no one on court):
          - Fall back to last recorded match: anyone who sat out that game
            must be included in the next suggestion.
        """
        playing_players = set(players_in_matchup)
        sitting_players = set(all_active_players) - playing_players

        penalty = 0
        for player in sitting_players:
            if currently_playing_players:
                # Game in progress: penalise leaving out anyone currently off court
                if player not in currently_playing_players:
                    penalty += 10000
            else:
                # Between games: penalise leaving out anyone who sat out last game
                if player not in last_game_players:
                    penalty += 10000

        # Small base penalty per sitting player to prefer fewer sit-outs
        penalty += len(sitting_players) * 10

        return penalty
    
    def calculate_john_balance_penalty(players_in_matchup):
        """Calculate penalty for John's pairing imbalance with other players."""
        if 'John' not in players_in_matchup:
            return 0
        
        # Get John's current counts
        john_teammates = teammate_counts.get('John', Counter())
        john_opponents = opponent_counts.get('John', Counter())
        
        penalty = 0
        for player in players_in_matchup:
            if player == 'John':
                continue
            
            # Check if John is teammate or opponent in this matchup
            is_teammate = False
            for team_a, team_b in [((players_in_matchup[0], players_in_matchup[1]), (players_in_matchup[2], players_in_matchup[3])),
                                   ((players_in_matchup[0], players_in_matchup[2]), (players_in_matchup[1], players_in_matchup[3])),
                                   ((players_in_matchup[0], players_in_matchup[3]), (players_in_matchup[1], players_in_matchup[2]))]:
                if 'John' in team_a and player in team_a:
                    is_teammate = True
                    break
                if 'John' in team_b and player in team_b:
                    is_teammate = True
                    break
            
            current_teammate_count = john_teammates.get(player, 0)
            current_opponent_count = john_opponents.get(player, 0)
            
            if is_teammate:
                # Penalize if John has already been teammates with this player more than opponents
                imbalance = current_teammate_count - current_opponent_count
                if imbalance > 0:
                    penalty += imbalance * 3  # Weight of 3 for teammate imbalance
            else:
                # Penalize if John has already been opponents with this player more than teammates
                imbalance = current_opponent_count - current_teammate_count
                if imbalance > 0:
                    penalty += imbalance * 3  # Weight of 3 for opponent imbalance
        
        return penalty
    
    def generate_matchup_for_players(candidate_players, partnership_counts, total_games):
        """Generate best single matchup for given players."""
        # Validate we have at least 4 players
        if len(candidate_players) < 4:
            return None
        
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
                
                # Calculate win rate imbalance penalty
                # Get average win rates for each team
                team_a_wr = (player_win_rates.get(team_a[0], 50.0) + player_win_rates.get(team_a[1], 50.0)) / 2
                team_b_wr = (player_win_rates.get(team_b[0], 50.0) + player_win_rates.get(team_b[1], 50.0)) / 2
                win_rate_diff = abs(team_a_wr - team_b_wr)
                
                # Calculate same-court penalty (how often these 4 players have been together)
                # Sum all pair combinations among the 4 players
                same_court_score = 0
                all_four = [p1, p2, p3, p4]
                for i in range(len(all_four)):
                    for j in range(i + 1, len(all_four)):
                        pair_key = frozenset([all_four[i], all_four[j]])
                        same_court_score += same_court_counts.get(pair_key, 0)
                
                # Calculate sit-out penalty (HIGHEST PRIORITY - avoid consecutive sit-outs)
                sitout_penalty = calculate_sitout_penalty([p1, p2, p3, p4])
                
                # Calculate John balance penalty (if John is in this matchup)
                john_penalty = calculate_john_balance_penalty([p1, p2, p3, p4])
                
                # Calculate opponent diversity scores
                opponent_score = 0
                for p_a in team_a:
                    for p_o in team_b:
                        opponent_score += opponent_counts.get(p_a, Counter()).get(p_o, 0)
                
                # Score tuple with NEW priorities:
                # 1. Sit-out penalty (HIGHEST - never sit out >1 round)
                # 2. Partnership variety (partner diversity - minimize repeats)
                # 3. Opponent variety (opponent diversity - minimize repeats)
                # 4. Games balance
                # 5. Win rate balance
                # 6. Same-court variety
                score = (
                    sitout_penalty,          # Priority 1 (HIGHEST): Sitting >1 round
                    max(count_a, count_b),  # Priority 2: Worst partnership repeat count
                    count_a + count_b,       # Priority 3: Total partnership repeats
                    opponent_score,          # Priority 4: Opponent diversity (minimize repeats)
                    games_balance,           # Priority 5: Balance of total games played
                    win_rate_diff * 2,       # Priority 6: Win rate balance (weighted at 2)
                    same_court_score,        # Priority 7: Same-court variety
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

        # First game: no history, return a random matchup
        if not session_matches:
            random.shuffle(all_matchups)
            return all_matchups[0]

        # Sort by score and return best
        all_matchups.sort(key=lambda x: x['score'])
        return all_matchups[0]
    
    if is_multi_court:
        # MULTI-COURT MODE: Generate N separate matchups based on player count
        # For cycling: shuffle ALL players to ensure rotation
        shuffled_players = players[:]
        random.shuffle(shuffled_players)
        
        # Calculate how many players we need (4 per court)
        players_needed = num_courts * 4
        selected_players = shuffled_players[:players_needed]
        
        # Validate we have enough players
        if len(selected_players) < players_needed:
            return jsonify({'error': f'Not enough players for {num_courts} courts'}), 400
        
        # Generate matchups for each court
        court_matchups = []
        player_ids = []
        
        for court_num in range(1, num_courts + 1):
            # Get 4 players for this court
            court_start = (court_num - 1) * 4
            court_end = court_num * 4
            court_players = selected_players[court_start:court_end]
            
            # Generate best matchup for these 4 players
            matchup = generate_matchup_for_players(court_players, partnership_counts, total_games)
            
            if not matchup:
                return '', 204  # No Content
            
            # Build court explanation
            court_explanation = f"{matchup['team_a'][0]}/{matchup['team_a'][1]} {format_count(matchup['count_a'])} vs {matchup['team_b'][0]}/{matchup['team_b'][1]} {format_count(matchup['count_b'])}"
            
            court_matchups.append({
                'court': court_num,
                'team_a': matchup['team_a'],
                'team_b': matchup['team_b'],
                'explanation': court_explanation
            })
            
            # Add player IDs in order: Team A, Team B
            player_ids.extend(matchup['team_a'])
            player_ids.extend(matchup['team_b'])
        
        return jsonify({
            'multi_court': True,
            'num_courts': num_courts,
            'matchups': court_matchups,
            'player_ids': player_ids,
            'current_index': 0
        })
        
        # Note: Keeping 'dual_court' for backward compatibility will be handled by frontend
    
    # SINGLE-COURT MODE: Generate 1 matchup (original behavior)
    best_matchup = generate_matchup_for_players(players, partnership_counts, total_games)
    
    if not best_matchup:
        return '', 204  # No Content
    
    # Generate alternatives for cycling
    # Special handling: if player count is 4 or 6 (even and small), ensure all players are included in recommendations
    # This prevents leaving someone out when everyone should play
    if len(players) in [4, 6]:
        # For 4 or 6 players: only consider matchups that include ALL players possible
        # For 4 players: all matchups include all 4
        # For 6 players: each matchup should try to rotate fairly, but we'll prioritize including different sets
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
                
                # Calculate win rate imbalance for alternatives
                team_a_wr = (player_win_rates.get(team_a[0], 50.0) + player_win_rates.get(team_a[1], 50.0)) / 2
                team_b_wr = (player_win_rates.get(team_b[0], 50.0) + player_win_rates.get(team_b[1], 50.0)) / 2
                win_rate_diff = abs(team_a_wr - team_b_wr)
                
                # Calculate same-court penalty for alternatives
                same_court_score = 0
                all_four = [p1, p2, p3, p4]
                for i in range(len(all_four)):
                    for j in range(i + 1, len(all_four)):
                        pair_key = frozenset([all_four[i], all_four[j]])
                        same_court_score += same_court_counts.get(pair_key, 0)
                
                # Calculate sit-out penalty for alternatives
                sitout_penalty = calculate_sitout_penalty([p1, p2, p3, p4])
                
                # Calculate John balance penalty for alternatives
                john_penalty = calculate_john_balance_penalty([p1, p2, p3, p4])
                
                # Calculate opponent diversity for alternatives
                opponent_score_alt = 0
                for p_a in team_a:
                    for p_o in team_b:
                        opponent_score_alt += opponent_counts.get(p_a, Counter()).get(p_o, 0)
                
                score = (
                    sitout_penalty,           # Priority 1: Sitting >1 round
                    max(count_a, count_b),   # Priority 2: Worst partnership repeat count
                    count_a + count_b,        # Priority 3: Total partnership repeats
                    opponent_score_alt,       # Priority 4: Opponent diversity
                    games_balance,            # Priority 5: Balance of total games played
                    win_rate_diff * 2,        # Priority 6: Win rate balance (weighted at 2)
                    same_court_score,         # Priority 7: Same-court variety
                    sorted([p1, p2, p3, p4])  # Deterministic tiebreaker
                )
                all_matchups_for_alternatives.append({
                    'score': score,
                    'team_a': list(team_a),
                    'team_b': list(team_b),
                    'count_a': count_a,
                    'count_b': count_b,
                    'players_in_match': set([p1, p2, p3, p4])
                })
    else:
        # For other player counts: standard generation
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
                
                # Calculate win rate imbalance for alternatives
                team_a_wr = (player_win_rates.get(team_a[0], 50.0) + player_win_rates.get(team_a[1], 50.0)) / 2
                team_b_wr = (player_win_rates.get(team_b[0], 50.0) + player_win_rates.get(team_b[1], 50.0)) / 2
                win_rate_diff = abs(team_a_wr - team_b_wr)
                
                # Calculate same-court penalty for alternatives
                same_court_score = 0
                all_four = [p1, p2, p3, p4]
                for i in range(len(all_four)):
                    for j in range(i + 1, len(all_four)):
                        pair_key = frozenset([all_four[i], all_four[j]])
                        same_court_score += same_court_counts.get(pair_key, 0)
                
                # Calculate sit-out penalty for alternatives
                sitout_penalty = calculate_sitout_penalty([p1, p2, p3, p4])
                
                # Calculate John balance penalty for alternatives
                john_penalty = calculate_john_balance_penalty([p1, p2, p3, p4])
                
                # Calculate opponent diversity for alternatives
                opponent_score_alt2 = 0
                for p_a in team_a:
                    for p_o in team_b:
                        opponent_score_alt2 += opponent_counts.get(p_a, Counter()).get(p_o, 0)
                
                score = (
                    sitout_penalty,           # Priority 1: Sitting >1 round
                    max(count_a, count_b),   # Priority 2: Worst partnership repeat count
                    count_a + count_b,        # Priority 3: Total partnership repeats
                    opponent_score_alt2,      # Priority 4: Opponent diversity
                    games_balance,            # Priority 5: Balance of total games played
                    win_rate_diff * 2,        # Priority 6: Win rate balance (weighted at 2)
                    same_court_score,         # Priority 7: Same-court variety
                    sorted([p1, p2, p3, p4])  # Deterministic tiebreaker
                )
                all_matchups_for_alternatives.append({
                    'score': score,
                    'team_a': list(team_a),
                    'team_b': list(team_b),
                    'count_a': count_a,
                    'count_b': count_b
                })
    
    if not session_matches:
        # First game: no history, randomize alternatives
        random.shuffle(all_matchups_for_alternatives)
    else:
        all_matchups_for_alternatives.sort(key=lambda x: x['score'])

    # Deduplicate by 4-player group: keep only the best-scoring partition per group.
    # This means cycling shows different PLAYER combinations, not just different team splits
    # of the same 4 players (the cycle-single-court button handles that separately).
    seen_groups = {}
    for m in all_matchups_for_alternatives:
        group_key = frozenset(m['team_a'] + m['team_b'])
        if group_key not in seen_groups:
            seen_groups[group_key] = m  # first occurrence is best (list is sorted)

    # Only include groups that achieve the minimum sit-out penalty.
    # This ensures mandatory sit-out players are respected across all suggestions.
    deduped = list(seen_groups.values())
    if deduped:
        min_sitout = min(m['score'][0] for m in deduped)
        valid = [m for m in deduped if m['score'][0] == min_sitout]
        valid.sort(key=lambda x: x['score'])
    else:
        valid = []

    # Return all valid groups (dynamically sized — e.g. 4 when 3 players are mandatory)
    # capped at 10 to keep the UI manageable when many combinations are equally valid.
    recommendations = []
    for matchup in valid[:10]:
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
        'current_index': 0,
        '_debug': {
            'all_active_players': all_active_players,
            'session_match_count': len(session_matches),
            'last_game_players': sorted(list(last_game_players)),
            'currently_playing_players': sorted(list(currently_playing_players)),
            'num_courts_for_last_round': _num_courts_for_last_round,
            'best_matchup_score': list(best_matchup['score'][:7]),
        }
    })


@app.route('/api/recommendations/court', methods=['GET'])
@login_required
def get_court_recommendation():
    """Get a single court recommendation for 4 players.
    
    Uses the same recommendation algorithm as main recommendations.
    Can include players already assigned to other courts.
    Excludes matchups that are already assigned to other courts.
    
    Query params:
        exclude_partnerships (JSON string): List of partnerships to exclude (as sorted player arrays)
        exclude_players (JSON string): List of individual players to exclude from recommendations
    
    Returns a single matchup for 4 players.
    """
    from collections import Counter, defaultdict
    import itertools
    import random
    import json
    from flask import request
    
    # Get excluded partnerships from query params
    excluded_partnerships_param = request.args.get('exclude_partnerships', '[]')
    try:
        excluded_partnerships = json.loads(excluded_partnerships_param)
        # Convert to frozensets for fast lookup
        excluded_partnership_sets = [frozenset(partnership) for partnership in excluded_partnerships]
    except (json.JSONDecodeError, TypeError):
        excluded_partnership_sets = []
    
    # Get excluded players from query params
    excluded_players_param = request.args.get('exclude_players', '[]')
    try:
        excluded_players = set(json.loads(excluded_players_param))
    except (json.JSONDecodeError, TypeError):
        excluded_players = set()
    
    # Get only active players (same as main recommendations)
    all_active_players = get_active_players()
    
    # Filter out excluded players
    if excluded_players:
        all_active_players = [p for p in all_active_players if p not in excluded_players]
    
    if len(all_active_players) < 4:
        return jsonify({'error': 'Not enough active players'}), 400
    
    # Get current session and its matches (for partnership history)
    current_session = storage.get_current_session()
    session_matches = storage.get_session_matches(current_session['session_id'])
    
    # Build partnership counter and total games (same logic as main)
    partnership_counts = Counter()
    total_games = Counter()
    same_court_counts = Counter()
    teammate_counts = defaultdict(Counter)
    opponent_counts = defaultdict(Counter)
    
    # Track who played in the last game
    last_game_players = set()
    if session_matches:
        last_match = session_matches[-1]
        last_team1 = last_match.get('team1', [])
        last_team2 = last_match.get('team2', [])
        last_game_players = set(last_team1 + last_team2)
    
    for match in session_matches:
        team1 = match.get('team1', [])
        team2 = match.get('team2', [])
        
        if len(team1) == 2:
            partnership_counts[frozenset(team1)] += 1
            for player in team1:
                total_games[player] += 1
            teammate_counts[team1[0]][team1[1]] += 1
            teammate_counts[team1[1]][team1[0]] += 1
        
        if len(team2) == 2:
            partnership_counts[frozenset(team2)] += 1
            for player in team2:
                total_games[player] += 1
            teammate_counts[team2[0]][team2[1]] += 1
            teammate_counts[team2[1]][team2[0]] += 1
        
        if len(team1) == 2 and len(team2) == 2:
            for p1 in team1:
                for p2 in team2:
                    opponent_counts[p1][p2] += 1
                    opponent_counts[p2][p1] += 1
        
        all_players_in_match = team1 + team2
        if len(all_players_in_match) == 4:
            for i in range(len(all_players_in_match)):
                for j in range(i + 1, len(all_players_in_match)):
                    pair_key = frozenset([all_players_in_match[i], all_players_in_match[j]])
                    same_court_counts[pair_key] += 1
    
    # Calculate win rates for all active players
    player_win_rates = {}
    for player in all_active_players:
        stats = storage.get_player_stats(player)
        total_matches = stats.get('total_matches', 0)
        wins = stats.get('wins', 0)
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 50.0
        player_win_rates[player] = win_rate
    
    def format_count(count):
        if count == 0:
            return "🆕"
        elif count == 1:
            return "①"
        else:
            return f"×{count}"
    
    def calculate_sitout_penalty(players_in_matchup):
        playing_players = set(players_in_matchup)
        sitting_players = set(all_active_players) - playing_players
        
        penalty = 0
        for player in sitting_players:
            if player not in last_game_players:
                penalty += 1000
        
        penalty += len(sitting_players) * 10
        return penalty
    
    def calculate_john_balance_penalty(players_in_matchup):
        if 'John' not in players_in_matchup:
            return 0
        
        john_teammates = teammate_counts.get('John', Counter())
        john_opponents = opponent_counts.get('John', Counter())
        
        penalty = 0
        for player in players_in_matchup:
            if player == 'John':
                continue
            
            is_teammate = False
            for team_a, team_b in [((players_in_matchup[0], players_in_matchup[1]), (players_in_matchup[2], players_in_matchup[3])),
                                   ((players_in_matchup[0], players_in_matchup[2]), (players_in_matchup[1], players_in_matchup[3])),
                                   ((players_in_matchup[0], players_in_matchup[3]), (players_in_matchup[1], players_in_matchup[2]))]:
                if 'John' in team_a and player in team_a:
                    is_teammate = True
                    break
                if 'John' in team_b and player in team_b:
                    is_teammate = True
                    break
            
            current_teammate_count = john_teammates.get(player, 0)
            current_opponent_count = john_opponents.get(player, 0)
            
            if is_teammate:
                imbalance = current_teammate_count - current_opponent_count
                if imbalance > 0:
                    penalty += imbalance * 3
            else:
                imbalance = current_opponent_count - current_teammate_count
                if imbalance > 0:
                    penalty += imbalance * 3
        
        return penalty
    
    # Shuffle all active players for variety
    shuffled_players = all_active_players[:]
    random.shuffle(shuffled_players)
    
    # Try all 4-player combinations from shuffled list
    all_matchups = []
    for four_players in itertools.combinations(shuffled_players, 4):
        p1, p2, p3, p4 = four_players
        
        partitions = [
            ((p1, p2), (p3, p4)),
            ((p1, p3), (p2, p4)),
            ((p1, p4), (p2, p3))
        ]
        
        for team_a, team_b in partitions:
            # Skip if this partnership is already on another court
            team_a_set = frozenset(team_a)
            team_b_set = frozenset(team_b)
            if team_a_set in excluded_partnership_sets or team_b_set in excluded_partnership_sets:
                continue
            
            count_a = partnership_counts.get(frozenset(team_a), 0)
            count_b = partnership_counts.get(frozenset(team_b), 0)
            
            games_a = total_games.get(team_a[0], 0) + total_games.get(team_a[1], 0)
            games_b = total_games.get(team_b[0], 0) + total_games.get(team_b[1], 0)
            games_balance = abs(games_a - games_b)
            
            team_a_wr = (player_win_rates.get(team_a[0], 50.0) + player_win_rates.get(team_a[1], 50.0)) / 2
            team_b_wr = (player_win_rates.get(team_b[0], 50.0) + player_win_rates.get(team_b[1], 50.0)) / 2
            win_rate_diff = abs(team_a_wr - team_b_wr)
            
            same_court_score = 0
            all_four = [p1, p2, p3, p4]
            for i in range(len(all_four)):
                for j in range(i + 1, len(all_four)):
                    pair_key = frozenset([all_four[i], all_four[j]])
                    same_court_score += same_court_counts.get(pair_key, 0)
            
            sitout_penalty = calculate_sitout_penalty([p1, p2, p3, p4])
            john_penalty = calculate_john_balance_penalty([p1, p2, p3, p4])
            
            score = (
                sitout_penalty,
                max(count_a, count_b),
                games_balance,
                john_penalty,
                count_a + count_b,
                win_rate_diff * 2,
                same_court_score,
                sorted([p1, p2, p3, p4])
            )
            
            all_matchups.append({
                'score': score,
                'team_a': list(team_a),
                'team_b': list(team_b),
                'count_a': count_a,
                'count_b': count_b
            })
    
    if not all_matchups:
        return '', 204
    
    # Sort and get best matchup
    all_matchups.sort(key=lambda x: x['score'])
    best_matchup = all_matchups[0]
    
    explanation = f"{best_matchup['team_a'][0]}/{best_matchup['team_a'][1]} {format_count(best_matchup['count_a'])} vs {best_matchup['team_b'][0]}/{best_matchup['team_b'][1]} {format_count(best_matchup['count_b'])}"
    player_ids = best_matchup['team_a'] + best_matchup['team_b']
    
    return jsonify({
        'team_a': best_matchup['team_a'],
        'team_b': best_matchup['team_b'],
        'explanation': explanation,
        'player_ids': player_ids
    })


# ==================== Admin Endpoints ====================

@app.route('/api/admin/recalculate-mmr', methods=['POST'])
@login_required
@admin_required
def recalculate_mmr():
    """
    Admin endpoint to recalculate MMR ratings for all players.
    Recalculates MMR from scratch based on all matches in the database.
    """
    try:
        from mmr_database import recalculate_all_mmr
        
        # Recalculate MMR for all players from all matches
        player_ratings = recalculate_all_mmr(k_factor=24)
        
        return jsonify({
            'message': 'MMR ratings recalculated successfully',
            'timestamp': _now_pacific().isoformat(),
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
