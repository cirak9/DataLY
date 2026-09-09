from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.session import IntakeSession


class MergeError(Exception):
    """يُرفع لما محاولة دمج فاتورة تخالف حالتها."""
    pass


# فريد بـ(store_id, barcode, COALESCE(expiration_date, ...)) — نفس تعريف الفهرس
# ux_inventory_lot بالضبط (app/models/inventory.py). قاعدة keep='last' الأصلية
# (InventoryManager.update_inventory(): drop_duplicates(subset=['barcode','expiration'],
# keep='last')) — أحدث فاتورة تحل محل بيانات نفس اللوت بالكامل، مو تراكم كمية.
_UPSERT_LOT_SQL = text("""
    INSERT INTO inventory_lots
        (store_id, barcode, item_name, expiration_date, quantity, unit_cost, last_invoice_item_id, updated_at)
    VALUES
        (:store_id, :barcode, :item_name, :expiration_date, :quantity, :unit_cost, :last_invoice_item_id, now())
    ON CONFLICT (store_id, barcode, COALESCE(expiration_date, DATE '9999-12-31'))
    DO UPDATE SET
        item_name = EXCLUDED.item_name,
        quantity = EXCLUDED.quantity,
        unit_cost = EXCLUDED.unit_cost,
        last_invoice_item_id = EXCLUDED.last_invoice_item_id,
        updated_at = now()
""")

# إدراج فقط لباركود جديد — بديل barcode_categories.learn_from_dataframe() المشروط
# بملف master_items.xlsx خارجي، هون يتراكم من كل فاتورة مباشرة (راجع ProductCatalog
# docstring). التسمية الأولى تتراكم بلا شرط؛ إعادة التسمية لباركود موجود أصلاً لازم
# تمر عبر reconciliation_matches (موافقة بشرية) — أبداً استبدال صامت هنا.
_LEARN_CATALOG_SQL = text("""
    INSERT INTO product_catalog (barcode, canonical_name, category_id, source_store_id, updated_at)
    VALUES (:barcode, :canonical_name, :category_id, :source_store_id, now())
    ON CONFLICT (barcode) DO NOTHING
""")


def merge_invoice(db: Session, invoice: Invoice) -> tuple[Invoice, int, int]:
    """
    بديل merge_invoice_and_session() + InventoryManager.update_inventory() +
    التعلّم من master_items.xlsx: هون الفاتورة والجلسة مربوطتين FK بجدول علائقي
    أصلاً (invoice_items/session_items)، فلا داعي لـpd.merge على item_id — نقرأ
    مباشرة ونكتب لـinventory_lots/product_catalog. يرجّع (الفاتورة، عدد لوتات
    اتحدّثت/انضافت، عدد أصناف جديدة انضافت لـproduct_catalog).
    """
    if invoice.status != "reconciled":
        raise MergeError(f"لازم تكمل التسوية أولاً (الحالة الحالية: {invoice.status}) قبل الدمج.")

    session = db.query(IntakeSession).filter(IntakeSession.invoice_id == invoice.id).first()
    if not session:
        raise MergeError("ما فيه جلسة استلام لهذي الفاتورة.")

    barcode_by_item = {si.invoice_item_id: si for si in session.items}

    lots_upserted = 0
    catalog_learned = 0

    for item in invoice.items:
        si = barcode_by_item.get(item.id)
        if not si or not si.barcode:
            continue

        db.execute(_UPSERT_LOT_SQL, {
            "store_id": invoice.store_id,
            "barcode": si.barcode,
            "item_name": item.item_name,
            "expiration_date": si.expiration_date,
            "quantity": item.quantity_pieces,
            "unit_cost": item.unit_cost,
            "last_invoice_item_id": item.id,
        })
        lots_upserted += 1

        result = db.execute(_LEARN_CATALOG_SQL, {
            "barcode": si.barcode,
            "canonical_name": item.item_name,
            "category_id": item.category_id,
            "source_store_id": invoice.store_id,
        })
        catalog_learned += result.rowcount

    invoice.status = "merged"
    db.commit()
    db.refresh(invoice)
    return invoice, lots_upserted, catalog_learned
