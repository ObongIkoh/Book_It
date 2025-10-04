from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.db.models import User
from app.core.exceptions import DatabaseError, NotFoundError, ConflictError
import logging
import uuid

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by ID with error handling"""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user by ID {user_id}: {e}")
            raise DatabaseError("Failed to retrieve user")

    def get_by_email(self, email: str) -> User | None:
        """Get user by email with error handling"""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user by email {email}: {e}")
            raise DatabaseError("Failed to retrieve user")

    def create(self, name: str, email: str, password_hash: str, role: str = "user") -> User:
        """Create new user with error handling"""
        try:
            user = User(
                name=name,
                email=email,
                password_hash=password_hash,
                role=role
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"User created successfully: {email}")
            return user
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error creating user {email}: {e}")
            if "email" in str(e.orig).lower():
                raise ConflictError("Email address is already registered")
            else:
                raise ConflictError("User data conflicts with existing records")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating user {email}: {e}")
            raise DatabaseError("Failed to create user account")

    def update(self, user: User, data: dict) -> User:
        """Update user with error handling and validation"""
        try:
            # Filter out None values and empty strings
            filtered_data = {k: v for k, v in data.items() if v is not None and v != ""}
            
            # Validate that we're not updating fields that don't exist
            valid_fields = {'name', 'email', 'role'}  # Add other updatable fields as needed
            invalid_fields = set(filtered_data.keys()) - valid_fields
            if invalid_fields:
                logger.warning(f"Attempted to update invalid fields: {invalid_fields}")
                filtered_data = {k: v for k, v in filtered_data.items() if k in valid_fields}
            
            # Apply updates
            for key, value in filtered_data.items():
                setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"User updated successfully: {user.email}")
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error updating user {user.id}: {e}")
            if "email" in str(e.orig).lower():
                raise ConflictError("Email address is already in use")
            else:
                raise ConflictError("User data conflicts with existing records")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating user {user.id}: {e}")
            raise DatabaseError("Failed to update user")

    def delete(self, user: User) -> bool:
        """Delete user with error handling"""
        try:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"User deleted successfully: {user.email}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting user {user.id}: {e}")
            raise DatabaseError("Failed to delete user")

    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email"""
        try:
            return self.db.query(User).filter(User.email == email).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking user existence by email {email}: {e}")
            raise DatabaseError("Failed to check user existence")

    def get_by_id_or_404(self, user_id: int) -> User:
        """Get user by ID or raise NotFoundError"""
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        return user