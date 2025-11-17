# Badminton Matchup Manager - Deployment Guide

This guide explains how to deploy your Badminton Matchup Manager app so you can access it from your phone at the badminton courts using Cloudflare Tunnel (free).

## 📋 Overview

Your app will:
- Run on your Windows PC at home
- Be accessible via HTTPS from anywhere (phone over LTE/WiFi)
- Work as a Progressive Web App (installable on your phone)
- Use Cloudflare Tunnel (completely free) for remote access
- Store all data locally on your PC

---

## ⚙️ Initial Setup

### Step 1: Set Up Python Environment

Open PowerShell in the `badminton-matchups` directory and run:

```powershell
# Verify Python version
python --version

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Generate and Set Secret Key

The app requires a secure secret key for sessions. Generate one:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated key (it will look like: `a3f5b2c8d9e1f4...`) and set it as an environment variable:

```powershell
setx FLASK_SECRET_KEY "PASTE_YOUR_GENERATED_KEY_HERE"
```

**Important:** After running `setx`, close PowerShell and open a new window for the change to take effect.

### Step 3: Test Locally

Before setting up remote access, verify the app works locally:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start the server
.\start_server.ps1
```

Visit http://127.0.0.1:5000 in your browser and verify:
- Dashboard loads
- You can add/manage players
- You can create matchups
- Data persists after restart

Keep this server running for the next steps.

---

## 🌐 Cloudflare Tunnel Setup

### Step 4: Install Cloudflared

Install the Cloudflare Tunnel client using Windows Package Manager:

```powershell
winget install -e --id Cloudflare.cloudflared
```

Verify installation (open a **new** PowerShell window):

```powershell
cloudflared --version
```

### Step 5: Authenticate with Cloudflare

Create a free Cloudflare account at https://dash.cloudflare.com/sign-up if you don't have one.

Then authenticate cloudflared:

```powershell
cloudflared tunnel login
```

A browser window will open. Log in to Cloudflare and authorize the certificate.

### Step 6: Start a Quick Tunnel (Free, Ephemeral URL)

With your Flask app still running on `http://127.0.0.1:5000`, open a **new** PowerShell window:

```powershell
cloudflared tunnel --url http://localhost:5000
```

You'll see output like:
```
2025-10-27 12:00:00 INF +--------------------------------------------------------------------------------------------+
2025-10-27 12:00:00 INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
2025-10-27 12:00:00 INF |  https://abc-def-123.trycloudflare.com                                                    |
2025-10-27 12:00:00 INF +--------------------------------------------------------------------------------------------+
```

**Copy this URL** and open it on your phone!

---

## 📱 Install as PWA on Your Phone

### On Android (Chrome/Edge):

1. Open the Cloudflare tunnel URL in Chrome
2. Wait a few seconds - you should see an "Install app" banner
3. Tap "Install" or use the menu (⋮) → "Add to Home screen"
4. The app will appear on your home screen like a native app

### On iOS (Safari):

1. Open the Cloudflare tunnel URL in Safari
2. Tap the Share button (□↑)
3. Scroll down and tap "Add to Home Screen"
4. Tap "Add"
5. The app will appear on your home screen

---

## 🚀 Daily Usage

### Starting the App

**Terminal 1 - Flask App:**
```powershell
cd C:\Users\Hayde\badminton-matchups
.\.venv\Scripts\Activate.ps1
.\start_server.ps1
```

**Terminal 2 - Cloudflare Tunnel:**
```powershell
cloudflared tunnel --url http://localhost:5000
```

Copy the generated URL and open it on your phone.

### Stopping the App

Press `Ctrl+C` in both PowerShell windows.

---

## 🔒 Security Notes

### Current Setup (Admin-Only)
- Your app is protected by URL obscurity (the random Cloudflare URL is hard to guess)
- Keep the URL private - don't share it publicly
- The app binds to `127.0.0.1` (localhost only) - it's not exposed on your local network
- All traffic goes through Cloudflare's HTTPS tunnel (encrypted)

### Future: Permanent URL with Your Own Domain

If you purchase a domain and add it to Cloudflare (free), you can set up a **Named Tunnel** with a permanent URL like `badminton.yourdomain.com`:

```powershell
# Create a named tunnel
cloudflared tunnel create badminton-pc

# Create config file: C:\Users\Hayde\.cloudflared\config.yml
# (Content shown below)

# Route DNS
cloudflared tunnel route dns badminton-pc badminton.yourdomain.com

# Run the tunnel
cloudflared tunnel run badminton-pc
```

**config.yml example:**
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: C:\Users\Hayde\.cloudflared\YOUR_TUNNEL_ID.json

ingress:
  - hostname: badminton.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
```

---

## 🛠 Troubleshooting

### "FLASK_SECRET_KEY not set" error
- Run the `setx` command from Step 2
- **Close PowerShell completely** and open a new window
- The environment variable only takes effect in new sessions

### Can't access the tunnel URL
- Verify your Flask app is running on http://127.0.0.1:5000
- Check that cloudflared is running and shows the tunnel URL
- Try the URL in incognito/private mode first
- Check your PC's firewall isn't blocking Python

### Tunnel URL changes every time
- This is normal for Quick Tunnels (free tier)
- For a permanent URL, you need to set up a Named Tunnel with a domain

### PWA won't install
- Verify you're accessing via HTTPS (the Cloudflare tunnel URL)
- Service workers require HTTPS (localhost also works)
- Try clearing browser cache and reloading

### Data lost after restart
- Data is stored in the `data/` folder
- Don't delete `data/players.json` or `data/matches.json`
- These files persist between restarts

### PC goes to sleep and app stops working
- Disable sleep when plugged in:
  - Windows Settings → System → Power & Sleep
  - Set "When plugged in, PC goes to sleep after" to "Never"
- Or run: `powercfg -change -standby-timeout-ac 0`

---

## 📊 Production Tips

### Auto-Start on Boot (Optional)

To run the tunnel as a Windows service (Named Tunnel only):

```powershell
cloudflared service install
```

This requires a Named Tunnel with a permanent domain.

### Development Mode

To run in development mode with auto-reload:

```powershell
$env:FLASK_ENV = "development"
python app.py
```

### Monitoring

Check if your tunnel is running:

```powershell
# For named tunnels
cloudflared tunnel list

# View logs
cloudflared tunnel logs badminton-pc
```

---

## 🎯 Next Steps

1. ✅ Test locally
2. ✅ Set up Quick Tunnel and test from phone
3. ✅ Install PWA on your phone
4. 📱 Use it at the badminton courts!
5. 🌐 (Optional) Purchase a domain for permanent URL
6. 👥 (Future) Add user authentication for sharing with others

---

## 📞 Need Help?

- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Flask docs: https://flask.palletsprojects.com/
- PWA best practices: https://web.dev/progressive-web-apps/

---

**Happy badminton! 🏸**
