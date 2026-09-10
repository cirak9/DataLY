from pydantic import BaseModel


class OcrExtractedItem(BaseModel):
    source_image: int
    item_name: str
    quantity: float
    unit_cost: float
    barcode: str | None = None
    confidence: str  # "high" | "medium" | "low"


class OcrExtractResponse(BaseModel):
    invoice_id: int
    items: list[OcrExtractedItem]


class OcrConfirmItem(BaseModel):
    item_name: str
    quantity: float
    unit_cost: float
    barcode: str | None = None


class OcrConfirmRequest(BaseModel):
    items: list[OcrConfirmItem]
