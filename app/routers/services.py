from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.service_repo import ServiceRepository
from app.services.service_service import ServiceService
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceOut
from app.db.models import Service
from app.core.security import get_current_user

router = APIRouter(prefix="/services", tags=["services"])

@router.get("/", response_model=list[ServiceOut])
def list_services(q: str | None = None, price_min: float = 0, price_max: float = 1e10, active: bool | None = None, db: Session = Depends(get_db)):
    repo = ServiceRepository(db)
    service = ServiceService(repo)
    return service.list(q=q, price_min=price_min, price_max=price_max, active=active)

@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: str, db: Session = Depends(get_db)):
    repo = ServiceRepository(db)
    service = ServiceService(repo)
    return service.get(service_id)

@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = ServiceRepository(db)
    service_svc = ServiceService(repo)
    service = Service(**payload.model_dump())
    return service_svc.create(service, current_user)

@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(service_id: str, payload: ServiceUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = ServiceRepository(db)
    service_svc = ServiceService(repo)
    return service_svc.update(service_id, payload.model_dump(exclude_unset=True), current_user)

@router.delete("/{service_id}")
def delete_service(service_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    repo = ServiceRepository(db)
    service_svc = ServiceService(repo)
    return service_svc.delete(service_id, current_user)
