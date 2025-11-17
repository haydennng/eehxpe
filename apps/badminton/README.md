# Badminton Matchup Manager

A Python application for managing fair 2v2 badminton matchups during multi-hour play sessions.

## Features

- **Fair Player Combinations**: Generates balanced 2v2 matchups ensuring players rotate partners and opponents evenly
- **Game Valuation**: Assigns dollar values to games with configurable pricing
- **Match History**: Tracks all previous matches with players, teams, scores, and values

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the CLI application:

```bash
python main.py
```

### Available Commands

- `add-players` - Add players to the session
- `generate` - Generate fair matchups for the session
- `record` - Record the result of a match
- `history` - View match history
- `status` - View current session status

## Project Structure

- `main.py` - CLI interface entry point
- `matchup_generator.py` - Fair matchup generation algorithm
- `game_valuation.py` - Dollar value assignment system
- `match_storage.py` - Match history persistence
- `data/` - JSON storage for match history

## Future Enhancements

This project is designed to transition to a web application for easy access by friends.
