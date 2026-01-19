#!/usr/bin/env pwsh
# Start Cloudflare Tunnel for eehxpe.com

$ErrorActionPreference = "Stop"

Write-Host "Starting Cloudflare Tunnel for eehxpe.com..." -ForegroundColor Cyan

# Set working directory
Set-Location "C:\Users\Hayde"

# Run the tunnel
cloudflared tunnel run eehxpe
