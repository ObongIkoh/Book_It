from fastapi import HTTPException, status
from app.repositories.review_repo import ReviewRepository
from app.db.models import Review, Booking
from sqlalchemy.orm import Session

class ReviewService:
    def __init__(self, repo: ReviewRepository, db: Session):
        self.repo = repo
        self.db = db

    def create(self, review: Review, user, booking: Booking):
        # only allow review for completed booking
        if booking.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not allowed for this booking")
        if booking.status != "completed":
            raise HTTPException(status_code=400, detail="Booking not completed")
        # one review per booking
        existing = self.repo.get_by_booking_id(str(booking.id))
        if existing:
            raise HTTPException(status_code=400, detail="Review already exists for this booking")
        return self.repo.create(review)

    def get(self, review_id: str):
        review = self.repo.get_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review

    def get_by_booking(self, booking_id: str):
        return self.repo.get_by_booking_id(booking_id)

    def update(self, review_id: str, data: dict, user):
        review = self.repo.get_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        if review.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return self.repo.update(review, data)

    def delete(self, review_id: str, user, is_admin=False):
        review = self.repo.get_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        if review.user_id != user.id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized")
        self.repo.delete(review)
        return {"detail": "Review deleted"}
