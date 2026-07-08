import sqlite3
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from config import DB_PATH, WEIGHTS, MAX_POINT_DIFF, MAX_ITERATIONS, RANKING_CONVERGENCE_THRESHOLD

class TeamMetrics:
    """Holds all calculated metrics for a single team."""
    def __init__(self, team: str, season: int):
        self.team = team
        self.season = season
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.games_played = 0
        self.points_for = 0
        self.points_against = 0
        self.opponents = []  # List of (opponent_name, opponent_points, team_points)
        self.quality_wins = 0
        self.quality_losses = 0
        self.close_wins = 0
        self.close_losses = 0
        self.comeback_wins = 0
        self.road_wins = 0
        self.bad_losses = 0
        self.heavy_losses = 0
        
        # Stats from team_stats table (may be None for older seasons)
        self.third_down_stops = 0
        self.third_down_attempts = 0
        self.red_zone_attempts = 0
        self.red_zone_scores_allowed = 0
        self.time_of_possession = 0
        self.total_yards = 0
        
    @property
    def win_pct(self) -> float:
        if self.games_played == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / self.games_played
    
    @property
    def point_differential(self) -> float:
        if self.games_played == 0:
            return 0.0
        return (self.points_for - self.points_against) / self.games_played

def load_games(conn: sqlite3.Connection, season: int) -> List[Dict]:
    """Load all games for a season."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT home_team, home_points, away_team, away_points,
               neutral_site, season_type, week
        FROM games
        WHERE season = ? AND home_points IS NOT NULL AND away_points IS NOT NULL
    """, (season,))
    
    games = []
    for row in cursor.fetchall():
        games.append({
            "home_team": row[0],
            "home_points": row[1],
            "away_team": row[2],
            "away_points": row[3],
            "neutral_site": row[4],
            "season_type": row[5],
            "week": row[6]
        })
    return games

def load_team_stats(conn: sqlite3.Connection, season: int) -> Dict[str, Dict]:
    """Load team statistics for a season."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team, third_down_attempts, third_down_conversions,
               red_zone_attempts, red_zone_scores, time_of_possession,
               total_yards, games, points_for, points_against
        FROM team_stats
        WHERE season = ?
    """, (season,))
    
    stats = {}
    for row in cursor.fetchall():
        stats[row[0]] = {
            "third_down_attempts": row[1] or 0,
            "third_down_conversions": row[2] or 0,
            "red_zone_attempts": row[3] or 0,
            "red_zone_scores": row[4] or 0,
            "time_of_possession": row[5] or 0,
            "total_yards": row[6] or 0,
            "games": row[7] or 0,
            "points_for": row[8] or 0,
            "points_against": row[9] or 0,
        }
    return stats

