import requests
import time
from typing import Optional, List, Dict, Any
from config import CFBD_API_KEY, CFBD_BASE_URL

class CFBDClient:
    """Client for CollegeFootballData.com API."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {CFBD_API_KEY}",
            "Accept": "application/json"
        })
        self.last_request_time = 0
        self.min_delay = 0.5  # seconds between requests (rate limiting)
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Make a GET request to the API."""
        self._rate_limit()
        
        url = f"{CFBD_BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return []
    
    def get_games(self, season: int, week: Optional[int] = None, 
                   season_type: str = "regular", team: Optional[str] = None,
                   conference: Optional[str] = None) -> List[Dict]:
        """Fetch games for a season/week."""
        params = {"season": season, "seasonType": season_type}
        if week:
            params["week"] = week
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        
        return self._get("/games", params)
    
    def get_team_stats(self, season: int, team: Optional[str] = None,
                       conference: Optional[str] = None) -> List[Dict]:
        """Fetch team statistics for a season."""
        params = {"year": season}
        if team:
            params["team"] = team
        if conference:
            params["conference"] = conference
        
        return self._get("/stats/season", params)
    
    def get_teams(self) -> List[Dict]:
        """Fetch all teams."""
        return self._get("/teams")
    
    def get_team_records(self, season: int, team: Optional[str] = None) -> List[Dict]:
        """Fetch team records for a season."""
        params = {"year": season}
        if team:
            params["team"] = team
        
        return self._get("/records", params)
    
    def get_conferences(self) -> List[Dict]:
        """Fetch all conferences."""
        return self._get("/conferences")

if __name__ == "__main__":
    # Test the client
    client = CFBDClient()
    teams = client.get_teams()
    print(f"Fetched {len(teams)} teams")
    if teams:
        print(f"Sample: {teams[0]['school']}")
