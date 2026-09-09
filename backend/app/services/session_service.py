from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.session import IntakeSession, SessionItem
from app.services import reconciliation_service


class SessionValidationError(Exception):
    """يُرفع لما محاولة إنشاء/تعديل/إكمال جلسة استلام تخالف حالة الفاتورة أو الجلسة."""
    pass


def _is_complete(barcode, expiration_date, sale_price) -> bool:
    return bool(barcode) and expiration_date is not None and sale_price is not None


def create_session(db: Session, invoice: Invoice) -> IntakeSession:
    """
    ينشئ جلسة استلام واحدة للفاتورة — بديل session_template.xlsx وتوزيعه يدوياً على
    التاجر (session/receiving_app.py الحالي). بالطريقة الثانية (method=2) الباركود/الصلاحية
    معروفين مسبقاً من مخزون المورد (InvoiceItem.barcode/expiry_date، تُعبّى وقت الإثراء —
    مو مبنية بعد بهالمرحلة)، فتُنسخ هون تلقائياً كتعبئة افتراضية للفورم — بديل
    enrich_invoice_from_supplier() الحالي. الطريقة الأولى تبدأ فاضية بالكامل.
    """
    existing = db.query(IntakeSession).filter(IntakeSession.invoice_id == invoice.id).first()
    if existing:
        raise SessionValidationError("جلسة استلام موجودة أصلاً لهذي الفاتورة.")

    if invoice.status != "cleaned":
        raise SessionValidationError(
            f"لازم تنظّف الفاتورة أولاً (الحالة الحالية: {invoice.status}) قبل ما تبدأ جلسة استلام."
        )

    session = IntakeSession(invoice_id=invoice.id, method=invoice.method, status="pending")
    db.add(session)
    db.flush()  # يحتاج session.id للأصناف تحت بدون commit كامل بعد

    for item in invoice.items:
        barcode = item.barcode if invoice.method == 2 else None
        expiry = item.expiry_date if invoice.method == 2 else None
        db.add(SessionItem(
            session_id=session.id,
            invoice_item_id=item.id,
            barcode=barcode,
            expiration_date=expiry,
            is_complete=_is_complete(barcode, expiry, None),
        ))

    invoice.status = "session_pending"
    db.commit()
    db.refresh(session)
    return session


def update_session_item(db: Session, session: IntakeSession, item_id: int, updates: dict) -> SessionItem:
    """
    تحديث صنف واحد بالجلسة. بالطريقة الثانية الباركود/الصلاحية مقفولين (معبّئين مسبقاً
    من مخزون المورد) — التاجر يعدّل سعر البيع بس، نفس قيد الفورم الأصلي بـreceiving_app.py.
    """
    session_item = (
        db.query(SessionItem)
        .filter(SessionItem.session_id == session.id, SessionItem.id == item_id)
        .first()
    )
    if not session_item:
        raise SessionValidationError("صنف الجلسة غير موجود.")

    if session.status == "complete":
        raise SessionValidationError("الجلسة مكتملة أصلاً — لا يمكن تعديل أصنافها.")

    if session.method == 2 and ({"barcode", "expiration_date"} & updates.keys()):
        raise SessionValidationError(
            "بالطريقة الثانية الباركود والصلاحية معبّأين مسبقاً من مخزون المورد — القابل للتعديل سعر البيع بس."
        )

    for field, value in updates.items():
        setattr(session_item, field, value)

    session_item.is_complete = _is_complete(
        session_item.barcode, session_item.expiration_date, session_item.sale_price
    )

    db.commit()
    db.refresh(session_item)
    return session_item


def complete_session(db: Session, session: IntakeSession) -> IntakeSession:
    """يقفل الجلسة بعد التأكد إن كل الأصناف مكتملة — بديل زر التحميل اللي كان يظهر
    بس بعد اكتمال كل الأصناف بـreceiving_app.py. مباشرة بعدها يطلق التسوية
    (reconciliation_service.generate_matches) — بديل استدعاء reconcile_dataframes()
    يدوياً بالخطوة التالية بـmain.py الأصلي، هون جزء من نفس فعل "إكمال الجلسة".
    """
    if session.status == "complete":
        raise SessionValidationError("الجلسة مكتملة أصلاً.")

    incomplete = [i for i in session.items if not i.is_complete]
    if incomplete:
        names = [i.item_name for i in incomplete[:5]]
        suffix = "..." if len(incomplete) > 5 else ""
        raise SessionValidationError(
            f"لسا فيه {len(incomplete)} صنف ناقص التعبئة: {names}{suffix}"
        )

    session.status = "complete"
    session.completed_at = datetime.now(timezone.utc)
    session.invoice.status = "session_complete"
    db.commit()
    db.refresh(session)

    try:
        reconciliation_service.generate_matches(db, session.invoice)
    except reconciliation_service.ReconciliationError as e:
        raise SessionValidationError(str(e))
    db.refresh(session)

    return session
