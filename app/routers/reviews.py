from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.review_repo import ReviewRepository
from app.services.review_service import ReviewService
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewOut
from app.db.models import Review, Booking
from app.core.security import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("/", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = ReviewRepository(db)
    service = ReviewService(repo, db)
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    review = Review(user_id=current_user.id, booking_id=payload.booking_id, rating=payload.rating, comment=payload.comment)
    return service.create(review, current_user, booking)

@router.get("/booking/{booking_id}", response_model=list[ReviewOut])
def get_reviews_by_booking(booking_id: str, db: Session = Depends(get_db)):
    repo = ReviewRepository(db)
    service = ReviewService(repo, db)
    return service.get_by_booking(booking_id)

@router.patch("/{review_id}", response_model=ReviewOut)
def update_review(review_id: str, payload: ReviewUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = ReviewRepository(db)
    service = ReviewService(repo, db)
    return service.update(review_id, payload.model_dump(exclude_unset=True), current_user)

@router.delete("/{review_id}")
def delete_review(review_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = ReviewRepository(db)
    service = ReviewService(repo, db)
    return service.delete(review_id, current_user, is_admin=(current_user.role=="admin"))
