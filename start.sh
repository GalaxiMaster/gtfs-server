#!/bin/sh
set -e

echo "Installing dependencies..."
pip install --no-cache-dir \
  fastapi \
  "uvicorn[standard]" \
  httpx \
  aiosqlite \
  firebase-admin \
  gtfs-realtime-bindings

echo "Checking required files..."

# if [ ! -f /app/app/data/gtfs.db.gz ]; then
#   echo "WARNING: gtfs.db.gz is missing"
# fi
if [ -z "$TFNSW_API_KEY" ]; then
  echo "WARNING: TFNSW_API_KEY not set"
fi

cd /app
echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000