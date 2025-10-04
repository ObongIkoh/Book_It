from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Any
import uuid
from datetime import datetime


class ServiceBase(BaseModel):
    title: str = Field(..., max_length=100) # Added max_length for safety
    description: Optional[str] = Field(None, max_length=1000) # Added max_length
    price: float
    duration_minutes: int
    is_active: bool = True

    # Use Pydantic V2 field_validator
    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v: Any) -> float:
        # Check for None explicitly in case this validator is used on Optional fields later
        if v is None:
            return v 
        
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        # Round to 2 decimal places for currency
        return round(float(v), 2)
    
    # Use Pydantic V2 field_validator
    @field_validator('duration_minutes', mode='before')
    @classmethod
    def validate_duration(cls, v: Any) -> int:
        if v is None:
            return v
        
        v_int = int(v)
        if v_int <= 0:
            raise ValueError('Duration must be greater than 0')
        if v_int > 1440:  # 24 hours max
            raise ValueError('Duration cannot exceed 24 hours (1440 minutes)')
        return v_int

    # Pydantic V2 Configuration
    model_config = ConfigDict(
        from_attributes=True,
    )


class ServiceCreate(ServiceBase):
    # Inherits all fields and validators from ServiceBase
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "title": "60-Minute Deep Tissue Massage",
                "description": "Therapeutic massage focusing on deep muscle layers",
                "price": 89.99,
                "duration_minutes": 60,
                "is_active": True
            }
        }
    )

class ServiceUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = None
    duration_minutes: Optional[int] = None # Added missing duration_minutes field
    is_active: Optional[bool] = None
    
    # Reimplement validators, ensuring they handle the Optional[None] case
    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v: Any) -> Optional[float]:
        if v is not None:
            v = float(v)
            if v <= 0:
                raise ValueError('Price must be greater than 0')
            return round(v, 2)
        return v
    
    @field_validator('duration_minutes', mode='before')
    @classmethod
    def validate_duration(cls, v: Any) -> Optional[int]:
        if v is not None:
            v_int = int(v)
            if v_int <= 0:
                raise ValueError('Duration must be greater than 0')
            if v_int > 1440:
                raise ValueError('Duration cannot exceed 24 hours (1440 minutes)')
            return v_int
        return v
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "title": "90-Minute Deep Tissue Massage",
                "price": 129.99,
                "duration_minutes": 90,
                "is_active": True
            }
        }
    )


class ServiceOut(ServiceBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "60-Minute Deep Tissue Massage",
                "description": "Therapeutic massage focusing on deep muscle layers",
                "price": 89.99,
                "duration_minutes": 60,
                "is_active": True,
                "created_at": "2024-02-01T10:00:00"
            }
        }
    )
    
class ServiceDetailOut(ServiceOut):
    """Extended service schema with booking statistics"""
    total_bookings: Optional[int] = Field(None, description="Total number of bookings for this service")
    average_rating: Optional[float] = Field(None, description="Average review rating")
    total_reviews: Optional[int] = Field(None, description="Total number of reviews")
    
    model_config = ConfigDict(
        from_attributes = True
    )

class ServiceListResponse(BaseModel):
    """Schema for paginated service list response"""
    services: list[ServiceOut]
    total: int = Field(..., description="Total number of services")
    active_count: int = Field(..., description="Number of active services")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "services": [],
                "total": 25,
                "active_count": 20
            }
        }
    )

class ServiceFilters(BaseModel):
    """Schema for service query filters"""
    q: Optional[str] = Field(None, description="Search query for service title")
    price_min: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    is_active: Optional[bool] = Field(None, description="Filter by active/inactive status")
    duration_min: Optional[int] = Field(None, ge=0, description="Minimum duration in minutes")
    duration_max: Optional[int] = Field(None, ge=0, description="Maximum duration in minutes")
    
    # Use Pydantic V2 model_validator for cross-field checks
    @model_validator(mode='after')
    def check_min_max_filters(cls, model_instance: 'ServiceFilters') -> 'ServiceFilters':
        # Check price range
        p_min = model_instance.price_min
        p_max = model_instance.price_max
        if p_min is not None and p_max is not None and p_max < p_min:
            raise ValueError('price_max must be greater than or equal to price_min')

        # Check duration range
        d_min = model_instance.duration_min
        d_max = model_instance.duration_max
        if d_min is not None and d_max is not None and d_max < d_min:
            raise ValueError('duration_max must be greater than or equal to duration_min')
            
        return model_instance
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "q": "massage",
                "price_min": 50.0,
                "price_max": 150.0,
                "is_active": True,
                "duration_min": 30,
                "duration_max": 120
            }
        }
    )
