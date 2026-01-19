#!/usr/bin/env python3
"""
Production server startup script for eehxpe.com
Uses Waitress WSGI server with single-threaded configuration to prevent race conditions.
"""
import sys
import os
import subprocess
import time
from pathlib import Path

# Kill any existing processes on port 8001
def kill_old_processes():
    try:
        # Find processes using port 8001
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if ':8001' in line and 'LISTENING' in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        print(f"✓ Killed old process on port 8001 (PID: {pid})")
                    except:
                        pass
        time.sleep(0.5)
    except Exception as e:
        print(f"Warning: Could not kill old processes: {e}")

print("Cleaning up old processes...")
kill_old_processes()

# Load environment variables from .env.production
env_file = Path(__file__).parent / '.env.production'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)
    print(f"✓ Loaded environment from {env_file}")
else:
    print(f"⚠ Warning: {env_file} not found")

# Set flag to indicate we're running under WSGI dispatcher
os.environ['WSGI_DISPATCHER'] = 'true'

# Add paths for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'apps' / 'badminton'))

# Import the WSGI application
from eehxpe.wsgi import application

if __name__ == '__main__':
    from waitress import serve
    
    print("\n" + "="*60)
    print("🚀 eehxpe.com Production Server")
    print("="*60)
    print("\n📍 Configuration:")
    print("   Host: 0.0.0.0")
    print("   Port: 8001")
    print("   Threads: 4 (moderate threading)")
    print("   URL: http://eehxpe.com or http://localhost:8001")
    print("\n💡 To stop: Press Ctrl+C or run: Get-Process python | Where-Object {(netstat -ano | findstr $_.Id) -match ':8001'} | Stop-Process")
    print("="*60 + "\n")
    
    # Start Waitress with moderate threading
    # SQLite can handle multiple readers, just not multiple writers
    serve(application, 
          host='0.0.0.0',  # Listen on all interfaces
          port=8001,
          threads=4,  # Allow 4 concurrent requests
          channel_timeout=60,
          cleanup_interval=30,
          asyncore_use_poll=True)
