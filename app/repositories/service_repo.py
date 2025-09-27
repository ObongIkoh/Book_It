from sqlalchemy.orm import Session
from app.db.models import Service
from typing import Optional

class ServiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, service: Service) -> Service:
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def get_by_id(self, service_id: str) -> Service | None:
        return self.db.query(Service).filter(Service.id == service_id).first()

    def list(self, q: Optional[str] = None, price_min: float = 0, price_max: float = float("inf"), active: Optional[bool] = None):
        query = self.db.query(Service)
        if q:
            query = query.filter(Service.name.ilike(f"%{q}%"))
        query = query.filter(Service.price >= price_min, Service.price <= price_max)
        if active is not None:
            query = query.filter(Service.active == active)
        return query.all()

    def update(self, service: Service, data: dict) -> Service:
        for key, value in data.items():
            setattr(service, key, value)
        self.db.commit()
        self.db.refresh(service)
        return service

    def delete(self, service: Service):
        self.db.delete(service)
        self.db.commit()
