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
    
    # Metadata
    h2h_override: bool = False  # True if ranked above a team with higher composite due to H2H


class RankingEngine:
    """Core ranking algorithm."""
    
    # Weights from spec - adjusted to boost SOS and reduce win/loss
    WEIGHTS = {
        'win_loss': 0.10,    # Don't overvalue raw wins
        'sos': 0.25,         # Schedule matters
        'sor': 0.20,         # Strength of record is key
        'point_diff': 0.05,  # Reduced - blowouts against bad teams shouldn't count
        'def_eff': 0.10,
        'qual_wins': 0.15,   # Boosted - beating good teams should matter more
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
        """Calculate schedule-aware win/loss score.
        
        Blends raw win percentage with SOR to prevent teams from
        ranking highly on record alone against weak schedules.
        """
        # First calculate raw win percentages
        raw_scores = {}
        for tm in team_metrics.values():
            total = tm.wins + tm.losses + tm.ties
            if total > 0:
                raw_scores[tm.team_name] = (tm.wins + 0.5 * tm.ties) / total * 100
            else:
                raw_scores[tm.team_name] = 50.0
        
        # Calculate SOR (Strength of Record)
        self.calculate_sor(team_metrics)
        
        # Blend: 30% raw win pct, 70% SOR (schedule-adjusted)
        for tm in team_metrics.values():
            raw = raw_scores[tm.team_name]
            sor = tm.sor_score
            tm.win_loss_score = (raw * 0.30) + (sor * 0.70)
    
    def get_conference_tier(self, conference: str, season: int) -> float:
        """Get conference strength tier multiplier.
        
        Power conferences get boost, non-power get penalty.
        This helps prevent non-power undefeated teams from jumping power champs.
        """
        # Power conferences by era
        power_conferences = {
            # Modern era (2014+)
            'SEC', 'Big Ten', 'Big 12', 'Pac-12', 'ACC',
            # Historical equivalents
            'Pac-10', 'Big East', 'Southwest', 'Big Eight', 'Border',
            'Southern', 'Western Athletic', 'Missouri Valley',
            # Independents that were power
            'Independent',
        }
        
        # Group of 5 / mid-major
        mid_major = {
            'Mountain West', 'American Athletic', 'Conference USA',
            'Mid-American', 'Sun Belt', 'WAC',
            'Mountain West Conference', 'Conference USA',
        }
        
        # FCS conferences (shouldn't appear after filtering, but just in case)
        fcs = {
            'Atlantic 10', 'Big Sky', 'Colonial', 'Ivy',
            'Missouri Valley Football', 'Northeast', 'Ohio Valley',
            'Patriot League', 'Pioneer', 'Southern Conference',
            'Southland', 'SWAC', 'MEAC',
        }
        
        conf_upper = conference.upper() if conference else ''
        
        # Check if it's a power conference
        for p in power_conferences:
            if p.upper() in conf_upper:
                return 1.0  # No adjustment
        
        # Check mid-major
        for m in mid_major:
            if m.upper() in conf_upper:
                return 0.85  # 15% penalty
        
        # Check FCS
        for f in fcs:
            if f.upper() in conf_upper:
                return 0.70  # 30% penalty
        
        return 0.90  # Default slight penalty for unknown
    
    def calculate_sos(self, team_metrics: Dict[str, TeamMetrics], 
                     games: List[sqlite3.Row]) -> None:
        """Calculate Strength of Schedule with conference tier adjustment."""
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
                base_sos = avg_opp_win_pct * 100
                
                # Apply conference tier multiplier to SOS
                # This reduces SOS for teams in weak conferences
                tier_multiplier = self.get_conference_tier(tm.conference, self.season)
                tm.sos_score = base_sos * tier_multiplier
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
    
    def calculate_point_diff(self, team_metrics: Dict[str, TeamMetrics],
                             games: List[sqlite3.Row]) -> None:
        """Calculate point differential with opponent-aware capping.
        
        Blowouts against weak opponents are capped more heavily than
        close wins against strong opponents.
        """
        for tm in team_metrics.values():
            if tm.games_played == 0:
                tm.point_diff_score = 50.0
                continue
            
            team_games = self.get_team_games(tm.team_name, games)
            weighted_diffs = []
            
            for game in team_games:
                opp_name = self.get_opponent_name(game, tm.team_name)
                if opp_name not in team_metrics:
                    continue
                
                opp = team_metrics[opp_name]
                margin = self.get_team_points(game, tm.team_name) - \
                        self.get_opponent_points(game, tm.team_name)
                
                # Cap margin based on opponent strength
                # Weak opponent (composite < 45): cap at ±7 (one score)
                # Medium opponent (45-55): cap at ±14 (two scores)
                # Strong opponent (55+): cap at ±28 (four scores)
                if opp.composite_score < 45:
                    cap = 7
                elif opp.composite_score < 55:
                    cap = 14
                else:
                    cap = 28
                
                capped_margin = max(-cap, min(cap, margin))
                weighted_diffs.append(capped_margin)
            
            if weighted_diffs:
                avg_diff = sum(weighted_diffs) / len(weighted_diffs)
                # Scale to 0-100: -28 = 0, 0 = 50, +28 = 100
                tm.point_diff_score = (avg_diff + 28) / 56 * 100
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
                # Typical scores: top team ~65-68, top 10 ~55-65, top 25 ~50-55
                if opp.composite_score >= 60:  # Approx top 10
                    qual_points += 10
                elif opp.composite_score >= 55:  # Approx top 25
                    qual_points += 7
                elif opp.composite_score >= 50:  # Approx top 40
                    qual_points += 4
                
                # Close losses to quality opponents (within 7 points)
                if margin <= 7 and opp.composite_score >= 55:
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
    
    def apply_head_to_head(self, rankings: List[TeamMetrics], 
                           games: List[sqlite3.Row], 
                           threshold: float = 2.0) -> List[TeamMetrics]:
        """Apply head-to-head tiebreaker for closely-ranked teams.
        
        If Team A beat Team B and they're within `threshold` composite points,
        bump Team A above Team B.
        """
        # Build lookup
        team_map = {tm.team_name: tm for tm in rankings}
        
        # Find head-to-head results among top teams
        h2h_wins = {}  # winner -> set of losers
        
        for game in games:
            if game['home_points'] is None or game['away_points'] is None:
                continue
            
            home = game['home_team']
            away = game['away_team']
            home_pts = game['home_points']
            away_pts = game['away_points']
            
            # Only care about games between ranked teams
            if home not in team_map or away not in team_map:
                continue
            
            if home_pts > away_pts:
                h2h_wins.setdefault(home, set()).add(away)
            elif away_pts > home_pts:
                h2h_wins.setdefault(away, set()).add(home)
        
        # Check for violations: loser ranked above winner within threshold
        changed = True
        passes = 0
        max_passes = 10
        
        while changed and passes < max_passes:
            changed = False
            passes += 1
            
            for i in range(len(rankings)):
                for j in range(i + 1, len(rankings)):
                    higher = rankings[i]  # Currently ranked higher
                    lower = rankings[j]   # Currently ranked lower
                    
                    # Check if lower team beat higher team
                    if lower.team_name in h2h_wins and higher.team_name in h2h_wins[lower.team_name]:
                        # Check if they're within threshold
                        score_diff = higher.composite_score - lower.composite_score
                        
                        if score_diff <= threshold:
                            # Swap them and mark as H2H override
                            rankings[i], rankings[j] = rankings[j], rankings[i]
                            lower.h2h_override = True
                            changed = True
                            break
                
                if changed:
                    break
        
        # Clear all H2H override flags - we will recompute based on final rankings
        for tm in rankings:
            tm.h2h_override = False
        
        # Re-assign ranks and compute which teams are actually ranked above
        # a team with higher composite due to H2H
        for i, tm in enumerate(rankings, 1):
            tm.overall_rank = i
            
            # Check if any team below has a higher composite score AND lost to this team
            for j in range(i, len(rankings)):
                below = rankings[j]
                if below.composite_score > tm.composite_score:
                    # tm is ranked above below despite worse composite
                    # Check if tm beat below head-to-head
                    if tm.team_name in h2h_wins and below.team_name in h2h_wins[tm.team_name]:
                        tm.h2h_override = True
                        break
        
        return rankings
    
    def apply_conference_champion_bonus(self, rankings: List[TeamMetrics],
                                         games: List[sqlite3.Row],
                                         bonus: float = 2.5) -> List[TeamMetrics]:
        """Apply bonus to conference champions.
        
        In the 12-team playoff era, conference championships are devalued.
        This bonus restores their importance in rankings.
        """
        # Build conference standings from conference-only games
        conf_records = {}  # conference -> {team: {wins, losses, ties}}
        
        for game in games:
            if game['home_points'] is None or game['away_points'] is None:
                continue
            
            home = game['home_team']
            away = game['away_team']
            home_conf = game['home_conference']
            away_conf = game['away_conference']
            
            # Only count games where both teams are in the same conference
            # and neither is Independent
            if (home_conf and away_conf and 
                home_conf == away_conf and 
                'Independent' not in home_conf):
                
                if home_conf not in conf_records:
                    conf_records[home_conf] = {}
                
                for team in [home, away]:
                    if team not in conf_records[home_conf]:
                        conf_records[home_conf][team] = {'wins': 0, 'losses': 0, 'ties': 0}
                
                if game['home_points'] > game['away_points']:
                    conf_records[home_conf][home]['wins'] += 1
                    conf_records[home_conf][away]['losses'] += 1
                elif game['home_points'] < game['away_points']:
                    conf_records[home_conf][home]['losses'] += 1
                    conf_records[home_conf][away]['wins'] += 1
                else:
                    conf_records[home_conf][home]['ties'] += 1
                    conf_records[home_conf][away]['ties'] += 1
        
        # Find conference champions (best conference record)
        champions = set()
        for conf, teams in conf_records.items():
            if len(teams) < 2:
                continue
            
            # Calculate win percentage for each team
            best_pct = -1
            best_team = None
            
            for team, record in teams.items():
                total = record['wins'] + record['losses'] + record['ties']
                if total >= 3:  # Need at least 3 conference games
                    pct = (record['wins'] + 0.5 * record['ties']) / total
                    if pct > best_pct:
                        best_pct = pct
                        best_team = team
            
            if best_team:
                champions.add(best_team)
        
        # Apply bonus to champions
        for tm in rankings:
            if tm.team_name in champions:
                tm.composite_score += bonus
        
        # Re-sort with bonus applied
        rankings = sorted(rankings, key=lambda x: x.composite_score, reverse=True)
        
        # Re-assign ranks
        for i, tm in enumerate(rankings, 1):
            tm.overall_rank = i
        
        return rankings
    
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
        
        # Get all FBS teams from teams table (which only stores FBS teams)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, conference FROM teams")
        fbs_teams = cursor.fetchall()
        
        # Get team IDs
        team_ids = {row['name']: row['id'] for row in fbs_teams}
        
        # Initialize metrics with historical conferences
        team_metrics = {}
        for team in fbs_teams:
            team_name = team['name']
            hist_conf = self.get_historical_conference(team_name, games)
            team_metrics[team_name] = TeamMetrics(
                team_id=team['id'],
                team_name=team_name,
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
        
        # Filter to teams that played at least 6 games (removes FCS teams with only 1-2 crossover games)
        min_games = 6
        team_metrics = {name: tm for name, tm in team_metrics.items() if tm.games_played >= min_games}
        print(f"Filtered to {len(team_metrics)} teams with >= {min_games} games")
        
        # Iterative ranking with damping
        print(f"\nRunning up to {max_iterations} iterations (convergence check: top {convergence_top_n}, damping: {damping})...")
        prev_rankings = None
        
        for i in range(max_iterations):
            # Save old composite scores for damping
            old_scores = {name: tm.composite_score for name, tm in team_metrics.items()}
            
            self.calculate_win_loss(team_metrics)
            self.calculate_sos(team_metrics, games)
            self.calculate_sor(team_metrics)
            self.calculate_point_diff(team_metrics, games)
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
        
        # Apply conference champion bonus first
        ranked = self.apply_conference_champion_bonus(ranked, games, bonus=2.5)
        
        # Apply head-to-head tiebreaker LAST (after all other adjustments)
        ranked = self.apply_head_to_head(ranked, games, threshold=2.0)
        
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
