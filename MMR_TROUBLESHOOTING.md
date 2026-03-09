# MMR Display Issue - Troubleshooting Guide

## Issue Reported
After recording a match (Hayden & Maric losing to Phi & John), the MMR changes didn't show up on the dashboard.

## Root Cause Identified
The server needs to be **restarted** to load the new MMR calculation code. The match you recorded (Game #511) was saved but the MMR update didn't happen because:

1. The server was still running the **old code** (before the MMR fixes)
2. The MMR update code wasn't executed, so `mmr_change = 0.0` in the database

## What I Fixed

### Immediate Fix (Manual)
I manually updated the MMR for Game #511:
- **Hayden**: 1694.91 → **1673.18** (-21.73 MMR)
- **Maric**: 1681.25 → **1659.52** (-21.73 MMR)  
- **Phi**: 1373.62 → **1395.36** (+21.73 MMR)
- **John**: 1217.43 → **1239.16** (+21.73 MMR)

The MMR changes are now correctly reflected in the database.

## How to See the Updated MMR

### Option 1: Hard Refresh Browser
The dashboard might be showing cached data. Try:
- **Windows/Linux**: `Ctrl + F5` or `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`

### Option 2: Clear Browser Cache
1. Open browser DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Option 3: Restart Server
**This is required for future matches to work correctly!**

Stop and restart your Flask/Waitress server to load the new MMR code:

```powershell
# Stop the current server (Ctrl+C)
# Then restart it using your normal start command
```

## Verification

### Check Dashboard
Visit `/badminton/dashboard` and look at the MMR Leaderboard:
- Hayden should be around **1673**
- Maric should be around **1660**
- Phi should be around **1395**
- John should be around **1239**

### Check Database Directly
```bash
python -c "import sys; sys.path.insert(0, 'C:/Users/Hayde/eehxpe/apps/badminton'); from database import session_scope; from models import User; session = session_scope().__enter__(); users = session.query(User).filter(User.username.in_(['Hayden', 'Maric', 'Phi', 'John'])).all(); [print(f'{u.username}: {u.mmr:.2f}') for u in users]"
```

## Testing Future Matches

After restarting the server, test with another match to verify MMR updates automatically:

1. Record a test match
2. Check the console logs - you should see:
   ```
   Updating MMR for match...
   MMR updated successfully. Changes: {'Player1': X, ...}
   MMR change value: X.XX
   ```
3. Refresh the dashboard (hard refresh) to see updated MMR

## If MMR Still Not Updating

### Step 1: Check Server Logs
Look for errors when recording a match:
```
Warning: Failed to update MMR: [error message]
```

### Step 2: Manual Recalculation
If a match was saved without MMR update:

```bash
# Recalculate all MMR from scratch
python apps/badminton/recalculate_mmr_db.py --yes
```

### Step 3: Check Match Has MMR Change
```bash
python -c "import sys; sys.path.insert(0, 'C:/Users/Hayde/eehxpe/apps/badminton'); from database import session_scope; from models import Match; session = session_scope().__enter__(); match = session.query(Match).order_by(Match.created_at.desc()).first(); print(f'Game #{match.game_number}: MMR Change = {match.mmr_change}')"
```

If `mmr_change = 0.0`, the automatic update didn't work.

## Current Status

✅ **Fixed for Game #511** - MMR manually updated  
⚠️ **Server restart required** - For automatic MMR updates on future matches  
✅ **Dashboard will show correct MMR** - After hard refresh  

## Next Steps

1. **Restart your server** to load the new MMR code
2. **Hard refresh the dashboard** (`Ctrl + F5`)
3. **Record a test match** to verify MMR updates automatically
4. If you see the logs showing "MMR updated successfully", you're all set!
