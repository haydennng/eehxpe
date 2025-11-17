# Badminton Matchup Manager - Web Application

A Flask-based web application for managing fair 2v2 badminton matchups during multi-hour play sessions.

## Features

- **Dark Theme UI**: Gun metal grey and dark green color scheme
- **Player Management**: Add and remove players for sessions
- **Session Configuration**: Customize duration, game length, pricing strategies
- **Fair Matchup Generation**: Automatically generates balanced 2v2 matchups
- **Match Recording**: Record game results with scores and values
- **Editable History**: Click-to-edit match scores and values
- **Player Statistics**: Track wins, losses, earnings, partners, and opponents
- **Multiple Pricing Strategies**:
  - Fixed: Same price for all games
  - Escalating: Price increases each game
  - Winner Takes All: Winner gets the pool
  - Per Point: Value based on point differential

## Prerequisites

- Python 3.10 or higher
- Windows PowerShell (or any shell for other OS)
- Modern web browser (Chrome, Firefox, Edge, Safari)

## Installation & Setup

### 1. Clone or Navigate to Project Directory

```powershell
cd C:\Users\Hayde\badminton-matchups
```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
```

### 3. Activate Virtual Environment

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

## Running the Application

### Development Mode

```powershell
python app.py
```

The application will start on http://localhost:5000

### Production Mode (Future Deployment)

For production deployment on Windows:

```powershell
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

For containerized deployment:

```dockerfile
# Example Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## Project Structure

```
badminton-matchups/
│
├── app.py                      # Flask application (main entry point)
├── matchup_generator.py        # Fair matchup generation algorithm
├── game_valuation.py           # Dollar value assignment system
├── match_storage.py            # Match history persistence
├── requirements.txt            # Python dependencies
│
├── templates/                  # HTML templates
│   ├── base.html              # Base layout with navigation
│   ├── index.html             # Dashboard page
│   ├── players.html           # Player management
│   ├── matchups.html          # Generated matchups
│   ├── history.html           # Match history (editable)
│   ├── stats.html             # Player statistics
│   └── record_match.html      # Record match results
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css          # Dark theme styles
│   └── js/
│       └── main.js            # Frontend interactions
│
└── data/                       # JSON data storage
    ├── matches.json           # Recorded match history
    └── sessions.json          # Current session state
```

## Usage Guide

### 1. Dashboard
- **Configure Session**: Set duration, minutes per game, pricing strategy, and base value
- **Quick Actions**: Generate matchups or navigate to other pages
- **Session Status**: View current player count, generated matches, and active strategy

### 2. Players Management
- **Add Players**: Enter player names (minimum 4 required)
- **Remove Players**: Delete players from the current session
- Players persist across sessions

### 3. Generate Matchups
- Navigate to **Matchups** page
- Click **Generate Matchups** button
- View scheduled games with:
  - Game number
  - Estimated start time
  - Team compositions
  - Game value

### 4. Record Match Results
- Navigate to **Record** page
- Select a game from the dropdown
- Enter scores for both teams
- Optionally override the game value
- Submit to save

### 5. View Match History
- Navigate to **History** page
- Click on scores or values to edit them
- Changes save automatically on blur
- View all recorded matches with timestamps

### 6. Player Statistics
- Navigate to **Stats** page
- View comprehensive statistics:
  - Total matches played
  - Wins and losses
  - Win rate percentage
  - Total earnings
  - Partners and opponents played with

## Data Storage

All data is stored locally in JSON files in the `data/` directory:

- **sessions.json**: Current session configuration, players, and generated matchups
- **matches.json**: All recorded match results with timestamps

**Note**: These files are created automatically on first run. Back them up regularly if deploying to friends.

## Configuration

### Pricing Strategies

**Fixed**: Each game has the same value
- Simple and predictable
- Good for casual play

**Escalating**: Value increases by 10% each game
- Creates excitement as session progresses
- Rewards performance in later games

**Winner Takes All**: Winner gets the entire pool
- High stakes gameplay
- Competitive atmosphere

**Per Point**: Value scales with point differential
- Rewards dominant performances
- Fair distribution based on skill

### Session Parameters

- **Duration**: Total session length in hours (e.g., 3.0)
- **Minutes per Game**: Average game duration (e.g., 12-15 minutes)
- **Base Value**: Starting dollar amount (e.g., $1.00 or $5.00)

## Tips & Best Practices

1. **Add All Players First**: Ensure all players are added before generating matchups
2. **Generate Once**: Generate all matchups at the start of the session
3. **Record Promptly**: Record match results immediately after games finish
4. **Edit if Needed**: Use the editable history to correct any mistakes
5. **Check Stats**: Review player statistics to ensure fair play

## Future Deployment

When ready to deploy for friends:

### Option 1: Local Network
- Run on your PC and share your local IP (e.g., http://192.168.1.100:5000)
- Ensure firewall allows Flask port

### Option 2: Cloud Hosting
- Deploy to Heroku, Railway, or similar platform
- Update `app.run()` to use environment-based configuration
- Consider using a production-grade database (PostgreSQL)

### Option 3: Containerization
- Use Docker for consistent deployment
- Deploy to any container platform (AWS, Azure, Google Cloud)

## Troubleshooting

### Port Already in Use
```powershell
# Find process using port 5000
netstat -ano | findstr :5000
# Kill the process (replace PID)
taskkill /PID <PID> /F
```

### Flask Not Found
```powershell
# Ensure virtual environment is activated
pip install Flask
```

### Permission Errors on Data Files
- Ensure the `data/` directory is writable
- Run the app with appropriate permissions

### Browser Not Loading
- Check that Flask is running (look for "Running on http://...")
- Try http://127.0.0.1:5000 instead of localhost
- Clear browser cache

## Contributing

This is a personal project, but feel free to:
- Report bugs
- Suggest features
- Fork and customize for your own use

## License

Personal use - feel free to modify and share with friends!

---

**Enjoy your badminton sessions!** 🏸
