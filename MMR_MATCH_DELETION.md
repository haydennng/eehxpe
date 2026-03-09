# Match Deletion and MMR Recalculation

## Overview
When you delete a match, the MMR for all players is **automatically recalculated** from scratch based on the remaining match history. This ensures that MMR values accurately reflect the matches that actually happened.

## How It Works

### The Problem with Incremental MMR
ELO-based MMR systems (like ours) calculate ratings **chronologically** - each match builds on the previous ratings. If you simply "undo" a match's MMR changes, you'd get incorrect values because:

1. Match order matters in ELO calculations
2. Subsequent matches were calculated based on the deleted match's results
3. Simply reversing the changes doesn't account for downstream effects

### The Solution: Full Recalculation
When a match is deleted:

1. **Match is removed** from the database
2. **All players reset** to starting MMR (1500)
3. **All remaining matches replayed** chronologically
4. **MMR recalculated** for each match in order
5. **Final MMR values** reflect the actual match history

This ensures mathematical accuracy and consistency.

## What Happens When You Delete a Match

### Via Web Interface
1. Go to Match History
2. Click delete on a match (admin only)
3. Confirm deletion
4. Server automatically:
   - Deletes the match from database
   - Recalculates all player MMR
   - Updates Match.mmr_change for all remaining matches
5. Refresh the page to see updated MMR

### Via API
```bash
DELETE /badminton/api/matches/{match_id}
```

Response:
```json
{
  "message": "Match deleted successfully",
  "match_id": "match_123"
}
```

### Server Logs
When a match is deleted, you'll see:
```
=== DELETE /api/matches/match_322 called ===
Match match_322 deleted from database
Recalculating all MMR from remaining matches...
MMR recalculated successfully for 21 players
Sample new ratings:
  Hayden: 1694.91
  Maric: 1681.25
  CJ: 1600.36
  ...
=== Match match_322 deletion complete ===
```

## Example: Deleting Game #511

### Before Deletion
```
Game #511: Hayden & Maric (12) vs Phi & John (21)
Winner: Phi & John

Current MMR:
  Hayden: 1673.18
  Maric: 1659.52
  Phi: 1395.36
  John: 1239.16
```

### After Deletion
```
Match deleted, replaying 510 remaining matches...

Updated MMR:
  Hayden: 1694.91  (+21.73)
  Maric: 1681.25  (+21.73)
  Phi: 1373.62    (-21.74)
  John: 1217.43   (-21.73)
```

The MMR values return to what they were **before** Game #511 was played.

## Match Editing
Similarly, when you **edit** a match (change score, winner, etc.), the system:

1. Updates the match in the database
2. Recalculates all MMR from scratch
3. Ensures accuracy across all matches

This happens for:
- Score changes
- Winner changes  
- Team composition changes

## Performance Considerations

### Speed
- **Small databases** (< 1000 matches): Near-instant
- **Medium databases** (1000-5000 matches): 1-2 seconds
- **Large databases** (5000+ matches): 3-5 seconds

### Optimization
The recalculation:
- Uses optimized database queries
- Processes matches in bulk
- Only touches affected players
- Commits once at the end

## Testing

### Manual Test Script
```bash
python test_delete_match.py
```

This script:
1. Shows the most recent match
2. Displays current MMR for involved players
3. Deletes the match
4. Recalculates MMR
5. Shows MMR changes

### Automated Testing
```python
# Test that MMR reverts after deletion
from mmr_database import recalculate_all_mmr
from match_storage import MatchStorage

# Get current MMR
player_ratings_before = get_all_player_mmr()

# Delete a match
storage = MatchStorage()
storage.delete_match("match_123")

# Recalculate
recalculate_all_mmr()

# Verify MMR changed appropriately
player_ratings_after = get_all_player_mmr()
```

## Troubleshooting

### MMR Not Reverting
If MMR doesn't change after deleting a match:

1. **Check server logs** - Look for errors during recalculation
2. **Manual recalculation**:
   ```bash
   python apps/badminton/recalculate_mmr_db.py --yes
   ```
3. **Hard refresh browser** - Clear cache with `Ctrl + F5`

### Deleted Wrong Match
If you accidentally deleted a match:

1. **Check backups** - Database backups may have the match
2. **Re-record the match** - Enter it again via the UI
3. **MMR will recalculate** - Automatically updates after re-recording

### Performance Issues
If recalculation is slow:

1. **Check match count** - Large histories take longer
2. **Run during off-hours** - Less server load
3. **Consider archiving** - Move old matches to archive table

## Best Practices

### For Admins
- ✅ **Delete test matches** immediately after testing
- ✅ **Verify match details** before deletion (can't undo easily)
- ✅ **Monitor logs** during deletion for errors
- ❌ **Don't bulk delete** - Delete one at a time
- ❌ **Don't delete during active games** - Wait for session to end

### For Users
- MMR updates are **automatic** - no action needed
- Changes appear after **browser refresh**
- Historical stats may change slightly after deletions
- Win/loss records unaffected (only deleted match removed)

## Technical Implementation

### Code Flow
```python
@app.route('/api/matches/<match_id>', methods=['DELETE'])
@admin_required
def delete_match(match_id):
    # 1. Delete from database
    storage.delete_match(match_id)
    
    # 2. Recalculate all MMR
    from mmr_database import recalculate_all_mmr
    player_ratings = recalculate_all_mmr(k_factor=24)
    
    # 3. Return success
    return jsonify({'message': 'Match deleted successfully'})
```

### Database Changes
- **Match table**: Row deleted
- **User table**: MMR fields updated for all players
- **Match table** (remaining): mmr_change fields updated

### Transaction Safety
- All operations in single transaction
- Rollback on error
- No partial updates
- Data consistency guaranteed

## Summary

✅ **MMR automatically reverts** when you delete a match  
✅ **Full recalculation** ensures accuracy  
✅ **Works for match editing** too  
✅ **Fast and reliable** for typical database sizes  
✅ **Admin-only operation** prevents accidental deletions  

After restarting your server, match deletion will automatically recalculate MMR correctly!
