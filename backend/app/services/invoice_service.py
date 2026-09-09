import os
import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core_logic.base_cleaner import clean_data
from app.core_logic.excel_extractor import extract_from_excel
from app.core_logic.invoice_calc import calc_per_box, calc_total, calc_unit_cost
from app.core_logic.validators import InvoiceValidationError
from app.models.invoice import Invoice, InvoiceItem
from app.models.store import Supplier
from app.services import catalog_service

SUPPORTED_EXCEL = {".xlsx", ".xls"}


def _invoices_dir(store_id: int) -> str:
    d = os.path.join(settings.storage_dir, "invoices", str(store_id))
    os.makedirs(d, exist_ok=True)
    return d


def save_uploaded_invoice(db: Session, store_id: int, filename: str, content: bytes) -> Invoice:
    """
    يحفظ الملف المرفوع على القرص (أرشيف/تدقيق — راجع docs/REBUILD_PLAN.md قسم 2،
    "ملفان بس يبقيان" بالتصميم الجديد)، وينشئ صف Invoice بحالة "uploaded". التنظيف
    الفعلي (extract_from_excel + clean_data) يصير بخطوة منفصلة (POST /invoices/{id}/clean)
    عشان لو فشل التنظيف، الملف الخام يبقى محفوظ وتقدر تعيد المحاولة بدون رفع من جديد.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXCEL:
        raise InvoiceValidationError(f"نوع الملف غير مدعوم ({ext}) — الصيغ المدعومة: xlsx, xls")

    safe_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(_invoices_dir(store_id), safe_name)
    with open(path, "wb") as f:
        f.write(content)

    invoice = Invoice(
        store_id=store_id,
        method=1,  # الطريقة 2 (إثراء من مخزون مورد) تُضاف لاحقاً — راجع docs/REBUILD_PLAN.md
        status="uploaded",
        raw_file_path=path,
        original_filename=filename,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def _parse_expiry(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _get_or_create_supplier(db: Session, name: str) -> Supplier | None:
    name = (name or "").strip()
    if not name:
        return None
    supplier = db.query(Supplier).filter(Supplier.name == name).first()
    if supplier:
        return supplier
    supplier = Supplier(name=name)
    db.add(supplier)
    db.flush()  # يحتاج id بدون commit كامل بعد — لسا داخل نفس عملية التنظيف
    return supplier


def clean_invoice(db: Session, invoice: Invoice) -> Invoice:
    """
    يشغّل extract_from_excel + clean_data (منقولين حرفياً من الأداة الأصلية) على الملف
    المحفوظ، ويحفظ الأصناف بجدول invoice_items — بما فيها التصنيف (category_id) عبر
    catalog_service.get_category_id(). الباركود لسا مو معروف بهالمرحلة (يجي لاحقاً من
    جلسة استلام التاجر بالطريقة الأولى)، فالتصنيف هنا مبني على تخمين الاسم بس — نفس
    ترتيب الأولوية الأصلي، أولوية الباركود تُفعَّل تلقائياً لاحقاً وقت الدمج لما يصير معروف.
    """
    df_raw, supplier_name = extract_from_excel(invoice.raw_file_path)
    df_clean = clean_data(df_raw)  # يرفع InvoiceValidationError لو فيه مشكلة — تنعكس 422 بالـAPI

    supplier = _get_or_create_supplier(db, supplier_name)
    invoice.supplier_id = supplier.id if supplier else None
    invoice.supplier_name_raw = supplier_name or None

    # حذف أي أصناف من محاولة تنظيف سابقة فاشلة/معاد تشغيلها
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()

    for _, row in df_clean.iterrows():
        row_dict = row.to_dict()
        item_name = str(row_dict.get("item_name", "")).strip()
        category_id = catalog_service.get_category_id(
            db, item_name, category_hint=str(row_dict.get("category", "") or "")
        )
        item = InvoiceItem(
            invoice_id=invoice.id,
            item_order=int(row_dict.get("item_id", 0)),
            item_name=item_name,
            category_id=category_id,
            unit_text=str(row_dict.get("unit", "")).strip() or None,
            quantity_pieces=float(row_dict.get("boxes", 0) or 0),
            per_box=calc_per_box(row_dict),
            unit_cost=calc_unit_cost(row_dict),
            total_price=calc_total(row_dict),
            discount_pct=float(row_dict.get("discount_pct", 0) or 0) or None,
            expiry_date=_parse_expiry(str(row_dict.get("expiry_date", "") or "")),
            supplier_item_code=str(row_dict.get("supplier_item_code", "")).strip() or None,
        )
        db.add(item)

    invoice.status = "cleaned"
    db.commit()
    db.refresh(invoice)
    return invoice
