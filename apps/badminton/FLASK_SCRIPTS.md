# Flask Helper Scripts

## Problem
Sometimes multiple Flask instances can run simultaneously, causing the browser to load cached/old versions of the app.

## Solution
Use these helper scripts to ensure clean starts and stops.

## Usage

### Starting Flask (Recommended)
```powershell
.\start-flask.ps1
```

This script will:
1. Check for and stop any existing Python processes
2. Ensure you're in the correct directory
3. Start Flask on http://localhost:5000
4. When you press Ctrl+C, it will automatically clean up all Python processes

### Stopping Flask Manually
```powershell
.\stop-flask.ps1
```

This script will:
1. Stop all Python processes
2. Verify they're stopped
3. Display any remaining processes if cleanup failed

## Troubleshooting

### Multiple Flask Instances
If you're seeing old content, run:
```powershell
.\stop-flask.ps1
.\start-flask.ps1
```

### Hard Refresh Browser
After restarting Flask, always do a hard refresh:
- **Chrome/Edge**: Ctrl+Shift+R or Ctrl+F5
- **Firefox**: Ctrl+Shift+R

### Check for Running Processes
```powershell
Get-Process -Name python
```

## Alternative: Manual Start/Stop

If you prefer to run Flask manually:

**Start:**
```powershell
python app.py
```

**Stop (in a new terminal):**
```powershell
Stop-Process -Name python -Force
```
