import os
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core_logic.alsahl_export import build_alsahl_workbook
from app.models.catalog import Category, ProductCatalog
from app.models.export import AlsahlExport
from app.models.invoice import Invoice, InvoiceItem
from app.models.session import IntakeSession

_TERMINAL_STATUSES = ("merged", "exported")


class ExportError(Exception):
    """يُرفع لما محاولة تصدير فاتورة تخالف حالتها."""
    pass


def _exports_dir(store_id: int) -> str:
    d = os.path.join(settings.storage_dir, "exports", str(store_id))
    os.makedirs(d, exist_ok=True)
    return d


def _resolve_export_category(db: Session, item: InvoiceItem, barcode: str | None) -> tuple[str, str]:
    """
    الباركود متوفّر هنا (بعد الدمج) — يتيح تصنيف مؤكد من الفهرس المشترك product_catalog
    بدل تخمين التصنيف المحفوظ على الصنف وقت التنظيف (ممكن يكون تغيّر لاحقاً بمتجر
    آخر عبر نفس الباركود). لو الباركود غير معروف بالفهرس، نرجع لتصنيف الصنف الحالي.
    """
    if barcode:
        entry = db.query(ProductCatalog).filter(ProductCatalog.barcode == barcode).first()
        if entry and entry.category_id:
            cat = db.get(Category, entry.category_id)
            if cat:
                return cat.main, cat.sub
    if item.category:
        return item.category.main, item.category.sub
    return "", ""


def export_invoice(db: Session, invoice: Invoice) -> AlsahlExport:
    """
    بديل export_to_alsahl(): يبني صف واحد لكل صنف بنفس ترتيب/تنسيق ملف Alsahl الأصلي
    بالضبط (نظام خارجي حقيقي يقرأ هذي الصيغة تحديداً). كل استدعاء يُنشئ سجل تصدير
    جديد (أرشيف كامل، بديل output_alsahl.xlsx المفرد اللي كان يُكتب فوقه بكل مرة) —
    التصدير المتكرر لنفس الفاتورة مسموح ومُتوقَّع (تنزيل الملف مرة ثانية مثلاً)، بس
    الحالة تنتقل لـexported أول مرة بس.
    """
    if invoice.status not in _TERMINAL_STATUSES:
        raise ExportError(f"لازم تكمل الدمج أولاً (الحالة الحالية: {invoice.status}) قبل التصدير.")

    session = db.query(IntakeSession).filter(IntakeSession.invoice_id == invoice.id).first()
    barcode_by_item = {si.invoice_item_id: si for si in (session.items if session else [])}

    rows = []
    for item in invoice.items:
        si = barcode_by_item.get(item.id)

        barcode = (si.barcode if si else None) or item.supplier_item_code or ""
        main_cat, sub_cat = _resolve_export_category(db, item, barcode or None)

        rows.append({
            "الكود": barcode,
            "الوصف": item.item_name,
            "العبوة": item.per_box if item.per_box else "",
            "العدد": float(item.quantity_pieces or 0),
            "التكلفة": float(item.unit_cost or 0),
            "البيع": float(si.sale_price) if si and si.sale_price is not None else 0.0,
            "الصلاحية": si.expiration_date.isoformat() if si and si.expiration_date else "",
            "المورد": invoice.supplier_name_raw or "",
            "فرعي": sub_cat,
            "رئيسي": main_cat,
            "الصندوق": "",
            "ب_الصندوق": "",
        })

    file_bytes = build_alsahl_workbook(rows)

    filename = f"{uuid.uuid4().hex}.xlsx"
    path = os.path.join(_exports_dir(invoice.store_id), filename)
    with open(path, "wb") as f:
        f.write(file_bytes)

    export = AlsahlExport(invoice_id=invoice.id, file_path=path)
    db.add(export)

    if invoice.status == "merged":
        invoice.status = "exported"

    db.commit()
    db.refresh(export)
    return export
