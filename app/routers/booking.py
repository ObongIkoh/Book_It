from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.booking_repo import BookingRepository
from app.services.booking_service import BookingService
from app.db.models import Booking
from app.core.security import get_current_user
from app.schemas.booking import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = BookingRepository(db)
    service = BookingService(repo)
    booking = Booking(
        user_id=str(current_user.id),
        service_id=payload.service_id,
        start_time=payload.start_time,
        end_time=payload.end_time
    )
    return service.create_booking(booking)

@router.get("/", response_model=list[BookingOut])
def list_bookings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = BookingRepository(db)
    service = BookingService(repo)
    return service.list_bookings(str(current_user.id), current_user.role == "admin")

@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = BookingRepository(db)
    service = BookingService(repo)
    return service.get_booking(booking_id, str(current_user.id), current_user.role == "admin")
