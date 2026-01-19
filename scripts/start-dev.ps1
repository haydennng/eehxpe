#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start eehxpe development server locally
.DESCRIPTION
    Starts the eehxpe multi-app server in development mode with auto-reload.
    Uses .env.development for configuration.
.EXAMPLE
    .\scripts\start-dev.ps1
#>

$ErrorActionPreference = "Stop"

# Navigate to project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    Write-Host "`n$('='*60)" -ForegroundColor Cyan
    Write-Host "eehxpe Development Server" -ForegroundColor Cyan
    Write-Host "$('='*60)`n" -ForegroundColor Cyan

    # Check if virtual environment exists
    if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
        Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
        Write-Host "✅ Virtual environment created" -ForegroundColor Green
        Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
        & ".\venv\Scripts\python.exe" -m pip install --upgrade pip
        & ".\venv\Scripts\pip.exe" install -r requirements.txt
        Write-Host "✅ Dependencies installed" -ForegroundColor Green
    }

    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"

    # Load development environment
    if (Test-Path ".\.env.development") {
        Write-Host "Loading development environment..." -ForegroundColor Yellow
        Get-Content ".\.env.development" | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
                Write-Host "  Set $key" -ForegroundColor Gray
            }
        }
        Write-Host "✅ Development environment loaded" -ForegroundColor Green
    } else {
        Write-Host "⚠️  .env.development not found, using defaults" -ForegroundColor Yellow
    }

    # Ensure data and log directories exist
    @("data\badminton", "logs\badminton") | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
            Write-Host "Created directory: $_" -ForegroundColor Gray
        }
    }

    Write-Host "`n$('='*60)" -ForegroundColor Cyan
    Write-Host "🚀 Starting development server..." -ForegroundColor Green
    Write-Host "$('='*60)" -ForegroundColor Cyan
    Write-Host "📍 Local URL:  http://127.0.0.1:8001/badminton" -ForegroundColor White
    Write-Host "🔄 Auto-reload: Enabled (Flask debug mode)" -ForegroundColor White
    Write-Host "📂 Data Dir:    $env:BADMINTON_DATA_DIR" -ForegroundColor Gray
    Write-Host "📝 Log Dir:     $env:LOG_DIR" -ForegroundColor Gray
    Write-Host "`n💡 Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host "$('='*60)`n" -ForegroundColor Cyan

    # Start the development server with Flask's built-in reloader
    $env:FLASK_APP = "eehxpe.wsgi:application"
    
    # Use Flask development server instead of Waitress for auto-reload
    python -c @"
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'apps' / 'badminton'))

# Load .env.development
import os
env_file = Path('.env.development')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# Import and run
from eehxpe.wsgi import application
from werkzeug.serving import run_simple

# Run with auto-reload
run_simple('127.0.0.1', 8001, application, 
           use_reloader=True, 
           use_debugger=True,
           use_evalex=True)
"@

} catch {
    Write-Host "`n❌ Error starting development server:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
