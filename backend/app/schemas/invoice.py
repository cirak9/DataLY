from datetime import datetime, date

from pydantic import BaseModel


class InvoiceOut(BaseModel):
    id: int
    store_id: int
    supplier_id: int | None
    supplier_name_raw: str | None
    method: int
    status: str
    original_filename: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    main: str
    sub: str

    model_config = {"from_attributes": True}


class InvoiceItemOut(BaseModel):
    id: int
    invoice_id: int
    item_order: int
    item_name: str
    category_id: int | None
    category: CategoryOut | None
    unit_text: str | None
    quantity_pieces: float
    per_box: int | None
    box_count: float | None
    unit_cost: float | None
    total_price: float | None
    discount_pct: float | None
    expiry_date: date | None
    supplier_item_code: str | None
    barcode: str | None

    model_config = {"from_attributes": True}


class InvoiceItemUpdate(BaseModel):
    item_name: str | None = None
    unit_cost: float | None = None
    total_price: float | None = None
    barcode: str | None = None
    expiry_date: date | None = None
