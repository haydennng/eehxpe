# eehxpe.com Production Server Management Script
# Usage: .\manage_server.ps1 [stop|start|restart|status]

param(
    [Parameter(Position=0)]
    [ValidateSet('stop','start','restart','status')]
    [string]$Action = 'status'
)

$Port = 8080
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-ServerProcess {
    # Find Python process listening on port 8080
    $netstat = netstat -ano | Select-String ":$Port.*LISTENING"
    if ($netstat) {
        $line = $netstat.Line -split '\s+' | Where-Object { $_ }
        $pid = $line[-1]
        if ($pid -match '^\d+$') {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            return $process
        }
    }
    return $null
}

function Stop-Server {
    Write-Host ""
    Write-Host "Stopping production server..." -ForegroundColor Yellow
    $process = Get-ServerProcess
    if ($process) {
        Write-Host "   Found server process (PID: $($process.Id))" -ForegroundColor Gray
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 2
        Write-Host "Server stopped" -ForegroundColor Green
    } else {
        Write-Host "   No server process found on port $Port" -ForegroundColor Gray
    }
}

function Start-Server {
    Write-Host ""
    Write-Host "Starting production server..." -ForegroundColor Cyan
    
    # Check if already running
    $existing = Get-ServerProcess
    if ($existing) {
        Write-Host "Server already running (PID: $($existing.Id))" -ForegroundColor Yellow
        Write-Host "   Run '.\manage_server.ps1 restart' to restart it" -ForegroundColor Gray
        return
    }
    
    # Start the server
    Push-Location $ProjectRoot
    Write-Host "   Starting from: $ProjectRoot" -ForegroundColor Gray
    python start_production.py
    Pop-Location
}

function Show-Status {
    Write-Host ""
    Write-Host "Production Server Status" -ForegroundColor Cyan
    Write-Host "============================================================"
    
    $process = Get-ServerProcess
    if ($process) {
        Write-Host "Status:  " -NoNewline -ForegroundColor Gray
        Write-Host "RUNNING" -ForegroundColor Green
        Write-Host "PID:     $($process.Id)" -ForegroundColor Gray
        Write-Host "Port:    $Port" -ForegroundColor Gray
        $memoryMB = [math]::Round($process.WorkingSet64/1MB, 2)
        Write-Host "Memory:  $memoryMB MB" -ForegroundColor Gray
        Write-Host "Start:   $($process.StartTime)" -ForegroundColor Gray
        
        # Show listening connections
        Write-Host ""
        Write-Host "Listening on:" -ForegroundColor Gray
        netstat -ano | Select-String ":$Port.*LISTENING" | ForEach-Object {
            Write-Host "   $($_.Line.Trim())" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "Status:  " -NoNewline -ForegroundColor Gray
        Write-Host "STOPPED" -ForegroundColor Red
        Write-Host "Port:    $Port (not in use)" -ForegroundColor Gray
    }
    Write-Host "============================================================"
    Write-Host ""
}

# Main action handler
switch ($Action) {
    'stop' {
        Stop-Server
    }
    'start' {
        Start-Server
    }
    'restart' {
        Stop-Server
        Start-Sleep -Seconds 1
        Start-Server
    }
    'status' {
        Show-Status
    }
}
