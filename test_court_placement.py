"""
Court Placement Test — 12 games across 2 courts with 8 players.

Mixes competitive / balanced / random recommendations in each session.
Runs the session 5 times and reports partnership distribution + games-played
per player so we can see whether:
  - partnerships are spread out evenly (low variance)
  - each player plays a similar number of games (here: always 12 since no sit-outs)
"""

import os
import sys
import random
from collections import Counter, defaultdict

# Make the badminton app importable
BADMINTON_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "apps", "badminton"
)
sys.path.insert(0, BADMINTON_DIR)

from matchup_generator import MatchupGenerator  # noqa: E402


# --- Player pool (snapshot of current MMRs from badminton.db) ---
PLAYERS_MMR = {
    "Maric":   1831.47,
    "Jonny":   1725.63,
    "Danny":   1580.94,
    "Hayden":  1545.45,
    "Brendon": 1534.32,
    "Felix":   1497.77,
    "Phi":     1450.49,
    "Bryan":   1429.91,
}
PLAYERS = list(PLAYERS_MMR.keys())

NUM_GAMES = 12
NUM_COURTS = 2


def make_strategy_sequence(seed: int) -> list:
    """Return a 12-item list of strategy names, 4 each, shuffled by seed."""
    base = ["competitive"] * 4 + ["balanced"] * 4 + ["random"] * 4
    rng = random.Random(seed)
    rng.shuffle(base)
    return base


def run_session(seed: int) -> dict:
    """Simulate one 12-game session with mixed strategies. Return stats."""
    rng = random.Random(seed * 1000 + 7)
    gen = MatchupGenerator(PLAYERS)
    strategies = make_strategy_sequence(seed)

    games_played = Counter()
    partnerships = Counter()
    opponents = Counter()
    strategy_games = defaultdict(int)
    game_log = []

    for game_idx, strategy in enumerate(strategies, start=1):
        scenarios = gen.generate_competitive_balanced_scenarios(
            num_courts=NUM_COURTS, player_mmrs=PLAYERS_MMR
        )
        options = scenarios[strategy]
        if not options:
            raise RuntimeError(f"No {strategy} options returned")
        # Pick randomly from the top options so runs differ
        chosen = rng.choice(options)

        # Record + apply history
        court_rows = []
        for court_num, match in enumerate(chosen, start=1):
            t1 = tuple(match["team1"])
            t2 = tuple(match["team2"])
            gen._update_history(t1, t2)

            for p in t1 + t2:
                games_played[p] += 1
            partnerships[tuple(sorted(t1))] += 1
            partnerships[tuple(sorted(t2))] += 1
            for a in t1:
                for b in t2:
                    opponents[tuple(sorted([a, b]))] += 1

            court_rows.append((court_num, t1, t2))

        strategy_games[strategy] += 1
        game_log.append((game_idx, strategy, court_rows))

    return {
        "strategies": strategies,
        "games_played": games_played,
        "partnerships": partnerships,
        "opponents": opponents,
        "strategy_games": strategy_games,
        "game_log": game_log,
    }


def fmt_pair(pair):
    return f"{pair[0]}+{pair[1]}"


def print_run(run_num: int, stats: dict):
    print(f"\n{'='*78}")
    print(f"RUN {run_num}")
    print("=" * 78)

    # Game log
    print("\nGame log (strategy | Court 1 | Court 2):")
    for game_idx, strategy, courts in stats["game_log"]:
        c1 = courts[0]
        c2 = courts[1] if len(courts) > 1 else None
        c1_str = f"{fmt_pair(c1[1])} vs {fmt_pair(c1[2])}"
        c2_str = f"{fmt_pair(c2[1])} vs {fmt_pair(c2[2])}" if c2 else "-"
        print(f"  G{game_idx:02d}  {strategy:12s}  [{c1_str}]  [{c2_str}]")

    # Games played
    print("\nGames played per player:")
    gp = stats["games_played"]
    for p in PLAYERS:
        print(f"  {p:8s} {gp.get(p, 0):>3d}")
    vals = [gp.get(p, 0) for p in PLAYERS]
    print(f"  min={min(vals)}  max={max(vals)}  spread={max(vals)-min(vals)}")

    # Partnership distribution
    print("\nPartnership distribution (times each pair teamed up):")
    all_pairs = []
    for i, a in enumerate(PLAYERS):
        for b in PLAYERS[i + 1:]:
            all_pairs.append(tuple(sorted([a, b])))
    pc = stats["partnerships"]
    counts = [pc.get(pair, 0) for pair in all_pairs]
    hist = Counter(counts)
    for c in sorted(hist):
        print(f"  {c}x partner:  {hist[c]} pairs")
    print(
        f"  pairs that partnered:   {sum(1 for c in counts if c > 0)}/{len(all_pairs)}"
    )
    print(
        f"  min={min(counts)}  max={max(counts)}  "
        f"mean={sum(counts)/len(counts):.2f}"
    )
    # Show most repeated partnerships
    top_repeats = sorted(pc.items(), key=lambda kv: -kv[1])[:5]
    print("  most-repeated partnerships:")
    for pair, cnt in top_repeats:
        print(f"    {fmt_pair(pair):<24s} {cnt}x")

    # Strategy usage
    sg = stats["strategy_games"]
    print(
        f"\nStrategy mix used: competitive={sg['competitive']} "
        f"balanced={sg['balanced']} random={sg['random']}"
    )


def print_summary(all_runs: list):
    print("\n" + "#" * 78)
    print("# SUMMARY ACROSS 5 RUNS")
    print("#" * 78)

    print("\nGames played per player (min/max across runs):")
    for p in PLAYERS:
        vals = [r["games_played"].get(p, 0) for r in all_runs]
        print(f"  {p:8s} min={min(vals):>2d}  max={max(vals):>2d}")

    print("\nPartnership-spread metric per run (lower spread = more even):")
    print(
        f"  {'Run':<5s}{'min':>5s}{'max':>5s}{'spread':>8s}"
        f"{'stdev':>8s}{'pairs_used':>12s}"
    )
    for i, r in enumerate(all_runs, start=1):
        all_pairs = []
        for ai, a in enumerate(PLAYERS):
            for b in PLAYERS[ai + 1:]:
                all_pairs.append(tuple(sorted([a, b])))
        counts = [r["partnerships"].get(pair, 0) for pair in all_pairs]
        mean = sum(counts) / len(counts)
        var = sum((c - mean) ** 2 for c in counts) / len(counts)
        stdev = var ** 0.5
        used = sum(1 for c in counts if c > 0)
        print(
            f"  {i:<5d}{min(counts):>5d}{max(counts):>5d}"
            f"{max(counts)-min(counts):>8d}{stdev:>8.2f}"
            f"{used:>8d}/{len(all_pairs)}"
        )

    print(
        "\nExpected partnership mean with 8 players / 12 games / 2 courts:"
        f" {(12*4)/28:.2f}  (48 partnership slots / 28 possible pairs)"
    )


if __name__ == "__main__":
    all_runs = []
    for run_num in range(1, 6):
        stats = run_session(seed=run_num)
        print_run(run_num, stats)
        all_runs.append(stats)
    print_summary(all_runs)
