"""Generate static HTML pages for TJC Rankings website."""

import sys
sys.path.insert(0, 'src')
from ranking_engine import RankingEngine
from collections import defaultdict

# Generate rankings for all seasons
seasons = [2021, 2022, 2023, 2024, 2025]
all_rankings = {}

for season in seasons:
    engine = RankingEngine(season=season, week=16)
    results, metadata = engine.run()
    all_rankings[season] = results
    print(f"Generated {season}: {results[0].team_name} #1")

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
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
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

def generate_rankings_table(results, season, week):
    html = f'<h1 style="font-family: \'Playfair Display\', serif; margin-bottom: 1.5rem; color: var(--primary);">Week {week} Rankings — {season} Season</h1>\n'
    html += '<table class="rankings-table">\n<thead>\n<tr><th>Rank</th><th>Team</th><th>Conference</th><th>Record</th><th style="text-align: right;">Score</th></tr>\n</thead>\n<tbody>\n'
    
    for rank, team in enumerate(results[:25], 1):
        record = f"{team.wins}-{team.losses}"
        html += f'<tr><td class="rank">{rank}</td><td><div class="team-name">{team.team_name}</div></td><td class="conference">{team.conference}</td><td class="record">{record}</td><td class="score">{team.composite_score:.1f}</td></tr>\n'
    
    html += '</tbody>\n</table>\n'
    return html

def generate_conference_standings(results, season):
    conferences = defaultdict(list)
    for team in results:
        conferences[team.conference].append(team)
    
    html = f'<h1 style="font-family: \'Playfair Display\', serif; margin-bottom: 1.5rem; color: var(--primary);">Conference Standings — {season} Season</h1>\n'
    
    for conf_name in sorted(conferences.keys()):
        teams = sorted(conferences[conf_name], key=lambda t: t.composite_score, reverse=True)
        html += f'<div class="conference-standings">\n'
        html += f'<h3>{conf_name}</h3>\n'
        html += '<table class="rankings-table">\n<thead>\n<tr><th>Rank</th><th>Team</th><th>Record</th><th style="text-align: right;">Score</th></tr>\n</thead>\n<tbody>\n'
        for rank, team in enumerate(teams[:10], 1):
            record = f"{team.wins}-{team.losses}"
            html += f'<tr><td class="rank">{rank}</td><td><div class="team-name">{team.team_name}</div></td><td class="record">{record}</td><td class="score">{team.composite_score:.1f}</td></tr>\n'
        html += '</tbody>\n</table>\n</div>\n'
    
    return html

# Generate pages for each season
for season in seasons:
    results = all_rankings[season]
    
    rankings_active = ' class="active"' if season == 2025 else ''
    
    # Season page
    page_html = get_header(f"Week 16 Rankings — {season} Season", rankings_active=rankings_active)
    page_html += generate_rankings_table(results, season, 16)
    page_html += footer_html
    
    filename = f'docs/{season}.html'
    with open(filename, 'w') as f:
        f.write(page_html)
    print(f"Generated {filename}")

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
    <h2>9 Metrics (Weighted)</h2>
    <ul class="metric-list">
        <li>Win/Loss Record <span class="metric-weight">20%</span></li>
        <li>Strength of Schedule <span class="metric-weight">20%</span></li>
        <li>Strength of Record <span class="metric-weight">15%</span></li>
        <li>Point Differential <span class="metric-weight">10%</span></li>
        <li>Defensive Efficiency <span class="metric-weight">10%</span></li>
        <li>Quality Wins <span class="metric-weight">10%</span></li>
        <li>Championship Behavior <span class="metric-weight">10%</span></li>
        <li>Special Teams <span class="metric-weight">3%</span></li>
        <li>Ball Control <span class="metric-weight">2%</span></li>
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
        <li>Calculate all 9 metrics for each team</li>
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
