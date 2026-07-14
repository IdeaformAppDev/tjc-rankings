"""Generate static HTML pages for TJC Rankings website."""

import sys
sys.path.insert(0, 'src')
from ranking_engine import RankingEngine
from collections import defaultdict
import sqlite3
import urllib.parse

# Generate rankings for all seasons (modern + iconic)
seasons = [1961, 1966, 1969, 1971, 1983, 1988, 1993, 1997, 2004, 2007, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
all_rankings = {}

for season in seasons:
    try:
        engine = RankingEngine(season=season, week=16)
        results, metadata = engine.run()
        all_rankings[season] = results
        print(f"Generated {season}: {results[0].team_name} #1")
    except Exception as e:
        print(f"Skipping {season}: {e}")

def get_header(title, rankings_active="", conferences_active="", about_active=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="assets/favicon-16x16.png">
    <link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Sans+Pro:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a365d;
            --accent: #c53030;
            --gold: #d69e2e;
            --bg: #f7fafc;
            --text: #2d3748;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Source Sans Pro', sans-serif;
            background: var(--bg);
            color: var(--text);
        }}
        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, #2c5282 100%);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}
        .logo {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 3px solid var(--gold);
            background: white;
            padding: 4px;
            flex-shrink: 0;
        }}
        .logo img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            border-radius: 50%;
        }}
        .brand-text {{ flex: 1; }}
        .brand-name {{
            font-family: 'Playfair Display', serif;
            font-size: 2rem;
            font-weight: 900;
            letter-spacing: -0.02em;
            line-height: 1.1;
        }}
        .brand-name span {{ color: var(--gold); }}
        .brand-tagline {{
            font-size: 0.95rem;
            opacity: 0.9;
            margin-top: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 600;
        }}
        .nav {{
            background: white;
            border-bottom: 2px solid #e2e8f0;
            padding: 0.75rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .nav-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            gap: 2rem;
            align-items: center;
        }}
        .nav a {{
            text-decoration: none;
            color: var(--text);
            font-weight: 600;
            padding: 0.5rem 0;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
        }}
        .nav a:hover, .nav a.active {{
            color: var(--accent);
            border-bottom-color: var(--accent);
        }}
        .season-dropdown {{
            margin-left: auto;
            padding: 0.5rem;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 0.9rem;
            cursor: pointer;
        }}
        .main {{
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 2rem;
        }}
        .rankings-table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        .rankings-table th {{
            background: var(--primary);
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
        }}
        .rankings-table td {{
            padding: 0.75rem 0.5rem;
            border-bottom: 1px solid #e2e8f0;
            font-size: 0.9rem;
        }}
        .rankings-table tr:hover {{ background: #f7fafc; }}
        .rank {{
            font-family: 'Playfair Display', serif;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent);
            width: 60px;
        }}
        .team-name {{
            font-weight: 600;
            color: var(--primary);
            text-decoration: none;
        }}
        a.team-name:hover {{
            color: var(--accent);
            text-decoration: underline;
        }}
        .conference {{
            font-size: 0.875rem;
            color: #718096;
        }}
        .record {{
            font-weight: 600;
            text-align: center;
        }}
        .score {{
            font-weight: 700;
            text-align: right;
            color: var(--primary);
        }}
        .metric-cell {{
            text-align: center;
            font-size: 0.85rem;
        }}
        .metric-high {{ color: #38a169; font-weight: 600; }}
        .metric-mid {{ color: #d69e2e; }}
        .metric-low {{ color: var(--accent); }}
        .h2h-badge {{
            display: inline-block;
            background: var(--gold);
            color: white;
            font-size: 0.75rem;
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
            margin-left: 0.3rem;
            font-weight: 700;
        }}
        .metrics-legend {{
            background: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metrics-legend h3 {{
            font-family: 'Playfair Display', serif;
            color: var(--primary);
            margin-bottom: 0.75rem;
            font-size: 1rem;
        }}
        .metrics-legend p {{
            font-size: 0.85rem;
            color: #718096;
            line-height: 1.5;
        }}
        .footer {{
            background: var(--primary);
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
            text-align: center;
        }}
        .footer-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }}
        .footer-brand {{
            font-family: 'Playfair Display', serif;
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }}
        .footer-brand span {{ color: var(--gold); }}
        .footer-links {{
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            margin: 1rem 0;
            flex-wrap: wrap;
        }}
        .footer-links a {{
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.2s;
        }}
        .footer-links a:hover {{ color: var(--gold); }}
        .footer-disclaimer {{
            font-size: 0.8rem;
            opacity: 0.7;
            margin-top: 1rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}
        .content-section {{
            background: white;
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .content-section h2 {{
            font-family: 'Playfair Display', serif;
            color: var(--primary);
            margin-bottom: 1rem;
        }}
        .content-section p {{
            line-height: 1.6;
            margin-bottom: 1rem;
        }}
        .metric-list {{
            list-style: none;
            padding: 0;
        }}
        .metric-list li {{
            padding: 0.5rem 0;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
        }}
        .metric-weight {{
            color: var(--accent);
            font-weight: 600;
        }}
        .conference-standings {{
            margin-bottom: 2rem;
        }}
        .conference-standings h3 {{
            font-family: 'Playfair Display', serif;
            color: var(--primary);
            margin: 1.5rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--gold);
        }}
        .conference-nav {{
            margin-bottom: 2rem;
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .conference-nav label {{
            font-weight: 600;
            color: var(--primary);
            margin-right: 0.5rem;
        }}
        .conference-select {{
            padding: 0.5rem;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 0.9rem;
            cursor: pointer;
            min-width: 200px;
        }}
        /* Team Detail Page */
        .team-header {{
            background: linear-gradient(135deg, var(--primary) 0%, #2c5282 100%);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
        }}
        .team-header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }}
        .team-header h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        .team-header .team-meta {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        .team-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-family: 'Playfair Display', serif;
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }}
        .stat-label {{
            font-size: 0.875rem;
            color: #718096;
            margin-top: 0.25rem;
        }}
        .games-table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .games-table th {{
            background: var(--primary);
            color: white;
            padding: 1rem;
            text-align: left;
        }}
        .games-table td {{
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        .win {{ color: #38a169; font-weight: 600; }}
        .loss {{ color: var(--accent); font-weight: 600; }}
        /* Social Sharing */
        .share-section {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .share-title {{
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 0.75rem;
        }}
        .share-buttons {{
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        .share-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }}
        .share-btn:hover {{ opacity: 0.85; }}
        .share-x {{ background: #000; color: white; }}
        .share-fb {{ background: #1877f2; color: white; }}
        .share-copy {{ background: #e2e8f0; color: var(--text); }}
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                text-align: center;
                gap: 1rem;
            }}
            .logo {{ width: 80px; height: 80px; }}
            .brand-name {{ font-size: 1.5rem; }}
            .nav-content {{
                overflow-x: auto;
                gap: 1rem;
            }}
            .season-dropdown {{ margin-left: 0; }}
            .team-stats {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <img src="assets/tjc-rankings-logo.png" alt="TJC Rankings Logo">
            </div>
            <div class="brand-text">
                <div class="brand-name">TJC <span>Rankings</span></div>
                <div class="brand-tagline">Computer College Football Rankings</div>
            </div>
        </div>
    </header>
    <nav class="nav">
        <div class="nav-content">
            <a href="index.html"{rankings_active}>Rankings</a>
            <a href="conferences.html"{conferences_active}>Conferences</a>
            <a href="about.html"{about_active}>About the Model</a>
            <select class="season-dropdown" onchange="window.location.href=this.value">
                <option value="">Past Seasons</option>
                <option value="2025.html">2025</option>
                <option value="2024.html">2024</option>
                <option value="2023.html">2023</option>
                <option value="2022.html">2022</option>
                <option value="2021.html">2021</option>
                <option value="2020.html">2020</option>
                <option value="2019.html">2019</option>
                <option value="2018.html">2018</option>
                <option value="2017.html">2017</option>
                <option value="2016.html">2016</option>
                <option value="2015.html">2015</option>
                <option value="">—— Historic ——</option>
                <option value="2007.html">2007 (Kansas #3)</option>
                <option value="2004.html">2004 (Auburn Screwed)</option>
                <option value="1997.html">1997 (Split Title)</option>
                <option value="1993.html">1993 (FSU #1)</option>
                <option value="1988.html">1988 (ND over Miami)</option>
                <option value="1983.html">1983 (Auburn Vindicated)</option>
                <option value="1971.html">1971 (Nebraska)</option>
                <option value="1969.html">1969 (Texas/PSU)</option>
                <option value="1966.html">1966 (ND/MSU)</option>
                <option value="1961.html">1961 (Bryant's First at Alabama)</option>
            </select>
        </div>
    </nav>
    <main class="main">
"""

footer_html = """
    </main>
    <footer class="footer">
        <div class="footer-content">
            <div class="footer-brand">TJC <span>Rankings</span></div>
            <div class="footer-links">
                <a href="about.html">About the Model</a>
                <a href="#">Data Sources</a>
                <a href="https://github.com/IdeaformAppDev/tjc-rankings" target="_blank">GitHub ↗</a>
                <a href="about.html">Methodology</a>
            </div>
            <div class="footer-disclaimer">
                Rankings generated algorithmically. No human bias, no conference favoritism — just math.
                Data corrections welcome via GitHub issues.
            </div>
        </div>
    </footer>
</body>
</html>
"""

def slugify(name):
    """Convert team name to URL-safe slug."""
    return urllib.parse.quote(name.lower().replace(' ', '-'))

def generate_rankings_table(results, season, week):
    html = f'<h1 style="font-family: \'Playfair Display\', serif; margin-bottom: 1.5rem; color: var(--primary);">Final Rankings — {season} Season</h1>\n'
    
    # Metrics legend
    html += '<div class="metrics-legend">\n'
    html += '<h3>📊 Understanding the Metrics</h3>\n'
    html += '<p><strong>WL:</strong> Win/Loss (10%) • <strong>SOS:</strong> Strength of Schedule (25%) • <strong>SOR:</strong> Strength of Record (20%) • <strong>PD:</strong> Point Differential (capped at ±28/game, opponent-aware) 5% • <strong>DE:</strong> Defensive Efficiency (10%) • <strong>QW:</strong> Quality Wins (15%) • <strong>CB:</strong> Championship Behavior (10%)</p>\n'
    html += '<p><span class="h2h-badge">↗</span> = Head-to-Head tiebreaker applied (team ranked above opponent with higher composite score)</p>\n'
    html += '</div>\n'
    
    html += '<table class="rankings-table">\n<thead>\n<tr><th>Rank</th><th>Team</th><th>Conf</th><th>Rec</th><th style="text-align: right;">Score</th><th class="metric-cell">WL</th><th class="metric-cell">SOS</th><th class="metric-cell">SOR</th><th class="metric-cell">PD</th><th class="metric-cell">DE</th><th class="metric-cell">QW</th><th class="metric-cell">CB</th></tr>\n</thead>\n<tbody>\n'
    
    for rank, team in enumerate(results[:25], 1):
        record = f"{team.wins}-{team.losses}"
        team_slug = slugify(team.team_name)
        
        # Color-code metrics
        def metric_class(score):
            if score >= 75: return 'metric-high'
            elif score >= 50: return 'metric-mid'
            else: return 'metric-low'
        
        html += f'<tr><td class="rank">{rank}</td><td><a href="team-{season}-{team_slug}.html" class="team-name">{team.team_name}</a>{" <span class=\"h2h-badge\">↗</span>" if team.h2h_override else ""}</td><td class="conference">{team.conference}</td><td class="record">{record}</td><td class="score">{team.composite_score:.1f}</td>'
        html += f'<td class="metric-cell {metric_class(team.win_loss_score)}">{team.win_loss_score:.0f}</td>'
        html += f'<td class="metric-cell {metric_class(team.sos_score)}">{team.sos_score:.0f}</td>'
        html += f'<td class="metric-cell {metric_class(team.sor_score)}">{team.sor_score:.0f}</td>'
        html += f'<td class="metric-cell {metric_class(team.point_diff_score)}">{team.point_diff_score:.0f}</td>'
        html += f'<td class="metric-cell {metric_class(team.def_eff_score)}">{team.def_eff_score:.0f}</td>'
        html += f'<td class="metric-cell {metric_class(team.qual_wins_score)}">{team.qual_wins_score:.0f}</td>'
        html += f'<td class="metric-cell {metric_class(team.champ_behavior_score)}">{team.champ_behavior_score:.0f}</td>'
        html += '</tr>\n'
    
    html += '</tbody>\n</table>\n'
    return html

def generate_conference_standings(results, season):
    conferences = defaultdict(list)
    for team in results:
        conferences[team.conference].append(team)
    
    html = f'<h1 style="font-family: \'Playfair Display\', serif; margin-bottom: 1.5rem; color: var(--primary);">Conference Standings — {season} Season</h1>\n'
    
    # Conference dropdown
    html += '<div class="conference-nav">\n'
    html += '<label for="conf-select">Jump to Conference:</label>\n'
    html += '<select id="conf-select" class="conference-select" onchange="window.location.hash=this.value">\n'
    html += '<option value="">Select a conference...</option>\n'
    for conf_name in sorted(conferences.keys()):
        conf_id = conf_name.lower().replace(' ', '-').replace('&', 'and')
        html += f'<option value="{conf_id}">{conf_name}</option>\n'
    html += '</select>\n</div>\n'
    
    for conf_name in sorted(conferences.keys()):
        conf_id = conf_name.lower().replace(' ', '-').replace('&', 'and')
        teams = sorted(conferences[conf_name], key=lambda t: t.composite_score, reverse=True)
        html += f'<div class="conference-standings" id="{conf_id}">\n'
        html += f'<h3>{conf_name}</h3>\n'
        html += '<table class="rankings-table">\n<thead>\n<tr><th>Rank</th><th>Team</th><th>Record</th><th style="text-align: right;">Score</th></tr>\n</thead>\n<tbody>\n'
        for rank, team in enumerate(teams[:10], 1):
            record = f"{team.wins}-{team.losses}"
            team_slug = slugify(team.team_name)
            html += f'<tr><td class="rank">{rank}</td><td><a href="team-{season}-{team_slug}.html" class="team-name">{team.team_name}</a></td><td class="record">{record}</td><td class="score">{team.composite_score:.1f}</td></tr>\n'
        html += '</tbody>\n</table>\n</div>\n'
    
    return html

def generate_team_page(team, season, results):
    """Generate a team detail page with stats and games."""
    conn = sqlite3.connect('data/cfb_ranking.db')
    cursor = conn.cursor()
    
    # Get team rank
    team_rank = None
    for i, t in enumerate(results, 1):
        if t.team_name == team.team_name:
            team_rank = i
            break
    
    # Get games with season_type
    cursor.execute('''
        SELECT g.home_team, g.away_team, g.home_points, g.away_points, g.week, g.season_type, g.start_date
        FROM games g
        WHERE (g.home_team = ? OR g.away_team = ?) AND g.season = ? AND g.completed = 1
        ORDER BY g.start_date
    ''', (team.team_name, team.team_name, season))
    
    games = cursor.fetchall()
    conn.close()
    
    # Calculate stats
    total_games = len(games)
    wins = sum(1 for g in games if (g[0] == team.team_name and g[2] > g[3]) or (g[1] == team.team_name and g[3] > g[2]))
    losses = total_games - wins
    points_for = sum(g[2] if g[0] == team.team_name else g[3] for g in games)
    points_against = sum(g[3] if g[0] == team.team_name else g[2] for g in games)
    
    team_slug = slugify(team.team_name)
    page_url = f"https://tjcrankings.com/team-{season}-{team_slug}.html"
    share_text = f"TJC Rankings has {team.team_name} ranked #{team_rank} in {season} with a {wins}-{losses} record!"
    
    html = get_header(f"{team.team_name} — {season} Season — TJC Rankings")
    
    # Team header
    html += f'''
    <div class="team-header">
        <div class="team-header-content">
            <h1>{team.team_name}</h1>
            <div class="team-meta">{season} Season • {team.conference} • Rank #{team_rank}</div>
        </div>
    </div>
    '''
    
    # Stats cards
    html += '<div class="team-stats">\n'
    html += f'<div class="stat-card"><div class="stat-value">{wins}-{losses}</div><div class="stat-label">Record</div></div>\n'
    html += f'<div class="stat-card"><div class="stat-value">{team.composite_score:.1f}</div><div class="stat-label">Composite Score</div></div>\n'
    html += f'<div class="stat-card"><div class="stat-value">{points_for}</div><div class="stat-label">Points For</div></div>\n'
    html += f'<div class="stat-card"><div class="stat-value">{points_against}</div><div class="stat-label">Points Against</div></div>\n'
    html += f'<div class="stat-card"><div class="stat-value">{points_for - points_against:+d}</div><div class="stat-label">Point Diff</div></div>\n'
    html += f'<div class="stat-card"><div class="stat-value">{total_games}</div><div class="stat-label">Games Played</div></div>\n'
    html += '</div>\n'
    
    # Metrics breakdown
    html += '<h2 style="font-family: \'Playfair Display\', serif; margin-bottom: 1rem; color: var(--primary);">Metric Breakdown</h2>\n'
    html += '<div class="content-section" style="margin-bottom: 2rem;">\n'
    html += '<p style="margin-bottom: 1rem; color: #718096; font-size: 0.9rem;">How {team.team_name} scores across all 7 factors (0-100 scale). Higher is better.</p>\n'
    html += '<ul class="metric-list">\n'
    html += f'<li>Win/Loss Record (10%) <span class="metric-weight">{team.win_loss_score:.1f}</span></li>\n'
    html += f'<li>Strength of Schedule (25%) <span class="metric-weight">{team.sos_score:.1f}</span></li>\n'
    html += f'<li>Strength of Record (20%) <span class="metric-weight">{team.sor_score:.1f}</span></li>\n'
    html += f'<li>Point Differential (capped at ±28/game, opponent-aware) (5%) <span class="metric-weight">{team.point_diff_score:.1f}</span></li>\n'
    html += f'<li>Defensive Efficiency (10%) <span class="metric-weight">{team.def_eff_score:.1f}</span></li>\n'
    html += f'<li>Quality Wins (15%) <span class="metric-weight">{team.qual_wins_score:.1f}</span></li>\n'
    html += f'<li>Championship Behavior (10%) <span class="metric-weight">{team.champ_behavior_score:.1f}</span></li>\n'
    html += '</ul>\n'
    html += '</div>\n'
    
    # Social sharing
    html += '<div class="share-section">\n'
    html += '<div class="share-title">Share these rankings</div>\n'
    html += '<div class="share-buttons">\n'
    html += f'<a href="https://twitter.com/intent/tweet?text={urllib.parse.quote(share_text)}&url={urllib.parse.quote(page_url)}" target="_blank" class="share-btn share-x">𝕏 Share on X</a>\n'
    html += f'<a href="https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(page_url)}" target="_blank" class="share-btn share-fb">f Share on Facebook</a>\n'
    html += f'<button class="share-btn share-copy" onclick="navigator.clipboard.writeText(\'{page_url}\');this.textContent=\'Copied!\';setTimeout(()=>this.textContent=\'Copy Link\',2000)">Copy Link</button>\n'
    html += '</div>\n</div>\n'
    
    # Games table
    html += '<h2 style="font-family: \'Playfair Display\', serif; margin-bottom: 1rem; color: var(--primary);">Game Log</h2>\n'
    html += '<table class="games-table">\n<thead>\n<tr><th>Week</th><th>Type</th><th>Opponent</th><th>Result</th><th>Score</th></tr>\n</thead>\n<tbody>\n'
    
    for game in games:
        week = game[4]
        season_type = game[5]
        is_home = game[0] == team.team_name
        opponent = game[1] if is_home else game[0]
        team_score = game[2] if is_home else game[3]
        opp_score = game[3] if is_home else game[2]
        won = team_score > opp_score
        result_class = "win" if won else "loss"
        result_text = "W" if won else "L"
        
        # Format week label
        if season_type == 'postseason':
            week_label = 'Postseason'
        else:
            week_label = f"Week {week}"
        
        html += f'<tr><td>{week_label}</td><td>{season_type.title()}</td><td>{"vs" if is_home else "@"} {opponent}</td><td class="{result_class}">{result_text}</td><td>{team_score}-{opp_score}</td></tr>\n'
    
    html += '</tbody>\n</table>\n'
    html += footer_html
    
    return html

# Generate pages for each season
for season in seasons:
    results = all_rankings[season]
    
    rankings_active = ' class="active"' if season == 2025 else ''
    
    # Season page
    page_html = get_header(f"Final Rankings — {season} Season", rankings_active=rankings_active)
    page_html += generate_rankings_table(results, season, 16)
    page_html += footer_html
    
    filename = f'docs/{season}.html'
    with open(filename, 'w') as f:
        f.write(page_html)
    print(f"Generated {filename}")
    
    # Generate team pages for top 25
    for team in results[:25]:
        team_html = generate_team_page(team, season, results)
        team_slug = slugify(team.team_name)
        team_filename = f'docs/team-{season}-{team_slug}.html'
        with open(team_filename, 'w') as f:
            f.write(team_html)
        print(f"Generated {team_filename}")

# Generate index.html (2025)
results = all_rankings[2025]
page_html = get_header("TJC Rankings — Computer College Football Rankings", rankings_active=' class="active"')
page_html += generate_rankings_table(results, 2025, 16)
page_html += footer_html

with open('docs/index.html', 'w') as f:
    f.write(page_html)
print("Generated docs/index.html")

# Generate conferences.html (2025)
page_html = get_header("Conference Standings — TJC Rankings", conferences_active=' class="active"')
page_html += generate_conference_standings(all_rankings[2025], 2025)
page_html += footer_html

with open('docs/conferences.html', 'w') as f:
    f.write(page_html)
print("Generated docs/conferences.html")

# Generate about.html
about_content = """
<h1 style="font-family: 'Playfair Display', serif; margin-bottom: 1.5rem; color: var(--primary);">About the Model</h1>

<div class="content-section">
    <h2>Algorithmic Rankings</h2>
    <p>TJC Rankings uses a transparent, iterative algorithm to rank college football teams based on actual game data. No human bias, no conference favoritism — just math.</p>
    <p>The model runs up to 10 iterations, recalculating team strengths based on opponent quality until rankings stabilize (typically 4-7 iterations).</p>
</div>

<div class="content-section">
    <h2>7 Metrics (Weighted)</h2>
    <ul class="metric-list">
        <li>Win/Loss Record <span class="metric-weight">15%</span></li>
        <li>Strength of Schedule <span class="metric-weight">28%</span></li>
        <li>Strength of Record <span class="metric-weight">20%</span></li>
        <li>Point Differential <span class="metric-weight">10%</span> (capped at ±28/game)</li>
        <li>Defensive Efficiency <span class="metric-weight">10%</span></li>
        <li>Quality Wins <span class="metric-weight">7%</span></li>
        <li>Championship Behavior <span class="metric-weight">10%</span></li>
    </ul>
</div>

<div class="content-section">
    <h2>Data Sources</h2>
    <p>All game data comes from <a href="https://api.collegefootballdata.com/" target="_blank">CollegeFootballData.com</a>, a free API for college football statistics.</p>
    <p>Rankings are updated weekly during the season and finalized after bowl games.</p>
</div>

<div class="content-section">
    <h2>Iterative Methodology</h2>
    <p>Because Strength of Schedule and Quality Wins depend on opponent rankings, the algorithm must iterate:</p>
    <ol style="margin-left: 1.5rem; line-height: 1.8;">
        <li>Start with neutral rankings (all teams at rank 65)</li>
        <li>Calculate all 7 metrics for each team</li>
        <li>Generate composite scores using weights</li>
        <li>Re-rank teams by composite score</li>
        <li>Repeat until top 25 stabilizes (≤2 position changes)</li>
    </ol>
</div>
"""

page_html = get_header("About the Model — TJC Rankings", about_active=' class="active"')
page_html += about_content
page_html += footer_html

with open('docs/about.html', 'w') as f:
    f.write(page_html)
print("Generated docs/about.html")

print("\n✅ All pages generated!")
