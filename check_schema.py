import sqlite3

# Check source schema
src_conn = sqlite3.connect('/home/jason/.openclaw/workspace/CollegeFootballRanking/data/cfb_ranking.db')
src_cursor = src_conn.cursor()

src_cursor.execute("PRAGMA table_info(games)")
print("Source games columns:")
for col in src_cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

src_conn.close()

# Check dest schema
dest_conn = sqlite3.connect('data/cfb_ranking.db')
dest_cursor = dest_conn.cursor()

dest_cursor.execute("PRAGMA table_info(games)")
print("\nDest games columns:")
for col in dest_cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

dest_conn.close()
