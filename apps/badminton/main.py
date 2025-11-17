#!/usr/bin/env python3
"""
Badminton Matchup Manager - CLI Application

Main entry point for the command-line interface.
"""

import sys
from matchup_generator import MatchupGenerator
from game_valuation import GameValuation, PricingStrategy
from match_storage import MatchStorage


class BadmintonCLI:
    def __init__(self):
        self.storage = MatchStorage()
        self.players = []
        self.generator = None
        self.valuator = GameValuation()
        self.current_session_matches = []
    
    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def add_players(self):
        """Add players to the current session."""
        self.print_header("Add Players")
        print("Enter player names (one per line, minimum 4 players)")
        print("Type 'done' when finished:\n")
        
        players = []
        while True:
            name = input(f"Player {len(players) + 1}: ").strip()
            if name.lower() == 'done':
                if len(players) < 4:
                    print("❌ At least 4 players are required!")
                    continue
                break
            if name:
                players.append(name)
        
        self.players = players
        self.generator = MatchupGenerator(players)
        print(f"\n✅ Added {len(players)} players: {', '.join(players)}")
    
    def configure_valuation(self):
        """Configure game valuation settings."""
        self.print_header("Configure Game Valuation")
        
        print("Available pricing strategies:")
        print("1. Fixed - Same price for all games")
        print("2. Escalating - Price increases each game")
        print("3. Winner Takes All - Winner gets the pool")
        print("4. Per Point - Value based on point differential")
        
        choice = input("\nSelect strategy (1-4) [1]: ").strip() or "1"
        
        strategy_map = {
            "1": PricingStrategy.FIXED,
            "2": PricingStrategy.ESCALATING,
            "3": PricingStrategy.WINNER_TAKES_ALL,
            "4": PricingStrategy.PER_POINT
        }
        
        strategy = strategy_map.get(choice, PricingStrategy.FIXED)
        
        base_value = input("Enter base dollar value per game [5.0]: ").strip() or "5.0"
        try:
            base_value = float(base_value)
        except ValueError:
            base_value = 5.0
        
        self.valuator = GameValuation(strategy, base_value)
        print(f"\n✅ Configured {strategy.value} pricing at ${base_value} base value")
    
    def generate_matchups(self):
        """Generate matchups for a session."""
        if not self.generator:
            print("❌ Please add players first!")
            return
        
        self.print_header("Generate Matchups")
        
        duration = input("Session duration in hours [4.0]: ").strip() or "4.0"
        try:
            duration = float(duration)
        except ValueError:
            duration = 4.0
        
        minutes_per_game = input("Minutes per game [15]: ").strip() or "15"
        try:
            minutes_per_game = int(minutes_per_game)
        except ValueError:
            minutes_per_game = 15
        
        matchups = self.generator.generate_session(duration, minutes_per_game)
        self.current_session_matches = matchups
        
        print(f"\n✅ Generated {len(matchups)} games for {duration} hour session\n")
        print(f"{'Game':<6} {'Team 1':<25} {'vs':<4} {'Team 2':<25} {'Value':<10} {'Start'}")
        print("-" * 85)
        
        for match in matchups:
            team1_str = f"{match['team1'][0]} & {match['team1'][1]}"
            team2_str = f"{match['team2'][0]} & {match['team2'][1]}"
            value_info = self.valuator.calculate_value(match['game_number'])
            value = f"${value_info['game_value']:.2f}"
            start_time = f"{match['estimated_start_time']} min"
            
            print(f"{match['game_number']:<6} {team1_str:<25} {'vs':<4} {team2_str:<25} {value:<10} {start_time}")
        
        total = self.valuator.calculate_session_total(len(matchups))
        print(f"\n💰 Total session value: ${total:.2f}")
    
    def record_match(self):
        """Record the result of a match."""
        if not self.current_session_matches:
            print("❌ No active session! Generate matchups first.")
            return
        
        self.print_header("Record Match Result")
        
        game_num = input("Game number: ").strip()
        try:
            game_num = int(game_num)
        except ValueError:
            print("❌ Invalid game number!")
            return
        
        # Find the match
        match = None
        for m in self.current_session_matches:
            if m['game_number'] == game_num:
                match = m
                break
        
        if not match:
            print(f"❌ Game {game_num} not found!")
            return
        
        print(f"\nTeam 1: {' & '.join(match['team1'])}")
        print(f"Team 2: {' & '.join(match['team2'])}")
        
        team1_score = input("\nTeam 1 score: ").strip()
        team2_score = input("Team 2 score: ").strip()
        
        try:
            team1_score = int(team1_score)
            team2_score = int(team2_score)
        except ValueError:
            print("❌ Invalid scores!")
            return
        
        # Calculate game value
        value_info = self.valuator.calculate_value(game_num, team1_score, team2_score)
        
        # Save match
        match_data = {
            'game_number': game_num,
            'team1': match['team1'],
            'team2': match['team2'],
            'team1_score': team1_score,
            'team2_score': team2_score,
            'game_value': value_info['game_value'],
            'winner': 'team1' if team1_score > team2_score else 'team2'
        }
        
        match_id = self.storage.save_match(match_data)
        
        winner_team = match['team1'] if team1_score > team2_score else match['team2']
        print(f"\n✅ Match recorded! ID: {match_id}")
        print(f"🏆 Winners: {' & '.join(winner_team)}")
        print(f"💰 Game value: ${value_info['game_value']:.2f}")
    
    def view_history(self):
        """View match history."""
        self.print_header("Match History")
        
        print("1. Recent matches")
        print("2. All matches")
        print("3. Player statistics")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            matches = self.storage.get_recent_matches(10)
            print(f"\n📜 Last {len(matches)} matches:\n")
            self._display_matches(matches)
        
        elif choice == "2":
            matches = self.storage.get_all_matches()
            print(f"\n📜 All {len(matches)} matches:\n")
            self._display_matches(matches)
        
        elif choice == "3":
            player_name = input("\nEnter player name: ").strip()
            stats = self.storage.get_player_stats(player_name)
            self._display_player_stats(player_name, stats)
        
        else:
            print("❌ Invalid choice!")
    
    def _display_matches(self, matches):
        """Display a list of matches."""
        if not matches:
            print("No matches found.")
            return
        
        print(f"{'Game':<6} {'Team 1':<25} {'Score':<7} {'Team 2':<25} {'Score':<7} {'Value'}")
        print("-" * 85)
        
        for match in matches:
            team1_str = ' & '.join(match.get('team1', []))
            team2_str = ' & '.join(match.get('team2', []))
            score1 = match.get('team1_score', '-')
            score2 = match.get('team2_score', '-')
            value = match.get('game_value', 0.0)
            game_num = match.get('game_number', '-')
            
            print(f"{game_num:<6} {team1_str:<25} {score1:<7} {team2_str:<25} {score2:<7} ${value:.2f}")
    
    def _display_player_stats(self, player_name, stats):
        """Display player statistics."""
        print(f"\n📊 Statistics for {player_name}:\n")
        print(f"Total matches: {stats['total_matches']}")
        print(f"Wins: {stats['wins']}")
        print(f"Losses: {stats['losses']}")
        print(f"Win rate: {stats['win_rate']}%")
        print(f"Total earnings: ${stats['total_earnings']:.2f}")
        print(f"\nPartners: {', '.join(stats['partners']) if stats['partners'] else 'None'}")
        print(f"Opponents: {', '.join(stats['opponents']) if stats['opponents'] else 'None'}")
    
    def show_status(self):
        """Show current session status."""
        self.print_header("Session Status")
        
        if not self.players:
            print("No active session. Add players to begin.")
            return
        
        print(f"Players ({len(self.players)}): {', '.join(self.players)}")
        print(f"Generated matches: {len(self.current_session_matches)}")
        print(f"Pricing strategy: {self.valuator.strategy.value}")
        print(f"Base value: ${self.valuator.base_value:.2f}")
        
        if self.generator:
            stats = self.generator.get_stats()
            print(f"\nPartnership count: {len(stats['partnerships'])}")
    
    def main_menu(self):
        """Display and handle the main menu."""
        while True:
            self.print_header("Badminton Matchup Manager")
            
            print("1. Add players")
            print("2. Configure valuation")
            print("3. Generate matchups")
            print("4. Record match result")
            print("5. View history")
            print("6. Session status")
            print("7. Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                self.add_players()
            elif choice == "2":
                self.configure_valuation()
            elif choice == "3":
                self.generate_matchups()
            elif choice == "4":
                self.record_match()
            elif choice == "5":
                self.view_history()
            elif choice == "6":
                self.show_status()
            elif choice == "7":
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice! Please select 1-7.")
            
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    cli = BadmintonCLI()
    try:
        cli.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
