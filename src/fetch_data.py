#!/usr/bin/env python3
"""
College Football Ranking System - Data Pipeline
Fetches game results and team stats from CollegeFootballData.com API
"""

import json
import sqlite3
import requests
from pathlib import Path
from datetime import datetime

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)

API_KEY = config["api_key"]
BASE_URL = config["base_url"]
DB_PATH = Path(__file__).parent.parent / config["db_path"]

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def init_db():
    """Initialize SQLite database with schema."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            conference TEXT,
            division TEXT,
            location TEXT,
            mascot TEXT,
            abbreviation TEXT
        )
    """)
    
    # Games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT,
            start_date TEXT,
            neutral_site INTEGER,
            conference_game INTEGER,
            attendance INTEGER,
            home_team TEXT,
            home_id INTEGER,
            home_conference TEXT,
            home_division TEXT,
            home_points INTEGER,
            home_line_scores TEXT,
            away_team TEXT,
            away_id INTEGER,
            away_conference TEXT,
            away_division TEXT,
            away_points INTEGER,
            away_line_scores TEXT,
            completed INTEGER,
            venue TEXT,
            notes TEXT
        )
    """)
    
    # Rankings table (for our computed rankings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            composite_score REAL,
            win_loss_rank INTEGER,
            sos_rank INTEGER,
            sor_rank INTEGER,
            point_diff_rank INTEGER,
            def_eff_rank INTEGER,
            qual_wins_rank INTEGER,
            champ_behavior_rank INTEGER,
            special_teams_rank INTEGER,
            ball_control_rank INTEGER,
            overall_rank INTEGER,
            created_at TEXT
        )
    """)
    
    # Game stats table (for advanced metrics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            team_name TEXT,
            total_yards INTEGER,
            passing_yards INTEGER,
            rushing_yards INTEGER,
            turnovers INTEGER,
            penalties INTEGER,
            penalty_yards INTEGER,
            possession_time TEXT,
            third_down_conversions INTEGER,
            third_down_attempts INTEGER,
            fourth_down_conversions INTEGER,
            fourth_down_attempts INTEGER,
            first_downs INTEGER,
            red_zone_attempts INTEGER,
            red_zone_scores INTEGER,
            created_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def fetch_teams():
    """Fetch all FBS teams."""
    url = f"{BASE_URL}/teams/fbs"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def fetch_games(season: int, week: int = None, season_type: str = "regular"):
    """Fetch games for a given season/week."""
    params = {"year": season, "seasonType": season_type}
    if week:
        params["week"] = week
    
    url = f"{BASE_URL}/games"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def store_teams(teams_data):
    """Store FBS teams in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for team in teams_data:
        # Only store FBS teams
        classification = team.get("classification", "").lower()
        if classification != "fbs":
            continue
            
        cursor.execute("""
            INSERT OR REPLACE INTO teams 
            (id, name, conference, division, location, mascot, abbreviation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            team.get("id"),
            team.get("school"),
            team.get("conference"),
            team.get("division"),
            team.get("location", {}).get("city", ""),
            team.get("mascot"),
            team.get("abbreviation")
        ))
        count += 1
    
    conn.commit()
    conn.close()
    print(f"Stored {count} FBS teams")


def store_games(games_data):
    """Store games in database. Filter to FBS vs FBS only."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    skipped = 0
    for game in games_data:
        # Skip non-FBS games
        home_class = (game.get("homeClassification") or "").lower()
        away_class = (game.get("awayClassification") or "").lower()
        
        # Only include FBS vs FBS games
        if home_class != "fbs" or away_class != "fbs":
            skipped += 1
            continue
        
        # Skip games without scores
        if game.get("homePoints") is None or game.get("awayPoints") is None:
            skipped += 1
            continue
        cursor.execute("""
            INSERT OR REPLACE INTO games 
            (id, season, week, season_type, start_date, neutral_site, conference_game,
             attendance, home_team, home_id, home_conference, home_division, home_points,
             home_line_scores, away_team, away_id, away_conference, away_division,
             away_points, away_line_scores, completed, venue, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game.get("id"),
            game.get("season"),
            game.get("week"),
            game.get("seasonType"),
            game.get("startDate"),
            1 if game.get("neutralSite") else 0,
            1 if game.get("conferenceGame") else 0,
            game.get("attendance"),
            game.get("homeTeam"),
            game.get("homeId"),
            game.get("homeConference"),
            game.get("homeDivision"),
            game.get("homePoints"),
            json.dumps(game.get("homeLineScores", [])),
            game.get("awayTeam"),
            game.get("awayId"),
            game.get("awayConference"),
            game.get("awayDivision"),
            game.get("awayPoints"),
            json.dumps(game.get("awayLineScores", [])),
            1 if game.get("completed") else 0,
            game.get("venue"),
            game.get("notes")
        ))
        count += 1
    
    conn.commit()
    conn.close()
    print(f"Stored {count} games (skipped {skipped} non-FBS or incomplete)")


def fetch_team_stats(season: int, team: str = None):
    """Fetch advanced team stats for a season."""
    params = {"year": season}
    if team:
        params["team"] = team
    
    url = f"{BASE_URL}/stats/season/advanced"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def main():
    """Main entry point for Phase 1."""
    print("=== College Football Ranking System - Data Pipeline ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize database
    init_db()
    
    # Fetch and store teams
    print("\n--- Fetching Teams ---")
    teams = fetch_teams()
    store_teams(teams)
    
    # Fetch and store 2024 regular season games
    print("\n--- Fetching 2024 Games ---")
    games = fetch_games(season=2024, season_type="regular")
    store_games(games)
    
    # Fetch postseason games
    print("\n--- Fetching 2024 Postseason ---")
    postseason = fetch_games(season=2024, season_type="postseason")
    store_games(postseason)
    
    print("\n=== Phase 1 Complete ===")
    print(f"Database: {DB_PATH}")
    print(f"Teams: {len(teams)}")
    print(f"Games: {len(games) + len(postseason)}")


if __name__ == "__main__":
    main()
