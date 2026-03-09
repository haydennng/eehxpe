"""
Migrate all existing UTC timestamps in the database to Pacific time.

Existing records were stored with datetime.utcnow(), so they are in UTC.
This script converts them to America/Los_Angeles (Pacific) time so they
are consistent with the new _now_pacific() default.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from zoneinfo import ZoneInfo
from database import init_db, session_scope
from models import User, Session, Match

UTC = ZoneInfo('UTC')
PACIFIC = ZoneInfo('America/Los_Angeles')


def utc_to_pacific(dt):
    """Convert a naive UTC datetime to a naive Pacific datetime."""
    if dt is None:
        return None
    # Treat the naive datetime as UTC, convert to Pacific, strip tzinfo
    aware_utc = dt.replace(tzinfo=UTC)
    aware_pacific = aware_utc.astimezone(PACIFIC)
    return aware_pacific.replace(tzinfo=None)


def migrate():
    init_db()

    with session_scope() as db:
        # Migrate Users
        users = db.query(User).all()
        print(f"Migrating {len(users)} users...")
        for u in users:
            u.created_at = utc_to_pacific(u.created_at)
            u.updated_at = utc_to_pacific(u.updated_at)

        # Migrate Sessions
        sessions = db.query(Session).all()
        print(f"Migrating {len(sessions)} sessions...")
        for s in sessions:
            s.created_at = utc_to_pacific(s.created_at)
            # session_date is just a date marker (midnight), leave it alone

        # Migrate Matches
        matches = db.query(Match).all()
        print(f"Migrating {len(matches)} matches...")
        for m in matches:
            m.created_at = utc_to_pacific(m.created_at)

        # Commit happens automatically via session_scope context manager

    print("Done! All timestamps converted from UTC to Pacific.")


if __name__ == '__main__':
    # Show a preview first
    print("Preview of changes:")
    with session_scope() as db:
        sample = db.query(Match).order_by(Match.created_at).first()
        if sample:
            old = sample.created_at
            new = utc_to_pacific(old)
            print(f"  Example match: {old} (UTC) -> {new} (Pacific)")

    confirm = input("\nProceed with migration? (y/n): ").strip().lower()
    if confirm == 'y':
        migrate()
    else:
        print("Aborted.")
