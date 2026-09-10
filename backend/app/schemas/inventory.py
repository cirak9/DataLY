from datetime import datetime, date

from pydantic import BaseModel


class InventoryLotOut(BaseModel):
    id: int
    barcode: str
    item_name: str | None
    expiration_date: date | None
    quantity: float | None
    unit_cost: float | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryImportResult(BaseModel):
    rows_read: int
    lots_processed: int
