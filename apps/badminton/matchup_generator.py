"""
Matchup Generator for Fair 2v2 Badminton Games

This module generates balanced matchups ensuring:
- Equal playing time (minimizes players sitting out multiple times) - HIGHEST PRIORITY
- Players rotate partners evenly - SECOND PRIORITY
- Players face different opponents - THIRD PRIORITY
- Fair distribution across multiple games
"""

import itertools
from typing import List, Tuple, Optional, Set
from collections import defaultdict

# Scoring weights for matchup priority (lower scores are better)
# These weights determine the priority order when selecting matchups:
# 1. Equal playing time (sit-out balance) - dominant factor   (~1000+ per extra sit-out)
# 2. MMR strategy (competitive vs balanced)   - primary after sit-out  (~20-100 per 100 MMR diff)
# 3. Partnership variety (new partners)       - secondary              (~5-25)
# 4. Opponent variety                         - tertiary tie-breaker   (~0-32)
SITOUT_WEIGHT = 100
PARTNERSHIP_WEIGHT = 5
OPPONENT_WEIGHT = 4
# Weight applied to per-team MMR difference when scoring competitive/balanced scenarios.
# A 200-MMR diff contributes 200 * 0.2 = 40, sitting above partnership (5-25) and
# below sit-out penalties (1000+), so strategy is the primary post-sitout differentiator.
MMR_STRATEGY_WEIGHT = 0.2


