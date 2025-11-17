#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Stop all eehxpe production services
#>

$ErrorActionPreference = "Stop"

Write-Host "Stopping eehxpe production services..." -ForegroundColor Cyan

# Stop Flask app service
Write-Host "  Stopping EehxpeBadminton service..." -ForegroundColor Yellow
nssm stop EehxpeBadminton
Start-Sleep -Seconds 2

# Check app service status
$appStatus = (nssm status EehxpeBadminton).Trim()
if ($appStatus -eq "SERVICE_STOPPED") {
    Write-Host "  ✓ EehxpeBadminton: $appStatus" -ForegroundColor Green
} else {
    Write-Host "  ! EehxpeBadminton: $appStatus" -ForegroundColor Yellow
}

# Stop Cloudflare Tunnel service
Write-Host "  Stopping Cloudflared service..." -ForegroundColor Yellow
Stop-Service Cloudflared
Start-Sleep -Seconds 2

# Check tunnel service status
$tunnelStatus = (Get-Service Cloudflared).Status
if ($tunnelStatus -eq "Stopped") {
    Write-Host "  ✓ Cloudflared: $tunnelStatus" -ForegroundColor Green
} else {
    Write-Host "  ! Cloudflared: $tunnelStatus" -ForegroundColor Yellow
}

Write-Host "`nProduction services stopped!" -ForegroundColor Cyan
