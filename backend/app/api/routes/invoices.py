from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core_logic.validators import InvoiceValidationError
from app.models.invoice import Invoice, InvoiceItem
from app.models.store import Store
from app.schemas.invoice import InvoiceItemOut, InvoiceItemUpdate, InvoiceOut
from app.services import invoice_service

router = APIRouter(tags=["invoices"], dependencies=[Depends(get_current_user)])


def _get_store_or_404(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المتجر غير موجود")
    return store


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفاتورة غير موجودة")
    return invoice


@router.get("/stores/{store_id}/invoices", response_model=list[InvoiceOut])
def list_store_invoices(store_id: int, db: Session = Depends(get_db)):
    _get_store_or_404(db, store_id)
    return (
        db.query(Invoice)
        .filter(Invoice.store_id == store_id)
        .order_by(Invoice.uploaded_at.desc())
        .all()
    )


@router.post("/stores/{store_id}/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def upload_invoice(store_id: int, file: UploadFile, db: Session = Depends(get_db)):
    _get_store_or_404(db, store_id)
    content = await file.read()
    try:
        return invoice_service.save_uploaded_invoice(db, store_id, file.filename, content)
    except InvoiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return _get_invoice_or_404(db, invoice_id)


@router.post("/invoices/{invoice_id}/clean", response_model=InvoiceOut)
def clean_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)
    try:
        return invoice_service.clean_invoice(db, invoice)
    except InvoiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/invoices/{invoice_id}/items", response_model=list[InvoiceItemOut])
def list_invoice_items(invoice_id: int, db: Session = Depends(get_db)):
    _get_invoice_or_404(db, invoice_id)
    return (
        db.query(InvoiceItem)
        .filter(InvoiceItem.invoice_id == invoice_id)
        .order_by(InvoiceItem.item_order)
        .all()
    )


@router.patch("/invoices/{invoice_id}/items/{item_id}", response_model=InvoiceItemOut)
def update_invoice_item(
    invoice_id: int, item_id: int, payload: InvoiceItemUpdate, db: Session = Depends(get_db)
):
    item = (
        db.query(InvoiceItem)
        .filter(InvoiceItem.invoice_id == invoice_id, InvoiceItem.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الصنف غير موجود")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item
