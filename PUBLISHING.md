# Publishing from Dev to Production

This guide explains how to publish code from your `badminton-matchups` development repository to the `eehxpe` production repository.

## Overview

**Development Flow:**
1. Develop and test locally in `badminton-matchups`
2. Push changes to `badminton-matchups` main branch
3. GitHub Action automatically copies code to `eehxpe` repo
4. Push to `eehxpe` triggers auto-deployment on your PC
5. GitHub Actions self-hosted runner deploys to production

---

## Option 1: Automated Publishing (Recommended)

### Step 1: Create Fine-Grained Personal Access Token (PAT)

1. Go to: https://github.com/settings/tokens?type=beta
2. Click **Generate new token**
3. Token name: `badminton-to-eehxpe-publisher`
4. Expiration: 1 year (or custom)
5. Repository access: **Only select repositories**
   - Select: `eehxpe` only
6. Permissions:
   - **Contents**: Read and write
   - **Metadata**: Read-only (automatically selected)
7. Click **Generate token**
8. **Copy the token immediately** (you won't see it again!)

### Step 2: Add PAT as Secret to badminton-matchups Repo

1. Go to: `https://github.com/<YOUR_USERNAME>/badminton-matchups/settings/secrets/actions`
2. Click **New repository secret**
3. Name: `EEHXPE_PAT`
4. Secret: Paste the PAT you copied
5. Click **Add secret**

### Step 3: Create Publishing Workflow

Create `.github/workflows/publish-to-eehxpe.yml` in your `badminton-matchups` repo:

```yaml
name: Publish to eehxpe Production

on:
  workflow_dispatch:  # Manual trigger
  push:
    branches: [ "main" ]
    paths-ignore:
      - '**.md'
      - '.gitignore'
      - 'tests/**'

jobs:
  publish:
    name: Publish to eehxpe repo
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout dev repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better commit messages
      
      - name: Prepare production payload
        run: |
          mkdir -p staging/apps/badminton
          
          # Copy files excluding dev-only content
          rsync -av \
            --exclude='.git' \
            --exclude='.github' \
            --exclude='.venv' \
            --exclude='venv' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='data/*.json' \
            --exclude='test_*.py' \
            --exclude='tests/' \
            --exclude='.vscode' \
            --exclude='.idea' \
            ./ staging/apps/badminton/
          
          echo "✓ Production payload prepared"
          du -sh staging/apps/badminton
      
      - name: Clone eehxpe production repo
        env:
          PAT: ${{ secrets.EEHXPE_PAT }}
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"
          
          git clone https://x-access-token:${PAT}@github.com/${{ github.repository_owner }}/eehxpe.git eehxpe-repo
          echo "✓ Production repo cloned"
      
      - name: Sync badminton app to production
        run: |
          cd eehxpe-repo
          
          # Ensure apps/badminton directory exists
          mkdir -p apps/badminton
          
          # Sync files (delete removed files)
          rsync -av --delete ../staging/apps/badminton/ apps/badminton/
          
          # Check if there are changes
          if [[ -n $(git status --porcelain) ]]; then
            echo "✓ Changes detected"
            git add apps/badminton/
            
            # Create meaningful commit message
            COMMIT_SHA="${{ github.sha }}"
            COMMIT_MSG="${{ github.event.head_commit.message }}"
            
            git commit -m "Publish badminton from dev@${COMMIT_SHA:0:7}

Dev commit: $COMMIT_MSG
Dev ref: ${{ github.ref }}
Published by: ${{ github.actor }}
Workflow: ${{ github.workflow }}"
            
            echo "✓ Commit created"
          else
            echo "ℹ No changes to publish"
            exit 0
          fi
      
      - name: Push to production repo
        env:
          PAT: ${{ secrets.EEHXPE_PAT }}
        run: |
          cd eehxpe-repo
          git push https://x-access-token:${PAT}@github.com/${{ github.repository_owner }}/eehxpe.git HEAD:main
          echo "✓ Pushed to production repo"
          echo "🚀 Production deployment will start automatically"
```

### Step 4: Commit and Push the Workflow

```powershell
cd C:\Users\Hayde\badminton-matchups

# Create .github/workflows directory if it doesn't exist
mkdir -p .github/workflows

# Create the workflow file (copy content from above)
# Then commit and push
git add .github/workflows/publish-to-eehxpe.yml
git commit -m "Add automatic publishing to eehxpe production"
git push
```

### Step 5: Test the Publishing Workflow

```powershell
cd C:\Users\Hayde\badminton-matchups

# Make a small change
echo "# Test publish workflow" >> README.md
git add README.md
git commit -m "Test: automatic publishing to production"
git push

# Watch the workflow:
# Go to: https://github.com/<YOUR_USERNAME>/badminton-matchups/actions
```

**What happens:**
1. Push triggers workflow in `badminton-matchups`
2. Workflow copies app to `eehxpe` repo and pushes
3. Push to `eehxpe` triggers deployment workflow
4. Self-hosted runner on your PC runs `deploy.ps1`
5. App restarts with new code

---

## Option 2: Manual Publishing

If you prefer manual control or the automated workflow isn't working:

### Method A: Using PowerShell Script

Create `C:\Users\Hayde\badminton-matchups\publish-to-prod.ps1`:

```powershell
#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Manually publish badminton app to eehxpe production
#>

$ErrorActionPreference = "Stop"

$devRepo = "C:\Users\Hayde\badminton-matchups"
$prodRepo = "C:\Users\Hayde\eehxpe"
$appDest = "$prodRepo\apps\badminton"

Write-Host "Publishing badminton to production..." -ForegroundColor Cyan

# Ensure we're in dev repo
Set-Location $devRepo

# Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "WARNING: You have uncommitted changes in dev repo" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Get current commit info
$commitSHA = (git rev-parse --short HEAD).Trim()
$commitMsg = (git log -1 --pretty=%B).Trim()

Write-Host "Current dev commit: $commitSHA" -ForegroundColor Gray
Write-Host "Message: $commitMsg" -ForegroundColor Gray

# Sync files to production
Write-Host "`nSyncing files to production..." -ForegroundColor Yellow

$exclude = @('.git', '.github', '.venv', 'venv', '__pycache__', 'data', 'test_*.py', 'tests')

# Remove old production app files
if (Test-Path $appDest) {
    Remove-Item -Path "$appDest\*" -Recurse -Force
}

# Create destination if doesn't exist
New-Item -ItemType Directory -Path $appDest -Force | Out-Null

# Copy files
Get-ChildItem -Path $devRepo -Recurse | 
    Where-Object { 
        $item = $_
        $shouldExclude = $false
        foreach ($pattern in $exclude) {
            if ($item.FullName -like "*\$pattern\*" -or $item.Name -eq $pattern) {
                $shouldExclude = $true
                break
            }
        }
        -not $shouldExclude
    } | 
    ForEach-Object {
        $targetPath = $appDest + $_.FullName.Substring($devRepo.Length)
        $targetDir = Split-Path $targetPath -Parent
        
        if (!(Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        
        if ($_.PSIsContainer -eq $false) {
            Copy-Item $_.FullName -Destination $targetPath -Force
        }
    }

Write-Host "✓ Files synced" -ForegroundColor Green

# Commit in production repo
Set-Location $prodRepo

$prodStatus = git status --porcelain
if ($prodStatus) {
    Write-Host "`nCommitting to production repo..." -ForegroundColor Yellow
    
    git add apps/badminton/
    git commit -m "Publish badminton from dev@$commitSHA

Dev commit: $commitMsg
Published manually via script"
    
    Write-Host "✓ Committed to production" -ForegroundColor Green
    
    # Ask to push
    $push = Read-Host "`nPush to GitHub and trigger deployment? (y/N)"
    if ($push -eq "y") {
        git push
        Write-Host "✓ Pushed to GitHub" -ForegroundColor Green
        Write-Host "🚀 Deployment will start automatically on your PC" -ForegroundColor Cyan
    } else {
        Write-Host "⚠ Changes committed but not pushed. Run 'git push' when ready." -ForegroundColor Yellow
    }
} else {
    Write-Host "ℹ No changes to publish" -ForegroundColor Gray
}

Set-Location $devRepo
Write-Host "`n✓ Publishing complete!" -ForegroundColor Cyan
```

Usage:
```powershell
cd C:\Users\Hayde\badminton-matchups
.\publish-to-prod.ps1
```

### Method B: Direct Copy

Quick and simple for one-off updates:

```powershell
# Copy files
robocopy C:\Users\Hayde\badminton-matchups C:\Users\Hayde\eehxpe\apps\badminton /E /XD .git .venv __pycache__ data tests /XF test_*.py

# Commit and push
cd C:\Users\Hayde\eehxpe
git add apps/badminton/
git commit -m "Manual update: badminton app"
git push
```

---

## Deployment Verification

After publishing (either method), verify the deployment:

```powershell
# 1. Check GitHub Actions (eehxpe repo)
# Go to: https://github.com/<YOUR_USERNAME>/eehxpe/actions

# 2. Check deployment log on your PC
Get-Content C:\Users\Hayde\eehxpe\logs\deploy.log -Tail 30

# 3. Check service status
nssm status EehxpeBadminton

# 4. Test the live site
curl https://eehxpe.com/badminton

# Or open in browser:
Start-Process "https://eehxpe.com/badminton"
```

---

## Troubleshooting

### "PAT authentication failed"
- Ensure PAT has correct permissions (Contents: Read & Write)
- Check PAT hasn't expired
- Verify secret name is exactly `EEHXPE_PAT`

### "No changes detected" when there should be
- Check `.gitignore` in both repos
- Verify files aren't being excluded by rsync patterns
- Run manual publish script with verbose output

### "Deployment didn't trigger"
- Check self-hosted runner is running: `cd C:\Users\Hayde\actions-runner; .\svc.cmd status`
- Check workflow file in eehxpe repo exists: `.github/workflows/deploy-on-push.yml`
- View runner logs: `Get-Content C:\Users\Hayde\actions-runner\_diag\*.log -Tail 50`

---

## Best Practices

### When to Publish

✅ **DO Publish:**
- After testing changes locally
- When feature is complete and working
- Before starting a new feature (clean state)

❌ **DON'T Publish:**
- Work-in-progress code
- Untested changes
- Code with known bugs

### Pre-Publish Checklist

```powershell
cd C:\Users\Hayde\badminton-matchups

# 1. Run tests (if you have them)
python -m pytest

# 2. Check for syntax errors
python -m py_compile *.py

# 3. Test locally
.\start_server.ps1
# Visit http://127.0.0.1:5000 and test

# 4. Commit all changes
git status
git add .
git commit -m "Descriptive message"

# 5. Publish
git push  # (if using automatic publishing)
# or
.\publish-to-prod.ps1  # (if using manual script)
```

---

## Rollback Procedure

If deployment breaks production:

```powershell
cd C:\Users\Hayde\eehxpe

# Find previous working commit
git log --oneline -10

# Rollback to specific commit
.\scripts\deploy.ps1 -Rollback -ToCommit <previous-commit-sha>

# Example:
.\scripts\deploy.ps1 -Rollback -ToCommit abc123d
```

---

**Happy Publishing! 🚀**
