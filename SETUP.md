# eehxpe Production Setup Guide

Complete step-by-step guide to set up the production environment for eehxpe.com

## Prerequisites

- ✅ Windows 10/11
- ✅ Python 3.13+
- ✅ Git 2.40+
- ✅ cloudflared installed and authenticated
- ✅ Domain `eehxpe.com` added to Cloudflare account
- ✅ PowerShell 5.1+

---

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `eehxpe`
3. Visibility: **Private**
4. Do NOT initialize with README (we already have one)
5. Click "Create repository"

6. Copy the repository URL: `https://github.com/<YOUR_USERNAME>/eehxpe.git`

---

## Step 2: Initialize Local Git Repository

```powershell
cd C:\Users\Hayde\eehxpe

# Initialize git
git init
git add .
git commit -m "Initial production setup"

# Add remote (replace <YOUR_USERNAME> with your GitHub username)
git remote add origin https://github.com/<YOUR_USERNAME>/eehxpe.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## Step 3: Copy Badminton App to Production

```powershell
# Copy badminton app files
$source = "C:\Users\Hayde\badminton-matchups"
$dest = "C:\Users\Hayde\eehxpe\apps\badminton"

# Copy all files except git, venv, and data
$exclude = @('.git', '.venv', '__pycache__', 'data')
Get-ChildItem -Path $source -Recurse | 
    Where-Object { 
        $exclude -notcontains $_.Name 
    } | 
    Copy-Item -Destination {
        $dest + $_.FullName.Substring($source.Length)
    } -Force

Write-Host "✓ Badminton app copied to production"
```

---

## Step 4: Create Python Virtual Environment

```powershell
cd C:\Users\Hayde\eehxpe

# Create venv
python -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

Write-Host "✓ Virtual environment created and dependencies installed"
```

---

## Step 5: Configure Environment Variables

```powershell
# Generate a strong secret key
$secretKey = python -c "import secrets; print(secrets.token_hex(32))"

# Create .env.production file
$envContent = @"
FLASK_ENV=production
FLASK_SECRET_KEY=$secretKey
BADMINTON_DATA_DIR=C:\Users\Hayde\eehxpe\data\badminton
LOG_DIR=C:\Users\Hayde\eehxpe\logs\badminton
SESSION_COOKIE_PATH=/badminton
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
"@

Set-Content -Path "C:\Users\Hayde\eehxpe\.env.production" -Value $envContent
Write-Host "✓ Environment file created with generated secret key"
```

---

## Step 6: Set Up Cloudflare Named Tunnel

```powershell
# Create named tunnel
cloudflared tunnel create eehxpe

# Note the tunnel ID from output (looks like: abc123def-456-789-...)
# The credentials file will be saved to: C:\Users\Hayde\.cloudflared\<TUNNEL_ID>.json

# Route DNS
cloudflared tunnel route dns eehxpe eehxpe.com

Write-Host "✓ Cloudflare tunnel created and DNS routed"
```

### Create Tunnel Configuration

Create/edit `C:\Users\Hayde\.cloudflared\config.yml`:

```yaml
tunnel: eehxpe
credentials-file: C:\Users\Hayde\.cloudflared\<YOUR_TUNNEL_ID>.json

ingress:
  - hostname: eehxpe.com
    path: /badminton*
    service: http://127.0.0.1:8001
  - service: http_status:404
```

**Replace `<YOUR_TUNNEL_ID>` with your actual tunnel ID!**

### Install Cloudflared as Service

```powershell
cloudflared service install
Start-Service Cloudflared
Get-Service Cloudflared  # Should show "Running"
```

---

## Step 7: Install NSSM (Service Manager)

### Option A: Using Scoop (recommended)
```powershell
# Install Scoop if not already installed
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# Install NSSM
scoop install nssm
```

### Option B: Manual Download
1. Download from: https://nssm.cc/download
2. Extract to `C:\Tools\nssm\`
3. Add `C:\Tools\nssm\win64` to PATH

---

## Step 8: Create Windows Service for Flask App

```powershell
# Service configuration
nssm install EehxpeBadminton "C:\Users\Hayde\eehxpe\venv\Scripts\waitress-serve.exe"

# Set application arguments
nssm set EehxpeBadminton AppParameters "--listen=127.0.0.1:8001 eehxpe.wsgi:application"

# Set working directory
nssm set EehxpeBadminton AppDirectory "C:\Users\Hayde\eehxpe"

# Set environment variables
nssm set EehxpeBadminton AppEnvironmentExtra "FLASK_ENV=production" "BADMINTON_DATA_DIR=C:\Users\Hayde\eehxpe\data\badminton" "LOG_DIR=C:\Users\Hayde\eehxpe\logs\badminton"

# Note: FLASK_SECRET_KEY should be loaded from .env.production in app code

# Set stdout/stderr logging
nssm set EehxpeBadminton AppStdout "C:\Users\Hayde\eehxpe\logs\badminton\stdout.log"
nssm set EehxpeBadminton AppStderr "C:\Users\Hayde\eehxpe\logs\badminton\stderr.log"

# Set startup type
nssm set EehxpeBadminton Start SERVICE_AUTO_START

