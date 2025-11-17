#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start all eehxpe production services
#>

$ErrorActionPreference = "Stop"

Write-Host "Starting eehxpe production services..." -ForegroundColor Cyan

# Start Flask app service
Write-Host "  Starting EehxpeBadminton service..." -ForegroundColor Yellow
nssm start EehxpeBadminton
Start-Sleep -Seconds 2

# Check app service status
$appStatus = (nssm status EehxpeBadminton).Trim()
if ($appStatus -eq "SERVICE_RUNNING") {
    Write-Host "  ✓ EehxpeBadminton: $appStatus" -ForegroundColor Green
} else {
    Write-Host "  ✗ EehxpeBadminton: $appStatus" -ForegroundColor Red
}

# Start Cloudflare Tunnel service
Write-Host "  Starting Cloudflared service..." -ForegroundColor Yellow
Start-Service Cloudflared
Start-Sleep -Seconds 2

# Check tunnel service status
$tunnelStatus = (Get-Service Cloudflared).Status
if ($tunnelStatus -eq "Running") {
    Write-Host "  ✓ Cloudflared: $tunnelStatus" -ForegroundColor Green
} else {
    Write-Host "  ✗ Cloudflared: $tunnelStatus" -ForegroundColor Red
}

Write-Host "`nProduction services started!" -ForegroundColor Cyan
Write-Host "Access your app at: https://eehxpe.com/badminton" -ForegroundColor White
