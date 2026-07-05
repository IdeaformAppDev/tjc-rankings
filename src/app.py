#!/usr/bin/env python3
"""
College Football Ranking System - Web Dashboard
Phase 3: Simple Flask app for viewing rankings
"""

import sqlite3
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify

DB_PATH = Path(__file__).parent.parent / "data" / "cfb_ranking.db"
TEMPLATE_PATH = Path(__file__).parent.parent / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_PATH))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    """Home page - season selector."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get available seasons
    cursor.execute("SELECT DISTINCT season FROM rankings ORDER BY season DESC")
    seasons = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return render_template("index.html", seasons=seasons)


@app.route("/season/<int:season>")
def season_rankings(season):
    """Show rankings for a specific season."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get rankings for this season (final = week 0 or max week)
    cursor.execute("""
        SELECT r.*, t.conference as conference
        FROM rankings r
        LEFT JOIN teams t ON r.team_id = t.id
        WHERE r.season = ? AND r.week = 0
        ORDER BY r.overall_rank
    """, (season,))
    
    rankings = cursor.fetchall()
    
    if not rankings:
        # Try to get the latest week for this season
        cursor.execute("""
            SELECT MAX(week) FROM rankings WHERE season = ?
        """, (season,))
        max_week = cursor.fetchone()[0]
        
        if max_week:
            cursor.execute("""
                SELECT r.*, t.conference as conference
                FROM rankings r
                LEFT JOIN teams t ON r.team_id = t.id
                WHERE r.season = ? AND r.week = ?
                ORDER BY r.overall_rank
            """, (season, max_week))
            rankings = cursor.fetchall()
    
    # Get conferences for filter
    cursor.execute("""
        SELECT DISTINCT t.conference 
        FROM rankings r
        LEFT JOIN teams t ON r.team_id = t.id
        WHERE r.season = ? AND r.week = 0
        ORDER BY t.conference
    """, (season,))
    conferences = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template("season.html", 
                         season=season, 
                         rankings=rankings,
                         conferences=conferences)


@app.route("/team/<team_name>")
def team_detail(team_name):
    """Show detailed breakdown for a team across seasons."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get team info
    cursor.execute("SELECT * FROM teams WHERE name = ?", (team_name,))
    team = cursor.fetchone()
    
    # Get all rankings for this team
    cursor.execute("""
        SELECT * FROM rankings 
        WHERE team_name = ?
        ORDER BY season DESC, week DESC
    """, (team_name,))
    rankings = cursor.fetchall()
    
    # Get games for the most recent season
    latest_season = None
    if rankings:
        latest_season = rankings[0]['season']
        cursor.execute("""
            SELECT * FROM games 
            WHERE (home_team = ? OR away_team = ?) AND season = ?
            ORDER BY start_date
        """, (team_name, team_name, latest_season))
        games = cursor.fetchall()
    else:
        games = []
    
    conn.close()
    
    return render_template("team.html", 
                         team_name=team_name,
                         team=team, 
                         rankings=rankings,
                         games=games)


@app.route("/api/rankings/<int:season>")
def api_rankings(season):
    """API endpoint for rankings data."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM rankings 
        WHERE season = ? AND week = 0
        ORDER BY overall_rank
    """, (season,))
    
    rankings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(rankings)


@app.route("/api/team/<team_name>")
def api_team(team_name):
    """API endpoint for team data."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM rankings 
        WHERE team_name = ?
        ORDER BY season DESC, week DESC
    """, (team_name,))
    
    rankings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(rankings)


@app.route("/compare")
def compare_teams():
    """Team comparison page."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get available seasons
    cursor.execute("SELECT DISTINCT season FROM rankings ORDER BY season DESC")
    seasons = [row[0] for row in cursor.fetchall()]
    
    # Get all team names
    cursor.execute("SELECT DISTINCT name FROM teams ORDER BY name")
    teams = [row[0] for row in cursor.fetchall()]
    
    team1_data = None
    team2_data = None
    
    team1_name = request.args.get('team1')
    team2_name = request.args.get('team2')
    season = request.args.get('season', type=int) or (seasons[0] if seasons else 2025)
    
    if team1_name and team2_name:
        # Get data for both teams
        cursor.execute("""
            SELECT * FROM rankings 
            WHERE season = ? AND team_name = ? AND week = 0
        """, (season, team1_name))
        team1_data = cursor.fetchone()
        
        cursor.execute("""
            SELECT * FROM rankings 
            WHERE season = ? AND team_name = ? AND week = 0
        """, (season, team2_name))
        team2_data = cursor.fetchone()
    
    conn.close()
    
    return render_template("compare.html",
                         seasons=seasons,
                         teams=teams,
                         team1_data=team1_data,
                         team2_data=team2_data)


@app.route("/conferences/<int:season>")
def conference_standings(season):
    """Show conference standings for a season."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get rankings grouped by conference
    cursor.execute("""
        SELECT r.*, t.conference
        FROM rankings r
        LEFT JOIN teams t ON r.team_id = t.id
        WHERE r.season = ? AND r.week = 0
        ORDER BY r.overall_rank
    """, (season,))
    
    rankings = cursor.fetchall()
    
    # Group by conference
    conferences = {}
    for team in rankings:
        conf = team['conference'] or 'Independent'
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(team)
    
    # Sort each conference by overall rank
    for conf in conferences:
        conferences[conf].sort(key=lambda x: x['overall_rank'])
    
    conn.close()
    
    return render_template("conferences.html",
                         season=season,
                         conferences=conferences)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
