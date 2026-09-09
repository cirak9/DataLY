from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.invoice import Invoice, InvoiceItem
from app.models.reconciliation import ReconciliationMatch
from app.models.user import User
from app.schemas.reconciliation import ReconciliationDecision, ReconciliationMatchOut
from app.services import reconciliation_service
from app.services.reconciliation_service import ReconciliationError

router = APIRouter(tags=["reconciliation"], dependencies=[Depends(get_current_user)])


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفاتورة غير موجودة")
    return invoice


def _get_match_or_404(db: Session, match_id: int) -> ReconciliationMatch:
    match = db.get(ReconciliationMatch, match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التطابق غير موجود")
    return match


@router.get("/invoices/{invoice_id}/reconciliation-matches", response_model=list[ReconciliationMatchOut])
def list_reconciliation_matches(invoice_id: int, db: Session = Depends(get_db)):
    _get_invoice_or_404(db, invoice_id)
    return (
        db.query(ReconciliationMatch)
        .join(InvoiceItem, ReconciliationMatch.invoice_item_id == InvoiceItem.id)
        .filter(InvoiceItem.invoice_id == invoice_id)
        .all()
    )


@router.post("/reconciliation-matches/{match_id}/decide", response_model=ReconciliationMatchOut)
def decide_reconciliation_match(
    match_id: int,
    payload: ReconciliationDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = _get_match_or_404(db, match_id)
    try:
        return reconciliation_service.decide_match(
            db, match, payload.decision, payload.manual_name, current_user.id
        )
    except ReconciliationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
