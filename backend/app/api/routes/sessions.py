from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_invoice, get_owned_session
from app.core.db import get_db
from app.models.invoice import Invoice
from app.models.session import IntakeSession
from app.schemas.session import SessionItemUpdate, SessionOut
from app.services import session_service
from app.services.session_service import SessionValidationError

router = APIRouter(tags=["sessions"], dependencies=[Depends(get_current_user)])


@router.post("/invoices/{invoice_id}/session", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    try:
        return session_service.create_session(db, invoice)
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session: IntakeSession = Depends(get_owned_session)):
    return session


@router.get("/invoices/{invoice_id}/session", response_model=SessionOut)
def get_session_by_invoice(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    session = db.query(IntakeSession).filter(IntakeSession.invoice_id == invoice.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ما فيه جلسة استلام لهذي الفاتورة بعد")
    return session


@router.patch("/sessions/{session_id}/items/{item_id}", response_model=SessionOut)
def update_session_item(
    item_id: int,
    payload: SessionItemUpdate,
    session: IntakeSession = Depends(get_owned_session),
    db: Session = Depends(get_db),
):
    try:
        session_service.update_session_item(db, session, item_id, payload.model_dump(exclude_unset=True))
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
def complete_session(session: IntakeSession = Depends(get_owned_session), db: Session = Depends(get_db)):
    try:
        return session_service.complete_session(db, session)
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
