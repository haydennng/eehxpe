#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy eehxpe production app (pull, install, restart)

.DESCRIPTION
    Pulls latest code from git, installs dependencies if changed,
    and restarts the production service.

.PARAMETER Rollback
    If specified, rollback to a specific commit instead of pulling latest

.PARAMETER ToCommit
    The commit SHA to rollback to (required if -Rollback is set)

.EXAMPLE
    .\deploy.ps1
    # Deploy latest from main branch

.EXAMPLE
    .\deploy.ps1 -Rollback -ToCommit abc123def
    # Rollback to specific commit
#>

param(
    [switch]$Rollback = $false,
    [string]$ToCommit = ""
)

$ErrorActionPreference = "Stop"
$repo = "C:\Users\Hayde\eehxpe"
$logFile = "C:\Users\Hayde\eehxpe\logs\deploy.log"
$venv = "C:\Users\Hayde\eehxpe\venv\Scripts"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage -Encoding UTF8
}

# Ensure log directory exists
$logDir = Split-Path $logFile -Parent
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Write-Log "========================================"
Write-Log "Starting deployment..."
Write-Log "========================================"

# Change to repo directory
Set-Location $repo

# Handle rollback or normal deployment
if ($Rollback) {
    if ([string]::IsNullOrWhiteSpace($ToCommit)) {
        Write-Log "ERROR: -ToCommit parameter required when using -Rollback"
        exit 1
    }
    Write-Log "Rollback mode: checking out commit $ToCommit"
    git fetch --all
    git checkout $ToCommit
    Write-Log "Checked out rollback commit $ToCommit"
} else {
    # Normal deployment: pull latest
    git fetch origin
    $before = (git rev-parse HEAD).Trim()
    Write-Log "Current commit: $before"
    
    git pull --rebase origin main
    $after = (git rev-parse HEAD).Trim()
    Write-Log "Updated to commit: $after"
    
    # Track last deployed commit
    Set-Content -Path "$repo\.last_deployed_commit" -Value $after -NoNewline
    
    if ($before -eq $after) {
        Write-Log "No changes detected, but continuing with restart..."
    }
}

# Check if requirements changed and reinstall if needed
$reqFile = Join-Path $repo "requirements.txt"
$hashFile = Join-Path $repo ".requirements.sha1"

if (Test-Path $reqFile) {
    $currHash = (Get-FileHash $reqFile -Algorithm SHA1).Hash
    $prevHash = if (Test-Path $hashFile) { Get-Content $hashFile } else { "" }
    
    if ($currHash -ne $prevHash) {
        Write-Log "Requirements changed, installing dependencies..."
        & "$venv\pip.exe" install --upgrade pip
        & "$venv\pip.exe" install -r $reqFile
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERROR: Failed to install requirements"
            exit 1
        }
        Set-Content -Path $hashFile -Value $currHash -NoNewline
        Write-Log "Dependencies installed successfully"
    } else {
        Write-Log "Requirements unchanged, skipping pip install"
    }
}

# Restart the service
Write-Log "Restarting service EehxpeBadminton..."
try {
    # Stop the service
    & nssm stop EehxpeBadminton 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    
    # Start the service
    & nssm start EehxpeBadminton
    if ($LASTEXITCODE -ne 0) {
        Write-Log "WARNING: Service start returned non-zero exit code"
    }
    
    Start-Sleep -Seconds 2
    
    # Check service status
    $status = (& nssm status EehxpeBadminton).Trim()
    Write-Log "Service status: $status"
    
    if ($status -eq "SERVICE_RUNNING") {
        Write-Log "✓ Service restarted successfully"
    } else {
        Write-Log "WARNING: Service may not be running properly. Status: $status"
    }
} catch {
    Write-Log "ERROR during service restart: $_"
    exit 1
}

Write-Log "========================================"
Write-Log "Deployment completed successfully!"
Write-Log "========================================"
