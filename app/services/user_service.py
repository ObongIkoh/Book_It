from sqlalchemy.orm import Session
from app.repositories.user_repo import UserRepository
from app.db.models import User
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    DatabaseError
)
import uuid
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def get_me(self, user_id: uuid.UUID) -> User:
        """Get current user profile"""
        try:
            user = self.repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve user profile")

    def update_me(self, user_id: uuid.UUID, name: str = None, email: str = None) -> User:
        """Update current user profile"""
        try:
            # Get user
            user = self.repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User")
            
            # Prepare update data
            update_data = {}
            
            # Validate and add name
            if name is not None:
                name = name.strip()
                if len(name) == 0:
                    raise ValidationError("Name cannot be empty")
                if len(name) > 100:
                    raise ValidationError("Name cannot exceed 100 characters")
                update_data['name'] = name
            
            # Validate and add email
            if email is not None:
                email = email.strip().lower()
                if len(email) == 0:
                    raise ValidationError("Email cannot be empty")
                
                # Check if email is already taken by another user
                existing_user = self.repo.get_by_email(email)
                if existing_user and existing_user.id != user_id:
                    raise ConflictError("Email address is already in use")
                
                update_data['email'] = email
            
            # Check if there's anything to update
            if not update_data:
                raise ValidationError("No valid fields to update")
            
            # Update user
            updated_user = self.repo.update(user, update_data)
            logger.info(f"User {user_id} profile updated successfully")
            return updated_user
            
        except (ValidationError, NotFoundError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise DatabaseError("Failed to update user profile")

    def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Get any user by ID (admin use)"""
        try:
            user = self.repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve user")

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email"""
        try:
            return self.repo.get_by_email(email.strip().lower())
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            raise DatabaseError("Failed to retrieve user")

    def delete_account(self, user_id: uuid.UUID, password: str) -> bool:
        """Delete user account (requires password confirmation)"""
        try:
            # Get user
            user = self.repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User")
            
            # Verify password (you'll need to import AuthService or pwd_context)
            from app.services.auth_service import pwd_context
            if not pwd_context.verify(password, user.password_hash):
                raise ValidationError("Invalid password")
            
            # Delete user (will cascade delete bookings, reviews, etc.)
            self.repo.delete(user)
            logger.info(f"User account {user_id} deleted successfully")
            return True
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise DatabaseError("Failed to delete user account")

    def get_user_statistics(self, user_id: uuid.UUID) -> dict:
        """Get user activity statistics"""
        try:
            from app.repositories.booking_repo import BookingRepository
            from app.repositories.review_repo import ReviewRepository
            
            user = self.repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User")
            
            booking_repo = BookingRepository(self.db)
            review_repo = ReviewRepository(self.db)
            
            # Get booking counts
            all_bookings = booking_repo.get_user_bookings(user_id)
            total_bookings = len(all_bookings)
            completed_bookings = len([b for b in all_bookings if b.status.value == 'completed'])
            pending_bookings = len([b for b in all_bookings if b.status.value == 'pending'])
            
            # Get review count
            reviews = review_repo.get_reviews_by_user(user_id)
            total_reviews = len(reviews)
            
            return {
                'user_id': user_id,
                'total_bookings': total_bookings,
                'completed_bookings': completed_bookings,
                'pending_bookings': pending_bookings,
                'total_reviews': total_reviews,
                'member_since': user.created_at
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user statistics for {user_id}: {e}")
            raise DatabaseError("Failed to retrieve user statistics")

    def change_password(self, user_id: uuid.UUID, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            # Get user
            user = self.repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User")
            
            # Verify current password
            from app.services.auth_service import pwd_context
            if not pwd_context.verify(current_password, user.password_hash):
                raise ValidationError("Current password is incorrect")
            
            # Validate new password
            if len(new_password) < 6:
                raise ValidationError("New password must be at least 6 characters long")
            
            if current_password == new_password:
                raise ValidationError("New password must be different from current password")
            
            # Hash and update password
            new_password_hash = pwd_context.hash(new_password)
            self.repo.update(user, {'password_hash': new_password_hash})
            
            logger.info(f"Password changed successfully for user {user_id}")
            return True
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            raise DatabaseError("Failed to change password")