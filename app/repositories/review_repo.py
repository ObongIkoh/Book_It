from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.db.models import Review, Booking
from app.core.exceptions import DatabaseError, NotFoundError, ValidationError, ConflictError
from typing import Optional, List
import logging
import uuid

logger = logging.getLogger(__name__)

class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, review: Review) -> Review:
        """Create new review with error handling"""
        try:
            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)
            logger.info(f"Review created successfully for booking {review.booking_id}")
            return review
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error creating review: {e}")
            if "booking_id" in str(e.orig).lower():
                raise ConflictError("A review already exists for this booking")
            else:
                raise ValidationError("Review data conflicts with existing records")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating review: {e}")
            raise DatabaseError("Failed to create review")

    def create_from_dict(self, data: dict) -> Review:
        """Create review from dictionary with validation"""
        try:
            # Validate required fields
            required_fields = ['booking_id', 'rating']
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            if missing_fields:
                raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Validate rating range
            rating = data.get('rating')
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                raise ValidationError("Rating must be an integer between 1 and 5")
            
            # Validate booking_id is UUID
            booking_id = data.get('booking_id')
            if not isinstance(booking_id, uuid.UUID):
                raise ValidationError("Booking ID must be a UUID")
            
            # Check if booking exists and is completed
            booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                raise ValidationError("Booking not found")
            
            if booking.status != "completed":
                raise ValidationError("Can only review completed bookings")
            
            # Check if review already exists for this booking
            existing_review = self.get_by_booking_id(booking_id)
            if existing_review:
                raise ConflictError("A review already exists for this booking")
            
            review = Review(**data)
            return self.create(review)
            
        except (ValidationError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Error creating review from data: {e}")
            raise DatabaseError("Failed to create review")

    def get_by_id(self, review_id: int) -> Review | None:
        """Get review by ID with error handling - fixed to use int"""
        try:
            return self.db.query(Review).filter(Review.id == review_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting review by ID {review_id}: {e}")
            raise DatabaseError("Failed to retrieve review")

    def get_by_id_or_404(self, review_id: int) -> Review:
        """Get review by ID or raise NotFoundError"""
        review = self.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review")
        return review

    def get_by_booking_id(self, booking_id: int) -> Review | None:
        """Get review by booking ID - fixed to use int and return single review"""
        try:
            # Since booking_id is unique in reviews table, we expect only one review per booking
            return self.db.query(Review).filter(Review.booking_id == booking_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting review by booking ID {booking_id}: {e}")
            raise DatabaseError("Failed to retrieve review")

    def get_reviews_for_service(self, service_id: int) -> List[Review]:
        """Get all reviews for a specific service"""
        try:
            return self.db.query(Review).join(Booking).filter(
                Booking.service_id == service_id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting reviews for service {service_id}: {e}")
            raise DatabaseError("Failed to retrieve service reviews")

    def get_reviews_by_user(self, user_id: uuid.UUID) -> List[Review]:
        """Get all reviews written by a specific user"""
        try:
            return self.db.query(Review).join(Booking).filter(
                Booking.user_id == user_id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting reviews by user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve user reviews")

    def update(self, review: Review, data: dict) -> Review:
        """Update review with error handling and validation"""
        try:
            # Filter out None values and empty strings
            filtered_data = {k: v for k, v in data.items() if v is not None and v != ""}
            
            # Validate updatable fields
            valid_fields = {'rating', 'comment'}
            invalid_fields = set(filtered_data.keys()) - valid_fields
            if invalid_fields:
                logger.warning(f"Attempted to update invalid fields: {invalid_fields}")
                filtered_data = {k: v for k, v in filtered_data.items() if k in valid_fields}
            
            # Validate rating if being updated
            if 'rating' in filtered_data:
                rating = filtered_data['rating']
                if not isinstance(rating, int) or not (1 <= rating <= 5):
                    raise ValidationError("Rating must be an integer between 1 and 5")
            
            # Apply updates
            for key, value in filtered_data.items():
                setattr(review, key, value)
            
            self.db.commit()
            self.db.refresh(review)
            logger.info(f"Review updated successfully: {review.id}")
            return review
            
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating review {review.id}: {e}")
            raise DatabaseError("Failed to update review")

    def delete(self, review: Review) -> bool:
        """Delete review with error handling"""
        try:
            self.db.delete(review)
            self.db.commit()
            logger.info(f"Review deleted successfully: {review.id}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting review {review.id}: {e}")
            raise DatabaseError("Failed to delete review")

    def get_average_rating_for_service(self, service_id: uuid.UUID) -> float | None:
        """Get average rating for a service"""
        try:
            from sqlalchemy import func
            result = self.db.query(func.avg(Review.rating)).join(Booking).filter(
                Booking.service_id == service_id
            ).scalar()
            return float(result) if result is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting average rating for service {service_id}: {e}")
            raise DatabaseError("Failed to calculate average rating")

    def get_rating_distribution_for_service(self, service_id: uuid.UUID) -> dict:
        """Get rating distribution (count of each rating 1-5) for a service"""
        try:
            from sqlalchemy import func
            results = self.db.query(
                Review.rating, 
                func.count(Review.rating).label('count')
            ).join(Booking).filter(
                Booking.service_id == service_id
            ).group_by(Review.rating).all()
            
            # Initialize all ratings to 0
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for rating, count in results:
                distribution[rating] = count
                
            return distribution
        except SQLAlchemyError as e:
            logger.error(f"Database error getting rating distribution for service {service_id}: {e}")
            raise DatabaseError("Failed to get rating distribution")

    def get_recent_reviews(self, limit: int = 10) -> List[Review]:
        """Get most recent reviews across all services"""
        try:
            return self.db.query(Review).order_by(
                Review.created_at.desc()
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting recent reviews: {e}")
            raise DatabaseError("Failed to retrieve recent reviews")