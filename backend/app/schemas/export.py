from datetime import datetime

from pydantic import BaseModel


class AlsahlExportOut(BaseModel):
    id: int
    invoice_id: int
    exported_at: datetime

    model_config = {"from_attributes": True}
