"""Configuration for TJC Rankings algorithm."""

# API Settings
CFBD_API_BASE = "https://api.collegefootballdata.com"
CFBD_API_KEY = ""  # Set via environment variable: CFBD_API_KEY

# Season Settings
CURRENT_SEASON = 2025
FBS_CONFERENCES = [
    "ACC", "Big 12", "Big Ten", "SEC", "Pac-12",
    "American Athletic", "Conference USA", "MAC",
    "Mountain West", "Sun Belt", "FBS Independents"
]

# Metric Weights (must sum to 1.0)
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

# Algorithm Settings
MAX_ITERATIONS = 10
CONVERGENCE_THRESHOLD = 2  # Stop if ≤2 teams change position

# Point Differential Cap
POINT_DIFF_CAP = 28

# Quality Win Tiers
QUALITY_WIN_TIERS = {
    "top_10": {"min_rank": 1, "max_rank": 10, "points": 10},
    "top_25": {"min_rank": 11, "max_rank": 25, "points": 7},
    "top_40": {"min_rank": 26, "max_rank": 40, "points": 4},
}

# Championship Behavior Scoring
CHAMP_BEHAVIOR = {
    "close_win": 1,           # Win by ≤7 points
    "comeback_win": 2,       # Trailed in 4th quarter
    "road_win": 1,           # Win on the road
    "bad_loss": -3,          # Loss to unranked team (outside Top 50)
    "bad_blowout_loss": -5,  # Loss by >21 to unranked team
    "upset_loss": -4,        # Loss as heavy favorite (ranked 15+ spots higher)
    "close_loss_quality": 2,  # Lose by ≤7 to Top 25
}

# Garbage Time Threshold (4th quarter, leading by >21)
GARBAGE_TIME_LEAD = 21
