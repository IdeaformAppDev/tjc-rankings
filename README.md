# TJC Rankings — Computer College Football Rankings

A transparent, algorithmic ranking system for college football FBS teams. Built with data, not bias.

## 🏈 Live Site
**Coming soon:** [tjcrankings.com](https://tjcrankings.com)

## 📊 The Model

Rankings are computed weekly using 9 normalized metrics:

| Metric | Weight | Description |
|--------|--------|-------------|
| Win/Loss Record | 20% | Simple winning percentage with close-win nuance |
| Strength of Schedule | 20% | Rolling opponent average (not preseason) |
| Strength of Record | 15% | How would avg Top-25 team do vs this schedule? |
| Point Differential | 10% | Margin capped at ±28, garbage time discounted |
| Defensive Efficiency | 10% | Points allowed per possession, tempo-adjusted |
| Quality Wins | 10% | Wins vs Top 10/25/40 (current-week rankings) |
| Championship Behavior | 10% | Grit wins, comeback bonuses, bad-loss penalties |
| Special Teams | 3% | FG%, punting, kickoff touchbacks |
| Ball Control | 2% | Time of possession, first downs |

### Iterative Ranking
Because Strength of Schedule and Quality Wins depend on opponent rankings (which depend on THEIR opponents), the algorithm iterates until rankings stabilize — usually 4-6 cycles.

## 🚀 Tech Stack

- **Data source:** [CollegeFootballData.com](https://api.collegefootballdata.com/) API
- **Language:** Python 3.x
- **Data store:** SQLite
- **Web:** Static HTML/CSS (no framework bloat)
- **Hosting:** Firebase Hosting
- **Scheduler:** Cron (Monday 6:00 AM ET)

## 🎨 Brand

**Logo:** Scholarly dog (terrier/chihuahua) in bow tie and glasses, lecturing on algorithms. Serious analytics with playful personality.

**Colors:**
- Primary: Navy (`#1a365d`)
- Accent: Red (`#c53030`)
- Highlight: Gold (`#d69e2e`)

## 🚀 Deploy

This project uses Firebase Hosting as a secondary site on the existing `tjcwordworks` project.

```bash
# Clone
git clone https://github.com/IdeaformAppDev/tjc-rankings.git
cd tjc-rankings

# Deploy (requires Firebase auth)
firebase use tjcwordworks
firebase deploy --only hosting:tjcrankings
```

**Custom domain:** Connect `tjcrankings.com` in Firebase Console → Hosting → tjcrankings → Add custom domain.

## 📁 Project Structure

```
CollegeFootballRanking/
├── assets/              # Logo, favicons
│   ├── tjc-rankings-logo.png
│   ├── favicon-*.png
│   └── apple-touch-icon.png
├── data/                # SQLite database
├── src/                 # Python modules
│   ├── fetch_games.py
│   ├── metrics.py
│   ├── rankings.py
│   └── report.py
├── web/                 # Static site
│   └── index.html
├── tests/               # Unit tests
└── reports/             # Generated weekly reports
```

## 🏗️ Development Status

- [x] Algorithm design
- [x] Web dashboard (static)
- [x] Logo + branding
- [x] Favicon package
- [x] Firebase hosting config (multi-site)
- [ ] Deploy to production
- [ ] Data pipeline (Phase 1)
- [ ] Core algorithm implementation (Phase 2)
- [ ] Historical backtest validation (Phase 3)
- [ ] Automation + cron (Phase 4)

## 📝 License

MIT — Feel free to fork, improve, or build your own ranking system. Just give credit.

---

*Built by Jason | Rankings generated algorithmically. No human bias, no conference favoritism — just math.*
