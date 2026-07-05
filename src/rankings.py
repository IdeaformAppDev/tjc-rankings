"""Core iterative ranking algorithm."""

from typing import Dict, List, Tuple
from collections import defaultdict

from config import WEIGHTS, MAX_ITERATIONS, CONVERGENCE_THRESHOLD
from metrics import calculate_all_metrics


class RankingEngine:
    """Iterative ranking solver."""
    
    def __init__(self, games: List[Dict], all_teams: Dict[str, Dict]):
        self.games = games
        self.all_teams = all_teams
        self.team_ids = list(all_teams.keys())
        self.current_rankings = {team: 65 for team in self.team_ids}  # Start neutral
    
    def compute_rankings(self) -> List[Tuple[str, float, Dict]]:
        """
        Run iterative ranking until convergence.
        Returns: [(team_id, composite_score, metrics_dict), ...] sorted by score
        """
        print("Starting iterative ranking...")
        
        for iteration in range(MAX_ITERATIONS):
            print(f"\nIteration {iteration + 1}/{MAX_ITERATIONS}")
            
            # Store previous rankings for convergence check
            previous_rankings = dict(self.current_rankings)
            
            # Calculate scores for all teams
            team_scores = {}
            for team_id in self.team_ids:
                metrics = calculate_all_metrics(
                    team_id, self.games, self.all_teams, self.current_rankings
                )
                composite = self._calculate_composite(metrics)
                team_scores[team_id] = (composite, metrics)
            
            # Update rankings based on composite scores
            sorted_teams = sorted(team_scores.items(), 
                                key=lambda x: x[1][0], reverse=True)
            
            for rank, (team_id, _) in enumerate(sorted_teams, 1):
                self.current_rankings[team_id] = rank
            
            # Check convergence
            changes = sum(1 for team in self.team_ids 
                         if previous_rankings[team] != self.current_rankings[team])
            
            print(f"Teams changing position: {changes}")
            
            if changes <= CONVERGENCE_THRESHOLD:
                print(f"Converged after {iteration + 1} iterations!")
                break
        
        # Final sort with metrics
        final_results = []
        for team_id in self.team_ids:
            metrics = calculate_all_metrics(
                team_id, self.games, self.all_teams, self.current_rankings
            )
            composite = self._calculate_composite(metrics)
            final_results.append((team_id, composite, metrics))
        
        # Sort by composite score descending
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results
    
    def _calculate_composite(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted composite score from individual metrics."""
        composite = 0.0
        
        for metric_name, weight in WEIGHTS.items():
            if metric_name in metrics:
                composite += metrics[metric_name] * weight
        
        # Normalize to 0-100 scale
        return composite * 100
    
    def get_ranking_delta(self, previous_rankings: Dict[str, int]) -> Dict[str, int]:
        """Calculate movement from previous week's rankings."""
        deltas = {}
        for team_id in self.team_ids:
            current_rank = self.current_rankings.get(team_id, 999)
            previous_rank = previous_rankings.get(team_id, 999)
            deltas[team_id] = previous_rank - current_rank  # Positive = moved up
        return deltas


def generate_rankings_report(results: List[Tuple[str, float, Dict]], 
                            season: int, week: int) -> str:
    """Generate a Markdown report of the rankings."""
    lines = [
        f"# TJC Rankings — Week {week}, {season} Season",
        "",
        "*Computer-generated rankings using transparent algorithmic methodology*",
        "",
        "## Top 25",
        "",
        "| Rank | Team | Record | Score |",
        "|------|------|--------|-------|",
    ]
    
    for rank, (team_id, score, metrics) in enumerate(results[:25], 1):
        # Get record from metrics
        wins = int(metrics["win_loss"] * 12)  # Rough estimate
        losses = 12 - wins
        record = f"{wins}-{losses}"
        
        lines.append(f"| {rank} | {team_id} | {record} | {score:.1f} |")
    
    lines.extend([
        "",
        "## Methodology",
        "",
        "Rankings are computed using 9 normalized metrics:",
        "",
    ])
    
    for metric_name, weight in WEIGHTS.items():
        lines.append(f"- **{metric_name.replace('_', ' ').title()}** ({weight*100:.0f}%)")
    
    lines.extend([
        "",
        "## Data Sources",
        "",
        "- [CollegeFootballData.com](https://api.collegefootballdata.com/)",
        "",
        "---",
        "",
        f"*Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M ET')}*",
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with sample data
    print("Ranking engine ready for testing!")
    print("Run fetch_games.py first to get real data.")
