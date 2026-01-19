#!/usr/bin/env python3
"""
Database Initialization Script

Creates all database tables and seeds initial admin user.
Run this script once to set up the database for the first time.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from auth import create_user
from models import UserRole


def initialize_database():
    """Initialize database tables and create admin user"""
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)
    
    # Initialize database and create tables
    print("\n1. Creating database tables...")
    db = init_db()
    print("✅ Database tables created successfully")
    
    # Create admin user
    print("\n2. Creating admin user...")
    try:
        admin = create_user(
            username="admin",
            password="watermelon",  # Default password - CHANGE THIS IN PRODUCTION!
            role=UserRole.ADMIN,
            mmr=1500.0
        )
        print(f"✅ Admin user created: {admin.username} (ID: {admin.id})")
        print("   ⚠️  Default password: watermelon")
        print("   ⚠️  IMPORTANT: Change this password after first login!")
    except ValueError as e:
        print(f"⚠️  Admin user already exists: {e}")
    
    print("\n" + "=" * 60)
    print("Database initialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If you have existing JSON data, run: python migrations/migrate_json_to_db.py")
    print("2. Start the development server: .\\dev.ps1")
    print("3. Login with username 'admin' and password 'watermelon'")
    print("4. Change the admin password immediately!")
    print()


if __name__ == "__main__":
    try:
        initialize_database()
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
