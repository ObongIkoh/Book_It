from sqlalchemy.orm import Session
from app.repositories.review_repo import ReviewRepository
from app.repositories.booking_repo import BookingRepository
from app.db.models import Review, Booking, User, BookingStatus
from app.core.exceptions import (
    ValidationError, 
    NotFoundError, 
    AuthorizationError, 
    ConflictError,
    DatabaseError
)
import uuid
import logging

logger = logging.getLogger(__name__)

class ReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReviewRepository(db)
        self.booking_repo = BookingRepository(db)

    def create(self, booking_id: uuid.UUID, rating: int, comment: str, user: User) -> Review:
        """Create a review for a completed booking with full validation"""
        try:
            # Validate rating
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                raise ValidationError("Rating must be an integer between 1 and 5")
            
            # Get booking
            booking = self.booking_repo.get_by_id(booking_id)
            if not booking:
                raise NotFoundError("Booking")
            
            # Check if user owns the booking
            if booking.user_id != user.id:
                raise AuthorizationError("You can only review your own bookings")
            
            # Check if booking is completed
            if booking.status != BookingStatus.completed:
                raise ValidationError("Can only review completed bookings")
            
            # Check for existing review
            existing_review = self.repo.get_by_booking_id(booking_id)
            if existing_review:
                raise ConflictError("A review already exists for this booking")
            
            # Create review
            review_data = {
                'booking_id': booking_id,
                'rating': rating,
                'comment': comment.strip() if comment else None
            }
            
            review = self.repo.create_from_dict(review_data)
            logger.info(f"Review created successfully for booking {booking_id} by user {user.id}")
            return review
            
        except (ValidationError, NotFoundError, AuthorizationError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating review: {e}")
            raise DatabaseError("Failed to create review")

    def get(self, review_id: uuid.UUID) -> Review:
        """Get review by ID"""
        try:
            review = self.repo.get_by_id(review_id)
            if not review:
                raise NotFoundError("Review")
            return review
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting review {review_id}: {e}")
            raise DatabaseError("Failed to retrieve review")

    def get_by_booking(self, booking_id: uuid.UUID) -> Review | None:
        """Get review for a specific booking"""
        try:
            return self.repo.get_by_booking_id(booking_id)
        except Exception as e:
            logger.error(f"Error getting review for booking {booking_id}: {e}")
            raise DatabaseError("Failed to retrieve review")

    def get_reviews_for_service(self, service_id: uuid.UUID):
        """Get all reviews for a service"""
        try:
            reviews = self.repo.get_reviews_for_service(service_id)
            
            # Calculate statistics
            if reviews:
                total = len(reviews)
                avg_rating = sum(r.rating for r in reviews) / total
                distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                for review in reviews:
                    distribution[review.rating] += 1
                
                return {
                    'reviews': reviews,
                    'total': total,
                    'average_rating': round(avg_rating, 2),
                    'rating_distribution': distribution
                }
            
            return {
                'reviews': [],
                'total': 0,
                'average_rating': None,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        except Exception as e:
            logger.error(f"Error getting reviews for service {service_id}: {e}")
            raise DatabaseError("Failed to retrieve service reviews")

    def update(self, review_id: uuid.UUID, rating: int = None, comment: str = None, user: User = None) -> Review:
        """Update a review"""
        try:
            # Get review
            review = self.repo.get_by_id(review_id)
            if not review:
                raise NotFoundError("Review")
            
            # Get booking to check ownership
            booking = self.booking_repo.get_by_id(review.booking_id)
            if not booking:
                raise NotFoundError("Associated booking")
            
            # Check authorization
            if booking.user_id != user.id:
                raise AuthorizationError("You can only update your own reviews")
            
            # Validate rating if provided
            if rating is not None:
                if not isinstance(rating, int) or not (1 <= rating <= 5):
                    raise ValidationError("Rating must be an integer between 1 and 5")
            
            # Prepare update data
            update_data = {}
            if rating is not None:
                update_data['rating'] = rating
            if comment is not None:
                update_data['comment'] = comment.strip() if comment else None
            
            if not update_data:
                raise ValidationError("No valid fields to update")
            
            updated_review = self.repo.update(review, update_data)
            logger.info(f"Review {review_id} updated successfully by user {user.id}")
            return updated_review
            
        except (ValidationError, NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating review {review_id}: {e}")
            raise DatabaseError("Failed to update review")

    def delete(self, review_id: uuid.UUID, user: User, is_admin: bool = False) -> bool:
        """Delete a review"""
        try:
            # Get review
            review = self.repo.get_by_id(review_id)
            if not review:
                raise NotFoundError("Review")
            
            # Get booking to check ownership
            booking = self.booking_repo.get_by_id(review.booking_id)
            if not booking:
                raise NotFoundError("Associated booking")
            
            # Check authorization
            if not is_admin and booking.user_id != user.id:
                raise AuthorizationError("You can only delete your own reviews")
            
            # Delete review
            self.repo.delete(review)
            logger.info(f"Review {review_id} deleted by {'admin' if is_admin else f'user {user.id}'}")
            return True
            
        except (NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting review {review_id}: {e}")
            raise DatabaseError("Failed to delete review")

    def get_user_reviews(self, user_id: uuid.UUID):
        """Get all reviews written by a user"""
        try:
            return self.repo.get_reviews_by_user(user_id)
        except Exception as e:
            logger.error(f"Error getting reviews for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve user reviews")

    def can_user_review_booking(self, booking_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """Check if a user can review a booking and return status"""
        try:
            booking = self.booking_repo.get_by_id(booking_id)
            if not booking:
                return {'can_review': False, 'reason': 'Booking not found'}
            
            if booking.user_id != user_id:
                return {'can_review': False, 'reason': 'Not your booking'}
            
            if booking.status != BookingStatus.completed:
                return {'can_review': False, 'reason': 'Booking not completed yet'}
            
            existing_review = self.repo.get_by_booking_id(booking_id)
            if existing_review:
                return {'can_review': False, 'reason': 'Review already exists'}
            
            return {'can_review': True, 'reason': None}
            
        except Exception as e:
            logger.error(f"Error checking review eligibility: {e}")
            return {'can_review': False, 'reason': 'System error'}