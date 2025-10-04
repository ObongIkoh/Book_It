from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.schemas.auth import RegisterIn, LoginIn, Token
from app.db import models
from app.db.session import get_db
from app.core import security
from app.core.security import ALGORITHM, SECRET_KEY, get_current_user
from app.schemas.auth import RefreshTokenIn
from jose import JWTError, jwt  # Add this import for JWT handling
from datetime import timedelta
import logging


router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        # check existing email
        existing = db.query(models.User).filter(models.User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = security.hash_password(payload.password)
        user = models.User(
            name=payload.name,
            email=payload.email,
            password_hash=hashed,
            role="user"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": str(user.id), "email": user.email, "name": user.name}
    except IntegrityError:
        db.rollback()
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=400, detail="Database integrity error")
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Unexpected server error. Please try again later.")
        

@router.post("/login", response_model=Token)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )
    
    access = security.create_access_token(subject=str(user.id))
    refresh = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(days=7)  # or use REFRESH_TOKEN_EXPIRE_DAYS from .env
    )
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }


@router.get("/me", response_model=dict)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
    }
    
@router.post("/refresh", response_model=Token)
def refresh_token(payload: RefreshTokenIn):
    try:
        # Decode the refresh token
        data = jwt.decode(payload.refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id = data.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Issue a new access token
        access = security.create_access_token(subject=user_id)
        
        # Optionally, issue a new refresh token (or keep the old one)
        refresh_token = security.create_access_token(subject=user_id, expires_delta=timedelta(days=7))

        return {"access_token": access, "refresh_token": refresh_token, "token_type": "bearer"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=400, detail="Invalid token")
        revoked = models.RevokedToken(jti=jti)
        db.add(revoked)
        db.commit()
        return {"msg": "Successfully logged out"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")