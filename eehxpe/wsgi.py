#!/usr/bin/env python3
"""
eehxpe WSGI Application
Multi-app aggregator that mounts sports apps on subpaths.
"""
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import NotFound

def not_found_app(environ, start_response):
    """Default 404 handler for unmapped paths."""
    return NotFound()(environ, start_response)

# Import and initialize badminton app
badminton_app = None
try:
    # Import the badminton Flask app
    from apps.badminton.app import app as badminton_app
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
