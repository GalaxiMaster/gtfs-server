import sqlite3

def build_adjacencies(path: str = 'assets/'):
    con = sqlite3.connect(f'{path}/gtfs.db')
    cur = con.cursor()

    # For each pair of parent stations connected by at least one trip,
    # store the connection
    cur.execute('''
        SELECT DISTINCT
            s_a.parent_station AS from_station,
            s_b.parent_station AS to_station,
            st_a.trip_id
        FROM stop_times st_a
        JOIN stop_times st_b ON st_a.trip_id = st_b.trip_id
            AND st_b.stop_sequence > st_a.stop_sequence
        JOIN stops s_a ON s_a.stop_id = st_a.stop_id
        JOIN stops s_b ON s_b.stop_id = st_b.stop_id
        WHERE s_a.parent_station != s_b.parent_station
        AND s_a.parent_station IS NOT NULL
        AND s_b.parent_station IS NOT NULL
    ''')

    # Build adjacency: station → set of reachable stations
    adjacency = {}
    for from_id, to_id, _ in cur.fetchall():
        adjacency.setdefault(from_id, set()).add(to_id)

    # Store as a lookup table in the db
    cur.execute('''
        CREATE TABLE IF NOT EXISTS station_adjacency (
            from_station TEXT,
            to_station   TEXT,
            PRIMARY KEY (from_station, to_station)
        )
    ''')
    cur.execute('DELETE FROM station_adjacency')
    cur.executemany(
        'INSERT INTO station_adjacency VALUES (?, ?)',
        [(f, t) for f, ts in adjacency.items() for t in ts]
    )


    print(f"Built adjacency for {len(adjacency)} stations")
    # Add to your preprocessing pipeline
    # Denormalize parent_station into stop_times — avoids the join at query time
    cur.execute('ALTER TABLE stop_times ADD COLUMN parent_station TEXT')
    cur.execute('''
        UPDATE stop_times 
        SET parent_station = (
            SELECT parent_station FROM stops 
            WHERE stops.stop_id = stop_times.stop_id
        )
    ''')
    
    cur.execute('''
        ALTER TABLE stop_times ADD COLUMN departure_secs INTEGER;
    ''')
    cur.execute('''
        ALTER TABLE stop_times ADD COLUMN arrival_secs INTEGER;
    ''')

    cur.execute('''
        UPDATE stop_times SET
        departure_secs = CAST(substr(departure_time,1,2) AS INTEGER)*3600
                        + CAST(substr(departure_time,4,2) AS INTEGER)*60
                        + CAST(substr(departure_time,7,2) AS INTEGER),
        arrival_secs = CAST(substr(arrival_time,1,2) AS INTEGER)*3600
                        + CAST(substr(arrival_time,4,2) AS INTEGER)*60
                        + CAST(substr(arrival_time,7,2) AS INTEGER);
    ''')
    cur.execute('''
        ALTER TABLE stop_times DROP COLUMN departure_time;
    ''')
    cur.execute('''
        ALTER TABLE stop_times DROP COLUMN arrival_time;
    ''')
    cur.execute('''
        ALTER TABLE stop_times DROP COLUMN shape_dist_traveled;
    ''')

    # Add indexes to speed up queries
    cur.execute('CREATE INDEX IF NOT EXISTS idx_st_trip_seq   ON stop_times(trip_id, stop_sequence)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_trips_service ON trips(service_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cal_service   ON calendar(service_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_st_parent_covering ON stop_times(parent_station, trip_id, departure_secs, arrival_secs)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_trips_trip_id ON trips(trip_id);')
    
    con.commit()
    
    con.isolation_level = None
    cur.execute('VACUUM')
    
    con.close()
    print("Done!")
if __name__ == "__main__":
    build_adjacencies()