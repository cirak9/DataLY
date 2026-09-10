from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_invoice, get_owned_store
from app.core.db import get_db
from app.core_logic.validators import InvoiceValidationError
from app.models.invoice import Invoice
from app.models.store import Store
from app.schemas.invoice import InvoiceOut
from app.schemas.ocr import OcrConfirmRequest, OcrExtractResponse
from app.services import ocr_service

router = APIRouter(tags=["ocr"], dependencies=[Depends(get_current_user)])


@router.post(
    "/stores/{store_id}/invoices/ocr", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED
)
async def upload_ocr_invoice(
    files: list[UploadFile], store: Store = Depends(get_owned_store), db: Session = Depends(get_db)
):
    contents = [(f.filename or "image", await f.read()) for f in files]
    try:
        return ocr_service.create_ocr_invoice(db, store.id, contents)
    except InvoiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/invoices/{invoice_id}/ocr-extract", response_model=OcrExtractResponse)
def extract_ocr_invoice(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    try:
        items = ocr_service.extract_items(db, invoice)
    except ocr_service.OcrNotConfiguredError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except InvoiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return OcrExtractResponse(invoice_id=invoice.id, items=items)


@router.post("/invoices/{invoice_id}/ocr-confirm", response_model=InvoiceOut)
def confirm_ocr_invoice(
    payload: OcrConfirmRequest,
    invoice: Invoice = Depends(get_owned_invoice),
    db: Session = Depends(get_db),
):
    try:
        return ocr_service.confirm_items(db, invoice, payload.items)
    except InvoiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
