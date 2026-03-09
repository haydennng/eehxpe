# MMR Calculation Update Summary

## Problem
The MMR (Matchmaking Rating) system was not updating after each match was recorded. The system was using old JSON-based MMR calculation code that wasn't compatible with the new database-backed architecture.

## Solution
Implemented a new database-based MMR calculation system that:

1. **Updates MMR after every match** - When a match is recorded, the MMR is immediately recalculated for all 4 players involved
2. **Stores MMR changes in the database** - Each match now records the MMR change value in the `Match.mmr_change` field
3. **Recalculates all MMR from scratch** - Admin endpoint and script available to recalculate everyone's MMR based on all historical matches

## Changes Made

### New File: `mmr_database.py`
A new module that provides database-compatible MMR calculation functions:

- `recalculate_all_mmr()` - Recalculates MMR for all players from all matches in the database
- `update_mmr_for_match()` - Updates MMR for a specific match
- `get_player_mmr_history()` - Gets MMR history for a player across all their matches

### Updated: `app.py`

#### Match Recording Endpoint (`/api/matches` POST)
- **Before**: Used JSON-based `calculate_mmr.py` that tried to read/write JSON files
- **After**: Uses `mmr_database.update_mmr_for_match()` to update MMR in the database immediately after saving a match

#### Admin Recalculate Endpoint (`/api/admin/recalculate-mmr` POST)
- **Before**: Used JSON-based recalculation
- **After**: Uses `mmr_database.recalculate_all_mmr()` to recalculate from database
- **Note**: Now requires admin authentication

### New Script: `recalculate_mmr_db.py`
A command-line script to recalculate MMR for all players:

```bash
# Interactive mode (prompts for confirmation)
python apps/badminton/recalculate_mmr_db.py

# Auto-confirm mode
python apps/badminton/recalculate_mmr_db.py --yes
```

## How It Works

### When Recording a Match

1. Match data is saved to the database via `MatchStorage.save_match()`
2. The match ID is extracted (e.g., "match_123" → 123)
3. `update_mmr_for_match()` is called with the match ID
4. The function:
   - Gets the current MMR for all 4 players
   - Calculates the expected outcome using ELO formula
   - Calculates the MMR change based on the actual result
   - Updates the `User.mmr` field for all 4 players
   - Stores the MMR change in `Match.mmr_change`

### When Recalculating All MMR

1. All users are reset to starting MMR (1500)
2. All matches are fetched and sorted chronologically
3. Each match is processed in order:
   - MMR is calculated based on current ratings
   - `User.mmr` is updated for all involved players
   - `Match.mmr_change` is updated
4. Final MMR values are committed to the database

## Testing

The MMR recalculation script was successfully run and updated all player MMRs:

```
Total players updated: 21

Top players after recalculation:
  Hayden: 1694.91
  Maric: 1681.25
  CJ: 1600.36
  Brendon: 1569.90
  Jonny: 1567.06
  ...
```

## Usage

### For Users
No action needed. MMR will automatically update after each match is recorded.

### For Admins
To recalculate all MMR from scratch (e.g., after changing K-factor or fixing data issues):

1. **Via Web API** (requires admin login):
   ```bash
   POST /badminton/api/admin/recalculate-mmr
   ```

2. **Via Command Line**:
   ```bash
   cd C:\Users\Hayde\eehxpe
   python apps/badminton/recalculate_mmr_db.py --yes
   ```

## Technical Details

### ELO System Parameters
- **Starting MMR**: 1500
- **K-Factor**: 24 (moderate rate of change)
- **Team Rating**: Average of both players' individual ratings

### Database Schema
- `User.mmr` (Float): Current MMR rating for each player
- `Match.mmr_change` (Float): Absolute MMR change for the match

### Formula
```
Expected Score = 1 / (1 + 10^((opponent_rating - player_rating) / 400))
New Rating = Old Rating + K * (Actual Score - Expected Score)
```

## Future Enhancements
- Add MMR change display in match history
- Show MMR trends/graphs on player profiles
- Allow configurable K-factor per match type
- Track MMR history over time for analytics
