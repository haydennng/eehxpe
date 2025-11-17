# Badminton Matchup Manager - Production Server Startup Script
# This script starts the Flask application using Waitress WSGI server

Write-Host "`n=== Badminton Matchup Manager - Starting Server ===" -ForegroundColor Green

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

# Start the server with Waitress
Write-Host "`nStarting Waitress WSGI server on http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

python -m waitress --listen=127.0.0.1:5000 app:app
