from sqlalchemy.orm import Session
from app.db.models import Review
from typing import Optional, List
import uuid

class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, review: Review) -> Review:
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get_by_id(self, review_id: str) -> Review | None:
        return self.db.query(Review).filter(Review.id == review_id).first()

    def get_by_booking_id(self, booking_id: str) -> List[Review]:
        return self.db.query(Review).filter(Review.booking_id == booking_id).all()

    def update(self, review: Review, data: dict) -> Review:
        for key, value in data.items():
            setattr(review, key, value)
        self.db.commit()
        self.db.refresh(review)
        return review

    def delete(self, review: Review):
        self.db.delete(review)
        self.db.commit()
