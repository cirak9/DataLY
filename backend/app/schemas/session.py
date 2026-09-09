from datetime import datetime, date

from pydantic import BaseModel


class SessionItemOut(BaseModel):
    id: int
    session_id: int
    invoice_item_id: int
    item_name: str
    unit_cost: float | None
    barcode: str | None
    expiration_date: date | None
    sale_price: float | None
    is_complete: bool

    model_config = {"from_attributes": True}


class SessionItemUpdate(BaseModel):
    barcode: str | None = None
    expiration_date: date | None = None
    sale_price: float | None = None


class SessionOut(BaseModel):
    id: int
    invoice_id: int
    method: int
    status: str
    created_at: datetime
    completed_at: datetime | None
    items: list[SessionItemOut]

    model_config = {"from_attributes": True}
