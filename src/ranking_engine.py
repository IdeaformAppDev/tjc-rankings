#!/usr/bin/env python3
"""
College Football Ranking System - Core Algorithm
Implements the 9-metric composite ranking with iterative solver.
"""

import json
import sqlite3
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "cfb_ranking.db"


@dataclass
class TeamMetrics:
    """Container for all computed metrics for a single team."""
    team_id: int
    team_name: str
    conference: str
    
    # Raw values
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: int = 0
    points_against: int = 0
    games_played: int = 0
    
    # Computed metrics (0-100 scale)
    win_loss_score: float = 50.0
    sos_score: float = 50.0
    sor_score: float = 50.0
    point_diff_score: float = 50.0
    def_eff_score: float = 50.0
    qual_wins_score: float = 50.0
    champ_behavior_score: float = 50.0
    special_teams_score: float = 50.0
    ball_control_score: float = 50.0
    
    # Final
    composite_score: float = 50.0
    overall_rank: int = 0


class RankingEngine:
    """Core ranking algorithm."""
    
    # Weights from spec
    WEIGHTS = {
        'win_loss': 0.20,
        'sos': 0.20,
        'sor': 0.15,
        'point_diff': 0.10,
        'def_eff': 0.10,
        'qual_wins': 0.10,
        'champ_behavior': 0.10,
        'special_teams': 0.03,
        'ball_control': 0.02
    }
    
    def __init__(self, season: int, week: Optional[int] = None):
        self.season = season
        self.week = week
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
    
    def get_games(self) -> List[sqlite3.Row]:
        """Fetch games for the season/week."""
        cursor = self.conn.cursor()
        if self.week:
            cursor.execute("""
                SELECT * FROM games 
                WHERE season = ? AND week <= ? AND completed = 1
                ORDER BY week, start_date
            """, (self.season, self.week))
        else:
            cursor.execute("""
                SELECT * FROM games 
                WHERE season = ? AND completed = 1
                ORDER BY week, start_date
            """, (self.season,))
        return cursor.fetchall()
    
    def get_team_games(self, team_name: str, games: List[sqlite3.Row]) -> List[sqlite3.Row]:
        """Filter games for a specific team."""
        return [
            g for g in games 
            if g['home_team'] == team_name or g['away_team'] == team_name
        ]
    
    def get_historical_conference(self, team_name: str, games: List[sqlite3.Row]) -> str:
        """Get the most common conference for a team from game data."""
        conferences = []
        for g in games:
            if g['home_team'] == team_name and g['home_conference']:
                conferences.append(g['home_conference'])
            elif g['away_team'] == team_name and g['away_conference']:
                conferences.append(g['away_conference'])
        
        if not conferences:
            return 'Independent'
        
        # Return most common conference
        from collections import Counter
        return Counter(conferences).most_common(1)[0][0]
    
    def is_team_home(self, game: sqlite3.Row, team_name: str) -> bool:
        return game['home_team'] == team_name
    
    def get_team_points(self, game: sqlite3.Row, team_name: str) -> int:
        if self.is_team_home(game, team_name):
            return game['home_points'] or 0
        return game['away_points'] or 0
    
    def get_opponent_points(self, game: sqlite3.Row, team_name: str) -> int:
        if self.is_team_home(game, team_name):
            return game['away_points'] or 0
        return game['home_points'] or 0
    
    def get_opponent_name(self, game: sqlite3.Row, team_name: str) -> str:
        if self.is_team_home(game, team_name):
            return game['away_team']
        return game['home_team']
    
    def calculate_win_loss(self, team_metrics: Dict[str, TeamMetrics]) -> None:
        """Calculate win/loss percentage (0-100 scale)."""
        for tm in team_metrics.values():
            total = tm.wins + tm.losses + tm.ties
            if total > 0:
                # Win pct scaled to 0-100
                tm.win_loss_score = (tm.wins + 0.5 * tm.ties) / total * 100
            else:
                tm.win_loss_score = 50.0  # Neutral for no games
    
    def calculate_sos(self, team_metrics: Dict[str, TeamMetrics], 
                     games: List[sqlite3.Row]) -> None:
        """Calculate Strength of Schedule."""
        opponent_win_pcts = []
        
        for tm in team_metrics.values():
            team_games = self.get_team_games(tm.team_name, games)
            opp_win_pcts = []
            
            for game in team_games:
                opp_name = self.get_opponent_name(game, tm.team_name)
                if opp_name in team_metrics:
                    opp = team_metrics[opp_name]
                    total = opp.wins + opp.losses + opp.ties
                    if total > 0:
                        win_pct = (opp.wins + 0.5 * opp.ties) / total
                        opp_win_pcts.append(win_pct)
            
            if opp_win_pcts:
                avg_opp_win_pct = statistics.mean(opp_win_pcts)
                # Scale: 0.500 = 50, higher/lower spread accordingly
                tm.sos_score = avg_opp_win_pct * 100
            else:
                tm.sos_score = 50.0
    
    def calculate_sor(self, team_metrics: Dict[str, TeamMetrics]) -> None:
        """Calculate Strength of Record.
        
        How would an average top-25 team perform against this schedule?
        Simplified: Compare actual win% to expected win% based on SOS.
        """
        for tm in team_metrics.values():
            # Expected win% for average team against this schedule
            # Simplified: inverse of SOS (harder schedule = lower expected wins)
            expected_win_pct = 1.0 - (tm.sos_score / 100.0 * 0.5)
            # Cap between 0.1 and 0.9
            expected_win_pct = max(0.1, min(0.9, expected_win_pct))
            
            actual_win_pct = tm.win_loss_score / 100.0
            
            # SOR = actual vs expected, scaled
            if expected_win_pct > 0:
                sor_ratio = actual_win_pct / expected_win_pct
                # Normalize: 1.0 = 50, higher = better
                tm.sor_score = min(100, max(0, sor_ratio * 50))
            else:
                tm.sor_score = 50.0
    
    def calculate_point_diff(self, team_metrics: Dict[str, TeamMetrics]) -> None:
        """Calculate point differential with 28-point cap."""
        differentials = []
        
        for tm in team_metrics.values():
            if tm.games_played > 0:
                avg_diff = (tm.points_for - tm.points_against) / tm.games_played
                # Cap at ±28
                capped_diff = max(-28, min(28, avg_diff))
                # Scale to 0-100: -28 = 0, 0 = 50, +28 = 100
                tm.point_diff_score = (capped_diff + 28) / 56 * 100
            else:
                tm.point_diff_score = 50.0
    
    def calculate_qual_wins(self, team_metrics: Dict[str, TeamMetrics],
                           games: List[sqlite3.Row]) -> None:
        """Calculate quality wins based on opponent rankings."""
        # First pass: use current rankings for quality calculation
        # We'll iterate to refine
        for tm in team_metrics.values():
            team_games = self.get_team_games(tm.team_name, games)
            qual_points = 0
            
            for game in team_games:
                if self.get_team_points(game, tm.team_name) <= \
                   self.get_opponent_points(game, tm.team_name):
                    continue  # Skip losses
                
                opp_name = self.get_opponent_name(game, tm.team_name)
                if opp_name not in team_metrics:
                    continue
                
                opp = team_metrics[opp_name]
                margin = abs(self.get_team_points(game, tm.team_name) - 
                           self.get_opponent_points(game, tm.team_name))
                
                # Tiered scoring based on opponent rank
                # Use composite score as proxy for ranking
                if opp.composite_score >= 85:  # Approx top 10
                    qual_points += 10
                elif opp.composite_score >= 75:  # Approx top 25
                    qual_points += 7
                elif opp.composite_score >= 65:  # Approx top 40
                    qual_points += 4
                
                # Close losses to quality opponents
                if margin <= 7 and opp.composite_score >= 75:
                    qual_points += 2
            
            # Normalize to 0-100 (cap at ~50 points max)
            tm.qual_wins_score = min(100, qual_points * 2)
    
    def calculate_champ_behavior(self, team_metrics: Dict[str, TeamMetrics],
                                games: List[sqlite3.Row]) -> None:
        """Calculate championship behavior metrics."""
        for tm in team_metrics.values():
            team_games = self.get_team_games(tm.team_name, games)
            behavior_points = 0
            
            for game in team_games:
                team_pts = self.get_team_points(game, tm.team_name)
                opp_pts = self.get_opponent_points(game, tm.team_name)
                margin = abs(team_pts - opp_pts)
                
                if team_pts > opp_pts:  # Win
                    # Close win
                    if margin <= 7:
                        behavior_points += 1
                    
                    # Road win (simplified: check if home/away)
                    if not self.is_team_home(game, tm.team_name):
                        behavior_points += 1
                else:  # Loss
                    # Bad loss penalty
                    opp_name = self.get_opponent_name(game, tm.team_name)
                    if opp_name in team_metrics:
                        opp = team_metrics[opp_name]
                        # Loss to unranked (low composite)
                        if opp.composite_score < 60:
                            behavior_points -= 3
                        # Blowout loss
                        if margin > 21:
                            behavior_points -= 5
                        # Upset loss (ranked 15+ spots higher)
                        if tm.composite_score - opp.composite_score > 15:
                            behavior_points -= 4
            
            # Normalize to 0-100 (center at 50)
            tm.champ_behavior_score = min(100, max(0, 50 + behavior_points * 3))
    
    def calculate_def_eff(self, team_metrics: Dict[str, TeamMetrics],
                         games: List[sqlite3.Row]) -> None:
        """Calculate defensive efficiency (simplified)."""
        # Without per-possession data, use points allowed per game
        # relative to opponent average
        for tm in team_metrics.values():
            if tm.games_played == 0:
                tm.def_eff_score = 50.0
                continue
            
            team_games = self.get_team_games(tm.team_name, games)
            total_opp_avg = 0
            count = 0
            
            for game in team_games:
                opp_name = self.get_opponent_name(game, tm.team_name)
                if opp_name in team_metrics:
                    opp = team_metrics[opp_name]
                    if opp.games_played > 0:
                        total_opp_avg += opp.points_for / opp.games_played
                        count += 1
            
            if count > 0:
                avg_opp_scoring = total_opp_avg / count
                pts_allowed_per_game = tm.points_against / tm.games_played
                
                if avg_opp_scoring > 0:
                    ratio = 1.0 - (pts_allowed_per_game / avg_opp_scoring)
                    tm.def_eff_score = min(100, max(0, 50 + ratio * 50))
                else:
                    tm.def_eff_score = 50.0
            else:
                tm.def_eff_score = 50.0
    
    def calculate_special_teams(self, team_metrics: Dict[str, TeamMetrics]) -> None:
        """Placeholder for special teams (requires detailed play-by-play data)."""
        # Without detailed kicking data, use a neutral score
        for tm in team_metrics.values():
            tm.special_teams_score = 50.0
    
    def calculate_ball_control(self, team_metrics: Dict[str, TeamMetrics]) -> None:
        """Placeholder for ball control (requires time of possession data)."""
        # Without TOP data, use a neutral score
        for tm in team_metrics.values():
            tm.ball_control_score = 50.0
    
    def compute_composite(self, team_metrics: Dict[str, TeamMetrics]) -> None:
        """Calculate final composite score."""
        for tm in team_metrics.values():
            tm.composite_score = (
                tm.win_loss_score * self.WEIGHTS['win_loss'] +
                tm.sos_score * self.WEIGHTS['sos'] +
                tm.sor_score * self.WEIGHTS['sor'] +
                tm.point_diff_score * self.WEIGHTS['point_diff'] +
                tm.def_eff_score * self.WEIGHTS['def_eff'] +
                tm.qual_wins_score * self.WEIGHTS['qual_wins'] +
                tm.champ_behavior_score * self.WEIGHTS['champ_behavior'] +
                tm.special_teams_score * self.WEIGHTS['special_teams'] +
                tm.ball_control_score * self.WEIGHTS['ball_control']
            )
    
    def compute_metric_ranks(self, team_metrics: Dict[str, TeamMetrics]) -> Dict[str, Dict[str, int]]:
        """Calculate individual rankings for each metric."""
        metric_names = [
            'win_loss_score', 'sos_score', 'sor_score', 'point_diff_score',
            'def_eff_score', 'qual_wins_score', 'champ_behavior_score',
            'special_teams_score', 'ball_control_score'
        ]
        
        ranks = {}
        for metric in metric_names:
            # Sort teams by this metric descending
            sorted_teams = sorted(
                team_metrics.values(),
                key=lambda x: getattr(x, metric),
                reverse=True
            )
            # Assign ranks
            metric_ranks = {}
            for i, tm in enumerate(sorted_teams, 1):
                metric_ranks[tm.team_name] = i
            ranks[metric] = metric_ranks
        
        return ranks
    
    def rank_teams(self, team_metrics: Dict[str, TeamMetrics]) -> List[TeamMetrics]:
        """Sort teams by composite score and assign ranks."""
        ranked = sorted(team_metrics.values(), 
                       key=lambda x: x.composite_score, 
                       reverse=True)
        for i, tm in enumerate(ranked, 1):
            tm.overall_rank = i
        return ranked
    
    def has_converged(self, prev_rankings: List[TeamMetrics], 
                     curr_rankings: List[TeamMetrics], 
                     top_n: int = 25) -> bool:
        """Check if top N rankings have stabilized."""
        if len(prev_rankings) != len(curr_rankings):
            return False
        
        # Compare top N teams
        prev_top = [tm.team_name for tm in prev_rankings[:top_n]]
        curr_top = [tm.team_name for tm in curr_rankings[:top_n]]
        
        return prev_top == curr_top
    
    def run(self, max_iterations: int = 10, convergence_top_n: int = 25, damping: float = 0.3) -> List[TeamMetrics]:
        """Run the iterative ranking algorithm.
        
        Args:
            max_iterations: Maximum iterations to run
            convergence_top_n: Check convergence on top N teams
            damping: Blending factor for score updates (0 = no change, 1 = full update)
        """
        print(f"Running ranking for season {self.season}")
        if self.week:
            print(f"Through week {self.week}")
        
        games = self.get_games()
        print(f"Loaded {len(games)} completed games")
        
        # Get all teams
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, conference FROM teams")
        teams = cursor.fetchall()
        
        # Initialize metrics with historical conferences
        team_metrics = {}
        for team in teams:
            hist_conf = self.get_historical_conference(team['name'], games)
            team_metrics[team['name']] = TeamMetrics(
                team_id=team['id'],
                team_name=team['name'],
                conference=hist_conf
            )
        
        # Populate basic stats from games
        for game in games:
            for is_home in [True, False]:
                if is_home:
                    team_name = game['home_team']
                    team_pts = game['home_points'] or 0
                    opp_pts = game['away_points'] or 0
                else:
                    team_name = game['away_team']
                    team_pts = game['away_points'] or 0
                    opp_pts = game['home_points'] or 0
                
                if team_name not in team_metrics:
                    continue
                
                tm = team_metrics[team_name]
                tm.games_played += 1
                tm.points_for += team_pts
                tm.points_against += opp_pts
                
                if team_pts > opp_pts:
                    tm.wins += 1
                elif team_pts < opp_pts:
                    tm.losses += 1
                else:
                    tm.ties += 1
        
        # Iterative ranking with damping
        print(f"\nRunning up to {max_iterations} iterations (convergence check: top {convergence_top_n}, damping: {damping})...")
        prev_rankings = None
        
        for i in range(max_iterations):
            # Save old composite scores for damping
            old_scores = {name: tm.composite_score for name, tm in team_metrics.items()}
            
            self.calculate_win_loss(team_metrics)
            self.calculate_sos(team_metrics, games)
            self.calculate_sor(team_metrics)
            self.calculate_point_diff(team_metrics)
            self.calculate_def_eff(team_metrics, games)
            self.calculate_qual_wins(team_metrics, games)
            self.calculate_champ_behavior(team_metrics, games)
            self.calculate_special_teams(team_metrics)
            self.calculate_ball_control(team_metrics)
            self.compute_composite(team_metrics)
            
            # Apply damping: blend old and new scores
            if i > 0:
                for tm in team_metrics.values():
                    tm.composite_score = (
                        damping * tm.composite_score + 
                        (1 - damping) * old_scores[tm.team_name]
                    )
            
            ranked = self.rank_teams(team_metrics)
            print(f"  Iteration {i+1}: Top team = {ranked[0].team_name} "
                  f"(score: {ranked[0].composite_score:.2f})")
            
            # Check convergence
            if prev_rankings and self.has_converged(prev_rankings, ranked, convergence_top_n):
                print(f"  ✓ Converged after {i+1} iterations (top {convergence_top_n} stable)")
                break
            
            prev_rankings = ranked
        
        # Compute individual metric ranks for final rankings
        metric_ranks = self.compute_metric_ranks(team_metrics)
        
        return ranked, metric_ranks
    
    def store_rankings(self, rankings: List[TeamMetrics], metric_ranks: Dict[str, Dict[str, int]]) -> None:
        """Store rankings to database with individual metric ranks."""
        cursor = self.conn.cursor()
        
        for tm in rankings:
            cursor.execute("""
                INSERT INTO rankings 
                (season, week, team_id, team_name, conference, composite_score,
                 win_loss_rank, sos_rank, sor_rank, point_diff_rank,
                 def_eff_rank, qual_wins_rank, champ_behavior_rank,
                 special_teams_rank, ball_control_rank, overall_rank, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                self.season, self.week or 0, tm.team_id, tm.team_name, tm.conference,
                tm.composite_score,
                metric_ranks['win_loss_score'][tm.team_name],
                metric_ranks['sos_score'][tm.team_name],
                metric_ranks['sor_score'][tm.team_name],
                metric_ranks['point_diff_score'][tm.team_name],
                metric_ranks['def_eff_score'][tm.team_name],
                metric_ranks['qual_wins_score'][tm.team_name],
                metric_ranks['champ_behavior_score'][tm.team_name],
                metric_ranks['special_teams_score'][tm.team_name],
                metric_ranks['ball_control_score'][tm.team_name],
                tm.overall_rank
            ))
        
        self.conn.commit()
        print(f"\nStored {len(rankings)} rankings")


def main():
    print("=== College Football Ranking System - Phase 2 ===")
    print("Computing rankings for 2024 season...\n")
    
    with RankingEngine(season=2024) as engine:
        rankings, metric_ranks = engine.run(max_iterations=10)
        
        print("\n" + "="*60)
        print("FINAL RANKINGS - 2024 Season")
        print("="*60)
        print(f"{'Rank':<6} {'Team':<30} {'Conf':<10} {'Score':<8}")
        print("-"*60)
        
        for i, tm in enumerate(rankings[:25], 1):
            print(f"{i:<6} {tm.team_name:<30} {tm.conference:<10} "
                  f"{tm.composite_score:.2f}")
        
        # Store in database
        engine.store_rankings(rankings, metric_ranks)
        
        print("\n" + "="*60)
        print("Top 10 by Metric:")
        print("="*60)
        
        # Show breakdown for top 5
        for tm in rankings[:5]:
            print(f"\n{tm.team_name}:")
            print(f"  Win/Loss:     {tm.win_loss_score:.1f}")
            print(f"  SoS:          {tm.sos_score:.1f}")
            print(f"  SoR:          {tm.sor_score:.1f}")
            print(f"  Point Diff:   {tm.point_diff_score:.1f}")
            print(f"  Def Eff:      {tm.def_eff_score:.1f}")
            print(f"  Qual Wins:    {tm.qual_wins_score:.1f}")
            print(f"  Champ Behav:  {tm.champ_behavior_score:.1f}")
            print(f"  COMPOSITE:    {tm.composite_score:.1f}")


if __name__ == "__main__":
    main()
