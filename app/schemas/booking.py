from pydantic import BaseModel
from datetime import datetime
import uuid

class BookingCreate(BaseModel):
    service_id: uuid.UUID
    start_time: datetime
    end_time: datetime

class BookingOut(BookingCreate):
    id: uuid.UUID
    user_id: uuid.UUID

    class Config:
        from_attributes = True
