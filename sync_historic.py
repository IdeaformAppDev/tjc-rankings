import sqlite3
import sys

# Source: workspace database with historic data
src_db = '/home/jason/.openclaw/workspace/CollegeFootballRanking/data/cfb_ranking.db'
# Dest: production database
dest_db = 'data/cfb_ranking.db'

src_conn = sqlite3.connect(src_db)
dest_conn = sqlite3.connect(dest_db)

src_cursor = src_conn.cursor()
dest_cursor = dest_conn.cursor()

# Get historic seasons from source
src_cursor.execute("SELECT DISTINCT season FROM games WHERE season < 2021")
historic_seasons = [row[0] for row in src_cursor.fetchall()]
print(f"Found historic seasons: {sorted(historic_seasons)}")

# Clear existing historic data from dest
for season in historic_seasons:
    dest_cursor.execute("DELETE FROM games WHERE season = ?", (season,))
    dest_cursor.execute("DELETE FROM rankings WHERE season = ?", (season,))
    print(f"Cleared existing data for {season}")

# Copy games (matching columns)
for season in historic_seasons:
    src_cursor.execute("""
        SELECT season, week, season_type, start_date, neutral_site, conference_game, attendance,
               home_team, home_id, home_conference, home_division, home_points, home_line_scores,
               away_team, away_id, away_conference, away_division, away_points, away_line_scores,
               completed, venue, notes
        FROM games WHERE season = ?
    """, (season,))
    
    games = src_cursor.fetchall()
    print(f"Copying {len(games)} games for {season}")
    
    for game in games:
        dest_cursor.execute("""
            INSERT INTO games (season, week, season_type, start_date, neutral_site, conference_game, attendance,
                home_team, home_id, home_conference, home_division, home_points, home_line_scores,
                away_team, away_id, away_conference, away_division, away_points, away_line_scores,
                completed, venue, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, game)

# Copy rankings
for season in historic_seasons:
    src_cursor.execute("""
        SELECT season, week, team_id, team_name, conference, composite_score,
               win_loss_rank, sos_rank, sor_rank, point_diff_rank,
               def_eff_rank, qual_wins_rank, champ_behavior_rank,
               special_teams_rank, ball_control_rank, overall_rank, created_at
        FROM rankings WHERE season = ?
    """, (season,))
    
    rankings = src_cursor.fetchall()
    print(f"Copying {len(rankings)} rankings for {season}")
    
    for rank in rankings:
        dest_cursor.execute("""
            INSERT INTO rankings (season, week, team_id, team_name, conference, composite_score,
                win_loss_rank, sos_rank, sor_rank, point_diff_rank,
                def_eff_rank, qual_wins_rank, champ_behavior_rank,
                special_teams_rank, ball_control_rank, overall_rank, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rank)

dest_conn.commit()
print("\n✅ Historic data synced!")

src_conn.close()
dest_conn.close()
