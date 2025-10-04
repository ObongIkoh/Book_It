from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional, Any
from uuid import UUID
from datetime import datetime # CRITICAL: Import the datetime class directly
from enum import Enum

# --- Enums ---

class UserRole(str, Enum):
    user = "user"
    admin = "admin"

# --- Base Schemas ---

class UserBase(BaseModel):
    """Base schema for shared user fields."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.user # Default role is the UserRole enum

    model_config = ConfigDict(
        from_attributes=True,
    )

    # Simple validator to ensure name is cleaned up
    @field_validator('name', mode='before')
    @classmethod
    def validate_name(cls, v: Any) -> Any:
        if isinstance(v, str) and len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        # Pydantic V2 handles stripping whitespace by default unless custom annotation is used
        return v


# --- Input Schemas ---

class UserCreate(UserBase):
    """Schema for creating a new user (requires password)"""
    password: str = Field(..., min_length=8)
    # Inherits name, email, role from UserBase

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "password": "strong-password-123",
                "role": "user"
            }
        }
    )

class UserUpdate(BaseModel):
    """Schema for updating user details (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    
    # Reimplement the name validator for the update schema
    @field_validator('name', mode='before')
    @classmethod
    def validate_name(cls, v: Any) -> Optional[str]:
        if v is not None:
            if isinstance(v, str) and len(v.strip()) == 0:
                raise ValueError('Name cannot be empty')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Updated",
                "email": "john.updated@example.com"
            }
        }
    )


# --- Output Schemas ---

class UserOut(UserBase):
    """Schema for returning base user data (excludes password hash)"""
    id: UUID
    created_at: datetime
    # Inherits name, email, role from UserBase
    
    model_config = ConfigDict(
        from_attributes=True,
        # Pydantic V2 automatically handles Enum serialisation to string for output
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "role": "user",
                "created_at": "2024-02-01T10:00:00"
            }
        }
    )
    
class UserDetailOut(UserOut):
    """Extended user schema with statistics"""
    total_bookings: Optional[int] = Field(None, description="Total number of bookings made")
    total_reviews: Optional[int] = Field(None, description="Total number of reviews written")
    
    model_config = ConfigDict(
        from_attributes=True
    )

class UserProfile(UserOut):
    """Full user profile with related data"""
    upcoming_bookings_count: Optional[int] = Field(None, description="Number of upcoming bookings")
    completed_bookings_count: Optional[int] = Field(None, description="Number of completed bookings")
    
    model_config = ConfigDict(
        from_attributes=True
    )

class UserListResponse(BaseModel):
    """Schema for paginated user list response (admin only)"""
    users: list[UserOut]
    total: int = Field(..., description="Total number of users")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(10, description="Number of users per page")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [],
                "total": 150,
                "page": 1,
                "per_page": 10
            }
        }
    )
