from pydantic import BaseModel, Field
from typing import Optional
import uuid

class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)  # rating 1-5
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    booking_id: uuid.UUID

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewOut(ReviewBase):
    id: uuid.UUID
    user_id: uuid.UUID
    booking_id: uuid.UUID

    class Config:
        from_attributes = True
