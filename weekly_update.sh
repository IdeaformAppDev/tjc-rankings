#!/bin/bash
# Weekly CFB Ranking Update Script
# Run Monday mornings after all games complete

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/weekly-$(date +%Y%m%d).log"
SEASON=$(date +%Y)

# Create logs directory if needed
mkdir -p "$SCRIPT_DIR/logs"

exec >> "$LOG_FILE" 2>&1

echo "========================================"
echo "CFB Weekly Update - $(date)"
echo "Season: $SEASON"
echo "========================================"

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Run data ingestion (fetch latest games)
echo "[$(date)] Fetching latest game data..."
cd "$SCRIPT_DIR"
python3 -m src.data_ingestion 2>&1 || echo "Warning: Data ingestion had issues"

# Generate rankings for current season through latest week
echo "[$(date)] Generating rankings..."
python3 -m src.rankings 2>&1 || echo "Warning: Rankings generation had issues"

# Generate static site
echo "[$(date)] Generating static site..."
python3 generate_site.py 2>&1 || echo "Warning: Site generation had issues"

# Commit and push to GitHub Pages (if configured)
if [ -d "$SCRIPT_DIR/.git" ]; then
    echo "[$(date)] Committing updates..."
    cd "$SCRIPT_DIR"
    git add docs/
    git commit -m "Weekly update: $(date +%Y-%m-%d)" || echo "No changes to commit"
    git push origin master 2>&1 || echo "Push failed - may need manual intervention"
fi

echo "[$(date)] Update complete!"
echo "========================================"
