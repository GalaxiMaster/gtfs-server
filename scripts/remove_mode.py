# 2: normal trains
# 4: ferry
# 106: regional trains
# 204: regional trains and coaches
# 205: temporary coaches
# 401: metro line
# 700: sydney buses
# 712: school buses
# 714: temporary buses
# 900: light rail

import pandas as pd
import os

def remove_mode(path: str = 'assets'):
    ROUTES_DTYPES = {'route_id': str, 'route_type': str}
    TRIPS_DTYPES  = {'route_id': str, 'trip_id': str}
    STIMES_DTYPES = {'trip_id': str, 'stop_id': str}
    STOPS_DTYPES  = {'stop_id': str, 'parent_station': str}

    # 1. Load routes and identify unwanted route IDs
    routes = pd.read_csv(f'{path}/routes.txt', dtype=ROUTES_DTYPES)
    routes['route_type'] = pd.to_numeric(routes['route_type'], errors='coerce')
    unwanted_route_ids = set(routes[routes['route_type'].isin([700, 712])]['route_id'])
    print(f"Found {len(unwanted_route_ids)} unwanted route IDs (types 700 and 712)")

    # 2. Filter trips
    trips = pd.read_csv(f'{path}/trips.txt', dtype=TRIPS_DTYPES, low_memory=False)
    filtered_trips = trips[~trips['route_id'].isin(unwanted_route_ids)]
    filtered_trips.to_csv(f'{path}/trips.txt', index=False)
    print(f"Trips:      {len(trips):>8,} -> {len(filtered_trips):>8,} (removed {len(trips) - len(filtered_trips):,})")

    # 3. Filter stop_times in chunks, collecting valid stop IDs in the same pass
    valid_trip_ids = set(filtered_trips['trip_id'])
    valid_stop_ids = set()
    chunk_size = 100_000
    first_chunk = True

    source_path = f'{path}/stop_times.txt'
    tmp_path = f'{path}/stop_times.txt.tmp'

    for chunk in pd.read_csv(source_path, chunksize=chunk_size, dtype=STIMES_DTYPES):
        filtered_chunk = chunk[chunk['trip_id'].isin(valid_trip_ids)]
        valid_stop_ids.update(filtered_chunk['stop_id'].unique())

        mode = 'w' if first_chunk else 'a'
        filtered_chunk.to_csv(tmp_path, mode=mode, index=False, header=first_chunk)
        first_chunk = False

    os.replace(tmp_path, source_path)  # atomic swap once reading is fully done

    print(f"stop_times: chunked filtering done. {len(valid_stop_ids):,} unique stops still referenced.")

    # 4. Filter stops — first pass: stops that appear in stop_times
    stops = pd.read_csv(f'{path}/stops.txt', dtype=STOPS_DTYPES)
    filtered_stops = stops[stops['stop_id'].isin(valid_stop_ids)]

    valid_parent_ids = set(filtered_stops['parent_station'].dropna().unique())
    parent_stations = stops[stops['stop_id'].isin(valid_parent_ids)]
    filtered_stops = pd.concat([filtered_stops, parent_stations]).drop_duplicates(subset='stop_id')

    filtered_stops.to_csv(f'{path}/stops.txt', index=False)
    print(f"Stops:      {len(stops):>8,} -> {len(filtered_stops):>8,} (removed {len(stops) - len(filtered_stops):,})")
    print(f"  (includes {len(parent_stations):,} parent stations re-added from parent_station references)")

    print("\nDone. Files written: trips.txt, stop_times.txt, stops.txt")