# Set restart on failure
nssm set EehxpeBadminton AppRestartDelay 5000

# Start service
nssm start EehxpeBadminton

# Check status
nssm status EehxpeBadminton  # Should show "SERVICE_RUNNING"
```

---

## Step 9: Test Local Deployment

```powershell
# Check if both services are running
Get-Service Cloudflared
nssm status EehxpeBadminton

# Test local endpoint (before tunnel)
curl http://127.0.0.1:8001/badminton

# Test via tunnel (may take a minute to propagate)
curl https://eehxpe.com/badminton
```

Visit https://eehxpe.com/badminton in your browser!

---

## Step 10: Set Up GitHub Actions Self-Hosted Runner

1. Go to your GitHub repo: `https://github.com/<YOUR_USERNAME>/eehxpe`
2. Navigate to: **Settings** → **Actions** → **Runners**
3. Click **New self-hosted runner**
4. Select **Windows** and **x64**
5. Follow the on-screen commands on your PC:

```powershell
# Example commands (yours will be different):
mkdir C:\Users\Hayde\actions-runner
cd C:\Users\Hayde\actions-runner

# Download (GitHub will provide exact URL)
Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.xxx.x/actions-runner-win-x64-2.xxx.x.zip -OutFile actions-runner-win-x64-2.xxx.x.zip

# Extract
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD\actions-runner-win-x64-2.xxx.x.zip", "$PWD")

# Configure (GitHub will provide exact token)
.\config.cmd --url https://github.com/<YOUR_USERNAME>/eehxpe --token <YOUR_TOKEN>

# Install as service
.\svc.cmd install
.\svc.cmd start

# Verify
.\svc.cmd status  # Should show "Running"
```

---

## Step 11: Set Up Automated Backups

```powershell
# Create scheduled task for daily backups
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\Users\Hayde\eehxpe\scripts\backup-data.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

Register-ScheduledTask -TaskName "eehxpe-daily-backup" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description "Daily backup of eehxpe production data"

Write-Host "✓ Daily backup task created (runs at 3:00 AM)"
```

---

## Step 12: Configure Power Settings

Ensure your PC stays awake for production use:

```powershell
# Disable sleep when plugged in
powercfg -change -standby-timeout-ac 0

# Prevent system from sleeping
powercfg -change -hibernate-timeout-ac 0

Write-Host "✓ Power settings configured for always-on operation"
```

---

## Verification Checklist

Run through this checklist to ensure everything is set up correctly:

```powershell
# 1. Check Git repository
cd C:\Users\Hayde\eehxpe
git status  # Should be clean

# 2. Check services
Get-Service Cloudflared  # Should be Running
nssm status EehxpeBadminton  # Should be SERVICE_RUNNING

# 3. Check runner
cd C:\Users\Hayde\actions-runner
.\svc.cmd status  # Should be Running

# 4. Test endpoints
curl http://127.0.0.1:8001/badminton  # Local
curl https://eehxpe.com/badminton  # Public

# 5. Check logs
Get-Content C:\Users\Hayde\eehxpe\logs\badminton\stdout.log -Tail 20

# 6. Test backup
C:\Users\Hayde\eehxpe\scripts\backup-data.ps1

# 7. Check scheduled task
Get-ScheduledTask -TaskName "eehxpe-daily-backup"
```

---

## Next Steps

### Set Up Dev-to-Prod Publishing

See `PUBLISHING.md` for instructions on:
- Creating GitHub Action in badminton-matchups repo
- Auto-publishing to eehxpe repo on push
- Manual publishing workflow

### Make Your First Deployment

```powershell
cd C:\Users\Hayde\eehxpe
# Make a change to README.md
echo "Test deployment" >> README.md
git add .
git commit -m "Test deployment"
git push

# GitHub Actions runner will automatically deploy!
# Check logs at: C:\Users\Hayde\eehxpe\logs\deploy.log
```

---

## Troubleshooting

### Service Won't Start
```powershell
# Check service logs
Get-Content C:\Users\Hayde\eehxpe\logs\badminton\stderr.log -Tail 50

# Test manually
cd C:\Users\Hayde\eehxpe
.\venv\Scripts\activate
python -m eehxpe.wsgi
```

### Tunnel Not Working
```powershell
# Check tunnel status
cloudflared tunnel info eehxpe

# Check tunnel logs
Get-EventLog -LogName Application -Source cloudflared -Newest 20

# Restart tunnel
Restart-Service Cloudflared
```

### Runner Not Responding
```powershell
cd C:\Users\Hayde\actions-runner
.\svc.cmd stop
.\svc.cmd start
.\svc.cmd status
```

---

## Security Notes

- ✅ App binds to localhost only (not exposed to LAN)
- ✅ All traffic through Cloudflare Tunnel (HTTPS + DDoS protection)
- ✅ Secrets in `.env.production` (not in git)
- ✅ Regular automated backups
- ⚠️ Keep Windows updated
- ⚠️ Keep cloudflared updated
- ⚠️ Rotate FLASK_SECRET_KEY periodically

---

**Setup Complete! 🎉**

Your production environment is now ready at: https://eehxpe.com/badminton
