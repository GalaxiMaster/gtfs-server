import gzip
import shutil
from pathlib import Path

def gzip_file(source: Path, dest: Path, file: str):
    SOURCE = Path(source)
    DEST = Path(dest) / file

    DEST.parent.mkdir(parents=True, exist_ok=True)

    with open(SOURCE, 'rb') as f_in:
        with gzip.open(DEST, 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"Compressed {SOURCE} -> {DEST} ({DEST.stat().st_size / 1e6:.1f} MB)")

if __name__ == "__main__":
    SOURCE = Path('/data/gtfs.db')
    DEST = Path('../app/data/')
    gzip_file(SOURCE, DEST, 'gtfs.db.gz')