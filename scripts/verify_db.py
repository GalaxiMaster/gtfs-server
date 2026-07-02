import sqlite3

def verify_and_fts(path:str = 'assets/'):
    con = sqlite3.connect(f'{path}/gtfs.db')
    cur = con.cursor()

    cur.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS stops_fts
        USING fts5(stop_name, content='stops', content_rowid='rowid')
    ''')
    cur.execute("INSERT INTO stops_fts(stops_fts) VALUES ('rebuild')")

    con.commit()

    # Verify
    cur.execute("SELECT COUNT(*) FROM stops_fts")
    print(f"FTS rows indexed: {cur.fetchone()[0]:,}")
    cur.execute("SELECT stop_name FROM stops_fts WHERE stops_fts MATCH 'Central*' LIMIT 5")
    print(f"Test search: {[r[0] for r in cur.fetchall()]}")

    con.close()