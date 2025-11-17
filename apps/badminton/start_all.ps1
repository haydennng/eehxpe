# Badminton Matchup Manager - Combined Startup Script
# Starts both Flask server and Cloudflare tunnel in one command

Write-Host "`n=== Badminton Matchup Manager - Complete Startup ===" -ForegroundColor Green

# Check if FLASK_SECRET_KEY is set
$secretKey = [System.Environment]::GetEnvironmentVariable("FLASK_SECRET_KEY", "User")
if (-not $secretKey) {
    Write-Host "`nERROR: FLASK_SECRET_KEY environment variable not set!" -ForegroundColor Red
    Write-Host "`nTo set it up:" -ForegroundColor Yellow
    Write-Host "1. Generate a secret key:" -ForegroundColor Yellow
    Write-Host '   python -c "import secrets; print(secrets.token_hex(32))"' -ForegroundColor Cyan
    Write-Host "`n2. Copy the generated key and run:" -ForegroundColor Yellow
    Write-Host '   setx FLASK_SECRET_KEY "PASTE_YOUR_KEY_HERE"' -ForegroundColor Cyan
    Write-Host "`n3. Close this PowerShell window and open a new one" -ForegroundColor Yellow
    Write-Host "4. Run this script again`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] FLASK_SECRET_KEY is set" -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "[OK] Activating virtual environment..." -ForegroundColor Green
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "[WARNING] Virtual environment not found - using global Python" -ForegroundColor Yellow
}

Write-Host "`nStarting Flask server..." -ForegroundColor Cyan

# Start Flask server in background job
$flaskJob = Start-Job -ScriptBlock {
    param($workingDir)
    Set-Location $workingDir
    & .\.venv\Scripts\Activate.ps1
    python -m waitress --listen=127.0.0.1:5000 app:app
} -ArgumentList (Get-Location).Path

Write-Host "[OK] Flask server starting (Job ID: $($flaskJob.Id))" -ForegroundColor Green

# Wait a moment for Flask to start
Write-Host "Waiting for Flask to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Test if Flask is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000" -UseBasicParsing -TimeoutSec 5
    Write-Host "[OK] Flask server is responding!" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Flask may still be starting up..." -ForegroundColor Yellow
}

Write-Host "`nStarting Cloudflare tunnel..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Yellow
Write-Host "Look for the tunnel URL below (https://...trycloudflare.com)" -ForegroundColor Yellow
Write-Host "============================================`n" -ForegroundColor Yellow

# Find cloudflared executable
$cloudflaredPath = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflaredPath) {
    # Try common installation paths
    $possiblePaths = @(
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Cloudflare.cloudflared_*\cloudflared.exe"
    )
    foreach ($path in $possiblePaths) {
        $found = Get-Item $path -ErrorAction SilentlyContinue
        if ($found) {
            $cloudflaredPath = $found.FullName
            break
        }
    }
}

if (-not $cloudflaredPath) {
    Write-Host "`nERROR: cloudflared not found!" -ForegroundColor Red
    Write-Host "Please close this PowerShell window and open a new one." -ForegroundColor Yellow
    Write-Host "The PATH may not be updated in this session." -ForegroundColor Yellow
    Write-Host "`nOr verify cloudflared is installed: winget list Cloudflare.cloudflared`n" -ForegroundColor Yellow
    Stop-Job -Job $flaskJob
    Remove-Job -Job $flaskJob
    exit 1
}

# Start Cloudflare tunnel in foreground (so we can see the URL)
& $cloudflaredPath tunnel --url http://localhost:5000

# Cleanup when tunnel stops (Ctrl+C)
Write-Host "`n`nStopping Flask server..." -ForegroundColor Yellow
Stop-Job -Job $flaskJob
Remove-Job -Job $flaskJob
Write-Host "[OK] All services stopped" -ForegroundColor Green
