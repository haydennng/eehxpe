# Stop all Python/Flask processes for this project
Write-Host "Stopping all Python processes..." -ForegroundColor Yellow

# Kill all python processes
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force

# Wait a moment
Start-Sleep -Seconds 1

# Verify they're stopped
$remaining = Get-Process -Name python -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Warning: Some Python processes are still running:" -ForegroundColor Red
    $remaining | Format-Table Id, ProcessName, StartTime
} else {
    Write-Host "All Python processes stopped successfully!" -ForegroundColor Green
}
