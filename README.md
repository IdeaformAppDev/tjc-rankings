# College Football Ranking System

A transparent, algorithmic college football ranking system.

## Quick Start

1. **Get API key:** Sign up free at [CollegeFootballData.com](https://collegefootballdata.com/)
2. **Set environment:** Copy `.env.example` to `.env` and add your key
3. **Install dependencies:** `pip install -r requirements.txt`
4. **Run:** `python src/main.py`

## Project Structure

```
CollegeFootballRanking/
├── src/
│   ├── config.py           # Configuration and weights
│   ├── database.py         # SQLite schema
│   ├── api_client.py       # CFBD API client
│   ├── data_ingestion.py   # Fetch and store data
│   ├── rankings.py         # Core ranking algorithm
│   └── main.py             # Entry point
├── data/                   # SQLite database
├── tests/                  # Unit tests
├── web/                    # Web dashboard
└── requirements.txt
```

## Backtest Scope

- **Primary:** 2000-2025 (26 seasons)
- **Iconic seasons:** 1961, 1966, 1969, 1971, 1983, 1988, 1993, 1997, 2004

## Algorithm

9 metrics, normalized and weighted:
- Win/Loss (20%)
- Strength of Schedule (20%)
- Strength of Record (15%)
- Point Differential (10%)
- Defensive Efficiency (10%)
- Quality Wins (10%)
- Championship Behavior (10%)
- Special Teams (3%)
- Ball Control (2%)

## License

MIT