def calculate_metrics(games: List[Dict], team_stats: Dict[str, Dict]) -> Dict[str, TeamMetrics]:
    """Calculate raw metrics for all teams from game data."""
    teams = defaultdict(lambda: None)
    
    def get_team(name: str) -> TeamMetrics:
        if teams[name] is None:
            teams[name] = TeamMetrics(name, games[0]["season"] if games else 0)
        return teams[name]
    
    for game in games:
        home = game["home_team"]
        away = game["away_team"]
        home_pts = game["home_points"]
        away_pts = game["away_points"]
        margin = home_pts - away_pts
        
        home_team = get_team(home)
        away_team = get_team(away)
        
        home_team.games_played += 1
        away_team.games_played += 1
        home_team.points_for += home_pts
        home_team.points_against += away_pts
        away_team.points_for += away_pts
        away_team.points_against += home_pts
        
        home_team.opponents.append((away, away_pts, home_pts))
        away_team.opponents.append((home, home_pts, away_pts))
        
        # Determine winner
        if margin > 0:
            home_team.wins += 1
            away_team.losses += 1
            
            # Quality win check (will be updated with rankings later)
            # Close win check
            if margin <= 7:
                home_team.close_wins += 1
            
            # Road win
            if not game.get("neutral_site", False):
                # Home team won at home - not a road win
                pass
            
            # Comeback win (simplified: trailed at some point - we don't have quarter data)
            # We'll approximate: if they won but were behind in scoring margin earlier
            # This is a limitation without play-by-play data
            
        elif margin < 0:
            away_team.wins += 1
            home_team.losses += 1
            
            if abs(margin) <= 7:
                away_team.close_wins += 1
            
            # Road win
            if not game.get("neutral_site", False):
                away_team.road_wins += 1
        else:
            home_team.ties += 1
            away_team.ties += 1
        
        # Bad loss check (will be updated with rankings later)
        # Heavy loss check
        if margin > 21:  # Home won by >21
            away_team.heavy_losses += 1
        elif margin < -21:  # Away won by >21
            home_team.heavy_losses += 1
    
    # Merge team stats if available
    for team_name, stats in team_stats.items():
        if team_name in teams:
            t = teams[team_name]
            t.third_down_attempts = stats.get("third_down_attempts", 0)
            t.third_down_stops = stats.get("third_down_attempts", 0) - stats.get("third_down_conversions", 0)
            t.red_zone_attempts = stats.get("red_zone_attempts", 0)
            t.red_zone_scores_allowed = stats.get("red_zone_scores", 0)
            t.time_of_possession = stats.get("time_of_possession", 0)
            t.total_yards = stats.get("total_yards", 0)
    
    return {k: v for k, v in teams.items() if v is not None}

def normalize_metric(values: List[float]) -> Dict[str, float]:
    """Normalize values to 0-100 scale."""
    if not values:
        return {}
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return {i: 50.0 for i in range(len(values))}
    
    return {i: 100 * (v - min_val) / (max_val - min_val) for i, v in enumerate(values)}

def calculate_strength_of_schedule(team: TeamMetrics, opponent_ranks: Dict[str, float]) -> float:
    """Calculate SoS based on opponent rankings."""
    if not team.opponents:
        return 50.0
    
    total_sos = 0
    count = 0
    for opponent_name, _, _ in team.opponents:
        if opponent_name in opponent_ranks:
            total_sos += opponent_ranks[opponent_name]
            count += 1
    
    if count == 0:
        return 50.0
    
    return total_sos / count

def calculate_strength_of_record(team: TeamMetrics, avg_top25_win_pct: float) -> float:
    """How would an average top-25 team do against this schedule?"""
    if not team.opponents:
        return 50.0
    
    # Expected wins for average top-25 team
    expected_wins = 0
    for opponent_name, opp_pts, team_pts in team.opponents:
        # Simplified: expected win if we'd predict top-25 team to win
        # This is an approximation - we'd need more data for a true SoR
        expected_wins += avg_top25_win_pct
    
    if expected_wins == 0:
        return 50.0
    
    actual_wins = team.wins + 0.5 * team.ties
    # Higher is better: if we won more than expected, we overperformed
    ratio = actual_wins / expected_wins if expected_wins > 0 else 1.0
    return min(100, ratio * 50)  # Scale so 1.0 = 50, 2.0 = 100

def calculate_defensive_efficiency(team: TeamMetrics) -> float:
    """Calculate defensive efficiency score."""
    if team.games_played == 0:
        return 50.0
    
    # Points allowed per game (lower is better, so invert)
    ppg_allowed = team.points_against / team.games_played
    # Normalize: assume 0-50 range is reasonable for college football
    defensive_score = max(0, 100 - (ppg_allowed * 2))
    
    # Add third down stop percentage if available
    if team.third_down_attempts > 0:
        stop_pct = team.third_down_stops / team.third_down_attempts
        defensive_score = defensive_score * 0.7 + (stop_pct * 100) * 0.3
    
    return defensive_score

