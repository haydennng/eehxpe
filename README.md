# eehxpe - Multi-Sport Web Platform

Production deployment repository for eehxpe.com

## Overview

This repository contains the production deployment code for multiple sports management applications:

- **Badminton** (`/badminton`) - Matchup generator and session manager
- More sports coming soon...

## Architecture

- **Hosting**: Windows PC with Cloudflare Named Tunnel
- **Server**: Waitress WSGI server (running as Windows service)
- **Domain**: https://eehxpe.com
- **Auto-Deploy**: GitHub Actions self-hosted runner

## Directory Structure

```
eehxpe/
├── eehxpe/              # Python package
│   ├── wsgi.py          # WSGI aggregator (mounts apps on subpaths)
│   └── shared/          # Shared utilities (auth, etc.)
├── apps/
│   └── badminton/       # Badminton app code
├── scripts/             # Deployment and management scripts
│   ├── deploy.ps1       # Main deployment script
│   ├── start-production.ps1
│   ├── stop-production.ps1
│   └── backup-data.ps1
├── data/                # Production data (local only, not in git)
├── logs/                # Application logs (local only)
└── backups/             # Data backups (local only)
```

## Deployment

### Automatic Deployment

Push to `main` branch triggers automatic deployment via GitHub Actions self-hosted runner:

1. Code pushed to `eehxpe` repo
2. Self-hosted runner executes `scripts/deploy.ps1`
3. Script pulls latest code, installs dependencies, restarts service

### Manual Deployment

```powershell
cd C:\Users\Hayde\eehxpe
.\scripts\deploy.ps1
```

### Rollback

```powershell
.\scripts\deploy.ps1 -Rollback -ToCommit <commit-sha>
```

## Service Management

### Start Services
```powershell
.\scripts\start-production.ps1
```

### Stop Services
```powershell
.\scripts\stop-production.ps1
```

### Check Status
```powershell
# App service
nssm status EehxpeBadminton

# Tunnel service
Get-Service Cloudflared
```

## Backup & Recovery

### Manual Backup
```powershell
.\scripts\backup-data.ps1
```

### Automated Backups
Daily backups via Windows Task Scheduler (3:00 AM)
- Retention: 30 days
- Location: `C:\Users\Hayde\eehxpe\backups\`

## Development Workflow

1. **Develop locally** in `badminton-matchups` repo
2. **Test locally** with Flask dev server
3. **Publish to production** via GitHub Action (or manual copy)
4. **Auto-deploy** triggers and restarts production service

## URLs

- **Production**: https://eehxpe.com/badminton
- **Local Testing**: http://127.0.0.1:8001/badminton

## Security

- All traffic through Cloudflare Tunnel (HTTPS, DDoS protection)
- App binds to localhost only (127.0.0.1:8001)
- No ports exposed directly to internet
- Secrets managed via `.env.production` (not in git)
- Regular automated backups

## Monitoring

### Logs
- **App logs**: `logs/badminton/app.log`
- **Service stdout**: `logs/badminton/stdout.log`
- **Service stderr**: `logs/badminton/stderr.log`
- **Deploy logs**: `logs/deploy.log`

### Health Check
- Endpoint: https://eehxpe.com/healthz (if configured)

## Troubleshooting

### App not responding
```powershell
# Check service status
nssm status EehxpeBadminton

# View logs
Get-Content C:\Users\Hayde\eehxpe\logs\badminton\stderr.log -Tail 50

# Restart
.\scripts\stop-production.ps1
.\scripts\start-production.ps1
```

### Tunnel issues
```powershell
# Check tunnel status
Get-Service Cloudflared

# View tunnel logs
cloudflared tunnel info eehxpe

# Restart tunnel
Restart-Service Cloudflared
```

## Future Enhancements

- [ ] User authentication system (Flask-Login + SQLite)
- [ ] Additional sports apps (volleyball, tennis, etc.)
- [ ] Shared SSO across all sports
- [ ] API rate limiting
- [ ] Database migration from JSON to SQLite/PostgreSQL
- [ ] Cloudflare Access for admin routes
