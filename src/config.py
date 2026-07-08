import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "cfb_rankings.db"

# API
CFBD_API_KEY = os.getenv("CFBD_API_KEY")
CFBD_BASE_URL = "https://api.collegefootballdata.com"

# Backtest scope
PRIMARY_BACKTEST_START = 2000
PRIMARY_BACKTEST_END = 2025

# Iconic seasons for spot-checking
ICONIC_SEASONS = [
    1961,   # Alabama's first Bear Bryant title
    1966,   # Notre Dame vs Michigan State tie controversy
    1969,   # Texas vs Arkansas (Game of the Century)
    1971,   # Nebraska's dominant team
    1983,   # Auburn (contested — beat #1 Georgia, #1 Alabama, but no title)
    1988,   # Notre Dame
    1993,   # FSU vs Notre Dame split
    1997,   # Michigan vs Nebraska split title
    2004,   # Auburn undefeated, left out of BCS
]

# Algorithm weights (must sum to 1.0)
WEIGHTS = {
    "win_loss": 0.20,
    "strength_of_schedule": 0.20,
    "strength_of_record": 0.15,
    "point_differential": 0.10,
    "defensive_efficiency": 0.10,
    "quality_wins": 0.10,
    "championship_behavior": 0.10,
    "special_teams": 0.03,
    "ball_control": 0.02,
}

# Point differential cap
MAX_POINT_DIFF = 28

# Iterative ranking
MAX_ITERATIONS = 10
RANKING_CONVERGENCE_THRESHOLD = 2  # teams changing positions
