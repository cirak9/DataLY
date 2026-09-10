from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.invoice import Invoice, InvoiceItem
from app.models.reconciliation import ReconciliationMatch
from app.models.session import IntakeSession
from app.models.store import Store
from app.models.user import User

# tokenUrl هون بس لتوثيق Swagger (/docs) — تسجيل الدخول الفعلي عبر /auth/login بجسم JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="غير مصرّح — سجّل الدخول من جديد",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    email = decode_access_token(token)
    if not email:
        raise unauthorized
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise unauthorized
    return user


# عزل بيانات العملاء: كل ما تحته أدناه يتحقق من ملكية المستخدم الحالي قبل ما يرجّع
# أي صف — 404 (مو 403) لو المتجر/الفاتورة موجودة بس مملوكة لمستخدم ثاني، عشان ما
# نسرّب حتى معلومة "هذا الـID موجود" لمستخدم ما يملكه.

def get_owned_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Store:
    store = db.get(Store, store_id)
    if not store or store.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المتجر غير موجود")
    return store


def get_owned_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    invoice = (
        db.query(Invoice)
        .join(Store, Invoice.store_id == Store.id)
        .filter(Invoice.id == invoice_id, Store.owner_id == current_user.id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفاتورة غير موجودة")
    return invoice


def get_owned_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntakeSession:
    session = (
        db.query(IntakeSession)
        .join(Invoice, IntakeSession.invoice_id == Invoice.id)
        .join(Store, Invoice.store_id == Store.id)
        .filter(IntakeSession.id == session_id, Store.owner_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جلسة الاستلام غير موجودة")
    return session


def get_owned_reconciliation_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReconciliationMatch:
    match = (
        db.query(ReconciliationMatch)
        .join(InvoiceItem, ReconciliationMatch.invoice_item_id == InvoiceItem.id)
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .join(Store, Invoice.store_id == Store.id)
        .filter(ReconciliationMatch.id == match_id, Store.owner_id == current_user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التطابق غير موجود")
    return match
