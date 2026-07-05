"""Fetch game data from CollegeFootballData.com API."""

import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

from config import CFBD_API_BASE, CFBD_API_KEY, CURRENT_SEASON


class CFBDClient:
    """Client for CollegeFootballData.com API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CFBD_API_KEY", "")
        self.base_url = CFBD_API_BASE
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params or {})
        response.raise_for_status()
        return response.json()
    
    def get_games(self, season: int = CURRENT_SEASON, week: Optional[int] = None,
                  season_type: str = "regular", team: Optional[str] = None) -> List[Dict]:
        """Fetch games for a season/week."""
        params = {
            "year": season,
            "seasonType": season_type,
        }
        if week:
            params["week"] = week
        if team:
            params["team"] = team
        
        return self._get("games", params)
    
    def get_team_stats(self, season: int = CURRENT_SEASON, 
                       season_type: str = "regular") -> List[Dict]:
        """Fetch team statistics."""
        params = {
            "year": season,
            "seasonType": season_type,
        }
        return self._get("stats/season", params)
    
    def get_teams(self) -> List[Dict]:
        """Fetch all FBS teams."""
        return self._get("teams/fbs")
    
    def get_lines(self, season: int = CURRENT_SEASON, week: Optional[int] = None) -> List[Dict]:
        """Fetch betting lines (optional)."""
        params = {"year": season}
        if week:
            params["week"] = week
        return self._get("lines", params)


def fetch_season_data(season: int = CURRENT_SEASON) -> Dict:
    """Fetch all data needed for a season's rankings."""
    client = CFBDClient()
    
    print(f"Fetching data for {season} season...")
    
    # Get all teams
    teams = client.get_teams()
    print(f"Found {len(teams)} FBS teams")
    
    # Get all games
    games = client.get_games(season=season)
    print(f"Found {len(games)} games")
    
    # Get team stats
    try:
        stats = client.get_team_stats(season=season)
        print(f"Found stats for {len(stats)} teams")
    except Exception as e:
        print(f"Warning: Could not fetch team stats: {e}")
        stats = []
    
    return {
        "teams": teams,
        "games": games,
        "stats": stats,
        "season": season,
    }


if __name__ == "__main__":
    # Test fetch
    data = fetch_season_data()
    print(f"\nSample team: {data['teams'][0]['school']}")
    print(f"Sample game: {data['games'][0]['home_team']} vs {data['games'][0]['away_team']}")
