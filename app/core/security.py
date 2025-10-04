import os
import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.db import models
from app.db.session import get_db
from app.core.exceptions import AuthenticationError, ValidationError
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Use HTTPBearer instead of OAuth2PasswordBearer for better compatibility
security = HTTPBearer()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-prod")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Use passlib with bcrypt for better security and consistency
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: uuid.UUID | str, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token
    
    Args:
        subject: User ID (UUID or string)
        expires_delta: Optional custom expiration time
    
    Returns:
        JWT token string
    """
    try:
        now = datetime.utcnow()
        expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        jti = str(uuid.uuid4())  # Unique ID for this token
        
        payload = {
            "sub": str(subject),  # Convert UUID to string
            "iat": now,
            "exp": expire,
            "jti": jti,
            "type": "access"
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise

def create_refresh_token(subject: uuid.UUID | str, expires_delta: timedelta | None = None) -> tuple[str, str]:
    """
    Create a JWT refresh token with JTI for revocation tracking
    
    Args:
        subject: User ID (UUID or string)
        expires_delta: Optional custom expiration time
    
    Returns:
        Tuple of (token_string, jti)
    """
    try:
        now = datetime.utcnow()
        expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": str(subject),
            "iat": now,
            "exp": expire,
            "jti": jti,
            "type": "refresh"
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token, jti
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload dictionary
    
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise AuthenticationError("Invalid or expired token")

def hash_password(plain: str) -> str:
    """
    Hash a plain text password using bcrypt
    
    Args:
        plain: Plain text password
    
    Returns:
        Hashed password string
    """
    try:
        plain_bytes = plain.encode('utf-8')[:72]
        return pwd_context.hash(plain_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise ValidationError("Failed to process password")

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain text password against a hashed password
    
    Args:
        plain: Plain text password
        hashed: Hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain, hashed)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency to get the current authenticated user from JWT token
    
    Args:
        credentials: HTTPBearer credentials containing the token
        db: Database session
    
    Returns:
        Current authenticated User object
    
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Decode token
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_type: str = payload.get("type")
        
        if user_id_str is None:
            raise credentials_exception
        
        # Ensure it's an access token
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Convert user_id to UUID
        try:
            user_id = uuid.UUID(user_id_str)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid user ID format in token: {user_id_str}")
            raise credentials_exception
        
        # Check if access token JTI is revoked (optional - usually only refresh tokens are tracked)
        # If you want to track access token revocation too, uncomment:
        # if jti and db.query(models.RefreshToken).filter(
        #     models.RefreshToken.jti == jti,
        #     models.RefreshToken.revoked == True
        # ).first():
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Token has been revoked",
        #         headers={"WWW-Authenticate": "Bearer"},
        #     )
        
    except AuthenticationError:
        raise credentials_exception
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise credentials_exception
    
    # Get user from database
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            logger.warning(f"User not found for ID: {user_id}")
            raise credentials_exception
        return user
    except Exception as e:
        logger.error(f"Database error getting user: {e}")
        raise credentials_exception

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency to require admin role
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user if they are an admin
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def verify_refresh_token(token: str, db: Session) -> uuid.UUID:
    """
    Verify a refresh token and return the user ID
    
    Args:
        token: Refresh token string
        db: Database session
    
    Returns:
        User ID from the token
    
    Raises:
        AuthenticationError: If token is invalid or revoked
    """
    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        jti = payload.get("jti")
        token_type = payload.get("type")
        
        if not user_id_str or not jti:
            raise AuthenticationError("Invalid token payload")
        
        if token_type != "refresh":
            raise AuthenticationError("Invalid token type")
        
        # Check if token is revoked
        refresh_token = db.query(models.RefreshToken).filter(
            models.RefreshToken.jti == jti
        ).first()
        
        if not refresh_token:
            raise AuthenticationError("Token not found")
        
        if refresh_token.revoked:
            raise AuthenticationError("Token has been revoked")
        
        if refresh_token.expires_at <= datetime.utcnow():
            raise AuthenticationError("Token has expired")
        
        return uuid.UUID(user_id_str)
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Error verifying refresh token: {e}")
        raise AuthenticationError("Invalid refresh token")