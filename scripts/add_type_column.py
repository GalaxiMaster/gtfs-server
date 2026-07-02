import sqlite3

# One bit per transport mode — these are your Dart constants too
ROUTE_TYPE_TO_BIT = {
    2:   1,    # train (Sydney Trains)
    4:   2,    # ferry
    106: 4,    # regional train
    204: 8,    # regional train/coach
    205: 16,   # temporary coach
    401: 32,   # metro
    700: 64,   # sydney buses    (likely already removed, bit won't be set)
    712: 128,  # school buses    (likely already removed, bit won't be set)
    714: 256,  # temporary buses
    900: 512,  # light rail
}

BIT_TO_NAME = {
    1:   'train',
    2:   'ferry',
    4:   'regional train',
    8:   'regional coach',
    16:  'temporary coach',
    32:  'metro',
    64:  'bus',
    128: 'school bus',
    256: 'temporary bus',
    512: 'light rail',
}



def add_type_column(path: str = 'assets'):
    def decode_modes(bitmask):
        return ', '.join(name for bit, name in BIT_TO_NAME.items() if bitmask & bit) or 'none'

    STOPS_DB      = f'{path}/stops.db'
    STOP_TIMES_DB = f'{path}/stop_times.db'
    TRIPS_DB      = f'{path}/trips.db'
    ROUTES_DB     = f'{path}/routes.db'
    # Connect to stops.db as the main connection, then attach the others
    con = sqlite3.connect(STOPS_DB)
    cur = con.cursor()
    cur.execute(f"ATTACH DATABASE '{STOP_TIMES_DB}' AS st_db")
    cur.execute(f"ATTACH DATABASE '{TRIPS_DB}'      AS trips_db")
    cur.execute(f"ATTACH DATABASE '{ROUTES_DB}'     AS routes_db")

    # Add the column, or reset it to 0 if it already exists from a previous run
    try:
        cur.execute('ALTER TABLE stops ADD COLUMN transport_modes INTEGER NOT NULL DEFAULT 0')
        print("Added transport_modes column.")
    except sqlite3.OperationalError:
        print("transport_modes already exists — resetting all values to 0.")
        cur.execute('UPDATE stops SET transport_modes = 0')
    con.commit()

    # Step 1: walk stop_times -> trips -> routes to get which route_types serve each stop.
    # DISTINCT keeps this from processing millions of duplicate (stop_id, route_type) pairs.
    print("Querying stop_times -> trips -> routes (this may take a moment)...")
    cur.execute('''
        SELECT DISTINCT st.stop_id, r.route_type
        FROM stop_times st
        JOIN trips t  ON st.trip_id  = t.trip_id
        JOIN routes r ON t.route_id  = r.route_id
    ''')

    # Aggregate bitmask per stop
    stop_modes = {}
    for stop_id, route_type_raw in cur.fetchall():
        try:
            route_type = int(route_type_raw)
        except (TypeError, ValueError):
            continue
        bit = ROUTE_TYPE_TO_BIT.get(route_type, 0)
        stop_modes[stop_id] = stop_modes.get(stop_id, 0) | bit

    # Step 2: write bitmasks to child stops
    cur.executemany(
        'UPDATE stops SET transport_modes = ? WHERE stop_id = ?',
        [(bitmask, stop_id) for stop_id, bitmask in stop_modes.items()]
    )
    con.commit()
    print(f"Updated {len(stop_modes):,} child stops.")

    # Step 3: propagate child modes up to parent stations.
    # Parent stations (location_type=1) never appear in stop_times directly,
    # so we OR their children's bitmasks up to them.
    print("Propagating modes to parent stations...")
    cur.execute('''
        SELECT parent_station, transport_modes
        FROM stops
        WHERE parent_station IS NOT NULL
        AND parent_station != ''
    ''')

    parent_modes = {}
    for parent_id, modes in cur.fetchall():
        parent_modes[parent_id] = parent_modes.get(parent_id, 0) | (modes or 0)

    cur.executemany(
        'UPDATE stops SET transport_modes = transport_modes | ? WHERE stop_id = ?',
        [(bitmask, stop_id) for stop_id, bitmask in parent_modes.items()]
    )
    con.commit()
    print(f"Updated {len(parent_modes):,} parent stations.")

    # Summary: show a sample of parent stations with their decoded modes
    cur.execute('''
        SELECT stop_name, transport_modes
        FROM stops
        WHERE location_type = 1
        AND transport_modes > 0
        ORDER BY stop_name
        LIMIT 20
    ''')

    print(f"\n{'Stop name':<40} {'Bits':<6}  Modes")
    print("-" * 75)
    for stop_name, modes in cur.fetchall():
        print(f"{stop_name:<40} {modes or 0:<6}  {decode_modes(modes or 0)}")

    con.close()
    print("\nDone.")