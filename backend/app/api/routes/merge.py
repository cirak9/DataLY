from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_invoice
from app.core.db import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceOut
from app.schemas.merge import MergeResult
from app.services import merge_service
from app.services.merge_service import MergeError

router = APIRouter(tags=["merge"], dependencies=[Depends(get_current_user)])


@router.post("/invoices/{invoice_id}/merge", response_model=MergeResult)
def merge_invoice(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    try:
        invoice, lots_upserted, catalog_learned = merge_service.merge_invoice(db, invoice)
    except MergeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return MergeResult(
        **InvoiceOut.model_validate(invoice).model_dump(),
        lots_upserted=lots_upserted,
        catalog_entries_learned=catalog_learned,
    )
