from pydantic import BaseModel

class SubscriptionRequest(BaseModel):
    trip_id: str
    stop_id: str
    fcm_token: str