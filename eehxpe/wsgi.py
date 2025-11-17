#!/usr/bin/env python3
"""
eehxpe WSGI Application
Multi-app aggregator that mounts sports apps on subpaths.
"""
import sys
import os
from pathlib import Path

# Load environment variables from .env.production
env_file = Path(__file__).parent.parent / '.env.production'
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

# Add project root and apps to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'apps' / 'badminton'))

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import NotFound

def not_found_app(environ, start_response):
    """Default 404 handler for unmapped paths."""
    return NotFound()(environ, start_response)

# Import and initialize badminton app
badminton_app = None
try:
    # Import the badminton Flask app
    from app import app as badminton_app
    print("✓ Badminton app loaded successfully")
except Exception as e:
    print(f"✗ Failed to load badminton app: {e}")
    import traceback
    traceback.print_exc()

# Build the mounts dictionary
mounts = {}
if badminton_app:
    mounts["/badminton"] = badminton_app
    print(f"✓ Mounted badminton app at /badminton")

# Create the dispatcher
application = DispatcherMiddleware(not_found_app, mounts)

if __name__ == "__main__":
    # For local testing
    from waitress import serve
    print("\n" + "="*60)
    print("eehxpe Multi-App Server")
    print("="*60)
    print(f"Mounted apps: {list(mounts.keys())}")
    print("Listening on http://127.0.0.1:8001")
    print("="*60 + "\n")
    serve(application, host='127.0.0.1', port=8001)
