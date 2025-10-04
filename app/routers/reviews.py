from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
import uuid
from typing import Optional, List

from app.db.session import get_db
from app.repositories.review_repo import ReviewRepository
from app.services.review_service import ReviewService
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewOut
from app.db.models import Review, Booking
from app.core.security import get_current_user, require_admin


from app.schemas.review import ReviewListResponse
from app.db.models import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("/", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = ReviewService(db)
    with db.begin():
        booking = db.query(Booking).filter(Booking.id == payload.booking_id, Booking.user_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    review = Review(user_id=current_user.id, booking_id=payload.booking_id, rating=payload.rating, comment=payload.comment)
    return service.create(review, current_user, booking)

@router.get("/service/{service_id}", response_model=ReviewListResponse)
def get_service_reviews(
    service_id: uuid.UUID, 
    db: Session = Depends(get_db)
):
    #  Get all reviews for a specific service with statistics
        # Returns:
    # - List of reviews
    # - Total count
    # - Average rating
    # - Rating distribution (1-5 stars)
    
    service = ReviewService(db)
    result = service.get_reviews_for_service(service_id)
    return result


@router.get("/booking/{booking_id}", response_model=list[ReviewOut])
def get_reviews_by_booking(booking_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReviewService(db)
    reviews = service.get_reviews_by_booking(booking_id)
    if not reviews:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Review for this booking")
    return reviews

@router.get("/my-reviews", response_model=List[ReviewOut])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get all reviews written by the current user
    service = ReviewService(db)
    return service.get_user_reviews(current_user.id)

@router.get("/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: uuid.UUID,
    db: Session = Depends(get_db)
):
   
    # Get a specific review by ID
    service = ReviewService(db)
    return service.get(review_id)

@router.get("/can-review/{booking_id}")
def can_review_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if a user can review a specific booking
    # Returns eligibility status and reason if not eligible
    
    service = ReviewService(db)
    return service.can_user_review_booking(booking_id, current_user.id)

@router.patch("/{review_id}", response_model=ReviewOut)
def update_review(review_id: uuid.UUID, payload: ReviewUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = ReviewService(db)
    return service.update(review_id, rating=payload.rating, comment=payload.comment, current_user=current_user)

@router.delete("/{review_id}")
def delete_review(review_id: uuid.UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = ReviewService(db)
    return service.delete(review_id, current_user, is_admin=(current_user.role=="admin"))
