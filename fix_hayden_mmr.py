#!/usr/bin/env python3
"""Fix Hayden's corrupted MMR value"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'badminton'))

from database import session_scope
from models import User

print("Fixing Hayden's MMR...")

with session_scope() as session:
    hayden = session.query(User).filter_by(username='Hayden').first()
    
    if not hayden:
        print("Hayden not found!")
        sys.exit(1)
    
    print(f"Current MMR: {hayden.mmr}")
    
    # Set to correct value
    hayden.mmr = 1694.91
    
    session.commit()
    
    print(f"Fixed MMR to: {hayden.mmr}")
    print("✓ Done!")
