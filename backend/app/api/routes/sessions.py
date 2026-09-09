from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.invoice import Invoice
from app.models.session import IntakeSession
from app.schemas.session import SessionItemUpdate, SessionOut
from app.services import session_service
from app.services.session_service import SessionValidationError

router = APIRouter(tags=["sessions"], dependencies=[Depends(get_current_user)])


def _get_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفاتورة غير موجودة")
    return invoice


def _get_session_or_404(db: Session, session_id: int) -> IntakeSession:
    session = db.get(IntakeSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جلسة الاستلام غير موجودة")
    return session


@router.post("/invoices/{invoice_id}/session", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)
    try:
        return session_service.create_session(db, invoice)
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    return _get_session_or_404(db, session_id)


@router.patch("/sessions/{session_id}/items/{item_id}", response_model=SessionOut)
def update_session_item(
    session_id: int, item_id: int, payload: SessionItemUpdate, db: Session = Depends(get_db)
):
    session = _get_session_or_404(db, session_id)
    try:
        session_service.update_session_item(db, session, item_id, payload.model_dump(exclude_unset=True))
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
def complete_session(session_id: int, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, session_id)
    try:
        return session_service.complete_session(db, session)
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
