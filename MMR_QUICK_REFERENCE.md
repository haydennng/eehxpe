# MMR System Quick Reference

## ✅ What's Fixed
- **MMR now updates automatically after each match is recorded**
- **MMR automatically reverts when you delete a match**
- **MMR recalculates when you edit a match**
- **All historical MMR has been recalculated from existing match data**
- **System now uses the database instead of JSON files**

## 🎮 For Users
**Nothing to do!** Just keep recording matches as normal. MMR will update automatically.

## 🔧 For Admins

### Recalculate All MMR (if needed)

#### Option 1: Web API
```bash
POST /badminton/api/admin/recalculate-mmr
# Must be logged in as admin
```

#### Option 2: Command Line (Recommended)
```bash
cd C:\Users\Hayde\eehxpe
python apps/badminton/recalculate_mmr_db.py --yes
```

### When to Recalculate
- After fixing match data errors
- After changing the K-factor (currently 24)
- After bulk importing matches
- If MMR values seem incorrect

## 📊 Current MMR Standings
After recalculation (as of last update):

| Rank | Player   | MMR    |
|------|----------|--------|
| 1    | Hayden   | 1694.91|
| 2    | Maric    | 1681.25|
| 3    | CJ       | 1600.36|
| 4    | Brendon  | 1569.90|
| 5    | Jonny    | 1567.06|
| 6    | Danny    | 1558.42|
| 7    | Kelvin   | 1547.90|
| 8    | Oscar    | 1533.81|
| 9    | Daniel   | 1530.22|

## 🔍 Technical Info

### Files Changed
- **NEW**: `apps/badminton/mmr_database.py` - Database MMR calculation
- **NEW**: `apps/badminton/recalculate_mmr_db.py` - Recalculation script
- **UPDATED**: `apps/badminton/app.py` - Match recording and admin endpoints

### Database Fields
- `User.mmr` - Current player rating (Float, default: 1500)
- `Match.mmr_change` - MMR change for that match (Float)

### ELO Parameters
- Starting Rating: **1500**
- K-Factor: **24**
- Team Rating: **Average of both players**

## 🐛 Troubleshooting

### MMR not updating?
1. Check that matches are being saved to the database
2. Look at server logs for errors during MMR calculation
3. Try manually recalculating: `python apps/badminton/recalculate_mmr_db.py --yes`

### MMR values seem wrong?
Run a full recalculation to reset from match history:
```bash
python apps/badminton/recalculate_mmr_db.py --yes
```

### Deleted a match but MMR didn't change?
1. **Restart server** to load new code
2. **Hard refresh browser** (`Ctrl + F5`)
3. Check server logs for recalculation errors

### Need detailed logs?
Check the console output:

**When recording a match:**
- "Updating MMR for match..."
- "MMR updated successfully. Changes: {player: change}"
- "MMR change value: X.XX"

**When deleting a match:**
- "DELETE /api/matches/match_XXX called"
- "Recalculating all MMR from remaining matches..."
- "MMR recalculated successfully for X players"
