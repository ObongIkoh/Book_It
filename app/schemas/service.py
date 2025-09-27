from pydantic import BaseModel
from typing import Optional
import uuid

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    active: bool = True

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    active: Optional[bool] = None

class ServiceOut(ServiceBase):
    id: uuid.UUID

    class Config:
        from_attributes = True