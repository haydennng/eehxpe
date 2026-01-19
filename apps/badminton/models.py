"""
Database Models for Badminton Matchup Manager

SQLAlchemy ORM models for users, sessions, matches, and player statistics.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(enum.Enum):
    """User role enumeration"""
    PLAYER = "player"
    ADMIN = "admin"


class User(Base):
    """User model for player accounts and authentication"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.PLAYER)
    mmr = Column(Float, nullable=False, default=1500.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches_as_team1_player1 = relationship('Match', foreign_keys='Match.team1_player1_id', back_populates='team1_player1')
    matches_as_team1_player2 = relationship('Match', foreign_keys='Match.team1_player2_id', back_populates='team1_player2')
    matches_as_team2_player1 = relationship('Match', foreign_keys='Match.team2_player1_id', back_populates='team2_player1')
    matches_as_team2_player2 = relationship('Match', foreign_keys='Match.team2_player2_id', back_populates='team2_player2')
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}', mmr={self.mmr})>"
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role.value,
            'mmr': self.mmr,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
        return data
    
    # Flask-Login integration
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)


class Session(Base):
    """Session model for tracking game sessions"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    session_date = Column(DateTime, nullable=False, index=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    matches = relationship('Match', back_populates='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Session(id={self.id}, date='{self.session_date}', matches={len(self.matches)})>"
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'session_date': self.session_date.isoformat() if self.session_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'match_count': len(self.matches) if self.matches else 0
        }


class Match(Base):
    """Match model for tracking individual games"""
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False, index=True)
    game_number = Column(Integer, nullable=False)
    
    # Team 1 players
    team1_player1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    team1_player2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Team 2 players
    team2_player1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    team2_player2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Scores
    team1_score = Column(Integer, nullable=False)
    team2_score = Column(Integer, nullable=False)
    
    # Game value and winner
    game_value = Column(Float, nullable=False, default=0.0)
    winner_team = Column(Integer, nullable=False)  # 1 or 2
    
    # MMR tracking
    mmr_change = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    session = relationship('Session', back_populates='matches')
    team1_player1 = relationship('User', foreign_keys=[team1_player1_id], back_populates='matches_as_team1_player1')
    team1_player2 = relationship('User', foreign_keys=[team1_player2_id], back_populates='matches_as_team1_player2')
    team2_player1 = relationship('User', foreign_keys=[team2_player1_id], back_populates='matches_as_team2_player1')
    team2_player2 = relationship('User', foreign_keys=[team2_player2_id], back_populates='matches_as_team2_player2')
    
    def __repr__(self):
        return f"<Match(id={self.id}, game={self.game_number}, winner_team={self.winner_team}, mmr_change={self.mmr_change})>"
    
    def to_dict(self):
        """Convert match to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'game_number': self.game_number,
            'team1': {
                'player1': self.team1_player1.to_dict() if self.team1_player1 else None,
                'player2': self.team1_player2.to_dict() if self.team1_player2 else None,
                'score': self.team1_score
            },
            'team2': {
                'player1': self.team2_player1.to_dict() if self.team2_player1 else None,
                'player2': self.team2_player2.to_dict() if self.team2_player2 else None,
                'score': self.team2_score
            },
            'game_value': self.game_value,
            'winner_team': self.winner_team,
            'mmr_change': self.mmr_change,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_player_ids(self):
        """Get all player IDs involved in this match"""
        return [
            self.team1_player1_id,
            self.team1_player2_id,
            self.team2_player1_id,
            self.team2_player2_id
        ]
    
    def is_player_in_match(self, user_id):
        """Check if a user was in this match"""
        return user_id in self.get_player_ids()
    
    def did_player_win(self, user_id):
        """Check if a player won this match"""
        if not self.is_player_in_match(user_id):
            return False
        
        if self.winner_team == 1:
            return user_id in [self.team1_player1_id, self.team1_player2_id]
        else:
            return user_id in [self.team2_player1_id, self.team2_player2_id]
