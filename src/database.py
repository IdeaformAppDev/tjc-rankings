import sqlite3
from pathlib import Path
from config import DB_PATH

def init_db():
    """Initialize SQLite database with schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school TEXT NOT NULL,
            conference TEXT,
            division TEXT,
            first_season INTEGER,
            last_season INTEGER,
            UNIQUE(school)
        )
    """)
    
    # Games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT NOT NULL,
            start_date TEXT,
            neutral_site BOOLEAN,
            conference_game BOOLEAN,
            attendance INTEGER,
            home_team TEXT NOT NULL,
            home_points INTEGER,
            home_conference TEXT,
            home_division TEXT,
            away_team TEXT NOT NULL,
            away_points INTEGER,
            away_conference TEXT,
            away_division TEXT,
            excitement_index REAL,
            highlights TEXT,
            notes TEXT,
            UNIQUE(season, week, home_team, away_team)
        )
    """)
    
    # Team stats per season
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            team TEXT NOT NULL,
            conference TEXT,
            games INTEGER,
            wins INTEGER,
            losses INTEGER,
            ties INTEGER,
            points_for INTEGER,
            points_against INTEGER,
            total_yards INTEGER,
            passing_yards INTEGER,
            rushing_yards INTEGER,
            turnovers INTEGER,
            penalties INTEGER,
            penalty_yards INTEGER,
            third_down_attempts INTEGER,
            third_down_conversions INTEGER,
            fourth_down_attempts INTEGER,
            fourth_down_conversions INTEGER,
            red_zone_attempts INTEGER,
            red_zone_scores INTEGER,
            time_of_possession INTEGER,  -- in seconds
            UNIQUE(season, team)
        )
    """)
    
    # Weekly rankings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            team TEXT NOT NULL,
            rank INTEGER NOT NULL,
            composite_score REAL NOT NULL,
            win_loss_score REAL,
            sos_score REAL,
            sor_score REAL,
            point_diff_score REAL,
            def_eff_score REAL,
            quality_wins_score REAL,
            champ_behavior_score REAL,
            special_teams_score REAL,
            ball_control_score REAL,
            UNIQUE(season, week, team)
        )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team, away_team)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_stats_season ON team_stats(season)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rankings_season_week ON rankings(season, week)")
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
