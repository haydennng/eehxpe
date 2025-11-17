# 🚀 Quick Start Guide

## What We've Done

✅ **PWA Features Added:**
- Progressive Web App manifest
- Service worker for offline support
- Installable app icons (green shuttlecock theme)
- Offline fallback page

✅ **Production Security:**
- Secret key from environment variable (required)
- Security headers (CSP, X-Frame-Options, etc.)
- Localhost-only binding (127.0.0.1)
- Waitress WSGI server for production use

✅ **Infrastructure:**
- Startup script (`start_server.ps1`)
- Comprehensive deployment guide (`DEPLOYMENT.md`)

---

## 🎯 Next Steps (5 Minutes)

### 1. Set Up Secret Key

Open PowerShell in this directory and run:

```powershell
# Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output (looks like: `a3f5b2c8d9e1f4a7b9c2...`) and set it:

```powershell
setx FLASK_SECRET_KEY "PASTE_YOUR_KEY_HERE"
```

**Important:** Close PowerShell and open a new window after running `setx`.

---

### 2. Install Dependencies

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# Install dependencies (including Waitress)
pip install -r requirements.txt
```

---

### 3. Test Locally

```powershell
# Start the server
.\start_server.ps1
```

Open http://127.0.0.1:5000 in your browser and verify everything works.

Keep this running for the next step!

---

### 4. Set Up Cloudflare Tunnel

Open a **new** PowerShell window:

```powershell
# Install cloudflared (one-time)
winget install -e --id Cloudflare.cloudflared

# Close and reopen PowerShell, then authenticate
cloudflared tunnel login
```

Log in to Cloudflare when the browser opens.

---

### 5. Start the Tunnel

```powershell
# Start Quick Tunnel (free, ephemeral URL)
cloudflared tunnel --url http://localhost:5000
```

You'll see a URL like: `https://abc-123.trycloudflare.com`

**Copy this URL and open it on your phone!** 📱

---

### 6. Install on Your Phone

**Android:**
- Open the tunnel URL in Chrome
- Look for "Install app" banner or use menu → "Add to Home screen"

**iOS:**
- Open the tunnel URL in Safari  
- Tap Share (□↑) → "Add to Home Screen"

---

## ✅ You're Done!

Now you can:
- Access your app from anywhere via the Cloudflare tunnel URL
- Install it as an app on your home screen
- Use it at the badminton courts over LTE/WiFi

---

## 📊 Daily Usage

**Start both these in separate terminals:**

```powershell
# Terminal 1: Flask server
cd C:\Users\Hayde\badminton-matchups
.\.venv\Scripts\Activate.ps1
.\start_server.ps1

# Terminal 2: Cloudflare tunnel
cloudflared tunnel --url http://localhost:5000
```

Copy the generated tunnel URL to your phone each time (it changes with Quick Tunnel).

---

## 🔧 Troubleshooting

**"FLASK_SECRET_KEY not set"**
- Did you close and reopen PowerShell after running `setx`?
- Try: `$env:FLASK_SECRET_KEY` to verify it's set

**Can't connect to tunnel URL**
- Is your Flask server running on 127.0.0.1:5000?
- Is cloudflared showing a valid URL?
- Try the URL in incognito mode first

**Need more help?**
- See `DEPLOYMENT.md` for detailed troubleshooting
- Check Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/

---

## 🎯 Future Improvements

Want a permanent URL instead of the changing Quick Tunnel URL?
- Purchase a domain ($10-15/year)
- Add it to Cloudflare (free)
- Set up a Named Tunnel with a permanent subdomain

See `DEPLOYMENT.md` for instructions!

---

**Happy badminton! 🏸**
