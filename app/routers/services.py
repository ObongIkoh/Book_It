from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
import uuid


from app.db.session import get_db
from app.repositories.service_repo import ServiceRepository
from app.services.service_service import ServiceService
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceOut
from app.db.models import Service, User
from app.core.security import get_current_user, require_admin
import logging


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/services", tags=["services"])

@router.get("/", response_model=list[ServiceOut])
def list_services(q: str | None = None, 
                  price_min: float = 0, 
                  price_max: float = 1e10, active: bool | None = None, 
                  is_active: Optional[bool] = None,
                  duration_min: Optional[int] = None,
                  duration_max: Optional[int] = None,
                  db: Session = Depends(get_db)
                  ):
    service = ServiceService(db)
    return service.list(q=q, price_min=price_min, price_max=price_max, active=active, is_active=is_active, duration_min=duration_min, duration_max=duration_max)

@router.get("/active", response_model=List[ServiceOut])
def list_active_services(db: Session = Depends(get_db)):
    
    # Get only active services available for booking
    # Public endpoint - no authentication required
    
    service = ServiceService(db)
    return service.get_active_services()

@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ServiceService(db)
    return service.get(service_id)

@router.get("/search/{search_term}", response_model=List[ServiceOut])
def search_services(
    search_term: str,
    db: Session = Depends(get_db)
):
    # Search services by title
    # Public endpoint - no authentication required
    service = ServiceService(db)
    return service.search(search_term)

@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = ServiceService(db)
    return service.create(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        duration_minutes=payload.duration_minutes,
        is_active=payload.is_active,
        current_user=current_user
    )
    
@router.post("/{service_id}/toggle", response_model=ServiceOut)
def toggle_service_status(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    
    # Toggle service active status (Admin only)
    # Convenient endpoint to enable/disable service availability
    
    service = ServiceService(db)
    return service.toggle_active(service_id, current_user)


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(service_id: uuid.UUID, payload: ServiceUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = ServiceService(db)
    return service.update(
        service_id=service_id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        duration_minutes=payload.duration_minutes,
        is_active=payload.is_active,
        current_user=current_user
    )

@router.delete("/{service_id}")
def delete_service(service_id: uuid.UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = ServiceService(db)
    return service.delete(service_id, current_user)