def calculate_quality_wins(team: TeamMetrics, rankings: Dict[str, int]) -> float:
    """Calculate quality wins score."""
    score = 0
    for opponent_name, opp_pts, team_pts in team.opponents:
        if team_pts > opp_pts:  # We won
            opp_rank = rankings.get(opponent_name, 999)
            if opp_rank <= 10:
                score += 10
            elif opp_rank <= 25:
                score += 7
            elif opp_rank <= 40:
                score += 4
        else:  # We lost
            opp_rank = rankings.get(opponent_name, 999)
            if opp_rank <= 25 and abs(team_pts - opp_pts) <= 7:
                score += 2  # Close loss to quality opponent
    
    # Normalize to 0-100
    return min(100, score * 2)

def calculate_championship_behavior(team: TeamMetrics, rankings: Dict[str, int]) -> float:
    """Calculate championship behavior score."""
    score = 0
    
    # Close wins (grit)
    score += team.close_wins * 1
    
    # Comeback wins (if we had quarter data)
    score += team.comeback_wins * 2
    
    # Road wins
    score += team.road_wins * 1
    
    # Bad losses penalty
    for opponent_name, opp_pts, team_pts in team.opponents:
        if team_pts < opp_pts:  # We lost
            opp_rank = rankings.get(opponent_name, 999)
            if opp_rank > 50:  # Unranked opponent
                score -= 3
                if abs(team_pts - opp_pts) > 21:
                    score -= 2  # Additional penalty for heavy loss
    
    # Normalize to 0-100 (center at 50)
    return max(0, min(100, 50 + score * 2))

def calculate_special_teams(team: TeamMetrics) -> float:
    """Special teams score (placeholder - limited data)."""
    # Without detailed special teams data, we'll use a neutral score
    # This could be enhanced with field goal data if available
    return 50.0

def calculate_ball_control(team: TeamMetrics) -> float:
    """Ball control/tempo score."""
    if team.games_played == 0 or team.time_of_possession == 0:
        return 50.0
    
    # Time of possession per game (in seconds)
    avg_top = team.time_of_possession / team.games_played
    # Average college football game has ~1800 seconds of possession per team
    # Higher TOP = better ball control
    score = min(100, (avg_top / 1800) * 100)
    return score