class MatchupGenerator:
    def __init__(self, players: List[str]):
        """
        Initialize the matchup generator with a list of players.
        
        Args:
            players: List of player names (minimum 4 required)
        """
        if len(players) < 4:
            raise ValueError("At least 4 players are required for 2v2 matches")
        
        self.players = players
        self.partnership_count = defaultdict(int)
        self.opponent_count = defaultdict(int)
        self.sitout_count = defaultdict(int)  # Track how many times each player sits out
        
    def _get_pair_key(self, player1: str, player2: str) -> Tuple[str, str]:
        """Create a sorted tuple key for a pair of players."""
        return tuple(sorted([player1, player2]))
    
    def _score_matchup(self, team1: Tuple[str, str], team2: Tuple[str, str],
                        all_playing: Optional[Set[str]] = None,
                        include_sitout: bool = True) -> float:
        """
        Score a potential matchup based on how balanced it is.
        Lower scores are better.

        Args:
            team1: Players on team 1.
            team2: Players on team 2.
            all_playing: Full set playing across ALL courts. When provided, sit-outs
                         are computed against this set (not just the 4 on this court).
            include_sitout: Set False when sit-out penalty is being computed once
                            at the round level (multi-court) to avoid double-counting.
        """
        p1, p2 = team1
        p3, p4 = team2
        playing_players = {p1, p2, p3, p4}
        effective_playing = all_playing if all_playing is not None else playing_players

        partnership_score = (
            self.partnership_count[self._get_pair_key(p1, p2)] +
            self.partnership_count[self._get_pair_key(p3, p4)]
        )

        opponent_score = (
            self.opponent_count[self._get_pair_key(p1, p3)] +
            self.opponent_count[self._get_pair_key(p1, p4)] +
            self.opponent_count[self._get_pair_key(p2, p3)] +
            self.opponent_count[self._get_pair_key(p2, p4)]
        )

        sitout_score = 0
        if include_sitout:
            for player in set(self.players) - effective_playing:
                sitout_count = self.sitout_count[player]
                if sitout_count == 1:
                    sitout_score += 10
                elif sitout_count > 1:
                    sitout_score += 50 * (sitout_count - 1)

        return (sitout_score * SITOUT_WEIGHT +
                partnership_score * PARTNERSHIP_WEIGHT +
                opponent_score * OPPONENT_WEIGHT)
    
    def _update_history(self, team1: Tuple[str, str], team2: Tuple[str, str],
                        all_playing: Optional[Set[str]] = None,
                        update_sitouts: bool = True):
        """Update partnership, opponent, and sit-out history after a match.

        Args:
            team1: Players on team 1 of this court.
            team2: Players on team 2 of this court.
            all_playing: Full set of players active across ALL courts this round.
                         When provided, sit-outs are computed against this set so
                         players on other courts are not wrongly counted as sitters.
            update_sitouts: Set False on subsequent courts in a multi-court round so
                            sit-outs are only counted once per round (on the first call).
        """
        p1, p2 = team1
        p3, p4 = team2

        # Update partnerships
        self.partnership_count[self._get_pair_key(p1, p2)] += 1
        self.partnership_count[self._get_pair_key(p3, p4)] += 1

        # Update opponents
        self.opponent_count[self._get_pair_key(p1, p3)] += 1
        self.opponent_count[self._get_pair_key(p1, p4)] += 1
        self.opponent_count[self._get_pair_key(p2, p3)] += 1
        self.opponent_count[self._get_pair_key(p2, p4)] += 1

        if update_sitouts:
            effective_playing = all_playing if all_playing is not None else {p1, p2, p3, p4}
            for player in set(self.players) - effective_playing:
                self.sitout_count[player] += 1
    
    def generate_matchup(self) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        """
        Generate a single fair matchup.
        
        Returns:
            Tuple of two teams, each team is a tuple of two player names
        """
        # Get all possible team combinations
        all_teams = list(itertools.combinations(self.players, 2))
        
        best_matchup = None
        best_score = float('inf')
        
        # Try all possible matchups
        for team1 in all_teams:
            remaining_players = [p for p in self.players if p not in team1]
            for team2 in itertools.combinations(remaining_players, 2):
                score = self._score_matchup(team1, team2)
                if score < best_score:
                    best_score = score
                    best_matchup = (team1, team2)
        
        if best_matchup:
            self._update_history(best_matchup[0], best_matchup[1])
        
        return best_matchup
    
    def generate_session(self, duration_hours: float, minutes_per_game: int = 15) -> List[dict]:
        """
        Generate matchups for an entire session.
        
        Args:
            duration_hours: Total session duration in hours
            minutes_per_game: Average time per game in minutes
            
        Returns:
            List of matchup dictionaries with team and game info
        """
        total_minutes = duration_hours * 60
        num_games = int(total_minutes / minutes_per_game)
        
        matchups = []
        for game_num in range(1, num_games + 1):
            team1, team2 = self.generate_matchup()
            matchups.append({
                'game_number': game_num,
                'team1': list(team1),
                'team2': list(team2),
                'estimated_start_time': (game_num - 1) * minutes_per_game
            })
        
        return matchups
    
    def seed_from_matches(self, matches: List[dict]):
        """
        Seed partnership, opponent, and sit-out history from previously played matches.
        Call this after creating a generator to replay session history so the generator
        has accurate state when the app restarts mid-session.

        Args:
            matches: List of match dicts with 'team1' (list of 2 names) and
                     'team2' (list of 2 names) keys.
        """
        for match in matches:
            team1 = tuple(match['team1'])
            team2 = tuple(match['team2'])
            self._update_history(team1, team2)

    def generate_paired_scenarios(self, num_courts: int,
                                   n_scenarios: int = 2) -> List[List[dict]]:
        """
        Generate n_scenarios complete scenarios that distribute all session players
        across num_courts courts simultaneously, with no player on two courts at once.

        Each scenario is a list of num_courts matchup dicts:
            [{'team1': ['A','B'], 'team2': ['C','D']},   # Court 1
             {'team1': ['E','F'], 'team2': ['G','H']}]   # Court 2

        Scenarios are ranked by total score across all courts so the algorithm
        optimises the full round, not each court in isolation.

        Args:
            num_courts: Number of courts to generate matchups for.
            n_scenarios: Number of distinct scenario options to return (default 2).

        Returns:
            List of up to n_scenarios scenarios. Each scenario is a list of
            matchup dicts (one per court), ordered Court 1 … Court num_courts.
        """
        players = list(self.players)
        players_needed = 4 * num_courts

        # Shrink num_courts until we have enough players
        while players_needed > len(players) and num_courts > 0:
            num_courts -= 1
            players_needed = 4 * num_courts

        if num_courts == 0:
            return []

        all_scored: List[Tuple[float, list]] = []

        # Enumerate every possible playing set (handles sit-outs automatically)
        for playing_tuple in itertools.combinations(players, players_needed):
            playing_list = list(playing_tuple)
            all_playing_set = set(playing_list)
            self._enumerate_court_assignments(
                playing_list, num_courts, [], all_scored, all_playing_set
            )

        # Sort ascending (lower score = better)
        all_scored.sort(key=lambda x: x[0])

        # Return top n_scenarios, deduplicating by canonical form
        result = []
        seen: Set[tuple] = set()
        for _, assignment in all_scored:
            if len(result) >= n_scenarios:
                break
            # Canonical form: for each court use frozenset of both team
            # frozensets so that (A+B vs C+D) and (C+D vs A+B) are treated
            # as the same matchup and correctly deduplicated.
            canonical = tuple(
                frozenset([frozenset(t1), frozenset(t2)])
                for t1, t2 in assignment
            )
            if canonical not in seen:
                seen.add(canonical)
                result.append([
                    {'team1': list(t1), 'team2': list(t2)}
                    for t1, t2 in assignment
                ])

        return result

    def _enumerate_court_assignments(
        self,
        remaining: List[str],
        courts_left: int,
        current: list,
        results: list,
        all_playing: Set[str],
    ):
        """
        Recursively enumerate all ways to assign `remaining` players to
        `courts_left` courts (4 players per court, 2v2).
        """
        if courts_left == 0:
            # Sit-out penalty computed once for the whole round, not per court
            sitout_score = 0
            for player in set(self.players) - all_playing:
                c = self.sitout_count[player]
                if c == 1:
                    sitout_score += 10
                elif c > 1:
                    sitout_score += 50 * (c - 1)

            # Per-court: partnership + opponent variety only (no sit-out)
            court_score = sum(
                self._score_matchup(t1, t2, all_playing=all_playing, include_sitout=False)
                for t1, t2 in current
            )
            results.append((sitout_score * SITOUT_WEIGHT + court_score, list(current)))
            return

        for team1 in itertools.combinations(remaining, 2):
            after_t1 = [p for p in remaining if p not in team1]
            for team2 in itertools.combinations(after_t1, 2):
                used = set(team1) | set(team2)
                left = [p for p in remaining if p not in used]
                current.append((team1, team2))
                self._enumerate_court_assignments(
                    left, courts_left - 1, current, results, all_playing
                )
                current.pop()

    def generate_competitive_balanced_scenarios(
        self,
        num_courts: int,
        player_mmrs: dict,
    ) -> dict:
        """
        Generate one scenario per mode (competitive, balanced, random).

        Priority order (same as the main algorithm):
          sit-out balance  >>  MMR strategy  >  partnership variety  >  opponent variety
        """
        players = list(self.players)
        players_needed = 4 * num_courts

        while players_needed > len(players) and num_courts > 0:
            num_courts -= 1
            players_needed = 4 * num_courts

        if num_courts == 0:
            return {'competitive': [], 'balanced': [], 'random': []}

        def get_mmr(name: str) -> float:
            return float(player_mmrs.get(name, 1500.0))

        def avg_opponent_mmr_for_top(t1: tuple, t2: tuple) -> float:
            court_players = list(t1) + list(t2)
            top = max(court_players, key=get_mmr)
            opp_team = t2 if top in t1 else t1
            return sum(get_mmr(p) for p in opp_team) / len(opp_team)

        def avg_team_mmr_diff(t1: tuple, t2: tuple) -> float:
            avg1 = sum(get_mmr(p) for p in t1) / len(t1)
            avg2 = sum(get_mmr(p) for p in t2) / len(t2)
            return abs(avg1 - avg2)

        def score_full(playing_list: list, assignment: list, strategy: str) -> float:
            all_playing = set(playing_list)
            sitting = set(players) - all_playing

            # ── Sit-out penalty (dominant) ──────────────────────────────────
            sitout_score = 0
            for p in sitting:
                c = self.sitout_count[p]
                if c == 1:
                    sitout_score += 10
                elif c > 1:
                    sitout_score += 50 * (c - 1)

            # ── Strategy-level score ────────────────────────────────────────
            detail_score = 0.0

            if strategy == 'competitive':
                if len(assignment) > 1:
                    court_avgs = [
                        sum(get_mmr(p) for p in list(t1) + list(t2)) / 4.0
                        for t1, t2 in assignment
                    ]
                    overall_mean = sum(court_avgs) / len(court_avgs)
                    inter_court_var = sum(
                        (avg - overall_mean) ** 2 for avg in court_avgs
                    )
                    detail_score -= inter_court_var * 0.02
                else:
                    t1, t2 = assignment[0]
                    detail_score -= avg_opponent_mmr_for_top(t1, t2) * MMR_STRATEGY_WEIGHT

            # ── Per-court: within-court balance + history ───────────────────
            for t1, t2 in assignment:
                if strategy in ('competitive', 'balanced'):
                    detail_score += avg_team_mmr_diff(t1, t2) * MMR_STRATEGY_WEIGHT

                detail_score += (
                    self.partnership_count[self._get_pair_key(t1[0], t1[1])] +
                    self.partnership_count[self._get_pair_key(t2[0], t2[1])]
                ) * PARTNERSHIP_WEIGHT

                for a in t1:
                    for b in t2:
                        detail_score += (
                            self.opponent_count[self._get_pair_key(a, b)] * OPPONENT_WEIGHT
                        )

            return sitout_score * SITOUT_WEIGHT + detail_score

        all_comp_scored: List[Tuple[float, list]] = []
        all_bal_scored:  List[Tuple[float, list]] = []
        all_rand_scored: List[Tuple[float, list]] = []

        for playing_tuple in itertools.combinations(players, players_needed):
            playing_list = list(playing_tuple)
            all_playing_set = set(playing_list)

            all_arrangements: List[Tuple[float, list]] = []
            self._enumerate_court_assignments(
                playing_list, num_courts, [], all_arrangements, all_playing_set
            )

            for _, assignment in all_arrangements:
                all_comp_scored.append((score_full(playing_list, assignment, 'competitive'), assignment))
                all_bal_scored.append((score_full(playing_list, assignment, 'balanced'),   assignment))
                all_rand_scored.append((score_full(playing_list, assignment, 'random'),    assignment))

        all_comp_scored.sort(key=lambda x: x[0])
        all_bal_scored.sort(key=lambda x: x[0])
        all_rand_scored.sort(key=lambda x: x[0])

        def pick_top_1(scored: list) -> List[dict]:
            seen: Set[tuple] = set()
            for _, assignment in scored:
                canonical = tuple(
                    frozenset([frozenset(t1), frozenset(t2)])
                    for t1, t2 in assignment
                )
                if canonical not in seen:
                    seen.add(canonical)
                    return [{'team1': list(t1), 'team2': list(t2)} for t1, t2 in assignment]
            return []

        return {
            'competitive': pick_top_1(all_comp_scored),
            'balanced':    pick_top_1(all_bal_scored),
            'random':      pick_top_1(all_rand_scored),
        }

    def reset_history(self):
        """Reset partnership, opponent, and sit-out tracking."""
        self.partnership_count.clear()
        self.opponent_count.clear()
        self.sitout_count.clear()

    def get_stats(self) -> dict:
        """Get current statistics about partnerships, matchups, and sit-outs."""
        return {
            'partnerships': dict(self.partnership_count),
            'opponents': dict(self.opponent_count),
            'sitouts': dict(self.sitout_count)
        }
