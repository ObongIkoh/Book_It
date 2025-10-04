from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid

from app.db.session import get_db
from app.repositories.booking_repo import BookingRepository
from app.services.booking_service import BookingService
from app.db.models import Booking, User
from app.core.security import get_current_user, require_admin
from app.schemas.booking import BookingCreate, BookingOut
import logging

from app.schemas.booking import BookingCreate, BookingOut, BookingUpdate, BookingStatus
from app.core.exceptions import NotFoundError, AuthorizationError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = BookingService(db)
    booking = service.create_booking(
        user_id=current_user.id,
        service_id=payload.service_id,
        start_time=payload.start_time
    )
    return booking

@router.get("/", response_model=list[BookingOut])
def list_bookings(
    status: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    from_date: Optional[datetime] = Query(None, description="Filter bookings from this date"),
    to_date: Optional[datetime] = Query(None, description="Filter bookings until this date"),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    List bookings
    
    - Regular users: See only their own bookings
    - Admins: See all bookings with optional filters
    """
    service = BookingService(db)
    
    # Convert enum to string if provided
    status_str = status.value if status else None
    
    bookings = service.list_bookings(
        user_id=current_user.id if current_user.role != "admin" else None,
        is_admin=current_user.role == "admin",
        status=status_str,
        from_date=from_date,
        to_date=to_date
    )
    return bookings

@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: uuid.UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific booking by ID
    
    - Users can only view their own bookings
    - Admins can view any booking
    """
    service = BookingService(db)
    booking = service.get_booking(
        booking_id=booking_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin"
    )
    return booking

@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: uuid.UUID,
    payload: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a booking
    
    - Users can reschedule or cancel their own pending/confirmed bookings
    - Admins can update any booking status
    """
    service = BookingService(db)
    
    # Convert enum to string if provided
    status_str = payload.status.value if payload.status else None
    
    booking = service.update_booking(
        booking_id=booking_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
        start_time=payload.start_time,
        status=status_str
    )
    return booking

@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a booking
    
    - Users can delete their own bookings before start time
    - Admins can delete any booking
    """
    service = BookingService(db)
    service.delete_booking(
        booking_id=booking_id,
        user_id=current_user.id,
        is_admin=current_user.role == "admin"
    )
    return

@router.get("/upcoming/me", response_model=list[BookingOut])
def get_my_upcoming_bookings(
    days_ahead: int = Query(30, ge=1, le=365, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's upcoming bookings
    """
    service = BookingService(db)
    return service.get_upcoming_bookings(
        user_id=current_user.id,
        days_ahead=days_ahead
    )