from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import uuid

class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")  # rating 1-5
    comment: Optional[str] = Field(None, max_length=500, description="Optional review comment")

class ReviewCreate(ReviewBase):
    booking_id: uuid.UUID
    @validator('comment')
    def validate_comment_length(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None  # Convert empty strings to None
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "booking_id": "123e4567-e89b-12d3-a456-426614174000",
                "rating": 5,
                "comment": "Excellent service! Very professional and timely."
            }
        }

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewOut(ReviewBase):
    id: uuid.UUID
    user_id: uuid.UUID
    booking_id: uuid.UUID
    created_at: datetime 
    

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174001",
                "booking_id": "123e4567-e89b-12d3-a456-426614174000",
                "rating": 5,
                "comment": "Excellent service! Very professional and timely.",
                "created_at": "2024-02-15T14:30:00"
            }
        }

class ReviewDetailOut(ReviewOut):
    """Extended review schema with booking and service details"""
    booking_start_time: Optional[datetime] = Field(None, description="Start time of the reviewed booking")
    service_title: Optional[str] = Field(None, description="Title of the reviewed service")
    service_price: Optional[float] = Field(None, description="Price of the reviewed service")
    user_name: Optional[str] = Field(None, description="Name of the reviewer (for admin views)")
    
    class Config:
        from_attributes = True

class ReviewListResponse(BaseModel):
    """Schema for paginated review list response"""
    reviews: list[ReviewOut]
    total: int = Field(..., description="Total number of reviews")
    average_rating: Optional[float] = Field(None, description="Average rating for the service")
    rating_distribution: Optional[dict] = Field(None, description="Count of each rating (1-5)")
    
    class Config:
        schema_extra = {
            "example": {
                "reviews": [],
                "total": 15,
                "average_rating": 4.2,
                "rating_distribution": {"1": 0, "2": 1, "3": 2, "4": 7, "5": 5}
            }
        }
