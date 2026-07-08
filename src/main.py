#!/usr/bin/env python3
"""
College Football Ranking System - Main Entry Point

Usage:
    python main.py --ingest           # Fetch all data from API
    python main.py --rank 2024        # Generate rankings for a season
    python main.py --backtest         # Run full backtest (2000-2025 + iconic)
    python main.py --report 2024      # Generate detailed report for season
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import PRIMARY_BACKTEST_START, PRIMARY_BACKTEST_END, ICONIC_SEASONS
from database import init_db
from data_ingestion import run_full_ingestion
from rankings import generate_final_rankings

def run_backtest():
    """Run the full backtest."""
    all_seasons = list(range(PRIMARY_BACKTEST_START, PRIMARY_BACKTEST_END + 1))
    all_seasons.extend(ICONIC_SEASONS)
    all_seasons = sorted(set(all_seasons))
    
    print(f"Running backtest for {len(all_seasons)} seasons...")
    print(f"Primary range: {PRIMARY_BACKTEST_START}-{PRIMARY_BACKTEST_END}")
    print(f"Iconic seasons: {ICONIC_SEASONS}\n")
    
    for season in all_seasons:
        generate_final_rankings(season)
        print()

def main():
    parser = argparse.ArgumentParser(description="College Football Ranking System")
    parser.add_argument("--ingest", action="store_true", help="Fetch data from API")
    parser.add_argument("--rank", type=int, metavar="SEASON", help="Generate rankings for season")
    parser.add_argument("--backtest", action="store_true", help="Run full backtest")
    parser.add_argument("--report", type=int, metavar="SEASON", help="Generate detailed report")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Initialize database
    init_db()
    
    if args.ingest:
        print("Running data ingestion...")
        run_full_ingestion()
    
    elif args.rank:
        generate_final_rankings(args.rank)
    
    elif args.backtest:
        run_backtest()
    
    elif args.report:
        print(f"Report generation for season {args.report} - not yet implemented")
        # TODO: Implement report generation

if __name__ == "__main__":
    main()
