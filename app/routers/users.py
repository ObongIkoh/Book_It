from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.schemas.user import UserUpdate, UserOut
from app.core.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
def get_me(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = UserRepository(db)
    service = UserService(repo)
    return service.get_me(str(current_user.id))

@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = UserRepository(db)
    service = UserService(repo)
    return service.update_me(str(current_user.id), payload.model_dump(exclude_unset=True))
