"""
Database Connection and Session Management

Handles SQLAlchemy database initialization and session management.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from models import Base

# Default database URL (can be overridden by environment variable)
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'badminton' / 'badminton.db'


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url=None):
        """
        Initialize database connection.
        
        Args:
            database_url: SQLAlchemy database URL (e.g., sqlite:///path/to/db.db)
                         If None, uses DATABASE_URL env var or default path
        """
        if database_url is None:
            database_url = os.environ.get('DATABASE_URL')
        
        if database_url is None:
            # Construct default SQLite URL
            db_path = DEFAULT_DB_PATH
            db_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f'sqlite:///{db_path}'
        
        self.database_url = database_url
        
        # Create engine
        # For SQLite, we use NullPool to avoid connection caching issues
        if database_url.startswith('sqlite'):
            self.engine = create_engine(
                database_url,
                connect_args={'check_same_thread': False},
                poolclass=NullPool,
                echo=False  # Set to True for SQL debugging
            )
        else:
            self.engine = create_engine(database_url, echo=False)
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(self.engine)
        # Expire all cached instances to force fresh loads
        try:
            self.Session.expire_all()
        except:
            pass
        print(f"Database tables created at: {self.database_url}")
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)
        print("All database tables dropped")
    
    def get_session(self):
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy session object
        """
        return self.Session()
    
    def close_session(self):
        """Close the scoped session"""
        self.Session.remove()


# Global database instance
_db_instance = None


def get_db():
    """
    Get the global database instance.
    Creates it if it doesn't exist.
    
    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        # Auto-initialize if not already done
        print("Warning: Database accessed before init_db() was called. Auto-initializing...")
        _db_instance = Database()
        _db_instance.create_tables()
    return _db_instance


def init_db(database_url=None):
    """
    Initialize the database with tables.
    
    Args:
        database_url: Optional database URL to use
    """
    global _db_instance
    # Force recreate instance to clear any cached metadata
    if _db_instance is not None:
        try:
            _db_instance.close_session()
        except:
            pass
    _db_instance = Database(database_url)
    _db_instance.create_tables()
    return _db_instance


def get_session():
    """
    Get a database session from the global instance.
    
    Returns:
        SQLAlchemy session
    """
    return get_db().get_session()


# Context manager for session handling
class SessionContext:
    """Context manager for database sessions with automatic commit/rollback"""
    
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        self.session = get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred, rollback
            self.session.rollback()
        else:
            # No exception, commit
            self.session.commit()
        self.session.close()
        return False  # Don't suppress exceptions


def session_scope():
    """
    Provide a transactional scope for database operations.
    
    Usage:
        with session_scope() as session:
            user = session.query(User).first()
            user.mmr = 1600
    """
    return SessionContext()
