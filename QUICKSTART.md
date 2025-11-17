# Quick Start Checklist

Use this checklist to set up your eehxpe.com production deployment.

## ☑️ Pre-Setup (Already Complete)

- [x] Production directory structure created
- [x] Core files and scripts created
- [x] Git repository initialized
- [x] Documentation written

## 📋 Setup Steps (Do These Next)

### 1. Create GitHub Repository
- [ ] Go to https://github.com/new
- [ ] Create private repo named `eehxpe`
- [ ] **DO NOT** initialize with README
- [ ] Copy the repo URL

### 2. Push Code to GitHub
```powershell
cd C:\Users\Hayde\eehxpe
git commit -m "Initial production setup"
git remote add origin https://github.com/<YOUR_USERNAME>/eehxpe.git
git branch -M main
git push -u origin main
```

### 3. Copy Badminton App
```powershell
# Option A: Use robocopy (Windows built-in)
robocopy C:\Users\Hayde\badminton-matchups C:\Users\Hayde\eehxpe\apps\badminton /E /XD .git .venv __pycache__ data tests .github /XF test_*.py *.pyc

# Option B: Manual copy (exclude .git, .venv, data, __pycache__)
# Then commit:
cd C:\Users\Hayde\eehxpe
git add apps/badminton/
git commit -m "Add badminton app"
git push
```

### 4. Create Python Environment
```powershell
cd C:\Users\Hayde\eehxpe
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Secrets
```powershell
# Generate secret key
$secret = python -c "import secrets; print(secrets.token_hex(32))"

# Create .env.production (modify template)
Copy-Item .env.production.example .env.production

# Edit .env.production and replace GENERATE_A_STRONG_SECRET_KEY_HERE with $secret
```

### 6. Set Up Cloudflare Tunnel
```powershell
# Create tunnel
cloudflared tunnel create eehxpe

# Note the tunnel ID and credentials file path
# Create config: C:\Users\Hayde\.cloudflared\config.yml
# (See SETUP.md Step 6 for config content)

# Route DNS
cloudflared tunnel route dns eehxpe eehxpe.com

# Install as service
cloudflared service install
Start-Service Cloudflared
```

### 7. Install NSSM
```powershell
# If you have Scoop:
scoop install nssm

# Otherwise download from: https://nssm.cc/download
# Extract to C:\Tools\nssm\
```

### 8. Create Windows Service
```powershell
# Install service
nssm install EehxpeBadminton "C:\Users\Hayde\eehxpe\venv\Scripts\waitress-serve.exe"

# Configure (see SETUP.md Step 8 for all commands)
nssm set EehxpeBadminton AppParameters "--listen=127.0.0.1:8001 eehxpe.wsgi:application"
nssm set EehxpeBadminton AppDirectory "C:\Users\Hayde\eehxpe"
# ... (more config commands)

# Start service
nssm start EehxpeBadminton
```

### 9. Set Up GitHub Actions Runner
- [ ] Go to repo Settings → Actions → Runners
- [ ] Add new self-hosted runner (Windows x64)
- [ ] Follow on-screen commands to install
- [ ] Install as service: `.\svc.cmd install; .\svc.cmd start`

### 10. Set Up Automated Backups
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\Users\Hayde\eehxpe\scripts\backup-data.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
Register-ScheduledTask -TaskName "eehxpe-daily-backup" -Action $action -Trigger $trigger -Principal $principal
```

### 11. Configure Power Settings
```powershell
powercfg -change -standby-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0
```

### 12. Test Everything
```powershell
# Check services
Get-Service Cloudflared
nssm status EehxpeBadminton

# Test local
curl http://127.0.0.1:8001/badminton

# Test public (may take a minute to propagate)
curl https://eehxpe.com/badminton

# Open in browser
Start-Process "https://eehxpe.com/badminton"
```

## 🚀 Set Up Dev-to-Prod Publishing (Optional but Recommended)

See `PUBLISHING.md` for complete instructions. Quick version:

1. Create GitHub PAT with write access to eehxpe repo
2. Add PAT as secret `EEHXPE_PAT` in badminton-matchups repo
3. Add workflow file to badminton-matchups repo
4. Push changes → automatic deployment!

## 📚 Documentation

- **SETUP.md** - Complete step-by-step setup guide
- **README.md** - Architecture overview and daily usage
- **PUBLISHING.md** - Dev-to-prod publishing workflows
- **QUICKSTART.md** - This file (checklist)

## 🆘 Getting Help

If you run into issues:
1. Check logs: `Get-Content C:\Users\Hayde\eehxpe\logs\badminton\stderr.log -Tail 50`
2. Review SETUP.md troubleshooting section
3. Check service status: `nssm status EehxpeBadminton`
4. Restart services: `.\scripts\stop-production.ps1; .\scripts\start-production.ps1`

## ✅ Verification

Once everything is set up, you should be able to:
- ✅ Access https://eehxpe.com/badminton from any device
- ✅ Push code to eehxpe repo → auto-deploy
- ✅ Services auto-start on PC reboot
- ✅ Daily backups running at 3 AM

---

**Current Status:** Initial scaffold created ✅

**Next:** Follow steps 1-12 above to complete setup.
