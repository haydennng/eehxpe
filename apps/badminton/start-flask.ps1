# Start Flask cleanly for badminton-matchups project
Write-Host "Starting Flask application..." -ForegroundColor Cyan

# First, ensure no old processes are running
Write-Host "Checking for existing Python processes..." -ForegroundColor Yellow
$existing = Get-Process -Name python -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Found existing Python processes. Stopping them first..." -ForegroundColor Yellow
    $existing | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Verify working directory
$expectedPath = "C:\Users\Hayde\badminton-matchups"
if ((Get-Location).Path -ne $expectedPath) {
    Write-Host "Changing to project directory: $expectedPath" -ForegroundColor Yellow
    Set-Location $expectedPath
}

# Start Flask
Write-Host "`nStarting Flask on http://localhost:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "----------------------------------------`n" -ForegroundColor Gray

# Run Python with app.py
python app.py

# This runs after Ctrl+C
Write-Host "`n----------------------------------------" -ForegroundColor Gray
Write-Host "Flask stopped. Cleaning up..." -ForegroundColor Yellow

# Ensure all Python processes are killed
Start-Sleep -Seconds 1
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Cleanup complete!" -ForegroundColor Green
