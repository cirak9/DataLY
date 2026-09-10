from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_invoice, get_owned_reconciliation_match
from app.core.db import get_db
from app.models.invoice import Invoice, InvoiceItem
from app.models.reconciliation import ReconciliationMatch
from app.models.user import User
from app.schemas.reconciliation import ReconciliationDecision, ReconciliationMatchOut
from app.services import reconciliation_service
from app.services.reconciliation_service import ReconciliationError

router = APIRouter(tags=["reconciliation"], dependencies=[Depends(get_current_user)])


@router.get("/invoices/{invoice_id}/reconciliation-matches", response_model=list[ReconciliationMatchOut])
def list_reconciliation_matches(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    return (
        db.query(ReconciliationMatch)
        .join(InvoiceItem, ReconciliationMatch.invoice_item_id == InvoiceItem.id)
        .filter(InvoiceItem.invoice_id == invoice.id)
        .all()
    )


@router.post("/reconciliation-matches/{match_id}/decide", response_model=ReconciliationMatchOut)
def decide_reconciliation_match(
    payload: ReconciliationDecision,
    match: ReconciliationMatch = Depends(get_owned_reconciliation_match),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return reconciliation_service.decide_match(
            db, match, payload.decision, payload.manual_name, current_user.id
        )
    except ReconciliationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
