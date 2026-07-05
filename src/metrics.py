"""Calculate individual metrics for team rankings."""

from typing import Dict, List, Optional
from config import (
    POINT_DIFF_CAP, GARBAGE_TIME_LEAD,
    QUALITY_WIN_TIERS, CHAMP_BEHAVIOR
)


class TeamMetrics:
    """Calculate all metrics for a single team."""
    
    def __init__(self, team_id: str, games: List[Dict], all_teams: Dict[str, Dict]):
        self.team_id = team_id
        self.games = games
        self.all_teams = all_teams
        self.team_games = [g for g in games 
                          if g["home_team"] == team_id or g["away_team"] == team_id]
    
    def win_loss_record(self) -> float:
        """Winning percentage (0-1 scale)."""
        wins = sum(1 for g in self.team_games if self._is_winner(g))
        total = len(self.team_games)
        return wins / total if total > 0 else 0.0
    
    def strength_of_schedule(self, current_rankings: Dict[str, int]) -> float:
        """Average opponent strength based on current rankings."""
        opponent_ranks = []
        for game in self.team_games:
            opponent = self._get_opponent(game)
            if opponent in current_rankings:
                opponent_ranks.append(current_rankings[opponent])
        
        if not opponent_ranks:
            return 0.5
        
        # Lower rank number = stronger opponent
        # Normalize: average rank / 130 (max teams)
        avg_rank = sum(opponent_ranks) / len(opponent_ranks)
        return 1.0 - (avg_rank / 130.0)
    
    def strength_of_record(self, current_rankings: Dict[str, int]) -> float:
        """How would an average top-25 team do against this schedule?"""
        # Simplified: compare actual wins to expected wins
        expected_wins = 0
        actual_wins = sum(1 for g in self.team_games if self._is_winner(g))
        
        for game in self.team_games:
            opponent = self._get_opponent(game)
            if opponent in current_rankings:
                opp_rank = current_rankings[opponent]
                # Top-25 team would be favored vs teams ranked 26+
                if opp_rank > 25:
                    expected_wins += 0.8  # Should win 80% vs weaker teams
                else:
                    expected_wins += 0.5  # Coin flip vs top teams
        
        if expected_wins == 0:
            return 0.5
        
        # Ratio of actual wins to expected wins
        ratio = actual_wins / expected_wins
        return min(ratio, 1.5) / 1.5  # Cap at 1.5x expected, normalize to 0-1
    
    def point_differential(self) -> float:
        """Average margin of victory/defeat, capped."""
        margins = []
        for game in self.team_games:
            margin = self._get_margin(game)
            # Cap at ±28
            capped = max(-POINT_DIFF_CAP, min(POINT_DIFF_CAP, margin))
            margins.append(capped)
        
        if not margins:
            return 0.0
        
        avg_margin = sum(margins) / len(margins)
        # Normalize: -28 to +28 → 0 to 1
        return (avg_margin + POINT_DIFF_CAP) / (2 * POINT_DIFF_CAP)
    
    def defensive_efficiency(self) -> float:
        """Points allowed per possession (simplified)."""
        total_points_allowed = 0
        total_games = 0
        
        for game in self.team_games:
            if game["home_team"] == self.team_id:
                points_allowed = game.get("away_points", 0)
            else:
                points_allowed = game.get("home_points", 0)
            
            total_points_allowed += points_allowed
            total_games += 1
        
        if total_games == 0:
            return 0.5
        
        avg_points_allowed = total_points_allowed / total_games
        # Normalize: 0-50 points → 1.0-0.0 (lower is better)
        return max(0.0, 1.0 - (avg_points_allowed / 50.0))
    
    def quality_wins(self, current_rankings: Dict[str, int]) -> float:
        """Score based on wins against ranked opponents."""
        score = 0
        
        for game in self.team_games:
            if not self._is_winner(game):
                continue
            
            opponent = self._get_opponent(game)
            if opponent not in current_rankings:
                continue
            
            opp_rank = current_rankings[opponent]
            
            # Check tiers
            if opp_rank <= 10:
                score += QUALITY_WIN_TIERS["top_10"]["points"]
            elif opp_rank <= 25:
                score += QUALITY_WIN_TIERS["top_25"]["points"]
            elif opp_rank <= 40:
                score += QUALITY_WIN_TIERS["top_40"]["points"]
        
        # Normalize: max realistic score ~50 → 0-1
        return min(score / 50.0, 1.0)
    
    def championship_behavior(self, current_rankings: Dict[str, int]) -> float:
        """Score based on grit, comebacks, and avoiding bad losses."""
        score = 0
        
        for game in self.team_games:
            margin = self._get_margin(game)
            opponent = self._get_opponent(game)
            opp_rank = current_rankings.get(opponent, 999)
            
            if self._is_winner(game):
                # Close win
                if 0 < margin <= 7:
                    score += CHAMP_BEHAVIOR["close_win"]
                
                # Road win (simplified — would need venue data)
                if game.get("neutral_site") == False and game.get("home_team") != self.team_id:
                    score += CHAMP_BEHAVIOR["road_win"]
            else:
                # Loss
                if opp_rank > 50:
                    # Bad loss to unranked team
                    if margin < -21:
                        score += CHAMP_BEHAVIOR["bad_blowout_loss"]
                    else:
                        score += CHAMP_BEHAVIOR["bad_loss"]
                
                # Close loss to quality opponent
                if -7 <= margin < 0 and opp_rank <= 25:
                    score += CHAMP_BEHAVIOR["close_loss_quality"]
        
        # Normalize: -50 to +50 → 0 to 1
        return (score + 50) / 100.0
    
    def special_teams(self) -> float:
        """Placeholder — would need detailed special teams stats."""
        # Simplified: assume average (0.5) until data available
        return 0.5
    
    def ball_control(self) -> float:
        """Placeholder — would need time of possession data."""
        # Simplified: assume average (0.5) until data available
        return 0.5
    
    def _is_winner(self, game: Dict) -> bool:
        """Check if team won this game."""
        home_team = game["home_team"]
        away_team = game["away_team"]
        home_points = game.get("home_points", 0)
        away_points = game.get("away_points", 0)
        
        if self.team_id == home_team:
            return home_points > away_points
        elif self.team_id == away_team:
            return away_points > home_points
        return False
    
    def _get_opponent(self, game: Dict) -> str:
        """Get opponent name from game."""
        if game["home_team"] == self.team_id:
            return game["away_team"]
        return game["home_team"]
    
    def _get_margin(self, game: Dict) -> int:
        """Get point margin (positive = win, negative = loss)."""
        home_points = game.get("home_points", 0)
        away_points = game.get("away_points", 0)
        
        if game["home_team"] == self.team_id:
            return home_points - away_points
        return away_points - home_points


def calculate_all_metrics(team_id: str, games: List[Dict], 
                         all_teams: Dict[str, Dict],
                         current_rankings: Dict[str, int]) -> Dict[str, float]:
    """Calculate all metrics for a team."""
    metrics = TeamMetrics(team_id, games, all_teams)
    
    return {
        "win_loss": metrics.win_loss_record(),
        "strength_of_schedule": metrics.strength_of_schedule(current_rankings),
        "strength_of_record": metrics.strength_of_record(current_rankings),
        "point_differential": metrics.point_differential(),
        "defensive_efficiency": metrics.defensive_efficiency(),
        "quality_wins": metrics.quality_wins(current_rankings),
        "championship_behavior": metrics.championship_behavior(current_rankings),
        "special_teams": metrics.special_teams(),
        "ball_control": metrics.ball_control(),
    }
