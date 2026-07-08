import sqlite3
from typing import List, Dict, Any
from pathlib import Path
from api_client import CFBDClient
from config import DB_PATH, PRIMARY_BACKTEST_START, PRIMARY_BACKTEST_END, ICONIC_SEASONS

def ingest_teams(client: CFBDClient, conn: sqlite3.Connection):
    """Fetch and store all teams."""
    cursor = conn.cursor()
    teams = client.get_teams()
    
    for team in teams:
        cursor.execute("""
            INSERT OR REPLACE INTO teams (school, conference, division, first_season, last_season)
            VALUES (?, ?, ?, ?, ?)
        """, (
            team.get("school"),
            team.get("conference"),
            team.get("division"),
            team.get("first_season"),
            team.get("last_season")
        ))
    
    conn.commit()
    print(f"Ingested {len(teams)} teams")

def ingest_games_for_season(client: CFBDClient, conn: sqlite3.Connection, season: int):
    """Fetch and store all games for a season."""
    cursor = conn.cursor()
    
    # Get regular season games
    games = client.get_games(season=season, season_type="regular")
    
    # Get postseason games
    postseason = client.get_games(season=season, season_type="postseason")
    games.extend(postseason)
    
    inserted = 0
    for game in games:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO games (
                    season, week, season_type, start_date, neutral_site, conference_game,
                    attendance, home_team, home_points, home_conference, home_division,
                    away_team, away_points, away_conference, away_division,
                    excitement_index, highlights, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                season,
                game.get("week"),
                game.get("season_type"),
                game.get("start_date"),
                game.get("neutral_site", False),
                game.get("conference_game", False),
                game.get("attendance"),
                game.get("home_team"),
                game.get("home_points"),
                game.get("home_conference"),
                game.get("home_division"),
                game.get("away_team"),
                game.get("away_points"),
                game.get("away_conference"),
                game.get("away_division"),
                game.get("excitement_index"),
                game.get("highlights"),
                game.get("notes")
            ))
            inserted += 1
        except Exception as e:
            print(f"Error inserting game: {e}")
            continue
    
    conn.commit()
    print(f"Ingested {inserted} games for season {season}")

def ingest_team_stats_for_season(client: CFBDClient, conn: sqlite3.Connection, season: int):
    """Fetch and store team statistics for a season."""
    cursor = conn.cursor()
    stats = client.get_team_stats(season=season)
    
    inserted = 0
    for stat in stats:
        team = stat.get("team")
        if not team:
            continue
            
        # Parse stats - the API returns a list of stat objects
        # Each stat has a category and stat value
        stats_dict = {}
        for s in stat.get("stats", []):
            stats_dict[s.get("category")] = s.get("stat")
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO team_stats (
                    season, team, conference, games, wins, losses, ties,
                    points_for, points_against, total_yards, passing_yards, rushing_yards,
                    turnovers, penalties, penalty_yards,
                    third_down_attempts, third_down_conversions,
                    fourth_down_attempts, fourth_down_conversions,
                    red_zone_attempts, red_zone_scores, time_of_possession
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                season,
                team,
                stat.get("conference"),
                stats_dict.get("games"),
                stats_dict.get("wins"),
                stats_dict.get("losses"),
                stats_dict.get("ties"),
                stats_dict.get("points"),
                stats_dict.get("pointsAllowed"),
                stats_dict.get("totalYards"),
                stats_dict.get("netPassingYards"),
                stats_dict.get("rushingYards"),
                stats_dict.get("turnovers"),
                stats_dict.get("penalties"),
                stats_dict.get("penaltyYards"),
                stats_dict.get("thirdDownAttempts"),
                stats_dict.get("thirdDownConversions"),
                stats_dict.get("fourthDownAttempts"),
                stats_dict.get("fourthDownConversions"),
                stats_dict.get("redZoneAttempts"),
                stats_dict.get("redZoneScores"),
                stats_dict.get("possessionTime")
            ))
            inserted += 1
        except Exception as e:
            print(f"Error inserting stats for {team}: {e}")
            continue
    
    conn.commit()
    print(f"Ingested {inserted} team stat records for season {season}")

def run_full_ingestion():
    """Run full data ingestion for all backtest seasons."""
    from database import init_db
    
    init_db()
    client = CFBDClient()
    conn = sqlite3.connect(DB_PATH)
    
    # Ingest teams (once)
    print("Ingesting teams...")
    ingest_teams(client, conn)
    
    # Determine all seasons to fetch
    all_seasons = list(range(PRIMARY_BACKTEST_START, PRIMARY_BACKTEST_END + 1))
    all_seasons.extend(ICONIC_SEASONS)
    all_seasons = sorted(set(all_seasons))
    
    print(f"\nFetching data for {len(all_seasons)} seasons...")
    for season in all_seasons:
        print(f"\n--- Season {season} ---")
        ingest_games_for_season(client, conn, season)
        ingest_team_stats_for_season(client, conn, season)
    
    conn.close()
    print("\nIngestion complete!")

if __name__ == "__main__":
    run_full_ingestion()
