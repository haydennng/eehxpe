#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Backup production data with automatic retention

.PARAMETER Source
    Source directory to backup (default: data folder)

.PARAMETER Dest
    Destination directory for backups (default: backups folder)

.PARAMETER Keep
    Number of backup archives to keep (default: 30)

.EXAMPLE
    .\backup-data.ps1
    # Backup with defaults (30-day retention)

.EXAMPLE
    .\backup-data.ps1 -Keep 90
    # Keep 90 days of backups
#>

param(
    [string]$Source = "C:\Users\Hayde\eehxpe\data",
    [string]$Dest = "C:\Users\Hayde\eehxpe\backups",
    [int]$Keep = 30
)

$ErrorActionPreference = "Stop"

# Ensure destination exists
if (!(Test-Path $Dest)) {
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Write-Host "Created backup directory: $Dest"
}

# Ensure source exists
if (!(Test-Path $Source)) {
    Write-Host "WARNING: Source directory does not exist: $Source" -ForegroundColor Yellow
    exit 0
}

# Create timestamped backup
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipFile = Join-Path $Dest "data-backup-$timestamp.zip"

Write-Host "Creating backup..." -ForegroundColor Cyan
Write-Host "  Source: $Source"
Write-Host "  Destination: $zipFile"

try {
    Compress-Archive -Path "$Source\*" -DestinationPath $zipFile -CompressionLevel Optimal
    $size = (Get-Item $zipFile).Length / 1MB
    Write-Host "  ✓ Backup created: $([math]::Round($size, 2)) MB" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Backup failed: $_" -ForegroundColor Red
    exit 1
}

# Retention: remove old backups
Write-Host "`nApplying retention policy (keep $Keep backups)..." -ForegroundColor Cyan
$backups = Get-ChildItem $Dest -Filter "data-backup-*.zip" | Sort-Object LastWriteTime -Descending

if ($backups.Count -gt $Keep) {
    $toRemove = $backups | Select-Object -Skip $Keep
    Write-Host "  Removing $($toRemove.Count) old backup(s)..."
    
    foreach ($backup in $toRemove) {
        Remove-Item $backup.FullName -Force
        Write-Host "    Removed: $($backup.Name)" -ForegroundColor Gray
    }
    
    Write-Host "  ✓ Retention applied" -ForegroundColor Green
} else {
    Write-Host "  No old backups to remove (currently $($backups.Count) backups)" -ForegroundColor Gray
}

Write-Host "`n✓ Backup completed successfully!" -ForegroundColor Green