def compute_rankings(season: int, conn: sqlite3.Connection) -> List[Tuple[str, float, Dict]]:
    """Compute rankings for a season using iterative algorithm."""
    games = load_games(conn, season)
    team_stats = load_team_stats(conn, season)
    
    if not games:
        print(f"No games found for season {season}")
        return []
    
    # Calculate base metrics
    teams = calculate_metrics(games, team_stats)
    team_names = list(teams.keys())
    
    # Initialize rankings (all teams at 50.0)
    rankings = {name: 50.0 for name in team_names}
    prev_rankings = None
    
    for iteration in range(MAX_ITERATIONS):
        # Sort by current score to get rankings
        sorted_teams = sorted(team_names, key=lambda t: rankings[t], reverse=True)
        current_ranks = {name: i+1 for i, name in enumerate(sorted_teams)}
        
        # Calculate all metrics
        new_scores = {}
        
        # Calculate average top-25 win pct for SoR
        top25_teams = sorted_teams[:25]
        top25_win_pcts = [teams[t].win_pct for t in top25_teams if t in teams]
        avg_top25_win_pct = sum(top25_win_pcts) / len(top25_win_pcts) if top25_win_pcts else 0.75
        
        for name in team_names:
            team = teams[name]
            
            # 1. Win/Loss (normalized)
            win_loss_scores = [teams[t].win_pct for t in team_names]
            win_loss_norm = normalize_metric(win_loss_scores)
            win_loss_score = win_loss_norm[list(team_names).index(name)]
            
            # 2. Strength of Schedule
            sos = calculate_strength_of_schedule(team, rankings)
            
            # 3. Strength of Record
            sor = calculate_strength_of_record(team, avg_top25_win_pct)
            
            # 4. Point Differential (capped)
            pd = team.point_differential
            capped_pd = max(-MAX_POINT_DIFF, min(MAX_POINT_DIFF, pd))
            pd_scores = [max(-MAX_POINT_DIFF, min(MAX_POINT_DIFF, teams[t].point_differential)) for t in team_names]
            pd_norm = normalize_metric(pd_scores)
            pd_score = pd_norm[list(team_names).index(name)]
            
            # 5. Defensive Efficiency
            def_scores = [calculate_defensive_efficiency(teams[t]) for t in team_names]
            def_norm = normalize_metric(def_scores)
            def_score = def_norm[list(team_names).index(name)]
            
            # 6. Quality Wins (depends on rankings)
            qw = calculate_quality_wins(team, current_ranks)
            
            # 7. Championship Behavior (depends on rankings)
            cb = calculate_championship_behavior(team, current_ranks)
            
            # 8. Special Teams
            st = calculate_special_teams(team)
            
            # 9. Ball Control
            bc = calculate_ball_control(team)
            
            # Composite score
            composite = (
                win_loss_score * WEIGHTS["win_loss"] +
                sos * WEIGHTS["strength_of_schedule"] +
                sor * WEIGHTS["strength_of_record"] +
                pd_score * WEIGHTS["point_differential"] +
                def_score * WEIGHTS["defensive_efficiency"] +
                qw * WEIGHTS["quality_wins"] +
                cb * WEIGHTS["championship_behavior"] +
                st * WEIGHTS["special_teams"] +
                bc * WEIGHTS["ball_control"]
            )
            
            new_scores[name] = composite
        
        rankings = new_scores
        
        # Check convergence
        if prev_rankings:
            changes = sum(1 for t in team_names if abs(rankings[t] - prev_rankings[t]) > 0.1)
            if changes <= RANKING_CONVERGENCE_THRESHOLD:
                print(f"  Converged after {iteration + 1} iterations")
                break
        
        prev_rankings = rankings.copy()
    
    # Final sort
    final_rankings = sorted(team_names, key=lambda t: rankings[t], reverse=True)
    
    results = []
    for rank, name in enumerate(final_rankings, 1):
        team = teams[name]
        results.append((name, rankings[name], {
            "wins": team.wins,
            "losses": team.losses,
            "ties": team.ties,
            "win_pct": team.win_pct,
            "point_diff": team.point_differential,
        }))
    
    return results

def save_rankings(season: int, week: int, rankings: List[Tuple], conn: sqlite3.Connection):
    """Save rankings to database."""
    cursor = conn.cursor()
    
    for rank, (team, score, details) in enumerate(rankings, 1):
        cursor.execute("""
            INSERT OR REPLACE INTO rankings (
                season, week, team, rank, composite_score,
                win_loss_score, sos_score, sor_score, point_diff_score,
                def_eff_score, quality_wins_score, champ_behavior_score,
                special_teams_score, ball_control_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            season, week, team, rank, score,
            details.get("win_pct", 0) * 100,
            0, 0, details.get("point_diff", 0),
            0, 0, 0, 0, 0
        ))
    
    conn.commit()
    print(f"Saved {len(rankings)} rankings for season {season}, week {week}")

def generate_final_rankings(season: int):
    """Generate final rankings for a season."""
    conn = sqlite3.connect(DB_PATH)
    
    print(f"\nComputing rankings for season {season}...")
    rankings = compute_rankings(season, conn)
    
    if rankings:
        # Use week 99 for final season rankings
        save_rankings(season, 99, rankings, conn)
        
        print(f"\nTop 25 for {season}:")
        for i, (team, score, details) in enumerate(rankings[:25], 1):
            record = f"{details['wins']}-{details['losses']}"
            if details['ties'] > 0:
                record += f"-{details['ties']}"
            print(f"{i:2d}. {team:25s} {score:.2f} ({record})")
    
    conn.close()
    return rankings

if __name__ == "__main__":
    from config import PRIMARY_BACKTEST_START, PRIMARY_BACKTEST_END
    
    for season in range(PRIMARY_BACKTEST_START, PRIMARY_BACKTEST_END + 1):
        generate_final_rankings(season)
