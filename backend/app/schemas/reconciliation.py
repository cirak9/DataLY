from datetime import datetime

from pydantic import BaseModel


class ReconciliationMatchOut(BaseModel):
    id: int
    invoice_item_id: int
    item_name: str
    match_method: str
    matched_barcode: str | None
    suggested_name: str | None
    suggested_category_id: int | None
    similarity_score: float | None
    warning_reason: str | None
    decision: str
    manual_name: str | None
    decided_at: datetime | None

    model_config = {"from_attributes": True}


class ReconciliationDecision(BaseModel):
    decision: str  # approve | reject | manual
    manual_name: str | None = None
