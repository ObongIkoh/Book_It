from sqlalchemy.orm import Session
from app.db.models import Booking
from datetime import datetime

class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_by_id(self, booking_id: str) -> Booking | None:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

    def get_all(self, user_id: str | None = None, admin: bool = False):
        query = self.db.query(Booking)
        if not admin and user_id:
            query = query.filter(Booking.user_id == user_id)
        return query.all()

    def delete(self, booking: Booking):
        self.db.delete(booking)
        self.db.commit()