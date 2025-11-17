# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

### Running the Application
```bash
python main.py
```

### Testing
```bash
python test_matchups.py
```

Run specific test class:
```bash
python -m unittest test_matchups.TestMatchupGenerator
```

Run specific test method:
```bash
python -m unittest test_matchups.TestMatchupGenerator.test_fairness
```

### Installation
```bash
pip install -r requirements.txt
```

## Architecture

### Core Algorithm: Fair Matchup Generation

The matchup generation algorithm (`MatchupGenerator`) ensures balanced 2v2 games by:

1. **Tracking partnership/opponent history** - Uses `defaultdict` counters to track how often players have partnered together and faced each other
2. **Scoring potential matchups** - Each potential matchup is scored based on:
   - Partnership frequency (weighted 2x) - prioritizes new partner combinations
   - Opponent frequency - prioritizes new opponent matchups
   - Lower scores = better matchups (fewer repeated pairings)
3. **Greedy selection** - For each game, evaluates all possible team combinations and selects the one with the lowest score

### Module Responsibilities

- **`main.py`** - CLI interface handling user interaction, session state, and coordinating other modules
- **`matchup_generator.py`** - Fair matchup algorithm with partnership/opponent balancing
- **`game_valuation.py`** - Dollar value assignment with 4 strategies:
  - `FIXED` - Same price all games
  - `ESCALATING` - 10% increase per game
  - `WINNER_TAKES_ALL` - Winner gets full pool
  - `PER_POINT` - Bonus based on point differential
- **`match_storage.py`** - JSON-based persistence layer for match history and player statistics

### Data Flow

1. User adds players → `BadmintonCLI.players` and `MatchupGenerator` initialized
2. User generates matchups → `MatchupGenerator.generate_session()` creates balanced games
3. Each matchup valued → `GameValuation.calculate_value()` assigns dollar amounts
4. User records results → `MatchStorage.save_match()` persists to `data/matches.json`
5. Statistics calculated → `MatchStorage.get_player_stats()` aggregates wins/losses/earnings

### Storage Format

Match records stored in `data/matches.json` with structure:
```json
{
  "match_id": "match_1_20241025...",
  "timestamp": "2024-10-25T...",
  "game_number": 1,
  "team1": ["Alice", "Bob"],
  "team2": ["Charlie", "Diana"],
  "team1_score": 21,
  "team2_score": 18,
  "game_value": 10.0,
  "winner": "team1"
}
```

### Future Web Application

The codebase is designed for transition to a web application. Key architectural decisions supporting this:
- Separation of CLI (`main.py`) from business logic (other modules)
- All core functionality in standalone, testable modules
- JSON-based storage layer easily replaceable with database
- Session and match data already structured for API responses
