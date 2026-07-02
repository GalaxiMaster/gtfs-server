import os
import sys
import hashlib
import zipfile
import io
import json
from pathlib import Path

import requests

from scripts.add_type_column import add_type_column
from scripts.gzip import gzip_file
from scripts.remove_mode import remove_mode
from scripts.merge_dbs import merge_dbs
from scripts.csv_to_db import csv_to_db
from scripts.verify_db import verify_and_fts
from scripts.indexes_and_adjacency import build_adjacencies

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIweC1vR25DelZRdlk4cUZxZm1yRmhrSl9jZzc3d05ueENBLXF3R1JTNGlvIiwiaWF0IjoxNzgyMzYyMTIyfQ.2p0Dt0xE_ePWEggmRUaR5Tl9DEYMSzMmzUZtaM7Ow2I'
if not API_KEY:
    sys.exit("Set the TFNSW_API_KEY environment variable before running this script.")

URL = "https://api.transport.nsw.gov.au/v1/publictransport/timetables/complete/gtfs"
HEADERS = {"Authorization": f"apikey {API_KEY}"}

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "scripts" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = BASE_DIR / "app" / "data" / ".gtfs_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state))


def check_for_new_data(state: dict) -> bool:
    """HEAD request to check ETag/Last-Modified before downloading anything."""
    try:
        head = requests.head(URL, headers=HEADERS, timeout=30)
        head.raise_for_status()
    except requests.RequestException as e:
        print(f"HEAD check failed ({e}), will fall back to full download.")
        return True  # can't tell, so proceed with download

    etag = head.headers.get("ETag")
    last_modified = head.headers.get("Last-Modified")

    if not etag and not last_modified:
        print("Server doesn't expose ETag/Last-Modified, will fall back to hash check after download.")
        return True

    if etag and etag == state.get("etag"):
        return False
    if last_modified and last_modified == state.get("last_modified"):
        return False

    return True


def download_with_progress() -> tuple[bytes, dict]:
    response = requests.get(URL, headers=HEADERS, timeout=60, stream=True)
    response.raise_for_status()

    total = int(response.headers.get("Content-Length", 0))
    chunks = []
    downloaded = 0

    for chunk in response.iter_content(chunk_size=1024 * 256):
        if not chunk:
            continue
        chunks.append(chunk)
        downloaded += len(chunk)
        if total:
            pct = downloaded / total * 100
            print(f"\rDownloading: {pct:5.1f}% ({downloaded / 1e6:.1f} MB / {total / 1e6:.1f} MB)", end="", flush=True)
        else:
            print(f"\rDownloading: {downloaded / 1e6:.1f} MB", end="", flush=True)

    print()

    content = b"".join(chunks)

    if total and downloaded != total:
        raise IOError(f"Download incomplete: got {downloaded} bytes, expected {total}")

    return content, response.headers

def fetch_gtfs():
    state = load_state()

    if not check_for_new_data(state):
        print("No new data since last run — skipping download.")
        return

    content, resp_headers = download_with_progress()

    # Fallback dedup: hash the content in case server didn't give ETag/Last-Modified
    content_hash = hashlib.sha256(content).hexdigest()
    if content_hash == state.get("content_hash"):
        print("Downloaded data is identical to last run — skipping processing.")
        return

    print("New data detected, extracting...")
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        z.extractall(OUTPUT_DIR)

    print(f"GTFS data extracted to {OUTPUT_DIR}")

    remove_mode(path=OUTPUT_DIR)
    csv_to_db(path=OUTPUT_DIR)
    add_type_column(path=OUTPUT_DIR)
    merge_dbs(path=OUTPUT_DIR)
    verify_and_fts(path=OUTPUT_DIR)
    build_adjacencies(path=OUTPUT_DIR)
    
    SOURCE = BASE_DIR / 'scripts' / 'data' / 'gtfs.db'
    DEST = BASE_DIR / 'app' / 'data'
    print(DEST)
    gzip_file(SOURCE, DEST, 'gtfs.db.gz')
    save_state({
        "version": state.get("version", 0),
        "etag": resp_headers.get("ETag"),
        "last_modified": resp_headers.get("Last-Modified"),
        "content_hash": content_hash,
    })

    print("Processing complete.")


if __name__ == "__main__":
    fetch_gtfs()