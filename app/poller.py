import asyncio
import httpx
import aiosqlite
import firebase_admin
from firebase_admin import credentials, messaging
from google.transit import gtfs_realtime_pb2

# cred = credentials.Certificate("firebase_key.json")
# firebase_admin.initialize_app(cred)

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIweC1vR25DelZRdlk4cUZxZm1yRmhrSl9jZzc3d05ueENBLXF3R1JTNGlvIiwiaWF0IjoxNzgyMzYyMTIyfQ.2p0Dt0xE_ePWEggmRUaR5Tl9DEYMSzMmzUZtaM7Ow2I"
FEED_URL = "https://api.transport.nsw.gov.au/v2/gtfs/realtime/sydneytrains"
DB_PATH = "subscriptions.db"
POLL_INTERVAL = 90  # seconds — within your 1-5 min target

# Track last-notified state to avoid spamming the same delay repeatedly
_last_notified = {}  # (trip_id, fcm_token) -> last delay bucket notified

async def start_polling():
  	print('yeah')
    # while True:
    #     try:
    #         await poll_once()
    #     except Exception as e:
    #         print(f"Poll error: {e}")
    #     await asyncio.sleep(POLL_INTERVAL)

async def poll_once():
  	print('test')
#     async with aiosqlite.connect(DB_PATH) as db:
#         cursor = await db.execute("SELECT trip_id, fcm_token, stop_id FROM subscriptions")
#         subs = await cursor.fetchall()

#     if not subs:
#         return  # nothing to check, skip the API call entirely

#     subscribed_trip_ids = {s[0] for s in subs}

#     async with httpx.AsyncClient() as client:
#         resp = await client.get(
#             FEED_URL,
#             headers={"Authorization": f"apikey {API_KEY}"},
#             timeout=20,
#         )
#         resp.raise_for_status()

#     feed = gtfs_realtime_pb2.FeedMessage()
#     feed.ParseFromString(resp.content)

#     for entity in feed.entity:
#         if not entity.HasField("trip_update"):
#             continue
#         update = entity.trip_update
#         trip_id = update.trip.trip_id
#         if trip_id not in subscribed_trip_ids:
#             continue

#         is_cancelled = update.trip.schedule_relationship == 3  # CANCELED

#         for stu in update.stop_time_update:
#             relevant_subs = [s for s in subs if s[0] == trip_id and s[2] == stu.stop_id]
#             if not relevant_subs:
#                 continue

#             delay = stu.departure.delay if stu.HasField("departure") else stu.arrival.delay
#             delay_mins = delay // 60
#             bucket = "cancelled" if is_cancelled else (delay_mins // 2) * 2  # group into 2-min buckets

#             for sub_trip_id, fcm_token, stop_id in relevant_subs:
#                 key = (sub_trip_id, fcm_token)
#                 if _last_notified.get(key) == bucket:
#                     continue  # already notified for this state

#                 _last_notified[key] = bucket

#                 if is_cancelled:
#                     send_notification(fcm_token, "Train Cancelled", f"Trip {trip_id} has been cancelled.")
#                 elif delay_mins >= 3:
#                     send_notification(fcm_token, "Train Delayed", f"Running {delay_mins} min late.")

def send_notification(token: str, title: str, body: str):
  	print('yeah')
    # message = messaging.Message(
    #     notification=messaging.Notification(title=title, body=body),
    #     token=token,
    # )
    # try:
    #     messaging.send(message)
    # except Exception as e:
    #     print(f"FCM send failed for {token[:10]}...: {e}")