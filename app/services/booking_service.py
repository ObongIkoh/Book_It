from datetime import datetime
from app.db.models import Booking
from app.repositories.booking_repo import BookingRepository  # Ensure this file exists
from fastapi import HTTPException, status

class BookingService:
    def __init__(self, repo: BookingRepository):
        self.repo = repo

    def create_booking(self, booking: Booking):
        # Example: prevent overlapping bookings
        overlapping = (
            self.repo.db.query(Booking)
            .filter(
                Booking.service_id == booking.service_id,
                Booking.start_time < booking.end_time,
                Booking.end_time > booking.start_time
            ).first()
        )
        if overlapping:
            raise HTTPException(status_code=400, detail="Booking overlaps with existing one")
        return self.repo.create(booking)

    def get_booking(self, booking_id: str, user_id: str, admin: bool):
        booking = self.repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if not admin and booking.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return booking

    def list_bookings(self, user_id: str, admin: bool):
        return self.repo.get_all(user_id=user_id, admin=admin)

    def delete_booking(self, booking: Booking, user_id: str, admin: bool):
        if not admin and booking.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        self.repo.delete(booking)