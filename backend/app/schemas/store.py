from datetime import datetime

from pydantic import BaseModel


class StoreCreate(BaseModel):
    name: str
    code: str


class StoreOut(BaseModel):
    id: int
    name: str
    code: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierCreate(BaseModel):
    name: str


class SupplierOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
