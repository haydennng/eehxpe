"""
Game Valuation System for Badminton Matches

This module assigns dollar values to games with various pricing strategies.
"""

from typing import Dict, List
from enum import Enum


class PricingStrategy(Enum):
    """Available pricing strategies for games."""
    FIXED = "fixed"  # Same price for all games
    ESCALATING = "escalating"  # Price increases each game
    WINNER_TAKES_ALL = "winner_takes_all"  # Winner gets the pool
    PER_POINT = "per_point"  # Value based on point differential


class GameValuation:
    def __init__(self, strategy: PricingStrategy = PricingStrategy.FIXED, 
                 base_value: float = 5.0):
        """
        Initialize the game valuation system.
        
        Args:
            strategy: Pricing strategy to use
            base_value: Base dollar value for games
        """
        self.strategy = strategy
        self.base_value = base_value
        
    def calculate_value(self, game_number: int, 
                       team1_score: int = None, 
                       team2_score: int = None) -> Dict[str, float]:
        """
        Calculate the dollar value for a game.
        
        Args:
            game_number: Sequential game number
            team1_score: Optional score for team 1
            team2_score: Optional score for team 2
            
        Returns:
            Dictionary with game value information
        """
        if self.strategy == PricingStrategy.FIXED:
            return self._fixed_value(game_number)
        elif self.strategy == PricingStrategy.ESCALATING:
            return self._escalating_value(game_number)
        elif self.strategy == PricingStrategy.WINNER_TAKES_ALL:
            return self._winner_takes_all(team1_score, team2_score)
        elif self.strategy == PricingStrategy.PER_POINT:
            return self._per_point_value(team1_score, team2_score)
        else:
            return self._fixed_value(game_number)
    
    def _fixed_value(self, game_number: int) -> Dict[str, float]:
        """Fixed value for all games."""
        return {
            'game_value': self.base_value,
            'team1_stake': self.base_value / 2,
            'team2_stake': self.base_value / 2,
            'winner_receives': self.base_value
        }
    
    def _escalating_value(self, game_number: int) -> Dict[str, float]:
        """Value increases with each game."""
        multiplier = 1 + (game_number - 1) * 0.1  # 10% increase per game
        game_value = self.base_value * multiplier
        return {
            'game_value': round(game_value, 2),
            'team1_stake': round(game_value / 2, 2),
            'team2_stake': round(game_value / 2, 2),
            'winner_receives': round(game_value, 2)
        }
    
    def _winner_takes_all(self, team1_score: int, team2_score: int) -> Dict[str, float]:
        """Winner takes the entire pool."""
        total_pool = self.base_value
        
        if team1_score is None or team2_score is None:
            return {
                'game_value': total_pool,
                'team1_stake': total_pool / 2,
                'team2_stake': total_pool / 2,
                'winner_receives': total_pool
            }
        
        winner_amount = total_pool if team1_score != team2_score else total_pool / 2
        return {
            'game_value': total_pool,
            'team1_stake': total_pool / 2,
            'team2_stake': total_pool / 2,
            'winner_receives': winner_amount,
            'team1_won': team1_score > team2_score
        }
    
    def _per_point_value(self, team1_score: int, team2_score: int) -> Dict[str, float]:
        """Value based on point differential."""
        if team1_score is None or team2_score is None:
            return {
                'game_value': self.base_value,
                'team1_stake': self.base_value / 2,
                'team2_stake': self.base_value / 2,
                'value_per_point': self.base_value / 21  # Standard badminton game to 21
            }
        
        point_diff = abs(team1_score - team2_score)
        value_per_point = self.base_value / 21
        bonus = point_diff * value_per_point
        total_value = self.base_value + bonus
        
        return {
            'game_value': round(total_value, 2),
            'team1_stake': self.base_value / 2,
            'team2_stake': self.base_value / 2,
            'point_differential': point_diff,
            'bonus_amount': round(bonus, 2),
            'winner_receives': round(total_value, 2),
            'team1_won': team1_score > team2_score
        }
    
    def calculate_session_total(self, num_games: int) -> float:
        """
        Calculate total dollar amount for a session.
        
        Args:
            num_games: Number of games in the session
            
        Returns:
            Total dollar value
        """
        if self.strategy == PricingStrategy.FIXED:
            return self.base_value * num_games
        elif self.strategy == PricingStrategy.ESCALATING:
            total = sum(self.base_value * (1 + (i - 1) * 0.1) 
                       for i in range(1, num_games + 1))
            return round(total, 2)
        else:
            return self.base_value * num_games
    
    def set_strategy(self, strategy: PricingStrategy):
        """Change the pricing strategy."""
        self.strategy = strategy
    
    def set_base_value(self, value: float):
        """Change the base value."""
        if value <= 0:
            raise ValueError("Base value must be positive")
        self.base_value = value
