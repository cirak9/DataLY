import io
import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core_logic.inventory_extractor import InventoryImportError, extract_old_inventory
from app.models.store import Store

SUPPORTED_EXCEL = {".xlsx", ".xls"}

# نفس تعريف الفهرس الفريد ux_inventory_lot بالضبط (store_id, barcode,
# COALESCE(expiration_date, ...)) — بديل drop_duplicates(subset=['barcode','expiration'],
# keep='last') بالأداة الأصلية. الاستيراد يحلّ محل بيانات اللوت الموجود بالضبط (اسم/كمية/
# تكلفة) لو نفس الباركود+الصلاحية موجودين مسبقاً — "الأحدث دايماً يفوز"، بالضبط زي قرار
# صاحب المشروع. last_invoice_item_id ما يتغيّر هنا عمداً (يبقى مرتبط بآخر فاتورة حقيقية
# مرّت على هذا اللوت عبر الدمج العادي — الاستيراد مو مرتبط بأي فاتورة بعينها).
_UPSERT_LOT_SQL = text("""
    INSERT INTO inventory_lots (store_id, barcode, item_name, expiration_date, quantity, unit_cost, updated_at)
    VALUES (:store_id, :barcode, :item_name, :expiration_date, :quantity, :unit_cost, now())
    ON CONFLICT (store_id, barcode, COALESCE(expiration_date, DATE '9999-12-31'))
    DO UPDATE SET
        item_name = EXCLUDED.item_name,
        quantity = COALESCE(EXCLUDED.quantity, inventory_lots.quantity),
        unit_cost = COALESCE(EXCLUDED.unit_cost, inventory_lots.unit_cost),
        updated_at = now()
""")


def import_old_inventory(db: Session, store: Store, filename: str, content: bytes) -> dict:
    """
    يستورد مخزون قديم (أول مرة للمتجر، أو لتغطية إضافات يدوية صارت من غير فاتورة عبرنا)
    ويدمجه بـinventory_lots — بديل InventoryManager.update_inventory() + save_updated_inventory()
    بالأداة الأصلية، هون upsert مباشر لقاعدة بيانات علائقية بدل DataFrame + كتابة ملف إكسل.
    يرجّع ملخّص: عدد الصفوف المقروءة والمعالَجة.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXCEL:
        raise InventoryImportError(f"نوع الملف غير مدعوم ({ext}) — الصيغ المدعومة: xlsx, xls")

    rows = extract_old_inventory(io.BytesIO(content))
    if not rows:
        return {"rows_read": 0, "lots_processed": 0}

    for row in rows:
        db.execute(_UPSERT_LOT_SQL, {
            "store_id": store.id,
            "barcode": row["barcode"],
            "item_name": row["item_name"],
            "expiration_date": row["expiration_date"],
            "quantity": row["quantity"],
            "unit_cost": row["unit_cost"],
        })

    db.commit()
    return {"rows_read": len(rows), "lots_processed": len(rows)}
