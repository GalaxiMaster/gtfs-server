from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import aiosqlite
import asyncio
from poller import start_polling
from pathlib import Path

app = FastAPI()
DB_PATH = "subscriptions.db"
DATA_DIR = Path(__file__).parent / "data"

@app.on_event("startup")
async def startup():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                trip_id TEXT,
                fcm_token TEXT,
                stop_id TEXT,
                PRIMARY KEY (trip_id, fcm_token)
            )
        """)
        await db.commit()
    asyncio.create_task(start_polling())

@app.get("/gtfs.db.gz")
async def get_gtfs():
    path = DATA_DIR / "gtfs.db.gz"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="application/gzip")

@app.get("/gtfs_version.json")
async def get_version():
    path = DATA_DIR / "gtfs_version.json"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="application/json")

@app.post("/subscribe")
async def subscribe(trip_id: str, stop_id: str, fcm_token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscriptions VALUES (?, ?, ?)",
            (trip_id, fcm_token, stop_id),
        )
        await db.commit()
    return {"status": "subscribed"}

@app.post("/unsubscribe")
async def unsubscribe(trip_id: str, fcm_token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE trip_id = ? AND fcm_token = ?",
            (trip_id, fcm_token),
        )
        await db.commit()
    return {"status": "unsubscribed"}

@app.get("/health")
async def health():
    return {"status": "ok"}