from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceOut
from app.schemas.merge import MergeResult
from app.services import merge_service
from app.services.merge_service import MergeError

router = APIRouter(tags=["merge"], dependencies=[Depends(get_current_user)])


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفاتورة غير موجودة")
    return invoice


@router.post("/invoices/{invoice_id}/merge", response_model=MergeResult)
def merge_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)
    try:
        invoice, lots_upserted, catalog_learned = merge_service.merge_invoice(db, invoice)
    except MergeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return MergeResult(
        **InvoiceOut.model_validate(invoice).model_dump(),
        lots_upserted=lots_upserted,
        catalog_entries_learned=catalog_learned,
    )
