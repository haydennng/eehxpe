#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Complete remaining setup steps that require administrator privileges

.DESCRIPTION
    This script must be run as Administrator. It will:
    - Install Cloudflared Windows service
    - Create Flask app Windows service (NSSM)
    - Set up automated daily backups
    - Configure power settings for always-on operation

.NOTES
    Run this script by right-clicking and selecting "Run as Administrator"
#>

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "eehxpe Admin Setup Script" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Install Cloudflared Service
Write-Host "[1/4] Installing Cloudflared Windows service..." -ForegroundColor Yellow
try {
    cloudflared service install
    Write-Host "  ✓ Cloudflared service installed" -ForegroundColor Green
    
    Start-Service Cloudflared
    Write-Host "  ✓ Cloudflared service started" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to install Cloudflared service: $_" -ForegroundColor Red
    Write-Host "  Cloudflared may already be running. Continuing..." -ForegroundColor Yellow
}

# Step 2: Create Flask App Service with NSSM
Write-Host "`n[2/4] Creating Flask app Windows service..." -ForegroundColor Yellow
$venvPath = "C:\Users\Hayde\eehxpe\venv\Scripts\waitress-serve.exe"
$appDir = "C:\Users\Hayde\eehxpe"
$logDir = "C:\Users\Hayde\eehxpe\logs\badminton"

# Ensure log directory exists
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

try {
    # Remove service if it exists
    $existing = nssm status EehxpeBadminton 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Removing existing service..." -ForegroundColor Gray
        nssm stop EehxpeBadminton
        nssm remove EehxpeBadminton confirm
    }
    
    # Install service
    nssm install EehxpeBadminton $venvPath
    nssm set EehxpeBadminton AppParameters "--listen=127.0.0.1:8001 eehxpe.wsgi:application"
    nssm set EehxpeBadminton AppDirectory $appDir
    nssm set EehxpeBadminton AppEnvironmentExtra "FLASK_ENV=production" "BADMINTON_DATA_DIR=C:\Users\Hayde\eehxpe\data\badminton" "LOG_DIR=C:\Users\Hayde\eehxpe\logs\badminton"
    nssm set EehxpeBadminton AppStdout "$logDir\stdout.log"
    nssm set EehxpeBadminton AppStderr "$logDir\stderr.log"
    nssm set EehxpeBadminton Start SERVICE_AUTO_START
    nssm set EehxpeBadminton AppRestartDelay 5000
    
    Write-Host "  ✓ Service configured" -ForegroundColor Green
    
    # Start service
    nssm start EehxpeBadminton
    Start-Sleep -Seconds 3
    
    $status = nssm status EehxpeBadminton
    if ($status -match "RUNNING") {
        Write-Host "  ✓ Service started successfully" -ForegroundColor Green
    } else {
        Write-Host "  ! Service status: $status" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Failed to create service: $_" -ForegroundColor Red
}

# Step 3: Set Up Automated Backups
Write-Host "`n[3/4] Setting up automated daily backups..." -ForegroundColor Yellow
try {
    # Remove existing task if it exists
    $existingTask = Get-ScheduledTask -TaskName "eehxpe-daily-backup" -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "  Removing existing backup task..." -ForegroundColor Gray
        Unregister-ScheduledTask -TaskName "eehxpe-daily-backup" -Confirm:$false
    }
    
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -File C:\Users\Hayde\eehxpe\scripts\backup-data.ps1"
    
    $trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
    
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
    
    Register-ScheduledTask -TaskName "eehxpe-daily-backup" `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Description "Daily backup of eehxpe production data" | Out-Null
    
    Write-Host "  ✓ Daily backup task created (runs at 3:00 AM)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to create backup task: $_" -ForegroundColor Red
}

# Step 4: Configure Power Settings
Write-Host "`n[4/4] Configuring power settings..." -ForegroundColor Yellow
try {
    # Disable sleep when plugged in
    powercfg -change -standby-timeout-ac 0
    powercfg -change -hibernate-timeout-ac 0
    
    Write-Host "  ✓ Power settings configured (PC will not sleep when plugged in)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to configure power settings: $_" -ForegroundColor Red
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Admin Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Services Status:" -ForegroundColor White
try {
    $cfStatus = (Get-Service Cloudflared).Status
    Write-Host "  Cloudflared: $cfStatus" -ForegroundColor $(if ($cfStatus -eq "Running") { "Green" } else { "Red" })
} catch {
    Write-Host "  Cloudflared: Not installed" -ForegroundColor Red
}

try {
    $appStatus = (nssm status EehxpeBadminton).Trim()
    Write-Host "  EehxpeBadminton: $appStatus" -ForegroundColor $(if ($appStatus -match "RUNNING") { "Green" } else { "Red" })
} catch {
    Write-Host "  EehxpeBadminton: Not installed" -ForegroundColor Red
}

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Test local endpoint: http://127.0.0.1:8001/badminton" -ForegroundColor White
Write-Host "  2. Test public endpoint: https://eehxpe.com/badminton" -ForegroundColor White
Write-Host "  3. Set up GitHub Actions runner (see QUICKSTART.md Step 9)" -ForegroundColor White
Write-Host "`n"

Read-Host "Press Enter to exit"
