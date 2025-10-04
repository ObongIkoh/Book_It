import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.repositories.user_repo import UserRepository
from app.repositories.token_repo import TokenRepo
from app.core.security import create_access_token
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError, 
    ValidationError, 
    DatabaseError,
    ConflictError
)
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return pwd_context.verify(plain, hashed)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def hash_password(self, password: str) -> str:
        try:
            if not password or len(password.strip()) < 6:
                raise ValidationError("Password must be at least 6 characters long")
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise DatabaseError("Failed to process password")

    def register(self, name: str, email: str, password: str):
        """Register a new user with proper error handling"""
        try:
            # Validate input
            if not name or not name.strip():
                raise ValidationError("Name is required")
            
            if not email or not email.strip():
                raise ValidationError("Email is required")
            
            name = name.strip()
            email = email.strip().lower()
            
            # Check if email already exists
            existing_user = self.user_repo.get_by_email(email)
            if existing_user:
                raise ConflictError("Email address is already registered")
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create user
            user = self.user_repo.create(
                name=name, 
                email=email, 
                password_hash=hashed_password
            )
            
            logger.info(f"User registered successfully: {email}")
            return user
            
        except (ValidationError, ConflictError) as e:
            # Re-raise our custom exceptions
            raise e
        except IntegrityError as e:
            logger.error(f"Database integrity error during registration: {e}")
            if "email" in str(e.orig).lower():
                raise ConflictError("Email address is already registered")
            else:
                raise DatabaseError("Failed to create user account")
        except SQLAlchemyError as e:
            logger.error(f"Database error during registration: {e}")
            raise DatabaseError("Failed to create user account")
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            raise DatabaseError("Failed to create user account")

    def login(self, email: str, password: str):
        """Login user with proper error handling"""
        try:
            if not email or not password:
                raise ValidationError("Email and password are required")
            
            email = email.strip().lower()
            
            # Get user
            user = self.user_repo.get_by_email(email)
            if not user:
                raise AuthenticationError("Invalid email or password")
            
            # Verify password
            if not self.verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid email or password")
            
            # Create tokens
            access = create_access_token(
                subject=user.id, 
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            # Create refresh token with JTI
            jti = str(uuid.uuid4())
            refresh_payload = {"sub": str(user.id), "jti": jti}
            refresh = jwt.encode({
                **refresh_payload, 
                "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            }, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            
            # Persist refresh token
            TokenRepo(self.db).create(
                jti=jti, 
                user_id=user.id, 
                expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            logger.info(f"User logged in successfully: {email}")
            return {"access": access, "refresh": refresh, "user": user}
            
        except (ValidationError, AuthenticationError) as e:
            raise e
        except SQLAlchemyError as e:
            logger.error(f"Database error during login: {e}")
            raise DatabaseError("Login failed due to system error")
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise DatabaseError("Login failed due to system error")

    def refresh(self, refresh_token: str):
        """Refresh access token with proper error handling"""
        try:
            if not refresh_token:
                raise ValidationError("Refresh token is required")
            
            # Decode token
            try:
                payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = int(payload.get("sub"))
                jti = payload.get("jti")
            except JWTError:
                raise AuthenticationError("Invalid refresh token")
            except (ValueError, TypeError):
                raise AuthenticationError("Malformed refresh token")
            
            # Check token in database
            repo = TokenRepo(self.db)
            token = repo.get(jti)
            if not token or token.revoked or token.expires_at <= datetime.utcnow():
                raise AuthenticationError("Refresh token expired or revoked")
            
            # Issue new access token
            access = create_access_token(
                subject=user_id, 
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            return {"access_token": access}
            
        except (ValidationError, AuthenticationError) as e:
            raise e
        except SQLAlchemyError as e:
            logger.error(f"Database error during token refresh: {e}")
            raise DatabaseError("Token refresh failed")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise DatabaseError("Token refresh failed")

    def logout(self, refresh_token: str):
        """Logout user with proper error handling"""
        try:
            if not refresh_token:
                raise ValidationError("Refresh token is required")
            
            # Decode token to get JTI
            try:
                payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                jti = payload.get("jti")
            except JWTError:
                raise AuthenticationError("Invalid refresh token")
            
            # Revoke token
            TokenRepo(self.db).revoke(jti)
            return True
            
        except (ValidationError, AuthenticationError) as e:
            raise e
        except SQLAlchemyError as e:
            logger.error(f"Database error during logout: {e}")
            raise DatabaseError("Logout failed")
        except Exception as e:
            logger.error(f"Unexpected error during logout: {e}")
            raise DatabaseError("Logout failed")