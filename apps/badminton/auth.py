"""
Authentication Module

Handles password hashing, user verification, and authentication decorators.
"""

from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from models import User, UserRole
from database import session_scope

# Initialize password hasher
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password_hash: The hashed password from database
        password: Plain text password to verify
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        ph.verify(password_hash, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def check_password_needs_rehash(password_hash: str) -> bool:
    """
    Check if a password hash needs to be rehashed (e.g., after updating security params).
    
    Args:
        password_hash: The hashed password
        
    Returns:
        True if rehashing is needed
    """
    return ph.check_needs_rehash(password_hash)


def authenticate_user(username: str, password: str) -> User:
    """
    Authenticate a user by username and password.
    
    Args:
        username: User's username
        password: User's plain text password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    with session_scope() as session:
        user = session.query(User).filter_by(username=username).first()
        
        if user is None:
            return None
        
        if not verify_password(user.password_hash, password):
            return None
        
        # Check if password needs rehashing
        if check_password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            # Session will auto-commit on exit
        
        # Detach user from session so it can be used outside context
        session.expunge(user)
        return user


def create_user(username: str, password: str, role: UserRole = UserRole.PLAYER, mmr: float = 1500.0) -> User:
    """
    Create a new user account.
    
    Args:
        username: Desired username (must be unique)
        password: Plain text password
        role: User role (default: PLAYER)
        mmr: Initial MMR (default: 1500.0)
        
    Returns:
        Created User object
        
    Raises:
        ValueError: If username already exists
    """
    with session_scope() as session:
        # Check if username exists
        existing_user = session.query(User).filter_by(username=username).first()
        if existing_user:
            raise ValueError(f"Username '{username}' already exists")
        
        # Create new user
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            mmr=mmr
        )
        
        session.add(user)
        session.flush()  # Get the ID assigned
        
        # Detach from session
        session.expunge(user)
        return user


def get_user_by_id(user_id: int) -> User:
    """
    Get a user by their ID.
    
    Args:
        user_id: User's ID
        
    Returns:
        User object or None if not found
    """
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            session.expunge(user)
        return user


def get_user_by_username(username: str) -> User:
    """
    Get a user by their username.
    
    Args:
        username: User's username
        
    Returns:
        User object or None if not found
    """
    with session_scope() as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            session.expunge(user)
        return user


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    """
    Change a user's password.
    
    Args:
        user_id: User's ID
        current_password: User's current password for verification
        new_password: New password to set
        
    Returns:
        True if password was changed successfully, False if current password is incorrect
        
    Raises:
        ValueError: If user not found
    """
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        
        if user is None:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Verify current password
        if not verify_password(user.password_hash, current_password):
            return False
        
        # Set new password
        user.password_hash = hash_password(new_password)
        # Session will auto-commit on exit
        return True


# Flask decorators for route protection
def login_required(f):
    """
    Decorator to require authentication for a route.
    Redirects to login page if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin role for a route.
    Returns 403 if user is not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        if current_user.role != UserRole.ADMIN:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index')), 403
        
        return f(*args, **kwargs)
    return decorated_function


def admin_or_self_required(f):
    """
    Decorator to require admin role OR accessing own resource.
    Useful for profile endpoints where users can view/edit their own data.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        # Check if accessing own resource
        user_id = kwargs.get('user_id') or request.view_args.get('user_id')
        if user_id is not None:
            if current_user.id == int(user_id) or current_user.role == UserRole.ADMIN:
                return f(*args, **kwargs)
            else:
                flash('Access denied.', 'danger')
                return redirect(url_for('index')), 403
        
        # No user_id specified, require admin
        if current_user.role != UserRole.ADMIN:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index')), 403
        
        return f(*args, **kwargs)
    return decorated_function
