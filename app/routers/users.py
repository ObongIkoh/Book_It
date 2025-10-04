from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from app.db.session import get_db
from app.repositories.user_repo import UserRepository
from app.schemas import service
from app.services.user_service import UserService
from app.schemas.user import UserUpdate, UserOut
from app.core.security import get_current_user
from app.db.models import User
import logging


from app.schemas.user import UserUpdate, UserOut, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
def get_me(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = UserService(db)
    return service.get_me(uuid.UUID(current_user.id))

@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = UserService(db)
    return service.update_me(uuid.UUID(current_user.id), payload.model_dump(exclude_unset=True))

@router.get("/me/profile", response_model=UserProfile)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get current user profile with statistics
    # Returns user info along with booking and review counts
    
    service = UserService(db)
    stats = service.get_user_statistics(current_user.id)
    return {
        **current_user.__dict__,
        "upcoming_bookings_count": stats.get("pending_bookings", 0),
        "completed_bookings_count": stats.get("completed_bookings", 0)
    }


@router.get("/me/statistics")
def get_my_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    # Get current user activity statistics
    # Returns:
    # - Total bookings
    # - Completed bookings
    # - Pending bookings
    # - Total reviews written
    # - Member since date

    service = UserService(db)
    return service.get_user_statistics(current_user.id)


# Password change schema
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@router.post("/me/change-password", status_code=status.HTTP_200_OK)
def change_password(payload: PasswordChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    # Change user password
    
    # - **current_password**: Current password for verification
    # - **new_password**: New password (min 6 characters)
    
    service = UserService(db)
    service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password
    )
    return {"message": "Password changed successfully"}


class AccountDeletion(BaseModel):
    password: str

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(payload: AccountDeletion, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
      
    # Delete user account
    # Requires password confirmation for security.
    # This action is irreversible and will delete:
    # - User account
    # - All bookings
    # - All reviews
    
    service = UserService(db)
    service.delete_account(
        user_id=current_user.id,
        password=payload.password
    )
    return {"message": "Account deleted successfully"}