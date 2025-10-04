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


from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid

class BookingStatus(str, Enum):
    """Enum for booking status values"""
    PENDING = "pending"
    CONFIRMED = "confirmed" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class BookingCreate(BaseModel):
    """Schema for creating a new booking"""
    service_id: uuid.UUID = Field(..., description="UUID of the service to book")
    start_time: datetime = Field(..., description="Start time of the booking")
    
    @validator('start_time')
    def start_time_must_be_future(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('Start time must be in the future')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "service_id": "550e8400-e29b-41d4-a716-446655440000",
                "start_time": "2024-02-15T10:00:00"
            }
        }

class BookingUpdate(BaseModel):
    """Schema for updating an existing booking"""
    start_time: Optional[datetime] = Field(None, description="New start time for the booking")
    status: Optional[BookingStatus] = Field(None, description="New status for the booking")
    
    @validator('start_time')
    def start_time_must_be_future(cls, v):
        if v is not None and v <= datetime.utcnow():
            raise ValueError('Start time must be in the future')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "start_time": "2024-02-15T14:00:00",
                "status": "confirmed"
            }
        }

class BookingOut(BaseModel):
    """Schema for booking output/response"""
    id: uuid.UUID = Field(..., description="Unique booking UUID")
    user_id: uuid.UUID = Field(..., description="UUID of the user who made the booking")
    service_id: uuid.UUID = Field(..., description="UUID of the booked service")
    start_time: datetime = Field(..., description="Start time of the booking")
    end_time: datetime = Field(..., description="End time of the booking")
    status: BookingStatus = Field(..., description="Current status of the booking")
    created_at: datetime = Field(..., description="When the booking was created")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "456e7890-e89b-12d3-a456-426614174001",
                "service_id": "550e8400-e29b-41d4-a716-446655440000",
                "start_time": "2024-02-15T10:00:00",
                "end_time": "2024-02-15T11:00:00", 
                "status": "pending",
                "created_at": "2024-02-14T15:30:00"
            }
        }

class BookingDetailOut(BookingOut):
    """Extended booking schema with related data"""
    service_title: Optional[str] = Field(None, description="Title of the booked service")
    service_price: Optional[float] = Field(None, description="Price of the booked service")
    user_name: Optional[str] = Field(None, description="Name of the user who made the booking")
    user_email: Optional[str] = Field(None, description="Email of the user who made the booking")
    
    class Config:
        from_attributes = True

class BookingListResponse(BaseModel):
    """Schema for paginated booking list response"""
    bookings: list[BookingOut]
    total: int = Field(..., description="Total number of bookings")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(10, description="Number of bookings per page")
    
    class Config:
        schema_extra = {
            "example": {
                "bookings": [],
                "total": 25,
                "page": 1,
                "per_page": 10
            }
        }

class BookingFilters(BaseModel):
    """Schema for booking query filters"""
    status: Optional[BookingStatus] = Field(None, description="Filter by booking status")
    from_date: Optional[datetime] = Field(None, description="Filter bookings from this date")
    to_date: Optional[datetime] = Field(None, description="Filter bookings up to this date")
    service_id: Optional[uuid.UUID] = Field(None, description="Filter by specific service UUID")
    
    @validator('to_date')
    def to_date_after_from_date(cls, v, values):
        if v and values.get('from_date') and v <= values['from_date']:
            raise ValueError('to_date must be after from_date')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "status": "confirmed",
                "from_date": "2024-02-01T00:00:00",
                "to_date": "2024-02-28T23:59:59",
                "service_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }