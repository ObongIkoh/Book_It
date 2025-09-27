from fastapi import HTTPException, status
from app.repositories.service_repo import ServiceRepository

class ServiceService:
    def __init__(self, repo: ServiceRepository):
        self.repo = repo

    def get(self, service_id: str):
        service = self.repo.get_by_id(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return service

    def list(self, **filters):
        return self.repo.list(**filters)

    def create(self, service, current_user):
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        return self.repo.create(service)

    def update(self, service_id: str, data: dict, current_user):
        service = self.repo.get_by_id(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        return self.repo.update(service, data)

    def delete(self, service_id: str, current_user):
        service = self.repo.get_by_id(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        self.repo.delete(service)
        return {"detail": "Service deleted"}
