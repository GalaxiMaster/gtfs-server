"""
csv_to_db.py — converts stops.csv → stops.db (SQLite)

stop_id is TEXT to support both numeric train IDs (e.g. "222010")
and alpha-prefixed bus IDs (e.g. "G2077181").
FTS5 uses SQLite's implicit integer rowid — not stop_id — as the link key.

Usage:
    python csv_to_db.py stops.csv
    python csv_to_db.py stops.csv --output assets/stops.db
"""

import csv
import sqlite3
import sys
import os
import argparse

TYPE_LABELS = {1: 'Train', 2: 'Bus', 3: 'Ferry'}


def build_database(csv_path: str, db_path: str) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # stop_id is TEXT — bus stops use G-prefixed IDs, trains are numeric strings
    # No PRIMARY KEY on stop_id since SQLite's implicit integer rowid is needed
    # for the FTS5 content link. UNIQUE constraint still prevents duplicates.
    cur.execute("""
        CREATE TABLE stops (
            stop_id   TEXT NOT NULL UNIQUE,
            stop_name TEXT NOT NULL,
            stop_lat  REAL NOT NULL,
            stop_lon  REAL NOT NULL,
            type      INTEGER NOT NULL
        )
    """)

    cur.execute("CREATE INDEX idx_type     ON stops(type)")
    cur.execute("CREATE INDEX idx_stop_id  ON stops(stop_id)")

    # content_rowid='rowid' tells FTS5 to use SQLite's implicit integer rowid
    # as the link to the content table — this works regardless of stop_id type.
    cur.execute("""
        CREATE VIRTUAL TABLE stops_fts USING fts5(
            stop_name,
            content='stops',
            content_rowid='rowid',
            tokenize='trigram'
        )
    """)

    rows = []
    with open(csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            rows.append((
                str(row['stop_id']).strip(),
                row['stop_name'].strip(),
                float(row['stop_lat']),
                float(row['stop_lon']),
                int(row['type']),
            ))

    cur.executemany("INSERT INTO stops VALUES (?, ?, ?, ?, ?)", rows)

    # Populate FTS using the implicit rowid — NOT stop_id
    cur.execute("""
        INSERT INTO stops_fts(rowid, stop_name)
        SELECT rowid, stop_name FROM stops
    """)

    conn.commit()
    conn.close()

    size_kb = os.path.getsize(db_path) / 1024
    by_type = {}
    for row in rows:
        by_type[row[4]] = by_type.get(row[4], 0) + 1

    print(f"SUCCESS: {db_path}")
    print(f"Size:    {size_kb:.0f} KB")
    print(f"Records: {len(rows):,} total")
    for type_id, label in TYPE_LABELS.items():
        print(f"         {by_type.get(type_id, 0):,} {label}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', help='Path to stops.csv')
    parser.add_argument('--output', default='stops.db')
    args = parser.parse_args()
    build_database(args.csv, args.output)